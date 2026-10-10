"""Characterization of app/services/csv/csv_reader.py (PandasCSVReader)."""
import io

import pytest

from app.services.csv.csv_reader import PandasCSVReader
from app.services.csv.processors.employee_report_processor import EmployeeReportProcessor
from app.services.csv.processors.job_description_processor import JobDescriptionProcessor
from app.services.csv.processors.supervisor_feedback_processor import SupervisorFeedbackProcessor
from app.services.csv.processors.vision_data_processor import VisionDataProcessor
from tests.golden.imports_sync.helpers import DATA_DIR, df_snapshot, outcome, tag

SAMPLE_FILES = sorted(p.name for p in DATA_DIR.iterdir() if p.is_file())

REQUIRED = {
    "employee": EmployeeReportProcessor.REQUIRED_HEADERS,
    "vision": VisionDataProcessor.REQUIRED_HEADERS,
    "job_description": JobDescriptionProcessor.REQUIRED_HEADERS,
    "supervisor": SupervisorFeedbackProcessor.REQUIRED_HEADERS,
}


def _reader_state(reader):
    return {
        "detected_encoding": reader._detected_encoding,
        "detected_delimiter": reader._detected_delimiter,
        "delimiter_attr": reader.delimiter,
        "headers": reader.get_headers(),
    }


def _read_rows(path, **ctor):
    reader = PandasCSVReader(**ctor)
    result = {"rows": outcome(lambda: list(reader.read_csv(file_path=str(path))))}
    result["state"] = _reader_state(reader)
    result["total_rows"] = outcome(reader.get_total_rows)
    if reader.headers:
        result["missing_required"] = {k: reader.validate_headers(v) for k, v in REQUIRED.items()}
    return result


@pytest.mark.parametrize("name", SAMPLE_FILES)
def test_read_csv_from_path(name, snapshot):
    snapshot(f"reader_read_csv__{name}", _read_rows(DATA_DIR / name))


@pytest.mark.parametrize("name", SAMPLE_FILES)
def test_read_dataframes_chunked(name, snapshot):
    reader = PandasCSVReader(chunk_size=2)
    chunks = outcome(lambda: [df_snapshot(df) for df in reader.read_dataframes(file_path=str(DATA_DIR / name))])
    snapshot(f"reader_read_dataframes_chunk2__{name}", {"chunks": chunks, "state": _reader_state(reader)})


@pytest.mark.parametrize("name", ["employee_reports_bom.csv", "vision_data.tsv", "employee_reports_cp1252.csv"])
def test_read_csv_from_file_objects(name, snapshot):
    raw = (DATA_DIR / name).read_bytes()
    result = {}

    reader = PandasCSVReader()
    result["bytesio"] = outcome(lambda: list(reader.read_csv(file_obj=io.BytesIO(raw))))
    result["bytesio_state"] = _reader_state(reader)
    result["bytesio_total_rows"] = outcome(reader.get_total_rows)

    reader = PandasCSVReader()
    result["raw_bytes"] = outcome(lambda: list(reader.read_csv(file_obj=raw)))
    result["raw_bytes_state"] = _reader_state(reader)

    text = raw.decode("utf-8", errors="replace")
    reader = PandasCSVReader()
    result["stringio"] = outcome(lambda: list(reader.read_csv(file_obj=io.StringIO(text))))
    result["stringio_state"] = _reader_state(reader)
    snapshot(f"reader_file_objects__{name}", result)


DELIMITER_CASES = {
    "ctor_tab_on_comma_file": ({"delimiter": "\t"}, {}),
    "ctor_comma": ({"delimiter": ","}, {}),
    "ctor_multi_char_invalid": ({"delimiter": "::"}, {}),
    "ctor_empty_string": ({"delimiter": ""}, {}),
    "ctor_non_string": ({"delimiter": 5}, {}),
    "ctor_disallowed_char": ({"delimiter": "#"}, {}),
    "call_semicolon_overrides_ctor": ({"delimiter": ","}, {"delimiter": ";"}),
    "call_colon": ({}, {"delimiter": ":"}),
    "call_encoding_ascii": ({}, {"encoding": "ascii"}),
    "ctor_encoding_latin1": ({"encoding": "latin-1"}, {}),
}


@pytest.mark.parametrize("case", sorted(DELIMITER_CASES))
def test_read_csv_delimiter_and_encoding_overrides(case, snapshot):
    ctor, call = DELIMITER_CASES[case]
    out = {}
    for name in ["employee_reports_semicolon.csv", "employee_reports_cp1252.csv"]:
        reader = PandasCSVReader(**ctor)
        rows = outcome(lambda: list(reader.read_csv(file_path=str(DATA_DIR / name), **call)))
        out[name] = {"rows": rows, "state": _reader_state(reader)}
    snapshot(f"reader_overrides__{case}", out)


def test_read_dataframes_delimiter_falsy_override(snapshot):
    # read_dataframes uses `delimiter or self.delimiter` while read_csv uses `is not None`.
    out = {}
    for label, ctor, call in [
        ("ctor_semicolon_call_empty", {"delimiter": ";"}, {"delimiter": ""}),
        ("ctor_none_call_tab", {}, {"delimiter": "\t"}),
    ]:
        reader = PandasCSVReader(**ctor)
        out[label] = {
            "chunks": outcome(lambda: [df_snapshot(df) for df in reader.read_dataframes(
                file_path=str(DATA_DIR / "employee_reports_semicolon.csv"), **call)]),
            "state": _reader_state(reader),
        }
    snapshot("reader_read_dataframes_delimiter_overrides", out)


def test_detection_helpers(snapshot):
    out = {}
    for name in SAMPLE_FILES:
        path = str(DATA_DIR / name)
        reader = PandasCSVReader()
        enc = reader._detect_encoding(path)
        out[name] = {
            "encoding": enc,
            "encoding_cached_second_call": reader._detect_encoding(path),
            "delimiter": reader._detect_delimiter(path),
            "delimiter_with_explicit_utf8": PandasCSVReader()._detect_delimiter(path, "utf-8"),
        }
    # File objects: _detect_encoding(file_obj=...) vs positional (as the reader itself calls it)
    raw = (DATA_DIR / "employee_reports_cp1252.csv").read_bytes()
    bio = io.BytesIO(raw)
    bio.seek(5)
    out["__fileobj__"] = {
        "encoding_via_file_obj_kw": PandasCSVReader()._detect_encoding(file_obj=bio),
        "position_restored": bio.tell(),
        "encoding_positional_fileobj": PandasCSVReader()._detect_encoding(io.BytesIO(raw)),
        "encoding_ctor_wins": PandasCSVReader(encoding="utf-16")._detect_encoding("nope.csv"),
        "encoding_missing_path": PandasCSVReader()._detect_encoding("does/not/exist.csv"),
        "delimiter_text_stream": PandasCSVReader()._detect_delimiter(io.StringIO("a|b|c\n1|2|3\n"), "utf-8"),
        "delimiter_binary_stream": PandasCSVReader()._detect_delimiter(io.BytesIO(b"a;b;c\n1;2;3\n"), "utf-8"),
        "delimiter_empty_stream": PandasCSVReader()._detect_delimiter(io.StringIO(""), "utf-8"),
        "delimiter_blank_lines_only": PandasCSVReader()._detect_delimiter(io.StringIO("\n\n  \n"), "utf-8"),
        "delimiter_sniffer_fail_manual": PandasCSVReader()._detect_delimiter(
            io.StringIO("a,b|c,d\n"), "utf-8"),
        "delimiter_space_separated": PandasCSVReader()._detect_delimiter(io.StringIO("a b c\n1 2 3\n"), "utf-8"),
    }
    snapshot("reader_detection_helpers", tag(out))


def test_misc_api(snapshot):
    out = {}
    reader = PandasCSVReader()
    out["validate_headers_before_read"] = outcome(lambda: reader.validate_headers(["Name"]))
    out["total_rows_before_read"] = outcome(reader.get_total_rows)
    out["get_file_obj_none"] = outcome(lambda: reader._get_file_obj())
    out["get_file_obj_bytes_type"] = type(reader._get_file_obj(file_obj=b"a,b\n")).__name__
    out["get_file_obj_path"] = reader._get_file_obj(file_path="x.csv")
    out["defaults"] = {
        "chunk_size": reader.chunk_size,
        "encoding": reader.encoding,
        "delimiter": reader.delimiter,
        "common_encodings": PandasCSVReader.COMMON_ENCODINGS,
    }
    # Row count fallback when pandas cannot parse: ragged lines
    ragged = io.StringIO('a,b\n1,2,3,4\n"unterminated\n')
    out["count_rows_ragged_stream"] = outcome(lambda: PandasCSVReader()._count_total_rows(ragged))
    out["count_rows_stream"] = outcome(lambda: PandasCSVReader()._count_total_rows(io.StringIO("a,b\n1,2\n\n3,4\n")))
    snapshot("reader_misc_api", out)
