"""The database contract: tables, columns, constraints and indexes declared on Base.metadata."""
from sqlalchemy.sql import ClauseElement

import app.models  # noqa: F401  (registers every model)
from app.db.base import Base


def _default(default):
    if default is None:
        return None
    arg = default.arg
    if isinstance(arg, ClauseElement):
        return f"sql:{arg}"
    if callable(arg):
        return f"callable:{getattr(arg, '__qualname__', getattr(arg, '__name__', 'fn'))}"
    return repr(arg)


def _column(column):
    return {
        "type": str(column.type),
        "nullable": column.nullable,
        "primary_key": column.primary_key,
        "unique": column.unique,
        "index": column.index,
        "default": _default(column.default),
        "server_default": str(column.server_default.arg) if column.server_default is not None else None,
        "foreign_keys": sorted(fk.target_fullname for fk in column.foreign_keys),
    }


def test_metadata(snapshot):
    tables = {}
    for table in Base.metadata.sorted_tables:
        tables[table.fullname] = {
            "columns": {column.name: _column(column) for column in table.columns},
            "constraints": sorted(
                f"{type(c).__name__}:{c.name}:{','.join(col.name for col in c.columns)}"
                for c in table.constraints if hasattr(c, "columns")
            ),
            "indexes": sorted(
                f"{index.name}:{','.join(col.name for col in index.columns)}:unique={index.unique}"
                for index in table.indexes
            ),
        }
    snapshot("orm_metadata", {"schema": Base.metadata.schema, "tables": tables})


def test_model_registry(snapshot):
    snapshot("model_registry", sorted(
        f"{mapper.class_.__module__}.{mapper.class_.__name__} -> {mapper.local_table.fullname}"
        for mapper in Base.registry.mappers
    ))


def test_database_import_registers_every_model(run_probe, snapshot):
    """get_database().create_tables() in a standalone script must create every table."""
    snapshot("tables_after_database_import", run_probe("tables_after_database_import", {}))
