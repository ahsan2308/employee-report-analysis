"""Characterization of the CSV row models in app/schemas/csv_import_schema.py.

Every date-bearing field runs the same table of date inputs, so the duplicated
parse cascades are locked side by side. Future dates use 2099 and past dates
use <= 2024 so results do not depend on today's date; the only today-dependent
text ("Today is YYYY-MM-DD") is scrubbed.
"""
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.services.csv.row_models import (
    CombinedCSVRow,
    JobDescriptionCSVRow,
    SupervisorFeedbackCSVRow,
    VisionDataCSVRow,
    _json_list_with_fixes,
    _top_level_split,
)
from app.schemas.csv_import_schema import (
    CSVImportJobCreate,
    CSVImportJobResponse,
    CSVImportOptions,
    ImportErrorResponse,
    ImportErrorsResponse,
)
from tests.golden.imports_sync.helpers import model_outcome, outcome

# ---------------------------------------------------------------------------
# Shared date table
# ---------------------------------------------------------------------------
DATE_CASES = {
    "iso": "2024-03-01",
    "iso_whitespace": "  2024-03-01  ",
    "iso_single_digit_parts": "2024-3-1",
    "iso_invalid_month": "2024-13-01",
    "iso_slashes_year_first": "2024/03/01",
    "us_mm_dd_ambiguous": "03/01/2024",
    "us_single_digits": "3/1/2024",
    "dd_mm_fallback": "13/02/2024",
    "mm_dd_unambiguous": "02/13/2024",
    "slash_both_invalid": "31/31/2024",
    "slash_feb_30": "02/30/2024",
    "slash_two_digit_year": "03/01/24",
    "dash_mm_dd_yyyy": "03-01-2024",
    "dash_dd_mm_yyyy": "13-02-2024",
    "dash_invalid": "31-31-2024",
    "dash_iso_with_time": "2024-03-01 10:30:00",
    "iso_t_time": "2024-03-01T10:30:00",
    "compact_no_separator": "20240301",
    "text_month": "March 1, 2024",
    "dotted": "01.03.2024",
    "empty": "",
    "spaces_only": "   ",
    "na_token": "N/A",
    "null_token": "null",
    "dash_token": "-",
    "none": None,
    "future_iso": "2099-01-01",
    "future_slash": "01/01/2099",
    "future_dash": "01-01-2099",
    "old_iso": "1965-01-01",
    "old_slash": "01/01/1965",
    "date_obj": date(2024, 3, 1),
    "datetime_obj": datetime(2024, 3, 1, 10, 30),
    "future_date_obj": date(2099, 1, 1),
    "old_date_obj": date(1965, 1, 1),
    "int": 20240301,
}


def _date_table(model_cls, base: dict, field: str):
    return {name: model_outcome(model_cls, {**base, field: value}) for name, value in DATE_CASES.items()}


# ---------------------------------------------------------------------------
# CombinedCSVRow
# ---------------------------------------------------------------------------
COMBINED_BASE = {
    "Employee_ID": "101",
    "Name": "Ayesha Khan",
    "Designation": "Deputy Director",
    "BPS": "BS-18",
    "Office_Hierarchy": "Technical>Tech-I>SOC",
    "From": "2020-01-01",
    "To": "2024-12-31",
    "Draft": None,
    "Tasks_Completed": "Reviewed 12 cases",
    "Impact": "Faster turnaround",
    "Challenges": None,
    "Support_Required": None,
    "Tasks_Planned": "Audit",
    "Confidence_Level": "4 - Confident",
    "NTR": None,
}


@pytest.mark.parametrize("field", ["From", "To"])
def test_combined_row_dates(field, snapshot):
    snapshot(f"schema_combined_dates__{field}", _date_table(CombinedCSVRow, COMBINED_BASE, field))


def test_combined_row_same_value_both_dates(snapshot):
    out = {name: model_outcome(CombinedCSVRow, {**COMBINED_BASE, "From": v, "To": v}) for name, v in DATE_CASES.items()}
    snapshot("schema_combined_dates__both_same", out)


COMBINED_CASES = {
    "valid_base": {},
    "extra_columns_ignored": {"Extra_Notes": "x", "department": "Given"},
    "employee_id_int": {"Employee_ID": 101},
    "employee_id_float_integral": {"Employee_ID": 101.0},
    "employee_id_float_string": {"Employee_ID": "101.0"},
    "employee_id_none": {"Employee_ID": None},
    "employee_id_text": {"Employee_ID": "abc"},
    "employee_id_negative": {"Employee_ID": "-5"},
    "employee_id_decimal": {"Employee_ID": Decimal("101")},
    "name_missing": {"Name": None},
    "name_one_char": {"Name": "A"},
    "name_whitespace_padded": {"Name": "  Ayesha Khan  "},
    "name_spaces_only": {"Name": "    "},
    "name_with_brackets_quotes": {"Name": "O'Brien [Acting] (Sr.)"},
    "name_unicode": {"Name": "José Muñoz"},
    "name_html": {"Name": "<script>x</script>"},
    "name_ampersand": {"Name": "Ali & Sons"},
    "name_101_chars": {"Name": "A" * 101},
    "designation_short": {"Designation": "X"},
    "bps_lowercase": {"BPS": "bs-17"},
    "bps_ts": {"BPS": "TS-16"},
    "bps_no_dash": {"BPS": "BS17"},
    "bps_empty": {"BPS": ""},
    "bps_na": {"BPS": "N/A"},
    "office_no_separator": {"Office_Hierarchy": "  Ops  "},
    "office_none": {"Office_Hierarchy": None},
    "office_leading_separator": {"Office_Hierarchy": ">Tech"},
    "confidence_plain": {"Confidence_Level": "3"},
    "confidence_int": {"Confidence_Level": 3},
    "confidence_zero": {"Confidence_Level": "0"},
    "confidence_six": {"Confidence_Level": "6 - Very"},
    "confidence_text": {"Confidence_Level": "High"},
    "confidence_embedded": {"Confidence_Level": "Level 2 of 5"},
    "confidence_empty": {"Confidence_Level": ""},
    "confidence_none": {"Confidence_Level": None},
    "confidence_decimal_text": {"Confidence_Level": "4.5"},
    "tasks_none_no_ntr": {"Tasks_Completed": None},
    "tasks_null_token_no_ntr": {"Tasks_Completed": "NULL"},
    "tasks_none_with_ntr": {"Tasks_Completed": None, "NTR": "On leave"},
    "tasks_none_ntr_null_token": {"Tasks_Completed": None, "NTR": "null"},
    "tasks_none_ntr_spaces": {"Tasks_Completed": None, "NTR": "   "},
    "tasks_na_token": {"Tasks_Completed": "N/A"},
    "tasks_dash_token": {"Tasks_Completed": "-"},
    "from_after_to": {"From": "2024-06-01", "To": "2024-05-01"},
    "from_after_to_mixed_formats": {"From": "06/01/2024", "To": "2024-05-01"},
    "from_unparsed_string_vs_date": {"From": "2024/01/01", "To": "2024-05-01"},
    "missing_dates": {"From": None, "To": None},
    "multiple_errors": {"Name": "<x>", "BPS": "B", "Confidence_Level": "9", "From": "2099-01-01"},
}


def test_combined_row_cases(snapshot):
    out = {}
    for name, overrides in COMBINED_CASES.items():
        raw = {**COMBINED_BASE, **overrides}
        out[name] = model_outcome(CombinedCSVRow, raw)
    out["required_only_keys_missing"] = model_outcome(CombinedCSVRow, {})
    snapshot("schema_combined_cases", out)


# ---------------------------------------------------------------------------
# VisionDataCSVRow
# ---------------------------------------------------------------------------
VISION_BASE = {
    "Employee_ID": "101",
    "From_Date": "2020-01-01",
    "To_Date": "2024-12-31",
    "Main_Entity": "Activities and Cases",
    "Sub_Entities": "Cases:2, Activities:1",
    "Sub_Entities_Content": 'Cases:[{"id": 1}, {"id": 2}], Activities:[{"type": "raid"}]',
}


@pytest.mark.parametrize("field", ["From_Date", "To_Date"])
def test_vision_row_dates(field, snapshot):
    snapshot(f"schema_vision_dates__{field}", _date_table(VisionDataCSVRow, VISION_BASE, field))


VISION_CASES = {
    "valid_base": {},
    "employee_id_int": {"Employee_ID": 7},
    "employee_id_zero": {"Employee_ID": "0"},
    "employee_id_negative": {"Employee_ID": -3},
    "employee_id_text": {"Employee_ID": "abc"},
    "employee_id_float": {"Employee_ID": 101.0},
    "employee_id_float_fraction": {"Employee_ID": 101.5},
    "employee_id_none": {"Employee_ID": None},
    "main_entity_unknown": {"Main_Entity": "Spaceships"},
    "main_entity_spaces": {"Main_Entity": "   "},
    "main_entity_padded": {"Main_Entity": "  Persons  "},
    "sub_entities_empty": {"Sub_Entities": ""},
    "sub_entities_na": {"Sub_Entities": "N/A"},
    "sub_entities_no_count": {"Sub_Entities": "Cases, Activities"},
    "sub_entities_partial_garbage": {"Sub_Entities": "Cases:2, junk, Tasks:x, Links:3"},
    "sub_entities_duplicate_keys": {"Sub_Entities": "Cases:2, Cases:5"},
    "sub_entities_zero": {"Sub_Entities": "Persons:0"},
    "sub_entities_none": {"Sub_Entities": None},
    "content_empty": {"Sub_Entities_Content": ""},
    "content_none": {"Sub_Entities_Content": None},
    "content_na": {"Sub_Entities_Content": "N/A"},
    "content_empty_lists": {"Sub_Entities_Content": "Cases:[], Tasks:[]"},
    "content_single_quotes_trailing_comma": {"Sub_Entities_Content": "Links:[{'url': 'x',}]"},
    "content_commas_inside_strings": {"Sub_Entities_Content": 'Cases:[{"t": "a, b: c"}]'},
    "content_nested_lists": {"Sub_Entities_Content": 'Cases:[{"tags": [1, 2]}], Tasks:[{"x": {"y": 1}}]'},
    "content_not_list": {"Sub_Entities_Content": 'Cases:{"id": 1}'},
    "content_list_of_ints": {"Sub_Entities_Content": "Events:[1, 2]"},
    "content_bad_json": {"Sub_Entities_Content": "Cases:[{id: 1}]"},
    "content_key_without_colon": {"Sub_Entities_Content": "Cases[]"},
    "content_apostrophe_in_value": {"Sub_Entities_Content": 'Persons:[{"name": "O\'Brien"}]'},
    "content_dict_input": {"Sub_Entities_Content": {"Cases": []}},
    "content_duplicate_key": {"Sub_Entities_Content": 'Cases:[{"a": 1}], Cases:[]'},
    "from_after_to": {"From_Date": "2024-06-01", "To_Date": "2024-05-01"},
    "from_unparsed_vs_date": {"From_Date": "2024/01/01", "To_Date": "2024-05-01"},
}


def test_vision_row_cases(snapshot):
    out = {name: model_outcome(VisionDataCSVRow, {**VISION_BASE, **ov}) for name, ov in VISION_CASES.items()}
    out["empty_input"] = model_outcome(VisionDataCSVRow, {})
    snapshot("schema_vision_cases", out)


# ---------------------------------------------------------------------------
# JobDescriptionCSVRow
# ---------------------------------------------------------------------------
JD_TEXT = "Leads the analysis team, prepares monthly performance summaries and coordinates with wings."
JD_BASE = {
    "Employee_ID": "101",
    "JD_ID": "1001",
    "Job_Description": JD_TEXT,
    "Assigned_Date": "2023-01-15",
    "Is_Current": "TRUE",
    "End_Date": None,
}


@pytest.mark.parametrize("field", ["Assigned_Date", "End_Date"])
def test_job_description_row_dates(field, snapshot):
    base = dict(JD_BASE)
    if field == "End_Date":
        base["Is_Current"] = "FALSE"
        base["Assigned_Date"] = "2000-01-01"
    snapshot(f"schema_job_description_dates__{field}", _date_table(JobDescriptionCSVRow, base, field))


JD_CASES = {
    "valid_base": {},
    "employee_id_int": {"Employee_ID": 101},
    "employee_id_padded": {"Employee_ID": " 101 "},
    "employee_id_float": {"Employee_ID": 101.0},
    "employee_id_bool": {"Employee_ID": True},
    "employee_id_zero": {"Employee_ID": "0"},
    "employee_id_text": {"Employee_ID": "E-101"},
    "employee_id_none": {"Employee_ID": None},
    "employee_id_decimal": {"Employee_ID": Decimal("101")},
    "jd_id_int": {"JD_ID": 1001},
    "jd_id_float_integral": {"JD_ID": 1001.0},
    "jd_id_float_fraction": {"JD_ID": 1001.5},
    "jd_id_float_string": {"JD_ID": "1002.0"},
    "jd_id_padded": {"JD_ID": "  1002 "},
    "jd_id_text": {"JD_ID": "JD-7"},
    "jd_id_negative": {"JD_ID": "-5"},
    "jd_id_leading_zeros": {"JD_ID": "007"},
    "jd_id_bool": {"JD_ID": True},
    "jd_id_none": {"JD_ID": None},
    "jd_id_empty": {"JD_ID": ""},
    "jd_id_decimal": {"JD_ID": Decimal("1001")},
    "jd_id_51_digits": {"JD_ID": "1" * 51},
    "jd_short": {"Job_Description": "Short text"},
    "jd_49_chars": {"Job_Description": "a" * 49},
    "jd_50_chars": {"Job_Description": "a" * 50},
    "jd_padded_to_50": {"Job_Description": "  " + "a" * 48 + "  "},
    "jd_digits_only": {"Job_Description": "1" * 60},
    "jd_placeholder_short": {"Job_Description": "TBD - responsibilities will be documented later on."},
    "jd_placeholder_long": {"Job_Description": "TBD " + JD_TEXT},
    "jd_contains_na_word": {"Job_Description": "Handles n/a cases and maintains the registry of seized goods."},
    "jd_none": {"Job_Description": None},
    "is_current_bool_false": {"Is_Current": False},
    "is_current_int_0": {"Is_Current": 0},
    "is_current_int_2": {"Is_Current": 2},
    "is_current_yes": {"Is_Current": "Yes"},
    "is_current_y": {"Is_Current": "y"},
    "is_current_no": {"Is_Current": "no", "End_Date": "2024-01-01"},
    "is_current_null_token": {"Is_Current": "NULL"},
    "is_current_none": {"Is_Current": None},
    "is_current_maybe": {"Is_Current": "maybe"},
    "is_current_float": {"Is_Current": 0.0},
    "is_current_missing_key": {"Is_Current": ...},
    "end_date_na": {"End_Date": "N/A"},
    "end_date_double_dash": {"End_Date": "--"},
    "end_date_tbd": {"End_Date": "TBD"},
    "end_date_before_assigned": {"Is_Current": "0", "End_Date": "2020-01-01"},
    "current_with_end_date": {"End_Date": "2024-01-01"},
    "assigned_missing_key": {"Assigned_Date": ...},
    "assigned_none": {"Assigned_Date": None},
    "assigned_int": {"Assigned_Date": 20240101},
    "extra_columns_ignored": {"LastModifiedDate": datetime(2024, 1, 1), "Name": "x"},
}


def test_job_description_row_cases(snapshot):
    out = {}
    for name, ov in JD_CASES.items():
        raw = {**JD_BASE, **ov}
        raw = {k: v for k, v in raw.items() if v is not ...}
        out[name] = model_outcome(JobDescriptionCSVRow, raw)
    out["empty_input"] = model_outcome(JobDescriptionCSVRow, {})
    snapshot("schema_job_description_cases", out)


# ---------------------------------------------------------------------------
# SupervisorFeedbackCSVRow
# ---------------------------------------------------------------------------
SF_BASE = {
    "L_RO_Form_Metric_ID": "74",
    "RO_Form_ID": "15",
    "Employee_ID": "1012",
    "Name": "Nadeem Arif",
    "Designation": "Director",
    "BPS": "BS-19",
    "Office_Hierarchy": "PPHQ>CI",
    "Executive_Office": "PPHQ",
    "From": "2020-01-01",
    "To": "2024-11-30",
    "Section_ID": "1",
    "Section": "Performance",
    "Metric_ID": "1",
    "Metric_Title": "Quality",
    "Instructions": "Delivers accurate work",
    "Metric_Type": "R",
    "Possible_Values": "Poor, Fair, Good, Excellent",
    "Value": "Good",
}


@pytest.mark.parametrize("field", ["From", "To"])
def test_supervisor_row_dates(field, snapshot):
    snapshot(f"schema_supervisor_dates__{field}", _date_table(SupervisorFeedbackCSVRow, SF_BASE, field))


SF_CASES = {
    "valid_base": {},
    "ints_native": {"L_RO_Form_Metric_ID": 74, "RO_Form_ID": 15, "Employee_ID": 1012, "Section_ID": 0, "Metric_ID": 1},
    "ids_float_strings": {"RO_Form_ID": "15.0", "L_RO_Form_Metric_ID": "74.0"},
    "employee_id_float": {"Employee_ID": 1012.0},
    "employee_id_text": {"Employee_ID": "abc"},
    "employee_id_zero": {"Employee_ID": "0"},
    "ro_form_id_zero": {"RO_Form_ID": "0"},
    "section_id_negative": {"Section_ID": "-1"},
    "metric_id_zero": {"Metric_ID": 0},
    "name_empty": {"Name": ""},
    "name_spaces": {"Name": "   "},
    "metric_type_lower": {"Metric_Type": "r"},
    "metric_type_padded": {"Metric_Type": " T ", "Possible_Values": None},
    "metric_type_other": {"Metric_Type": "X"},
    "rating_value_case_insensitive": {"Value": "good"},
    "rating_value_padded": {"Value": "  Excellent "},
    "rating_value_not_in_options": {"Value": "great"},
    "rating_value_none": {"Value": None},
    "rating_value_empty": {"Value": ""},
    "rating_no_possible_values": {"Possible_Values": None},
    "rating_possible_values_spaces": {"Possible_Values": "   "},
    "rating_possible_values_no_spaces": {"Possible_Values": "Poor,Fair,Good"},
    "text_metric_with_values": {"Metric_Type": "T", "Possible_Values": "A,B", "Value": "anything"},
    "text_metric_na_values": {"Metric_Type": "T", "Possible_Values": "N/A", "Value": "free text"},
    "text_metric_no_value": {"Metric_Type": "T", "Possible_Values": None, "Value": None},
    "from_equals_to": {"From": "2024-11-01", "To": "2024-11-01"},
    "from_after_to": {"From": "2024-12-01", "To": "2024-11-01"},
    "date_objects": {"From": date(2024, 11, 1), "To": date(2024, 11, 30)},
    "datetime_objects": {"From": datetime(2024, 11, 1, 8), "To": datetime(2024, 11, 30, 17)},
    "datetime_vs_date": {"From": datetime(2024, 11, 1, 8), "To": date(2024, 11, 30)},
    "instructions_1001": {"Instructions": "x" * 1001},
    "value_5001": {"Metric_Type": "T", "Possible_Values": None, "Value": "x" * 5001},
    "optional_fields_none": {"Designation": None, "BPS": None, "Office_Hierarchy": None, "Executive_Office": None,
                             "Instructions": None},
}


def test_supervisor_row_cases(snapshot):
    out = {name: model_outcome(SupervisorFeedbackCSVRow, {**SF_BASE, **ov}) for name, ov in SF_CASES.items()}
    out["empty_input"] = model_outcome(SupervisorFeedbackCSVRow, {})
    snapshot("schema_supervisor_cases", out)


# ---------------------------------------------------------------------------
# Helpers and job/options models
# ---------------------------------------------------------------------------
SPLIT_CASES = [
    None,
    "",
    "a,b,c",
    " a , b ,c ",
    "Cases:[1,2], Tasks:[{\"a\": 1, \"b\": 2}]",
    "x:{\"k\": [1, {\"z\": 3}]}, y:[]",
    "q:\"a,b\", r:'c,d'",
    "esc:\\,next, other",
    "unbalanced:]], after",
    "open:[1,2",
    "trailing,",
    ",leading",
    "a,,b",
    "mixed:\"it's, fine\", z:1",
    12345,
]


def test_top_level_split(snapshot):
    out = []
    for case in SPLIT_CASES:
        out.append({"input": repr(case), "comma": outcome(lambda: _top_level_split(case)),
                    "pipe": outcome(lambda: _top_level_split(case, delimiter="|"))})
    out.append({"input": "a|b,[c|d]|e", "pipe": outcome(lambda: _top_level_split("a|b,[c|d]|e", "|"))})
    snapshot("schema_top_level_split", out)


JSON_LIST_CASES = [
    None,
    "",
    "[]",
    "[1, 2]",
    '[{"a": 1}]',
    "{\"a\": 1}",
    "[{'a': 'b'}]",
    "[{'a': 'b',}]",
    '[{"a": 1},]',
    "[{\"name\": \"O'Brien\"}]",
    "[{'name': 'O\\'Brien'}]",
    "[\"tab\there\"]",
    "[\"new\nline\"]",
    "[{a: 1}]",
    "not json",
    "  [1]  ",
    "null",
    "\"[1]\"",
]


def test_json_list_with_fixes(snapshot):
    out = [{"input": repr(c), "result": outcome(lambda: _json_list_with_fixes(c))} for c in JSON_LIST_CASES]
    snapshot("schema_json_list_with_fixes", out)


def test_import_options_and_job_models(snapshot):
    out = {}
    option_cases = {
        "defaults": {},
        "bulk_tsv": {"processing_mode": "bulk", "file_format": "tsv", "delimiter": "\t", "encoding": "utf-16"},
        "bad_mode": {"processing_mode": "parallel"},
        "bad_format": {"file_format": "xlsx"},
        "chunk_size_string": {"chunk_size": "500"},
        "chunk_size_text": {"chunk_size": "lots"},
        "chunk_size_negative": {"chunk_size": -1},
        "threshold_string": {"error_threshold_percent": "12.5"},
        "dry_run_strings": {"dry_run": "yes", "stop_on_error": "0"},
        "multi_char_delimiter": {"delimiter": "::"},
        "unknown_key": {"surprise": True},
    }
    out["options"] = {k: model_outcome(CSVImportOptions, v) for k, v in option_cases.items()}

    job_create_cases = {
        "csv": {"filename": "reports.csv"},
        "upper_csv": {"filename": "REPORTS.CSV"},
        "tsv": {"filename": "reports.tsv"},
        "txt": {"filename": "reports.txt"},
        "no_ext": {"filename": "reports"},
        "with_options": {"filename": "a.csv", "options": {"chunk_size": 10}},
        "bad_options": {"filename": "a.csv", "options": {"processing_mode": "nope"}},
    }
    out["job_create"] = {k: model_outcome(CSVImportJobCreate, v) for k, v in job_create_cases.items()}

    base = {
        "job_id": "job-1", "filename": "a.csv", "status": "processing",
        "submitted_at": datetime(2024, 1, 1, 9, 0, 0), "total_rows": 200, "processed_rows": 50,
        "successful_rows": 45, "error_count": 5, "percent_complete": 0.0,
    }
    response_cases = {
        "computed_quarter": {},
        "percent_supplied_ignored": {"percent_complete": 99.9},
        "percent_missing": {"percent_complete": ...},
        "zero_total": {"total_rows": 0},
        "negative_total": {"total_rows": -5},
        "processed_exceeds_total": {"processed_rows": 300},
        "rounding": {"total_rows": 3, "processed_rows": 1},
        "total_rows_invalid": {"total_rows": "many"},
        "processed_rows_invalid": {"processed_rows": "some"},
        "string_numbers": {"total_rows": "10", "processed_rows": "4"},
        "metrics_and_type": {"csv_type": "vision_data", "metrics": {"vision_records_created": 3}},
        "submitted_at_string": {"submitted_at": "2024-01-01T09:00:00"},
    }
    resp = {}
    for k, ov in response_cases.items():
        raw = {**base, **ov}
        raw = {kk: vv for kk, vv in raw.items() if vv is not ...}
        resp[k] = model_outcome(CSVImportJobResponse, raw)
    out["job_response"] = resp

    out["import_error_response"] = {
        "row_level": model_outcome(ImportErrorResponse, {"row_number": 3, "error_message": "bad"}),
        "field_level": model_outcome(ImportErrorResponse, {"row_number": "4", "field_name": "Name",
                                                           "error_message": "x", "row_data": {"Name": None}}),
        "missing_message": model_outcome(ImportErrorResponse, {"row_number": 1}),
    }
    out["import_errors_response"] = model_outcome(ImportErrorsResponse, {
        "total": 1, "page": 1, "page_size": 50, "errors": [{"row_number": 1, "error_message": "e"}]})
    snapshot("schema_options_and_job_models", out)
