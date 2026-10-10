"""Characterization of app/services/sync/transformers.py with SQL-Server-shaped rows."""
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from app.services.csv.row_models import (
    CombinedCSVRow,
    JobDescriptionCSVRow,
    SupervisorFeedbackCSVRow,
    VisionDataCSVRow,
)
from app.services.sync.transformers import (
    EmployeeReportTransformer,
    JobDescriptionTransformer,
    SupervisorFeedbackTransformer,
    VisionDataTransformer,
    _format_date,
)
from tests.golden.imports_sync.helpers import model_outcome, outcome, tag


def test_format_date(snapshot):
    cases = {
        "none": None,
        "date": date(2024, 3, 1),
        "datetime": datetime(2024, 3, 1, 23, 59, 59),
        "early_year": date(5, 1, 2),
        "string_passthrough": " 03/01/2024 ",
        "empty_string": "",
        "int": 20240301,
        "decimal": Decimal("20240301"),
        "time": time(10, 30),
        "bytes": b"2024-03-01",
        "float": 1.5,
    }
    snapshot("transformers_format_date", {k: outcome(lambda: _format_date(v)) for k, v in cases.items()})


EMP_SQL_ROWS = {
    "typical": {
        "Employee_ID": 101, "Name": "Ayesha Khan", "Designation": "Deputy Director", "BPS": "BS-18",
        "Office_Hierarchy": "Technical>Tech-I", "From": date(2024, 3, 1), "To": date(2024, 3, 31), "Draft": None,
        "Tasks_Completed": "Reviewed cases", "Impact": "High", "Challenges": None, "Support_Required": None,
        "Tasks_Planned": "Audit", "Confidence_Level": "4 - Confident", "NTR": None,
        "LastModifiedDate": datetime(2024, 4, 1, 8, 0, 0, 123000),
    },
    "datetimes_and_whitespace": {
        "Employee_ID": Decimal("102"), "Name": "  Bilal Ahmed  ", "Designation": "Officer ", "BPS": " BS-17",
        "Office_Hierarchy": None, "From": datetime(2024, 2, 1, 0, 0), "To": datetime(2024, 2, 29, 23, 59),
        "Tasks_Completed": "  Filed  ", "Confidence_Level": 3, "NTR": "",
    },
    "all_none": {k: None for k in ["Employee_ID", "Name", "Designation", "From", "To", "Tasks_Completed"]},
    "empty_dict": {},
    "string_dates_and_extra_columns": {
        "Employee_ID": "103", "Name": "Sara", "Designation": "Analyst", "From": "2024-01-01", "To": "01/31/2024",
        "Tasks_Completed": "x", "Unexpected": "dropped", "from": date(2020, 1, 1),
    },
    "ntr_only": {
        "Employee_ID": 104, "Name": "Usman Tariq", "Designation": "Director", "From": date(2024, 1, 1),
        "To": date(2024, 1, 31), "Tasks_Completed": None, "NTR": "On leave", "Confidence_Level": Decimal("2"),
    },
    "float_id_and_bad_types": {
        "Employee_ID": 105.0, "Name": "Zara", "Designation": "Officer", "From": 20240101, "To": time(9, 0),
        "Tasks_Completed": "x", "Confidence_Level": 4.0,
    },
}


@pytest.mark.parametrize("case", sorted(EMP_SQL_ROWS))
def test_employee_report_transformer(case, snapshot):
    out = EmployeeReportTransformer.transform(EMP_SQL_ROWS[case])
    snapshot(f"transformers_employee__{case}", {
        "transformed": tag(out), "key_order": list(out), "validated": model_outcome(CombinedCSVRow, out)})


VISION_SQL_ROWS = {
    "typical": {
        "Employee_ID": 101, "From_Date": date(2024, 4, 1), "To_Date": date(2024, 4, 30),
        "Main_Entity": "Activities and Cases", "Sub_Entities": "Cases:2, Activities:1",
        "Sub_Entities_Content": 'Cases:[{"id": 1}, {"id": 2}], Activities:[{"t": "raid"}]',
        "ModifiedDate": datetime(2024, 5, 1, 12, 0),
    },
    "datetimes_whitespace": {
        "Employee_ID": 102, "From_Date": datetime(2024, 4, 1, 8, 30), "To_Date": datetime(2024, 4, 30, 17, 0),
        "Main_Entity": "  Persons ", "Sub_Entities": " Persons:0 ", "Sub_Entities_Content": " Persons:[] ",
    },
    "nones": {"Employee_ID": None, "From_Date": None, "To_Date": None, "Main_Entity": None, "Sub_Entities": None,
              "Sub_Entities_Content": None},
    "empty_strings": {"Employee_ID": 103, "From_Date": date(2024, 4, 1), "To_Date": date(2024, 4, 30),
                      "Main_Entity": "Media", "Sub_Entities": "", "Sub_Entities_Content": ""},
    "decimal_id": {"Employee_ID": Decimal("104"), "From_Date": date(2024, 4, 1), "To_Date": date(2024, 4, 30),
                   "Main_Entity": "Tasks", "Sub_Entities": "Tasks:1", "Sub_Entities_Content": "Tasks:[{'a': 1,}]"},
    "empty_dict": {},
}


@pytest.mark.parametrize("case", sorted(VISION_SQL_ROWS))
def test_vision_data_transformer(case, snapshot):
    out = VisionDataTransformer.transform(VISION_SQL_ROWS[case])
    snapshot(f"transformers_vision__{case}", {
        "transformed": tag(out), "key_order": list(out), "validated": model_outcome(VisionDataCSVRow, out)})


JD_TEXT = "Leads the analysis team, prepares monthly performance summaries and coordinates with wings."
JD_SQL_ROWS = {
    "typical": {"Employee_ID": 101, "JD_ID": 1001, "Job_Description": JD_TEXT, "Assigned_Date": date(2024, 1, 15),
                "Is_Current": True, "End_Date": None, "LastModifiedDate": datetime(2024, 2, 1)},
    "ended_role_datetimes": {"Employee_ID": 102, "JD_ID": "1002", "Job_Description": "  " + JD_TEXT + "  ",
                             "Assigned_Date": datetime(2023, 6, 1, 9, 0), "Is_Current": False,
                             "End_Date": datetime(2024, 5, 31, 0, 0)},
    "bit_as_int_and_decimal_ids": {"Employee_ID": Decimal("103"), "JD_ID": Decimal("1003"),
                                   "Job_Description": JD_TEXT, "Assigned_Date": date(2023, 1, 1), "Is_Current": 0,
                                   "End_Date": None},
    "float_jd_id_and_null_bit": {"Employee_ID": 104, "JD_ID": 1004.0, "Job_Description": JD_TEXT,
                                 "Assigned_Date": "2023-01-01", "Is_Current": None, "End_Date": "NULL"},
    "nones": {k: None for k in ["Employee_ID", "JD_ID", "Job_Description", "Assigned_Date", "Is_Current", "End_Date"]},
    "empty_dict": {},
}


@pytest.mark.parametrize("case", sorted(JD_SQL_ROWS))
def test_job_description_transformer(case, snapshot):
    out = JobDescriptionTransformer.transform(JD_SQL_ROWS[case])
    snapshot(f"transformers_job_description__{case}", {
        "transformed": tag(out), "key_order": list(out), "validated": model_outcome(JobDescriptionCSVRow, out)})


SF_BASE = {
    "L_RO_Form_Metric_ID": 74, "RO_Form_ID": 15, "Employee_ID": 1012, "Name": "MAJ.(R) NADEEM ARIF CH",
    "Designation": "Director", "BPS": "BS-19", "Office_Hierarchy": "PPHQ>CI", "Executive_Office": "PPHQ",
    "From": date(2024, 11, 1), "To": date(2024, 11, 30), "Section_ID": 1, "Section": "Performance & Work Habits",
    "Metric_ID": 1, "Metric_Title": "Quality & Accuracy", "Instructions": "Ability to deliver",
    "Value": "Good", "Metric_Type": "R", "Possible_Values": "Poor,Fair,Good,Excellent",
    "LastModifiedDate": datetime(2024, 12, 1, 10, 0),
}
SF_SQL_ROWS = {
    "typical": SF_BASE,
    "datetimes": dict(SF_BASE, From=datetime(2024, 11, 1, 0, 0), To=datetime(2024, 11, 30, 0, 0)),
    "mixed_date_datetime": dict(SF_BASE, From=datetime(2024, 11, 1, 0, 0)),
    "text_metric_nulls": dict(SF_BASE, Metric_Type="T", Possible_Values=None, Value=None, Instructions=None,
                              Designation=None, BPS=None, Office_Hierarchy=None, Executive_Office=None),
    "decimal_ids_whitespace": dict(SF_BASE, RO_Form_ID=Decimal("15"), Employee_ID=Decimal("1012"),
                                   Value="  good ", Metric_Type=" R"),
    "string_dates": dict(SF_BASE, From="2024-11-01", To="11/30/2024"),
    "empty_dict": {},
}


@pytest.mark.parametrize("case", sorted(SF_SQL_ROWS))
def test_supervisor_feedback_transformer(case, snapshot):
    out = SupervisorFeedbackTransformer.transform(SF_SQL_ROWS[case])
    snapshot(f"transformers_supervisor__{case}", {
        "transformed": tag(out), "key_order": list(out), "validated": model_outcome(SupervisorFeedbackCSVRow, out)})


def test_transformers_do_not_mutate_input(snapshot):
    row = dict(EMP_SQL_ROWS["typical"])
    before = tag(row)
    EmployeeReportTransformer.transform(row)
    snapshot("transformers_input_untouched", {"unchanged": tag(row) == before,
                                              "non_dict_input": outcome(lambda: VisionDataTransformer.transform(None))})
