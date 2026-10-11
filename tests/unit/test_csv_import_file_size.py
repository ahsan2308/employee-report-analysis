"""The file-size check that picks an import's processing mode."""
import io

from app.services.csv_import_service import _file_size_mb


def test_size_of_a_file_path(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_bytes(b"x" * 1024 * 1024)
    assert _file_size_mb(str(path), None) == 1.0


def test_size_of_a_file_object_keeps_its_position():
    file_obj = io.BytesIO(b"x" * 512 * 1024)
    file_obj.seek(10)
    assert _file_size_mb(None, file_obj) == 0.5
    assert file_obj.tell() == 10


def test_unknown_size_is_none(tmp_path):
    assert _file_size_mb(None, object()) is None  # no seek/tell
    assert _file_size_mb(str(tmp_path / "missing.csv"), None) is None
