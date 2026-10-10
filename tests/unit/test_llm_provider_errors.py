"""B6: provider transport errors reach the caller instead of becoming "" or None."""
from unittest import mock

import pytest
import requests

from app.integrations.llm.ollama import OllamaProvider
from app.integrations.llm.vllm import VLLMProvider


def _http_response(status, payload=None):
    response = requests.Response()
    response.status_code = status
    response._content = b"{}" if payload is None else payload
    response.url = "http://vllm/v1/chat/completions"
    return response


def _chat(content):
    return _http_response(200, ('{"choices": [{"message": {"content": %s}}]}' % content).encode())


@pytest.fixture
def ollama():
    with mock.patch("app.integrations.llm.ollama.ollama.Client") as client:
        provider = OllamaProvider()
        yield provider, client.return_value


@pytest.mark.parametrize("method", ["generate_text", "generate_structured_output"])
def test_ollama_client_errors_propagate(ollama, method):
    provider, client = ollama
    client.generate.side_effect = ConnectionError("ollama down")
    with pytest.raises(ConnectionError):
        getattr(provider, method)("prompt")


@pytest.mark.parametrize("answer", ["", "{not json"])
def test_ollama_structured_output_without_json_returns_none(ollama, answer):
    provider, client = ollama
    client.generate.return_value = {"response": answer}
    assert provider.generate_structured_output("prompt") is None


@pytest.mark.parametrize("method", ["generate_text", "generate_structured_output"])
@pytest.mark.parametrize("failure", [
    requests.ConnectionError("vllm down"),
    _http_response(503),
], ids=["connection", "http_503"])
def test_vllm_transport_errors_propagate(method, failure):
    provider = VLLMProvider()
    post = mock.Mock(side_effect=failure) if isinstance(failure, Exception) else mock.Mock(return_value=failure)
    with mock.patch.object(provider.session, "post", post), pytest.raises(requests.RequestException):
        getattr(provider, method)("prompt")


def test_vllm_structured_output_without_json_returns_none():
    provider = VLLMProvider()
    with mock.patch.object(provider.session, "post", return_value=_chat('"no json here"')):
        assert provider.generate_structured_output("prompt") is None


def test_vllm_generate_text_returns_content():
    provider = VLLMProvider()
    with mock.patch.object(provider.session, "post", return_value=_chat('"hello"')):
        assert provider.generate_text("prompt") == "hello"
