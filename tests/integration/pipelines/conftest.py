"""Fixtures for the end-to-end pipeline characterization tests.

``ext`` patches every external boundary (LLM HTTP client, embedding provider,
vector store, SQL Server connector) with recording fakes. The database is real.
"""
import os
import time

import pytest

from tests.integration.pipelines.fakes import (
    FakeEmbeddingProvider,
    FakeOllamaClient,
    FakeVectorStore,
    Recorder,
)

COLLECTION = "employee_reports"
EMBED_DIM = 4


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    """Run each pipeline in an empty directory, so nothing it writes there leaks between tests."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _utc_timezone():
    """report_date_ts payloads and search cutoffs use naive local-time timestamps; pin TZ."""
    previous = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    yield
    if previous is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = previous
    time.tzset()


class External:
    def __init__(self):
        self.recorder = Recorder()
        self.llm = FakeOllamaClient(self.recorder)
        self.embedder = FakeEmbeddingProvider(self.recorder, dim=EMBED_DIM)
        self.vector_store = FakeVectorStore(self.recorder, collections={COLLECTION: EMBED_DIM})
        self.sqlserver = None

    @property
    def calls(self):
        return self.recorder.calls


@pytest.fixture
def ext(monkeypatch):
    import app.integrations.llm.ollama as ollama_host
    import app.services.embedding_service as embedding_service
    import app.services.sync_service as sync_service
    import app.services.vector_store_service as vector_store_service

    external = External()
    monkeypatch.setattr(ollama_host.ollama, "Client", external.llm)
    monkeypatch.setattr(embedding_service, "get_embedding_provider", lambda *a, **k: external.embedder)
    monkeypatch.setattr(vector_store_service, "get_vector_store", lambda *a, **k: external.vector_store)

    def _connector():
        assert external.sqlserver is not None, "test did not configure ext.sqlserver"
        return external.sqlserver

    monkeypatch.setattr(sync_service, "create_sqlserver_connector", _connector)
    return external
