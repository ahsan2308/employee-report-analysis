"""check_qdrant_version reads the installed distribution's version."""
from importlib.metadata import version

from app.utils.version_check import check_qdrant_version


def test_reports_installed_qdrant_client_version():
    assert check_qdrant_version() == (True, version("qdrant-client"))
