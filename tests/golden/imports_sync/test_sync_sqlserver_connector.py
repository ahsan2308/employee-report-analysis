"""Characterization of app/database/sqlserver_connector.py without any real connection.

``pyodbc`` inside the module is replaced by a fake whose ``connect`` hands out an
in-memory cursor that records SQL text and parameters.
"""
from datetime import datetime
from unittest.mock import MagicMock

import pyodbc as real_pyodbc
import pytest

from app.database import sqlserver_connector as mod
from app.database.sqlserver_connector import SQLServerConnector, create_sqlserver_connector
from tests.golden.imports_sync.helpers import outcome, tag

ENV_KEYS = [
    "SQLSERVER_HOST", "SQLSERVER_DATABASE", "SQLSERVER_USERNAME", "SQLSERVER_PASSWORD", "SQLSERVER_PORT",
    "SQLSERVER_USE_ENCRYPTION", "SQLSERVER_DRIVER", "SQLSERVER_ALLOWED_TABLES",
    "SQLSERVER_ALLOWED_TIMESTAMP_COLUMNS", "SQLSERVER_MAX_BATCH_SIZE",
]


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = None
        self._rows = []

    def execute(self, sql, *params):
        self.conn.log.append({"sql": " ".join(sql.split()), "params": tag(list(params))})
        result = self.conn.script.pop(0) if self.conn.script else {"columns": ["x"], "rows": [(1,)]}
        if isinstance(result, Exception):
            raise result
        self.description = [(c, None) for c in result["columns"]]
        self._rows = list(result["rows"])

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def fetchmany(self, n):
        rows, self._rows = self._rows[:n], self._rows[n:]
        return rows


class FakeConnection:
    def __init__(self, script, log):
        self.script, self.log = script, log
        self.closed = False
        self.timeout = None

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True
        self.log.append({"closed": True, "timeout_was": self.timeout})


@pytest.fixture
def fake_pyodbc(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    fake = MagicMock(name="pyodbc")
    fake.Error = real_pyodbc.Error
    fake.drivers.return_value = ["ODBC Driver 18 for SQL Server"]
    fake.log = []
    fake.script = []
    fake.connect_calls = []

    def connect(conn_str, timeout=None):
        fake.connect_calls.append({"conn_str": conn_str, "timeout": timeout})
        if fake.script and isinstance(fake.script[0], BaseException) and getattr(fake.script[0], "on_connect", False):
            raise fake.script.pop(0)
        return FakeConnection(fake.script, fake.log)

    fake.connect.side_effect = connect
    monkeypatch.setattr(mod, "pyodbc", fake)
    return fake


def _conn(**kw):
    base = dict(server="db.example.local", database="HRDB", username="sync_user", password="s3cret")
    base.update(kw)
    return SQLServerConnector(**base)


def _describe(c):
    return {
        "driver": c.driver, "port": c.port, "use_encryption": c.use_encryption,
        "connection_timeout": c.connection_timeout, "query_timeout": c.query_timeout,
        "allowed_tables": sorted(c.allowed_tables), "allowed_timestamp_columns": sorted(c.allowed_timestamp_columns),
        "max_batch_size": c.max_batch_size, "connection_string": c.connection_string,
    }


def test_driver_detection(fake_pyodbc, monkeypatch, snapshot):
    out = {}
    lists = {
        "none_installed": [],
        "only_18": ["ODBC Driver 18 for SQL Server"],
        "17_and_18_prefers_17": ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"],
        "native_client": ["SQL Server Native Client 11.0", "PostgreSQL Unicode"],
        "fallback_contains_sql_server": ["FreeTDS", "Custom SQL Server Bridge"],
        "unrelated_only": ["FreeTDS", "SQLite3"],
        "lowercase_name": ["odbc driver 17 for sql server"],
    }
    for name, drivers in lists.items():
        fake_pyodbc.drivers.return_value = drivers
        out[name] = outcome(lambda: _conn().driver)
    fake_pyodbc.drivers.return_value = []
    out["explicit_driver_skips_detection"] = outcome(lambda: _conn(driver="My Driver").driver)
    for env_value in ["FreeTDS", "auto", "AUTO", ""]:
        monkeypatch.setenv("SQLSERVER_DRIVER", env_value)
        fake_pyodbc.drivers.return_value = ["ODBC Driver 13 for SQL Server"]
        out[f"env_driver={env_value!r}"] = outcome(lambda: _conn().driver)
    snapshot("connector_driver_detection", out)


def test_env_config_parsing(fake_pyodbc, monkeypatch, snapshot):
    out = {"defaults": _describe(_conn())}
    monkeypatch.setenv("SQLSERVER_ALLOWED_TABLES", " EmployeeReports , ,Custom_Table,EmployeeReports,")
    monkeypatch.setenv("SQLSERVER_ALLOWED_TIMESTAMP_COLUMNS", "UpdatedAt,  RowVersion ")
    for size in ["500", "abc", "0", "-5", " 42 ", "1e3"]:
        monkeypatch.setenv("SQLSERVER_MAX_BATCH_SIZE", size)
        out[f"env_batch={size!r}"] = outcome(lambda: _describe(_conn()))
    monkeypatch.setenv("SQLSERVER_ALLOWED_TABLES", ",,")
    out["env_tables_only_commas"] = outcome(lambda: sorted(_conn().allowed_tables))
    out["explicit_overrides_env"] = outcome(lambda: _describe(_conn(
        allowed_tables={"A"}, allowed_timestamp_columns=set(), max_batch_size=0)))
    snapshot("connector_env_config", out)


def test_connection_param_validation_and_string(fake_pyodbc, snapshot):
    cases = {
        "named_instance": dict(server="localhost\\SQLEXPRESS"),
        "server_with_port_syntax": dict(server="10.0.0.5,1433"),
        "semicolon_server": dict(server="host;Trusted_Connection=yes"),
        "comment_dash": dict(database="HR--DB"),
        "sp_prefix_in_host": dict(server="dsp_host"),
        "xp_in_username": dict(username="exp_user"),
        "update_in_username": dict(username="update_svc"),
        "drop_lowercase_db": dict(database="dropzone"),
        "delete_in_db": dict(database="Deleted_Items"),
        "empty_server": dict(server=""),
        "none_username": dict(username=None),
        "int_database": dict(database=5),
        "long_server": dict(server="a" * 201),
        "server_200": dict(server="a" * 200),
        "password_with_semicolon": dict(password="p;w=d}"),
        "password_empty": dict(password=""),
        "port_and_no_encryption": dict(port=1433, use_encryption=False),
        "port_zero": dict(port=0),
        "port_string": dict(port="1433"),
        "timeouts": dict(connection_timeout=5, query_timeout=0),
    }
    snapshot("connector_params_and_connection_string",
             {k: outcome(lambda: _describe(_conn(**v))) for k, v in cases.items()})


def test_table_and_column_validation(fake_pyodbc, snapshot):
    c = _conn()
    tables = ["EmployeeReports", "employeereports", "VisionEmployeeData", "Users", "", "EmployeeReports;DROP"]
    columns = {
        "plain": ("LastModifiedDate", None),
        "plain_whitelisted": ("LastModifiedDate", c.allowed_timestamp_columns),
        "not_whitelisted": ("CreatedAt", c.allowed_timestamp_columns),
        "multi_column": ("RO_Form_ID, LastModifiedDate", None),
        "multi_with_direction": ("RO_Form_ID DESC", None),
        "space_in_name": ("Last Modified", None),
        "uppercase_update": ("UPDATED_AT", None),
        "mixedcase_update": ("UpdatedAt", c.allowed_timestamp_columns),
        "lowercase_drop": ("dropped_at", None),
        "parentheses": ("MAX(x)", None),
        "semicolon": ("x;y", None),
        "dash_comment": ("x--", None),
        "bracketed": ("[Name]", None),
        "unicode_letters": ("Datum_Änderung", None),
        "empty": ("", None),
        "trailing_comma": ("a,", None),
        "empty_whitelist_set": ("Anything", set()),
    }
    out = {
        "tables": {t: outcome(lambda: c._validate_table_name(t)) for t in tables},
        "columns": {k: outcome(lambda: c._validate_column_name(col, allowed)) for k, (col, allowed) in columns.items()},
    }
    c.add_allowed_table("Extra")
    c.remove_allowed_table("VisionEmployeeData")
    c.remove_allowed_table("NotThere")
    out["after_add_remove"] = {
        "get_allowed_tables": sorted(c.get_allowed_tables()),
        "ALLOWED_TABLES_is_live_set": c.ALLOWED_TABLES is c.allowed_tables,
        "get_allowed_tables_is_copy": c.get_allowed_tables() is not c.allowed_tables,
        "ALLOWED_TIMESTAMP_COLUMNS": sorted(c.ALLOWED_TIMESTAMP_COLUMNS),
        "class_default_untouched": sorted(SQLServerConnector.DEFAULT_ALLOWED_TABLES),
    }
    snapshot("connector_table_column_validation", out)


def _run(fake, fn, script=()):
    fake.log.clear()
    fake.connect_calls.clear()
    fake.script[:] = list(script)
    result = outcome(fn)
    return {"result": result, "sql_log": list(fake.log),
            "connect_timeouts": [call["timeout"] for call in fake.connect_calls]}


def test_query_building(fake_pyodbc, snapshot):
    c = _conn()
    since = datetime(2024, 5, 1, 12, 30, 0, 500000)
    rows5 = {"columns": ["Employee_ID", "LastModifiedDate"],
             "rows": [(i, datetime(2024, 5, 2, 0, 0, i)) for i in range(5)]}
    schema = {"columns": ["COLUMN_NAME", "DATA_TYPE"],
              "rows": [("Employee_ID", "int"), ("Name", "nvarchar"), ("ModifiedDate", "datetime2"),
                       ("LastModifiedDate", "datetime2")]}
    schema_no_ts = {"columns": ["COLUMN_NAME", "DATA_TYPE"], "rows": [("Employee_ID", "int")]}
    out = {
        "get_table_schema": _run(fake_pyodbc, lambda: c.get_table_schema("EmployeeReports"), [schema]),
        "get_table_schema_unauthorized": _run(fake_pyodbc, lambda: c.get_table_schema("sys.tables")),
        "records_since_default_order": _run(fake_pyodbc, lambda: list(c.get_records_since(
            "EmployeeReports", "LastModifiedDate", since, batch_size=2)), [rows5]),
        "records_since_custom_order": _run(fake_pyodbc, lambda: list(c.get_records_since(
            "SupervisorFeedback", "LastModifiedDate", since, batch_size=10, order_by="RO_Form_ID, LastModifiedDate")),
            [rows5]),
        "records_since_bad_column": _run(fake_pyodbc, lambda: list(c.get_records_since(
            "EmployeeReports", "CreatedAt", since))),
        "records_since_batch_zero": _run(fake_pyodbc, lambda: list(c.get_records_since(
            "EmployeeReports", "LastModifiedDate", since, batch_size=0))),
        "records_since_batch_too_big": _run(fake_pyodbc, lambda: list(c.get_records_since(
            "EmployeeReports", "LastModifiedDate", since, batch_size=10001))),
        "records_since_bad_order_by": _run(fake_pyodbc, lambda: list(c.get_records_since(
            "EmployeeReports", "LastModifiedDate", since, order_by="Name DESC"))),
        "all_records_schema_ts": _run(fake_pyodbc, lambda: list(c.get_all_records("VisionEmployeeData", batch_size=3)),
                                      [schema, rows5]),
        "all_records_no_ts": _run(fake_pyodbc, lambda: list(c.get_all_records("VisionEmployeeData")),
                                  [schema_no_ts, rows5]),
        "all_records_order_by": _run(fake_pyodbc, lambda: list(c.get_all_records(
            "EmployeeJobDescriptions", order_by="Employee_ID")), [schema, {"columns": ["a"], "rows": []}]),
        "record_count_plain": _run(fake_pyodbc, lambda: c.get_record_count("EmployeeReports"),
                                   [{"columns": [""], "rows": [(42,)]}]),
        "record_count_param": _run(fake_pyodbc, lambda: c.get_record_count(
            "EmployeeReports", "Employee_ID = ?", (5,)), [{"columns": [""], "rows": [(1,)]}]),
        "record_count_no_params_eq": _run(fake_pyodbc, lambda: c.get_record_count("EmployeeReports", "Name = 'x'")),
        "record_count_is_null_no_params": _run(fake_pyodbc, lambda: c.get_record_count(
            "EmployeeReports", "NTR IS NULL"), [{"columns": [""], "rows": [(3,)]}]),
        "record_count_update_substring": _run(fake_pyodbc, lambda: c.get_record_count(
            "EmployeeReports", "LastUpdated > ?", (since,))),
        "record_count_exec_substring": _run(fake_pyodbc, lambda: c.get_record_count(
            "EmployeeReports", "ExecutiveOffice = ?", ("PPHQ",))),
        "max_timestamp": _run(fake_pyodbc, lambda: c.get_max_timestamp("EmployeeReports", "LastModifiedDate"),
                              [{"columns": [""], "rows": [(since,)]}]),
        "max_timestamp_empty": _run(fake_pyodbc, lambda: c.get_max_timestamp("EmployeeReports", "ModifiedDate"),
                                    [{"columns": [""], "rows": [(None,)]}]),
        "execute_select": _run(fake_pyodbc, lambda: c.execute_query("SELECT Name FROM EmployeeReports"),
                               [{"columns": ["Name"], "rows": [("A",), ("B",)]}]),
        "execute_select_no_fetch": _run(fake_pyodbc, lambda: c.execute_query("select 1", fetch_all=False)),
        "execute_where_without_params": _run(fake_pyodbc, lambda: c.execute_query("SELECT * FROM T WHERE a = 1")),
        "execute_where_with_params": _run(fake_pyodbc, lambda: c.execute_query("SELECT * FROM T WHERE a = ?", (1,)),
                                          [{"columns": ["a"], "rows": [(1,)]}]),
        "execute_non_select": _run(fake_pyodbc, lambda: c.execute_query("WITH x AS (SELECT 1) SELECT * FROM x")),
        "execute_created_at_column": _run(fake_pyodbc, lambda: c.execute_query("SELECT CreatedAt FROM T")),
        "execute_semicolon_batch": _run(fake_pyodbc, lambda: c.execute_query("SELECT 1; SELECT 2")),
    }
    snapshot("connector_query_building", out)


def test_connection_handling(fake_pyodbc, snapshot):
    c = _conn(connection_timeout=7, query_timeout=99)
    connect_error = real_pyodbc.OperationalError("08001", "login timeout")
    connect_error.on_connect = True
    out = {
        "test_connection_ok": _run(fake_pyodbc, c.test_connection, [{"columns": [""], "rows": [(1,)]}]),
        "test_connection_wrong_value": _run(fake_pyodbc, c.test_connection, [{"columns": [""], "rows": [(2,)]}]),
        "test_connection_connect_fails": _run(fake_pyodbc, c.test_connection, [connect_error]),
        "query_error_wrapped": _run(fake_pyodbc, lambda: c.get_table_schema("EmployeeReports"),
                                    [real_pyodbc.ProgrammingError("42S02", "Invalid object")]),
        "query_error_non_pyodbc": _run(fake_pyodbc, lambda: c.get_table_schema("EmployeeReports"),
                                       [RuntimeError("driver crashed")]),
    }
    connect_error2 = real_pyodbc.InterfaceError("IM002", "no driver")
    connect_error2.on_connect = True
    out["schema_connect_fails"] = _run(fake_pyodbc, lambda: c.get_table_schema("EmployeeReports"), [connect_error2])
    snapshot("connector_connection_handling", out)


def test_create_from_env(fake_pyodbc, monkeypatch, snapshot):
    out = {"all_defaults": outcome(lambda: _describe(create_sqlserver_connector()))}
    c = create_sqlserver_connector()
    out["all_defaults_identity"] = {"server": c.server, "database": c.database, "username": c.username,
                                    "password_is_empty": c.password == ""}
    envs = {
        "full": {"SQLSERVER_HOST": "sql.prod", "SQLSERVER_DATABASE": "Prod", "SQLSERVER_USERNAME": "reader",
                 "SQLSERVER_PASSWORD": "pw", "SQLSERVER_PORT": "1444", "SQLSERVER_USE_ENCRYPTION": "TRUE"},
        "encryption_false": {"SQLSERVER_USE_ENCRYPTION": "false"},
        "encryption_zero": {"SQLSERVER_USE_ENCRYPTION": "0"},
        "encryption_yes": {"SQLSERVER_USE_ENCRYPTION": "yes"},
        "port_empty": {"SQLSERVER_PORT": ""},
        "port_text": {"SQLSERVER_PORT": "abc"},
        "host_with_sp_": {"SQLSERVER_HOST": "sp_server"},
    }
    for name, env in envs.items():
        for key in ENV_KEYS:
            monkeypatch.delenv(key, raising=False)
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        out[name] = outcome(lambda: _describe(create_sqlserver_connector()))
    snapshot("connector_create_from_env", out)


def test_no_real_connection_attempted(fake_pyodbc):
    fake_pyodbc.script[:] = [{"columns": ["COLUMN_NAME", "DATA_TYPE"], "rows": [("Name", "nvarchar")]}]
    assert _conn().get_table_schema("EmployeeReports") == {"Name": "nvarchar"}
    assert isinstance(mod.pyodbc, MagicMock)
    assert fake_pyodbc.connect.called
