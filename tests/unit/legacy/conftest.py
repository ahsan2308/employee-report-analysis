"""Legacy tests write scratch files (prompts, formatted data) to the working directory."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
