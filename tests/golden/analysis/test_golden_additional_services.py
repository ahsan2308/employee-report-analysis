"""Golden-master tests for vision filtering (app.domain.vision_catalog), the vision and JD prompt sections (app.prompts.vision, app.prompts.job_descriptions) and jd_mapping; formerly app/services/additional_services.py.

These lock in today's behaviour (including bugs) of the vision-data filters,
prompt formatters and the report -> job-description mapper.
"""
import copy
from datetime import date, datetime

import pytest

from app.prompts import job_descriptions as jd_formatting
from app.services.analysis import jd_mapping
from app.domain import vision_catalog
from app.prompts import vision as vision_prompts
from tests.golden.analysis.fixtures import (
    DEFAULT_DESCRIPTION_KEYS,
    content_entries,
    jd,
    raw_monthly_vision,
    raw_quarterly_vision,
    raw_weekly_vision,
    report,
    vision_item,
)


def outcome(fn, *args, **kwargs):
    """Return the value, or the exception type and message, so both can be snapshotted."""
    try:
        return {"returned": fn(*args, **kwargs)}
    except Exception as exc:  # noqa: BLE001 - characterizing whatever is raised
        return {"raised": type(exc).__name__, "message": str(exc)}


# --------------------------------------------------------------------------- _truncate_content_value

def test_truncate_content_value_table(snapshot):
    cases = [
        ("none", None, {}),
        ("empty_string", "", {}),
        ("zero", 0, {}),
        ("false", False, {}),
        ("short", "hello", {}),
        ("exactly_300", "x" * 300, {}),
        ("301", "y" * 301, {}),
        ("int_long", int("9" * 20), {"max_length": 5}),
        ("list", [1, 2, 3], {"max_length": 4}),
        ("dict", {"a": 1}, {}),
        ("max_zero", "abc", {"max_length": 0}),
        ("max_negative", "abcdef", {"max_length": -2}),
        ("unicode", "é" * 10, {"max_length": 3}),
    ]
    snapshot(
        "truncate_content_value_table",
        {name: outcome(vision_prompts._truncate_content_value, value, **kw) for name, value, kw in cases},
    )


# --------------------------------------------------------------------------- filter_vision_data

def test_default_descriptions_effective_mapping(snapshot):
    """An entity missing from the catalog gets the flat view (a repeated name takes its later entry)."""
    vision = {"current_data": [vision_item("All", {key: 1 for key in DEFAULT_DESCRIPTION_KEYS})]}
    filtered = vision_catalog.filter_vision_data(vision)
    subs = filtered["current_data"][0]["sub_entities"]
    snapshot("default_descriptions", {key: subs[key]["description"] for key in DEFAULT_DESCRIPTION_KEYS})


def test_default_descriptions_follow_the_main_entity():
    """B4 fixed: a repeated sub-entity name is described within its own entity."""
    names = ["Groups", "Labels", "Lookup", "Special Reports", "Attachments", "Notings"]
    vision = {"current_data": [vision_item(entity, {name: 1 for name in names})
                               for entity in ("Persons", "Organizations", "Correspondence", "Events", "Nadra")]}
    filtered = vision_catalog.filter_vision_data(vision)
    described = {item["main_entity"]: {name: sub["description"] for name, sub in item["sub_entities"].items()}
                 for item in filtered["current_data"]}
    assert described["Persons"]["Groups"] == "Persons marked with specific groups (muli-level labeling)"
    assert described["Organizations"]["Groups"] == "Long term categorization of an organization (e.g. its type, etc.)"
    assert described["Events"]["Groups"] == "Events marked with specific groups (muli-level labeling)"
    assert described["Persons"]["Lookup"] == "Lookup details added with persons (Related to wanted criminals)"
    assert described["Organizations"]["Attachments"] == "Attachments uploaded with organization Particulars"
    assert described["Correspondence"]["Attachments"] == "Attachments added with correspondence"
    assert described["Correspondence"]["Notings"] == "Notings added with correspondence"
    assert described["Nadra"]["Notings"] == "Notings added with NADRA person verification requests"
    # A name the entity does not have gets no description, rather than another entity's.
    assert described["Organizations"]["Labels"] == ""


def test_filter_vision_data_empty_inputs(snapshot):
    snapshot("filter_vision_data_empty_inputs", {
        "none": outcome(vision_catalog.filter_vision_data, None),
        "empty_dict": outcome(vision_catalog.filter_vision_data, {}),
        "only_date_context": outcome(vision_catalog.filter_vision_data, {"date_context": {"a": 1}}),
        "unknown_shape": outcome(vision_catalog.filter_vision_data, {"foo": [1, 2]}),
        "current_key_only_empty": outcome(vision_catalog.filter_vision_data, {"current_data": []}),
        "previous_key_only": outcome(vision_catalog.filter_vision_data, {"previous_data": [
            vision_item("Tasks", {"Tasks": 2})]}),
        "weeks_data_empty": outcome(vision_catalog.filter_vision_data, {"weeks_data": []}),
        "months_data_empty": outcome(vision_catalog.filter_vision_data, {"months_data": []}),
    })


def test_filter_vision_data_weekly_default_descriptions(snapshot):
    raw = raw_weekly_vision()
    before = copy.deepcopy(raw)
    result = vision_catalog.filter_vision_data(raw)
    snapshot("filter_weekly_default", result)
    snapshot("filter_weekly_input_mutated", {"input_unchanged": raw == before})


def test_filter_vision_data_weekly_custom_descriptions(snapshot):
    custom = {"Persons": "custom persons", "Tasks": "custom tasks"}
    snapshot("filter_weekly_custom", vision_catalog.filter_vision_data(raw_weekly_vision(), custom))


def test_filter_vision_data_weekly_wins_over_other_shapes(snapshot):
    raw = raw_weekly_vision()
    raw["weeks_data"] = raw_monthly_vision()["weeks_data"]
    raw["months_data"] = raw_quarterly_vision()["months_data"]
    snapshot("filter_mixed_shapes", vision_catalog.filter_vision_data(raw))


def test_filter_vision_data_monthly(snapshot):
    snapshot("filter_monthly_default", vision_catalog.filter_vision_data(raw_monthly_vision()))
    snapshot("filter_monthly_custom", vision_catalog.filter_vision_data(raw_monthly_vision(), {"Persons": "P!"}))


def test_filter_vision_data_quarterly(snapshot):
    snapshot("filter_quarterly_default", vision_catalog.filter_vision_data(raw_quarterly_vision()))
    # Custom descriptions are NOT propagated into the per-month recursion.
    snapshot("filter_quarterly_custom", vision_catalog.filter_vision_data(raw_quarterly_vision(), {"Events": "E!"}))


def test_filter_vision_data_missing_sub_entities_raises(snapshot):
    weird = {"current_data": [{"main_entity": "X", "sub_entities": [("a", 1)]}]}
    snapshot("filter_sub_entities_not_dict", outcome(vision_catalog.filter_vision_data, weird))


# --------------------------------------------------------------------------- weekly prompt

def test_weekly_prompt_empty(snapshot):
    snapshot("weekly_prompt_empty", {
        "none": outcome(vision_prompts.format_vision_data_for_weekly_analysis_prompt, None),
        "empty": outcome(vision_prompts.format_vision_data_for_weekly_analysis_prompt, {}),
        "empty_lists": outcome(vision_prompts.format_vision_data_for_weekly_analysis_prompt,
                               {"current_data": [], "previous_data": []}),
        "monthly_shape": outcome(vision_prompts.format_vision_data_for_weekly_analysis_prompt,
                                 vision_catalog.filter_vision_data(raw_monthly_vision())),
    })


def test_weekly_prompt_default_limits(snapshot):
    filtered = vision_catalog.filter_vision_data(raw_weekly_vision())
    snapshot("weekly_prompt_default", vision_prompts.format_vision_data_for_weekly_analysis_prompt(filtered))


def test_weekly_prompt_custom_limits(snapshot):
    filtered = vision_catalog.filter_vision_data(raw_weekly_vision())
    snapshot("weekly_prompt_limits_2_10",
             vision_prompts.format_vision_data_for_weekly_analysis_prompt(filtered, 2, 10))
    snapshot("weekly_prompt_limits_0_0",
             vision_prompts.format_vision_data_for_weekly_analysis_prompt(filtered, 0, 0))


def test_weekly_prompt_current_only_and_previous_only(snapshot):
    filtered = vision_catalog.filter_vision_data(raw_weekly_vision())
    snapshot("weekly_prompt_current_only", vision_prompts.format_vision_data_for_weekly_analysis_prompt(
        {"current_data": filtered["current_data"]}))
    snapshot("weekly_prompt_previous_only", vision_prompts.format_vision_data_for_weekly_analysis_prompt(
        {"previous_data": filtered["previous_data"], "current_data": []}))


def test_weekly_prompt_item_limit_boundary(snapshot):
    data = {"current_data": [{
        "main_entity": "Persons", "from_date": "a", "to_date": "b",
        "sub_entities": {"Persons": {"value": 5, "description": "d"},
                         "Numbers": {"value": 6, "description": "e"}},
        "sub_entities_content": {"Persons": content_entries(5), "Numbers": content_entries(6)},
    }]}
    snapshot("weekly_prompt_item_limit_boundary", vision_prompts.format_vision_data_for_weekly_analysis_prompt(data))


def test_weekly_prompt_unfiltered_item_raises(snapshot):
    data = {"current_data": [vision_item("Persons", {"Persons": 3})]}
    snapshot("weekly_prompt_unfiltered", outcome(vision_prompts.format_vision_data_for_weekly_analysis_prompt, data))


# --------------------------------------------------------------------------- monthly prompt

def test_monthly_prompt_empty(snapshot):
    snapshot("monthly_prompt_empty", {
        "none": outcome(vision_prompts.format_vision_data_for_monthly_analysis_prompt, None),
        "empty": outcome(vision_prompts.format_vision_data_for_monthly_analysis_prompt, {}),
        "weeks_empty": outcome(vision_prompts.format_vision_data_for_monthly_analysis_prompt, {"weeks_data": []}),
        "week_without_activities": outcome(vision_prompts.format_vision_data_for_monthly_analysis_prompt,
                                           {"weeks_data": [{"week_number": 1, "activities": []}]}),
        "weekly_shape": outcome(vision_prompts.format_vision_data_for_monthly_analysis_prompt,
                                vision_catalog.filter_vision_data(raw_weekly_vision())),
    })


def test_monthly_prompt_default_and_custom_limits(snapshot):
    filtered = vision_catalog.filter_vision_data(raw_monthly_vision())
    snapshot("monthly_prompt_default", vision_prompts.format_vision_data_for_monthly_analysis_prompt(filtered))
    snapshot("monthly_prompt_limits_1_12",
             vision_prompts.format_vision_data_for_monthly_analysis_prompt(filtered, 1, 12))


# --------------------------------------------------------------------------- quarterly prompt

def test_quarterly_prompt_empty(snapshot):
    snapshot("quarterly_prompt_empty", {
        "none": outcome(vision_prompts.format_vision_data_for_quarterly_analysis_prompt, None),
        "empty": outcome(vision_prompts.format_vision_data_for_quarterly_analysis_prompt, {}),
        "months_empty": outcome(vision_prompts.format_vision_data_for_quarterly_analysis_prompt, {"months_data": []}),
        "missing_date_context": outcome(vision_prompts.format_vision_data_for_quarterly_analysis_prompt,
                                        {"months_data": [{"weeks_data": []}]}),
    })


def test_quarterly_prompt_filtered(snapshot):
    filtered = vision_catalog.filter_vision_data(raw_quarterly_vision())
    snapshot("quarterly_prompt_filtered_default", vision_prompts.format_vision_data_for_quarterly_analysis_prompt(filtered))
    snapshot("quarterly_prompt_filtered_limits_3_15",
             vision_prompts.format_vision_data_for_quarterly_analysis_prompt(filtered, 3, 15))


def test_quarterly_prompt_months_without_weeks(snapshot):
    data = {
        "date_context": {"year": 2024, "quarter": 4, "period_start": "2024-10-01", "period_end": "2024-12-31"},
        "months_data": [
            {"month_name": "October", "weeks_data": []},
            {"weeks_data": [{"week_number": 2, "activities": [{
                "main_entity": "Tasks", "from_date": "x", "to_date": "y",
                "sub_entities": {"Tasks": {"value": 1, "description": ""}}}]}]},
            {"month_name": "december", "weeks_data": [{"week_number": 5, "activities": []}]},
        ],
    }
    snapshot("quarterly_prompt_months_without_weeks", vision_prompts.format_vision_data_for_quarterly_analysis_prompt(data))


def test_quarterly_prompt_missing_main_entity(snapshot):
    data = {
        "date_context": {"year": 2025, "quarter": 2, "period_start": "s", "period_end": "e"},
        "months_data": [{"month_name": "April", "weeks_data": [{"week_number": 1, "activities": [
            {"sub_entities": {}}, {"main_entity": "Orgs", "sub_entities": {}}]}]}],
    }
    snapshot("quarterly_prompt_missing_main_entity",
             outcome(vision_prompts.format_vision_data_for_quarterly_analysis_prompt, data))


# --------------------------------------------------------------------------- map_reports_to_jds

JD_A = jd("JD_A", "Analyst duties", date(2025, 1, 1), date(2025, 1, 15))
JD_B = jd("JD_B", "Team lead duties", date(2025, 1, 16), date(2025, 1, 31))
JD_FULL = jd("JD_FULL", "Full month duties", date(2025, 1, 1), date(2025, 1, 31))
JANUARY_REPORTS = [report(date(2025, 1, d)) for d in (5, 12, 19, 26)]


def test_map_reports_to_jds_empty_inputs(snapshot):
    snapshot("map_empty_inputs", {
        "no_reports": outcome(jd_mapping.map_reports_to_jds, [], [JD_A]),
        "none_reports": outcome(jd_mapping.map_reports_to_jds, None, [JD_A]),
        "no_jds": outcome(jd_mapping.map_reports_to_jds, JANUARY_REPORTS[:2], []),
        "none_jds": outcome(jd_mapping.map_reports_to_jds, JANUARY_REPORTS[:1], None),
    })


@pytest.mark.parametrize("name,jds", [
    ("stable_single", [JD_FULL]),
    ("transition", [JD_B, JD_A]),
    ("concurrent_input_order_b_a", [jd("JD_B", "B text", date(2025, 1, 1), date(2025, 1, 31)),
                                    jd("JD_A", "A text", date(2025, 1, 1), date(2025, 1, 31))]),
    ("concurrent_then_single", [JD_FULL, JD_B]),
    ("jd_starting_mid_month", [jd("JD_LATE", "late", date(2025, 1, 20), date(2025, 1, 31))]),
    ("open_ended_jd_end_none", [jd("JD_OPEN", "open", date(2025, 1, 1), None)]),
    ("jd_missing_effective_period", [{"jd_id": "JD_X", "job_description": "x"}]),
])
def test_map_reports_to_jds_scenarios(snapshot, name, jds):
    snapshot(f"map_{name}", outcome(jd_mapping.map_reports_to_jds, JANUARY_REPORTS, jds))


def test_map_reports_to_jds_week_overlap_boundaries(snapshot):
    jds = [jd("JD_EDGE", "edge", date(2025, 1, 10), date(2025, 1, 10))]
    reports = [report(date(2025, 1, d)) for d in (9, 10, 16, 17)]
    snapshot("map_overlap_boundaries", jd_mapping.map_reports_to_jds(reports, jds))


def test_map_reports_to_jds_date_variants(snapshot):
    reports = [
        {"text": "no date", "report_id": "r-nodate"},
        {"text": "none date", "date": None},
        {"text": "iso string", "date": "2025-01-12", "report_id": "r-iso"},
        {"text": "iso datetime string", "date": "2025-01-19T10:30:00", "report_id": "r-isodt"},
        {"text": "bad string", "date": "12/01/2025", "report_id": "r-bad"},
        {"text": "before jd", "date": date(2024, 12, 1), "report_id": "r-early"},
        {"text": "no report id", "date": date(2025, 1, 26)},
    ]
    snapshot("map_date_variants", outcome(jd_mapping.map_reports_to_jds, reports, [JD_FULL]))


def test_map_reports_to_jds_input_not_mutated(snapshot):
    reports = copy.deepcopy(JANUARY_REPORTS)
    jd_mapping.map_reports_to_jds(reports, [JD_FULL])
    snapshot("map_input_not_mutated", {"unchanged": reports == JANUARY_REPORTS})


def test_map_reports_to_jds_error_paths(snapshot):
    snapshot("map_error_paths", {
        "report_id_none": outcome(jd_mapping.map_reports_to_jds,
                                  [{"date": date(2025, 1, 5), "report_id": None}], [JD_FULL]),
        "datetime_object_date": outcome(jd_mapping.map_reports_to_jds,
                                        [{"date": datetime(2025, 1, 5, 9, 0), "report_id": "r"}], [JD_FULL]),
        "jd_without_jd_id": outcome(jd_mapping.map_reports_to_jds, [report(date(2025, 1, 5))],
                                    [{"job_description": "x", "effective_during_period": {
                                        "start": date(2025, 1, 1), "end": date(2025, 1, 31)}}]),
    })


# --------------------------------------------------------------------------- weekly JD prompt

def test_weekly_jd_prompt(snapshot):
    jd_old = jd("J1", "Old role text", date(2025, 1, 1), date(2025, 1, 31), assigned=date(2023, 5, 1))
    jd_new = jd("J2", "New role text", date(2025, 1, 1), date(2025, 1, 31), assigned=date(2024, 8, 15))
    jd_third = jd("J3", "Third role", date(2025, 1, 1), date(2025, 1, 31), assigned=date(2024, 1, 1))
    snapshot("weekly_jd_prompt_cases", {
        "none": outcome(jd_formatting.format_job_descriptions_for_weekly_prompt, None),
        "empty": outcome(jd_formatting.format_job_descriptions_for_weekly_prompt, []),
        "single_with_none_assigned": outcome(jd_formatting.format_job_descriptions_for_weekly_prompt,
                                             [{"jd_id": "x", "assigned_date": None}]),
        "single_missing_keys": outcome(jd_formatting.format_job_descriptions_for_weekly_prompt, [{}]),
        "single_string_assigned": outcome(jd_formatting.format_job_descriptions_for_weekly_prompt,
                                          [{"assigned_date": "2024-02-29", "job_description": "S"}]),
        "multiple_with_none_assigned": outcome(jd_formatting.format_job_descriptions_for_weekly_prompt,
                                               [jd_old, {"assigned_date": None, "job_description": "n"}]),
    })
    snapshot("weekly_jd_prompt_single", jd_formatting.format_job_descriptions_for_weekly_prompt([jd_old]))
    snapshot("weekly_jd_prompt_multiple", jd_formatting.format_job_descriptions_for_weekly_prompt([jd_new, jd_old, jd_third]))


# --------------------------------------------------------------------------- monthly JD prompt

def test_monthly_jd_prompt_empty(snapshot):
    snapshot("monthly_jd_prompt_empty", {
        "none": outcome(jd_formatting.format_job_descriptions_for_monthly_prompt, None),
        "empty": outcome(jd_formatting.format_job_descriptions_for_monthly_prompt, {}),
        "no_groups": outcome(jd_formatting.format_job_descriptions_for_monthly_prompt,
                             {"jd_groups": [], "unmapped_reports": JANUARY_REPORTS}),
    })


@pytest.mark.parametrize("name,reports,jds", [
    ("stable_single", JANUARY_REPORTS, [JD_FULL]),
    ("stable_single_with_unmapped", JANUARY_REPORTS + [report(date(2024, 12, 20))],
     [jd("JD_FULL", "Full", date(2025, 1, 1), date(2025, 1, 31))]),
    ("stable_concurrent", JANUARY_REPORTS, [jd("JD_B", "B text", date(2025, 1, 1), date(2025, 1, 31)),
                                            jd("JD_A", "A text", date(2025, 1, 1), date(2025, 1, 31))]),
    ("transition", JANUARY_REPORTS, [JD_A, JD_B]),
    ("transition_with_unmapped", JANUARY_REPORTS + [{"text": "x", "date": None}],
     [JD_A, JD_B]),
    ("complex_concurrent_and_single", JANUARY_REPORTS, [JD_FULL, JD_B]),
])
def test_monthly_jd_prompt_from_mapping(snapshot, name, reports, jds):
    mapping = jd_mapping.map_reports_to_jds(reports, jds)
    snapshot(f"monthly_jd_prompt_{name}", jd_formatting.format_job_descriptions_for_monthly_prompt(mapping))


def test_monthly_jd_prompt_handmade_groups(snapshot):
    """Groups without week ranges, None/str dates and missing texts drive the fallbacks."""
    transition = {
        "jd_groups": [
            {"jd_ids": ["A"], "jd_texts": ["A text"], "effective_dates": {"start": None, "end": "2025-01-10"},
             "reports": [{"date": date(2025, 1, 5)}, {"date": "2025-01-09"}]},
            {"jd_ids": ["B"], "effective_dates": {"start": date(2025, 1, 11)},
             "reports": [{"week_start_date": date(2025, 1, 13), "week_end_date": date(2025, 1, 19)}]},
        ],
        "unmapped_reports": [{"date": date(2024, 12, 29)},
                             {"week_start_date": "2024-12-16", "week_end_date": "2024-12-22"}],
    }
    complex_case = {
        "jd_groups": [
            {"jd_ids": ["A", "B"], "jd_texts": ["A text", "B text"],
             "effective_dates": {"start": date(2025, 1, 1), "end": date(2025, 1, 12)},
             "reports": [{"date": date(2025, 1, 12)}]},
            {"jd_ids": ["C"], "jd_texts": [], "effective_dates": {}, "reports": []},
        ],
        "unmapped_reports": [{"date": None}],
    }
    snapshot("monthly_jd_prompt_handmade", {
        "transition": outcome(jd_formatting.format_job_descriptions_for_monthly_prompt, transition),
        "complex": outcome(jd_formatting.format_job_descriptions_for_monthly_prompt, complex_case),
        "single_group_no_texts": outcome(jd_formatting.format_job_descriptions_for_monthly_prompt,
                                         {"jd_groups": [{"jd_ids": ["A"], "jd_texts": []}]}),
        "single_group_no_ids": outcome(jd_formatting.format_job_descriptions_for_monthly_prompt,
                                       {"jd_groups": [{"jd_texts": ["t1", "t2"]}]}),
    })


# --------------------------------------------------------------------------- quarterly JD prompt

Q1_WEEKLY = [report(date(2025, m, d)) for m, d in ((1, 12), (1, 26), (2, 9), (2, 23), (3, 9), (3, 23))]


def test_quarterly_jd_prompt_empty(snapshot):
    snapshot("quarterly_jd_prompt_empty", {
        "none": outcome(jd_formatting.format_job_descriptions_for_quarterly_prompt, None),
        "empty": outcome(jd_formatting.format_job_descriptions_for_quarterly_prompt, {}),
        "no_groups": outcome(jd_formatting.format_job_descriptions_for_quarterly_prompt, {"jd_groups": []}),
    })


@pytest.mark.parametrize("name,reports,jds", [
    ("stable_single", Q1_WEEKLY, [jd("Q", "Quarter role", date(2025, 1, 1), date(2025, 3, 31))]),
    ("stable_concurrent", Q1_WEEKLY, [jd("Q2", "Second", date(2025, 1, 1), date(2025, 3, 31)),
                                      jd("Q1", "First", date(2025, 1, 1), date(2025, 3, 31))]),
    ("stable_single_q4", [report(date(2024, 10, 13)), report(date(2024, 12, 29))],
     [jd("Q", "Q4 role", date(2024, 10, 1), date(2024, 12, 31))]),
    ("three_phases", Q1_WEEKLY, [jd("P1", "Phase one", date(2025, 1, 1), date(2025, 1, 31)),
                                 jd("P2", "Phase two", date(2025, 2, 1), date(2025, 2, 28)),
                                 jd("P3", "Phase three", date(2025, 3, 1), date(2025, 3, 31))]),
    ("with_concurrent_phase", Q1_WEEKLY, [jd("A", "Role A", date(2025, 1, 1), date(2025, 3, 31)),
                                          jd("B", "Role B", date(2025, 2, 15), date(2025, 3, 31))]),
    ("unmapped_ignored", Q1_WEEKLY, [jd("L", "Late role", date(2025, 3, 1), date(2025, 3, 31))]),
])
def test_quarterly_jd_prompt_from_mapping(snapshot, name, reports, jds):
    mapping = jd_mapping.map_reports_to_jds(reports, jds)
    snapshot(f"quarterly_jd_prompt_{name}", jd_formatting.format_job_descriptions_for_quarterly_prompt(mapping))


def test_quarterly_jd_prompt_handmade_groups(snapshot):
    snapshot("quarterly_jd_prompt_handmade", {
        "single_start_none": outcome(jd_formatting.format_job_descriptions_for_quarterly_prompt, {"jd_groups": [
            {"jd_ids": ["A"], "jd_texts": ["A"], "effective_dates": {"start": None, "end": None}}]}),
        "single_start_string": outcome(jd_formatting.format_job_descriptions_for_quarterly_prompt, {"jd_groups": [
            {"jd_ids": ["A"], "jd_texts": ["A"], "effective_dates": {"start": "2025-07-01", "end": "x"},
             "reports": [{}, {}]}]}),
        "multi_phase_empty_texts": outcome(jd_formatting.format_job_descriptions_for_quarterly_prompt, {"jd_groups": [
            {"jd_texts": ["A"], "effective_dates": {}, "reports": []},
            {"jd_texts": [], "effective_dates": {}, "reports": []}]}),
        "multi_phase_reports_without_week_range": outcome(
            jd_formatting.format_job_descriptions_for_quarterly_prompt, {"jd_groups": [
                {"jd_texts": ["A"], "effective_dates": {"start": date(2025, 4, 1), "end": date(2025, 4, 30)},
                 "reports": [{"date": date(2025, 4, 6)}]},
                {"jd_texts": ["B"], "effective_dates": {"start": date(2025, 5, 1), "end": date(2025, 6, 30)},
                 "reports": [{"week_start_date": date(2025, 5, 5), "week_end_date": None}]}]}),
    })


def test_quarterly_jd_prompt_week_end_formatting(snapshot):
    """Coverage lines format week_end by its own type (B9 fixed: it used to check the group end)."""
    groups = {"jd_groups": [
        {"jd_texts": ["A"], "effective_dates": {"start": date(2025, 1, 1), "end": None},
         "reports": [{"week_start_date": datetime(2025, 1, 6, 0, 0), "week_end_date": datetime(2025, 1, 12, 0, 0)}]},
        {"jd_texts": ["B"], "effective_dates": {"start": date(2025, 2, 1), "end": date(2025, 3, 31)},
         "reports": [{"week_start_date": datetime(2025, 2, 3, 0, 0), "week_end_date": datetime(2025, 2, 9, 0, 0)}]},
    ]}
    snapshot("quarterly_jd_prompt_week_end", jd_formatting.format_job_descriptions_for_quarterly_prompt(groups))
    # Group end is a date but week_end is a string: the string is used as is.
    string_week_end = {"jd_groups": [
        {"jd_texts": ["A"], "effective_dates": {"start": date(2025, 1, 1), "end": date(2025, 1, 31)},
         "reports": [{"week_start_date": "2025-01-06", "week_end_date": "2025-01-12"}]},
        {"jd_texts": ["B"], "effective_dates": {}, "reports": []},
    ]}
    snapshot("quarterly_jd_prompt_string_week_end",
             outcome(jd_formatting.format_job_descriptions_for_quarterly_prompt, string_week_end))


def test_unmapped_reports_section(snapshot):
    snapshot("unmapped_reports_section", jd_formatting._format_unmapped_reports_section([
        {"date": date(2025, 1, 5)},
        {"week_start_date": date(2024, 12, 30), "week_end_date": date(2025, 1, 5)},
        {"week_start_date": date(2024, 12, 30)},
        {"date": "2025-01-01"},
        {},
    ]))
    snapshot("unmapped_reports_section_empty", jd_formatting._format_unmapped_reports_section([]))
