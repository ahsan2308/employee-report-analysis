"""B12: the shared Qdrant client stays open while any `with vector_store:` block is still using it."""
import threading
from unittest import mock

import pytest

from app.integrations.vector_store import qdrant


@pytest.fixture
def provider(tmp_path):
    """A fresh singleton with a fake client (the provider keeps its state on the class)."""
    saved_instance, saved_state = qdrant.QdrantProvider._instance, dict(qdrant.QdrantProvider._conn_state)
    qdrant.QdrantProvider._instance = None
    qdrant.QdrantProvider._conn_state.update(initialized=False, connected=False, client=None, users=0)
    with mock.patch.object(qdrant, "QdrantClient") as client_class:
        client_class.side_effect = lambda **kwargs: mock.MagicMock(name="QdrantClient")
        yield qdrant.QdrantProvider(path=str(tmp_path))
    qdrant.QdrantProvider._instance = saved_instance
    qdrant.QdrantProvider._conn_state.clear()
    qdrant.QdrantProvider._conn_state.update(saved_state)


def test_inner_exit_keeps_the_shared_client_open(provider):
    with provider:
        client = provider._conn_state["client"]
        with provider:
            pass
        assert provider._conn_state["client"] is client
        client.close.assert_not_called()
    client.close.assert_called_once()
    assert provider._conn_state["client"] is None


def test_concurrent_blocks_share_one_client(provider):
    first_inside, second_done = threading.Event(), threading.Event()
    seen = {}

    def first():
        with provider:
            first_inside.set()
            second_done.wait(5)
            seen["client_after_second_exit"] = provider._conn_state["client"]

    def second():
        first_inside.wait(5)
        with provider:
            seen["client"] = provider._conn_state["client"]
        second_done.set()

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    assert seen["client_after_second_exit"] is seen["client"]
    seen["client"].close.assert_called_once()
    assert provider._conn_state["users"] == 0


def test_exit_after_an_error_still_releases(provider):
    with pytest.raises(RuntimeError):
        with provider:
            client = provider._conn_state["client"]
            raise RuntimeError("search failed")
    client.close.assert_called_once()
    assert provider._conn_state["users"] == 0
