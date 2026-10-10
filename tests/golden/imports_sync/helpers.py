"""Shared helpers for the imports/sync characterization tests.

Values are converted to JSON-friendly, *type-tagged* forms so a snapshot shows
whether a field came out as a string, a date or a number.
"""
import math
import re
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from pydantic import ValidationError

DATA_DIR = Path(__file__).parent / "data"

_ADDR_RE = re.compile(r"0x[0-9a-fA-F]+|(?<=id=')\d+")
_TODAY_RE = re.compile(r"Today is \d{4}-\d{2}-\d{2}")


def tag(value: Any) -> Any:
    """Recursively convert a value into JSON-safe data that keeps type information."""
    if isinstance(value, dict):
        return {str(k): tag(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [tag(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return {"<set>": sorted(tag(v) for v in value)}
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "<float nan>"
        return value
    if isinstance(value, datetime):
        return f"<datetime {value.isoformat()}>"
    if isinstance(value, date):
        return f"<date {value.isoformat()}>"
    if isinstance(value, time):
        return f"<time {value.isoformat()}>"
    if isinstance(value, Decimal):
        return f"<Decimal {value}>"
    if value is pd.NaT:
        return "<NaT>"
    if isinstance(value, bytes):
        return f"<bytes {value!r}>"
    return _ADDR_RE.sub("0x?", f"<{type(value).__name__} {value!r}>")


def scrub_today(text: str) -> str:
    return _TODAY_RE.sub("Today is <today>", text)


def errors_of(exc: ValidationError) -> list:
    """Pydantic errors reduced to loc/type/msg (date of today scrubbed)."""
    return [
        {"loc": [str(p) for p in err.get("loc", ())], "type": err.get("type"), "msg": scrub_today(err.get("msg", ""))}
        for err in exc.errors()
    ]


def outcome(fn: Callable[[], Any]) -> Any:
    """Run fn; return {'ok': tagged result} or a description of what it raised."""
    try:
        return {"ok": tag(fn())}
    except ValidationError as exc:
        return {"validation_errors": errors_of(exc)}
    except Exception as exc:  # noqa: BLE001 - characterization: record whatever is raised
        return {"raised": type(exc).__name__, "message": scrub_today(str(exc)).replace(str(DATA_DIR), "<data>")}


def model_outcome(model_cls, raw: dict) -> Any:
    return outcome(lambda: model_cls(**raw).model_dump())


def df_snapshot(df: pd.DataFrame) -> dict:
    return {
        "columns": [str(c) for c in df.columns],
        "dtypes": {str(c): str(t) for c, t in df.dtypes.items()},
        "index": [tag(i) for i in df.index.tolist()],
        "records": tag(df.to_dict("records")),
    }


def handler_errors(handler) -> list:
    return [
        {
            "row_number": e.row_number,
            "field_name": e.field_name,
            "category": e.category.value,
            "error_message": scrub_today(e.error_message),
            "row_data": tag(e.row_data),
            "exception": None if e.exception is None else type(e.exception).__name__,
        }
        for e in handler.errors
    ]
