"""Minimal golden-file snapshots.

Strings are stored verbatim as ``.txt``; everything else as pretty, key-sorted
``.json``. A missing snapshot fails unless updating, so CI never silently
records a new baseline. Update with ``pytest --snapshot-update`` (or
``SNAPSHOT_UPDATE=1``) and review the diff before committing.
"""
import json
from pathlib import Path
from typing import Any


def to_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str, ensure_ascii=False) + "\n"


class SnapshotAsserter:
    def __init__(self, directory: Path, update: bool = False):
        self.directory = directory
        self.update = update

    def __call__(self, name: str, value: Any) -> None:
        if isinstance(value, str):
            path, text = self.directory / f"{name}.txt", value
        else:
            path, text = self.directory / f"{name}.json", to_json(value)

        if self.update:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return

        assert path.exists(), f"missing snapshot {path}; run pytest --snapshot-update and review it"
        expected = path.read_text(encoding="utf-8")
        assert text == expected, f"snapshot mismatch: {path}"
