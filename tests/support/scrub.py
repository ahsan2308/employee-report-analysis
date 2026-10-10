"""Replace run-dependent values (UUIDs, timestamps) so snapshots are stable."""
import re
from typing import Any

UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
TIMESTAMP_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:?\d{2}|Z)?\b")


def scrub(value: Any, keep_uuids: tuple = ()) -> Any:
    """Recursively replace UUIDs with <uuid:N> (stable numbering) and timestamps with <timestamp>.

    Dates without a time part are left alone: they are usually business data.
    """
    seen: dict = {}

    def replace_uuid(match):
        text = match.group(0).lower()
        if text in keep_uuids:
            return text
        seen.setdefault(text, f"<uuid:{len(seen) + 1}>")
        return seen[text]

    def walk(item):
        if isinstance(item, dict):
            return {walk(key): walk(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [walk(val) for val in item]
        if isinstance(item, str):
            return TIMESTAMP_RE.sub("<timestamp>", UUID_RE.sub(replace_uuid, item))
        return item

    return walk(value)
