"""One database object (engine and connection pool) per process, and tables created at server start."""
from unittest import mock

from fastapi.testclient import TestClient

from app.db import database


def test_get_database_reuses_one_engine_per_process():
    first = database.get_database()
    assert database.get_database() is first
    assert database.get_database().engine is first.engine


def test_forked_process_builds_its_own_engine_without_closing_the_parents(monkeypatch):
    parent = database.get_database()
    with mock.patch.object(parent.engine, "dispose") as dispose:
        monkeypatch.setattr(database.os, "getpid", lambda: -1)  # as seen from a forked child
        child = database.get_database()
    assert child is not parent
    assert child.engine is not parent.engine
    dispose.assert_called_once_with(close=False)
    assert all(key[0] == -1 for key in database._databases)


def test_tables_are_created_when_the_server_starts_not_on_import():
    import app.api.main as main

    with mock.patch.object(type(database.get_database()), "create_tables") as create_tables:
        create_tables.assert_not_called()
        with TestClient(main.app):
            create_tables.assert_called_once_with()
