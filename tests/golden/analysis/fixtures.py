"""Fixture builders for the analysis golden-master tests.

All data is synthetic and fixed; nothing here depends on the clock.
"""
from datetime import date
from typing import Any, Dict, List

# Every distinct sub-entity name that appears in the default descriptions
# dictionary of additional_services.filter_vision_data (source order, first
# occurrence). Several names appear more than once in the source (bug B4).
DEFAULT_DESCRIPTION_KEYS = [
    "Persons", "Numbers", "Pictures", "Addresses", "Features", "Skills", "Education",
    "Profession", "Docs", "Doc Attach", "POIs", "Labels", "Groups", "History Sheet",
    "HS Attachments", "LDs", "Crime Status", "Lookup", "Special Reports", "Orgs", "OOIs",
    "Particulars", "Attachments", "OPs", "Label", "Per-Per", "Per-Org", "Per-Event",
    "Per-Activity", "Per-Case", "Per-Task", "Per-News Report", "Per-Correspondence",
    "Org-Event", "Org-Task", "Org-Activity", "Org-News Report", "Org-Case",
    "Org-Correspondence", "Event-Case", "Event-Activity", "Event-Event", "Event-News Report",
    "Event-Task", "Event-Correspondence", "Activity-Case", "Activity-News Report",
    "Activity-Task", "Activity-Correspondence", "Task-Correspondence", "Task-Case",
    "Task-News Report", "Correspondence-Case", "Case-News Report", "Tasks", "Task Updates",
    "Task Attachments", "Assigned/CC", "DFA", "Correspondence", "Notings", "Events", "EOIs",
    "Information", "Activities", "Activity Information", "Activity Attachments", "Cases",
    "Case Attachments", "Issues", "Issues Briefs", "Old Sit-Rep", "News/Media Reports",
    "News/Media Reports Briefs", "SM Profiles", "SM Attachments", "Initiated",
    "Drafted as RO", "Received as RO", "Submitted as RO", "Received as CSO2",
    "Recieved as CSO1", "Submitted as CSO1", "Submitted as CSO2", "Files Uploaded",
    "Requests", "Forwarded", "Feedbacks", "VeriSys", "Family Tree",
]

LONG_TEXT = "L" * 320  # longer than every default truncation limit (300/250/200)


# --------------------------------------------------------------------------- vision data

def vision_item(main_entity: str, sub_entities: Dict[str, Any], from_date="2025-01-06",
                to_date="2025-01-12", content: Dict[str, List[Any]] = None) -> Dict[str, Any]:
    item = {
        "main_entity": main_entity,
        "from_date": from_date,
        "to_date": to_date,
        "sub_entities": sub_entities,
    }
    if content is not None:
        item["sub_entities_content"] = content
    return item


def content_entries(n: int, prefix: str = "Name") -> List[Dict[str, Any]]:
    return [{"name": f"{prefix} {i}", "ref": f"R-{i}", "empty": ""} for i in range(1, n + 1)]


def raw_weekly_vision() -> Dict[str, Any]:
    """Weekly shape as returned by get_employee_vision_data (unfiltered)."""
    return {
        "date_context": {"report_date": "2025-01-12", "num_previous_weeks": 2},
        "current_data": [
            vision_item("Persons", {"Persons": 3, "Numbers": 0, "Pictures": 2, "Unknown Thing": 5},
                        content={"Persons": content_entries(7),
                                 "Pictures": [{"file": LONG_TEXT}, {}, {"file": None}],
                                 "Unknown Thing": [{"x": 1}]}),
            vision_item("Orgs", {"Orgs": 0, "OOIs": 0}),           # all zero -> dropped
            vision_item("Empty", {}),                               # no sub entities -> dropped
            {"main_entity": "NoSubs", "from_date": "2025-01-06", "to_date": "2025-01-12"},
            vision_item("Correspondence", {"Labels": 1, "Groups": 2, "Lookup": 1,
                                           "Special Reports": 1, "Attachments": 4, "Notings": 2}),
        ],
        "previous_data": [
            vision_item("Tasks", {"Tasks": 1, "Task Updates": -1, "Assigned/CC": 0.0},
                        from_date="2024-12-30", to_date="2025-01-05",
                        content={"Tasks": content_entries(5, "Task")}),
            vision_item("Events", {"Events": None, "EOIs": "3"},
                        from_date="2024-12-23", to_date="2024-12-29"),
        ],
    }


def raw_monthly_vision() -> Dict[str, Any]:
    """Monthly shape as returned by get_employee_vision_data_for_month (unfiltered)."""
    return {
        "date_context": {"year": 2025, "month": 2, "period_start": "2025-02-01",
                         "period_end": "2025-02-28"},
        "weeks_data": [
            {"week_number": 1, "iso_week": "2025-W06", "activities": [
                vision_item("Persons", {"Persons": 2, "Skills": 0},
                            from_date="2025-02-03", to_date="2025-02-09",
                            content={"Persons": content_entries(6)}),
                vision_item("Nadra", {"Requests": 10, "Forwarded": 4, "Notings": 1},
                            from_date="2025-02-03", to_date="2025-02-09",
                            content={"Requests": [{"cnic": LONG_TEXT, "status": "ok"}]}),
            ]},
            {"week_number": 2, "iso_week": "2025-W07", "activities": [
                vision_item("Orgs", {"Orgs": 0}, from_date="2025-02-10", to_date="2025-02-16"),
            ]},  # all zero -> week dropped
            {"week_number": 3, "iso_week": "2025-W08", "activities": []},
            {"week_number": 4, "activities": [
                vision_item("PER", {"Initiated": 1, "Recieved as CSO1": 2},
                            from_date="2025-02-17", to_date="2025-02-23"),
            ]},
        ],
    }


def raw_quarterly_vision() -> Dict[str, Any]:
    """Quarterly shape as returned by get_employee_vision_data_for_quarter (unfiltered)."""
    month = raw_monthly_vision()
    return {
        "date_context": {"year": 2025, "quarter": 1, "period_start": "2025-01-01",
                         "period_end": "2025-03-31"},
        "months_data": [
            {"month_name": "January", "date_context": {"month": 1},
             "weeks_data": [{"week_number": 1, "iso_week": "2025-W02", "activities": [
                 vision_item("Events", {"Events": 1, "Labels": 2, "Attachments": 1},
                             content={"Events": ["plain string entry", LONG_TEXT, "", None]
                                      + [f"evt {i}" for i in range(10)]}),
             ]}]},
            {"month_name": "February", "date_context": month["date_context"],
             "weeks_data": month["weeks_data"]},
            {"month_name": "March", "date_context": {"month": 3},
             "weeks_data": [{"week_number": 1, "activities": [vision_item("Orgs", {"Orgs": 0})]}]},
            {"date_context": {}, "weeks_data": [{"week_number": 9, "activities": [
                vision_item("Cases", {"Cases": 1}, from_date="2025-03-24", to_date="2025-03-30")]}]},
        ],
    }


# --------------------------------------------------------------------------- job descriptions

def jd(jd_id: str, text: str, start: date, end: date, assigned: date = None,
       end_date: date = None, is_current: bool = True) -> Dict[str, Any]:
    return {
        "jd_id": jd_id,
        "job_description": text,
        "assigned_date": assigned or start,
        "end_date": end_date,
        "is_current": is_current,
        "effective_during_period": {"start": start, "end": end},
    }


def report(day: date, report_id: str = None, text: str = "weekly report") -> Dict[str, Any]:
    return {"text": text, "date": day, "report_id": report_id or f"rep-{day.isoformat()}"}


# --------------------------------------------------------------------------- monthly service

EMPLOYEE = {"id": 42, "name": "Test Employee", "wing": "Ops", "position": "Analyst"}


def weekly_analysis(day: date, sentiment=0.5, risk="medium", topics=None, achievements=None,
                    challenges=None, report_id=None, **extra) -> Dict[str, Any]:
    base = {
        "analysis_id": f"an-{day.isoformat()}",
        "report_id": report_id or f"rep-{day.isoformat()}",
        "date": day,
        "sentiment_score": sentiment,
        "risk_level": risk,
        "topics": topics if topics is not None else [],
        "achievements": achievements if achievements is not None else [],
        "challenges": challenges if challenges is not None else [],
        "credibility_rating": None,
        "exaggeration_flags": [],
        "performance_rating": None,
    }
    base.update(extra)
    return base


# --------------------------------------------------------------------------- quarterly service

def monthly_analysis(month: int, month_name: str = None, *, sentiment=0.5, report_ids=None,
                     achievements=None, challenges=None, impact_avg=None, risk=None,
                     progress=None, consistency=None, summary=None) -> Dict[str, Any]:
    return {
        "analysis_id": month,
        "month": month,
        "month_name": month_name or f"M{month}",
        "year": 2025,
        "weekly_report_ids": report_ids if report_ids is not None else [],
        "avg_sentiment_score": sentiment,
        "progress_trends": progress if progress is not None else {},
        "monthly_achievements": achievements if achievements is not None else [],
        "recurring_challenges": challenges if challenges is not None else [],
        "consistency_assessment": consistency if consistency is not None else {},
        "achievement_impact_avg": impact_avg,
        "monthly_risk_assessment": {"overall_risk_level": risk} if risk else {},
        "monthly_summary": summary,
    }
