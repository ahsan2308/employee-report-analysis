"""Characterization of app/services/csv/error_handler.py (ImportErrorHandler)."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from pydantic import BaseModel, ValidationError

from app.services.csv.row_models import CombinedCSVRow
from app.services.csv.error_handler import ErrorCategory, ImportErrorHandler
from tests.golden.imports_sync.helpers import handler_errors, outcome, tag


def _populated_handler():
    h = ImportErrorHandler()
    h.add_error(1, "generic problem")
    h.add_validation_error(2, "Name too short", field_name="Name", row_data={"Name": "A"})
    h.add_validation_error(2, "BPS bad", field_name="BPS", row_data={"BPS": "X"})
    h.add_processing_error(3, "boom", row_data={"x": 1}, exception=RuntimeError("boom"))
    h.add_database_error(4, "unique violation", row_data={"id": 4}, exception=ValueError("dup"))
    h.add_error(5, "Name too short", field_name="Name", category=ErrorCategory.SYSTEM)
    h.add_validation_error(0, "header problem", field_name="")
    return h


def test_collection_and_summaries(snapshot):
    h = _populated_handler()
    out = {
        "errors": handler_errors(h),
        "count": h.get_error_count(),
        "count_by_category": {k.value: v for k, v in h.get_error_count_by_category().items()},
        "count_by_category_key_types": sorted({type(k).__name__ for k in h.get_error_count_by_category()}),
        "summary_by_field": h.get_error_summary_by_field(),
        "patterns": list(h.get_error_patterns().items()),
        "get_errors_is_same_list": h.get_errors() is h.errors,
        "percentages": {str(n): h.get_error_percentage(n) for n in [-1, 0, 1, 3, 6, 100]},
    }
    h.clear()
    out["after_clear"] = {"count": h.get_error_count(), "percentage_10": h.get_error_percentage(10),
                          "patterns": h.get_error_patterns()}
    snapshot("error_handler_collection", out)


def test_should_abort_matrix(snapshot):
    out = {}
    for n_err_rows in [0, 1, 25]:
        h = ImportErrorHandler()
        for r in range(n_err_rows):
            h.add_validation_error(r + 1, "e")
            h.add_validation_error(r + 1, "e2")  # duplicate row: counted once in percentage
        for total in [0, 10, 199, 200, 250, 1000]:
            for threshold in [0.0, 10.0, 12.5]:
                for stop in [False, True]:
                    key = f"errrows={n_err_rows}|total={total}|threshold={threshold}|stop={stop}"
                    out[key] = list(h.should_abort(total, threshold, stop))
        out[f"errrows={n_err_rows}|total=50|min_rows=10"] = list(
            h.should_abort(50, 10.0, False, minimum_rows_before_threshold=10))
    snapshot("error_handler_should_abort", out)


class _Opaque:
    def __str__(self):
        return "opaque-object"

    def __repr__(self):
        return "Opaque()"


class _Strict(BaseModel):
    a: int
    nested: dict[str, int]


def test_normalize_pydantic_errors(snapshot):
    h = ImportErrorHandler()
    try:
        CombinedCSVRow(Name="<x>", Designation="D", From="2024-01-01", To="2023-01-01", BPS="Q")
    except ValidationError as exc:
        h.normalize_pydantic_errors(exc, 7, {"raw": True})
    try:
        CombinedCSVRow(Name="Valid Name", Designation="Officer", From="2024-02-01", To="2024-01-01",
                       Tasks_Completed="x")
    except ValidationError as exc:  # model-level error: empty loc
        h.normalize_pydantic_errors(exc, 8, {"raw": 2})
    try:
        _Strict(a="x", nested={"k": "v"})
    except ValidationError as exc:  # nested loc path joined with dots
        h.normalize_pydantic_errors(exc, 9, None)

    broken = MagicMock(spec=ValidationError)
    broken.errors.side_effect = RuntimeError("cannot list errors")
    broken.__str__ = lambda self: "broken validation error"
    h.normalize_pydantic_errors(broken, 10, {"r": 1})
    snapshot("error_handler_normalize_pydantic", handler_errors(h))


def test_to_db_models(snapshot):
    h = ImportErrorHandler()
    h.add_validation_error(1, "plain", field_name="Name", row_data={"Name": "A", "n": 1, "none": None})
    h.add_processing_error(2, "non-serializable", row_data={
        "d": date(2024, 1, 2), "dt": datetime(2024, 1, 2, 3, 4, 5), "dec": Decimal("1.50"),
        "s": {1}, "ok": "fine", "none": None, "nan": float("nan"), "obj": _Opaque(),
    })
    h.add_database_error(3, "no data", row_data=None)
    h.add_error(4, "empty dict", row_data={})
    models = h.to_db_models("job-123")
    out = [
        {"type": type(m).__name__, "job_id": m.job_id, "row_number": m.row_number, "field_name": m.field_name,
         "error_message": m.error_message, "row_data": tag(m.row_data)}
        for m in models
    ]
    # Original error objects keep their un-cleaned row_data
    out.append({"original_row_data_after": tag(h.errors[1].row_data)})
    out.append({"empty_handler": outcome(lambda: ImportErrorHandler().to_db_models("j"))})
    snapshot("error_handler_to_db_models", out)
