"""Golden-master tests for the DB-free period helpers in app/services/db_service.py."""
from app.services import db_service


def outcome(fn, *args):
    try:
        return {"returned": fn(*args)}
    except Exception as exc:  # noqa: BLE001
        return {"raised": type(exc).__name__, "message": str(exc)}


YEARS = (1900, 1999, 2000, 2023, 2024, 2025, 2100)


def test_get_month_date_range_table(snapshot):
    table = {f"{y}-{m:02d}": db_service.get_month_date_range(y, m) for y in YEARS for m in range(1, 13)}
    snapshot("month_date_range_table", table)


def test_get_month_date_range_invalid(snapshot):
    snapshot("month_date_range_invalid", {
        f"{y}-{m}": outcome(db_service.get_month_date_range, y, m)
        for y, m in ((2025, 0), (2025, 13), (2025, -1), (0, 1), (10000, 1), (9999, 12), (1, 1))
    })


def test_get_quarter_date_range_table(snapshot):
    table = {f"{y}-Q{q}": db_service.get_quarter_date_range(y, q) for y in YEARS for q in range(1, 5)}
    snapshot("quarter_date_range_table", table)


def test_get_quarter_date_range_invalid(snapshot):
    snapshot("quarter_date_range_invalid", {
        f"{y}-Q{q}": outcome(db_service.get_quarter_date_range, y, q)
        for y, q in ((2025, 0), (2025, 5), (2025, -1), (0, 1), (9999, 4), (10000, 1))
    })


def test_quarter_and_month_ranges_agree():
    for year in YEARS:
        for quarter in range(1, 5):
            q_start, q_end = db_service.get_quarter_date_range(year, quarter)
            first = db_service.get_month_date_range(year, (quarter - 1) * 3 + 1)
            last = db_service.get_month_date_range(year, quarter * 3)
            assert (q_start, q_end) == (first[0], last[1])
