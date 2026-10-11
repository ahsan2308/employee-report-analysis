"""get_embeddings sends at most VECTOR_EMBEDDING_BATCH_SIZE texts per provider call."""
import app.services.embedding_service as embedding_service


class FakeProvider:
    model = "fake"

    def __init__(self, fail_on_call=None):
        self.calls = []
        self.fail_on_call = fail_on_call

    def get_embedding(self, texts, is_query=False):
        self.calls.append(list(texts))
        if self.fail_on_call == len(self.calls):
            return []
        return [[float(len(text))] for text in texts]


def _use(monkeypatch, provider, batch_size):
    monkeypatch.setattr(embedding_service, "get_embedding_provider", lambda *a, **k: provider)
    monkeypatch.setattr(embedding_service, "VECTOR_EMBEDDING_BATCH_SIZE", batch_size)


def test_texts_are_embedded_in_batches_in_order(monkeypatch):
    provider = FakeProvider()
    _use(monkeypatch, provider, 2)
    texts = ["a", "bb", "ccc", "dddd", "eeeee"]
    assert embedding_service.get_embeddings(texts) == [[1.0], [2.0], [3.0], [4.0], [5.0]]
    assert provider.calls == [["a", "bb"], ["ccc", "dddd"], ["eeeee"]]


def test_a_failed_batch_fails_the_whole_call(monkeypatch):
    _use(monkeypatch, FakeProvider(fail_on_call=2), 2)
    assert embedding_service.get_embeddings(["a", "b", "c"]) == []


def test_provider_error_returns_no_embeddings(monkeypatch):
    class Broken(FakeProvider):
        def get_embedding(self, texts, is_query=False):
            raise RuntimeError("down")

    _use(monkeypatch, Broken(), 10)
    assert embedding_service.get_embeddings(["a"]) == []
