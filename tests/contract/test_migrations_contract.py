"""Alembic revision graph. Revision IDs are recorded in deployed databases and must never change,
including the placeholder-looking ones ('create_a_unique_id_here', '812ef54a9d2b' in xxx_*.py)."""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_revision_graph(snapshot):
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    scripts = ScriptDirectory.from_config(config)
    revisions = [
        {"revision": rev.revision, "down_revision": rev.down_revision, "file": Path(rev.path).name}
        for rev in scripts.walk_revisions()
    ]
    snapshot("revision_graph", {"heads": scripts.get_heads(), "base": scripts.get_bases(), "chain_head_to_base": revisions})
