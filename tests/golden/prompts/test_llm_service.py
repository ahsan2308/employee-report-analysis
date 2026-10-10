"""Golden master for prompt assembly + response parsing in app/services/llm_service.py.

The provider is replaced by a fake at ``app.services.llm_service.get_llm_provider``
so every call (prompt, schema, temperature, max_tokens, num_ctx) is captured.
``time`` and ``logger`` in that module are replaced so retries do not wait and
log calls can be inspected.
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.llm_service as llm_module
from app.models.structured_models_llm import EmployeeAnalysis, MonthlyAnalysis, QuarterlyAnalysis
from app.prompts.structured_prompts import StructuredPrompts
from tests.golden.prompts.fixtures import (
    FakeStructuredProvider,
    FakeTextProvider,
    describe_calls,
    monthly_full_data,
    quarterly_full_data,
    weekly_full_kwargs,
)

VALID = {"sentiment": "positive", "risk_level": "low", "topics": ["threat assessment"]}
VALID_JSON = json.dumps(VALID)

# name -> text the provider's generate_text returns (or raises)
TEXT_RESPONSES = {
    "valid_json": VALID_JSON,
    "fenced_json": f"Here you go:\n```json\n{VALID_JSON}\n```\nThanks!",
    "fenced_no_lang": f"```\n{VALID_JSON}\n```",
    "extra_text_around_braces": f"Sure! The analysis is {VALID_JSON} -- hope this helps.",
    "invalid_fence_valid_braces": "```json\nnot json\n``` but later {\"a\": 1}",
    "two_objects": '{"a": 1} and then {"b": 2}',
    "invalid_json": "{sentiment: positive, risk_level: low",
    "json_array": "[1, 2, 3]",
    "bare_number": "42",
    "empty_string": "",
    "whitespace": "   \n  ",
    "none": None,
}


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Install fakes; returns a namespace used to build services and read sleeps/logs."""
    monkeypatch.chdir(tmp_path)  # quarterly builder writes a debug file into CWD
    sleeps = []
    logger = MagicMock()
    monkeypatch.setattr(llm_module, "time", SimpleNamespace(sleep=sleeps.append))
    monkeypatch.setattr(llm_module, "logger", logger)
    factory_calls = []

    def make(provider):
        def fake_get_llm_provider(**kwargs):
            factory_calls.append(kwargs)
            return provider

        monkeypatch.setattr(llm_module, "get_llm_provider", fake_get_llm_provider)
        return llm_module.LLMService(model="golden-test-model")

    return SimpleNamespace(make=make, sleeps=sleeps, logger=logger, factory_calls=factory_calls)


# ---------------------------------------------------------------------------
# Entry points: one per period, the builder they use and the default model
# ---------------------------------------------------------------------------

def _weekly_call(service, **kw):
    return service.analyze_report(**weekly_full_kwargs(), **kw)


def _weekly_prompt():
    return StructuredPrompts.employee_analysis_prompt(**weekly_full_kwargs())


ENTRY_POINTS = {
    "weekly": (_weekly_call, _weekly_prompt),
    "monthly": (
        lambda s, **kw: s.analyze_monthly_reports(monthly_full_data(), **kw),
        lambda: StructuredPrompts.monthly_analysis_prompt(monthly_full_data()),
    ),
    "quarterly": (
        lambda s, **kw: s.analyze_quarterly_reports(quarterly_full_data(), **kw),
        lambda: StructuredPrompts.quarterly_analysis_prompt(quarterly_full_data()),
    ),
}


def _run(env, period, provider, **kw):
    call, prompt_fn = ENTRY_POINTS[period]
    service = env.make(provider)
    result = call(service, **kw)
    task_prompt = prompt_fn()
    return {
        "result": result,
        "provider_calls": describe_calls(provider.calls, task_prompt),
        "sleeps": list(env.sleeps),
    }


def test_service_init(env):
    service = env.make(FakeTextProvider())
    assert env.factory_calls == [{"model": "golden-test-model"}]
    assert (service.model, service.retry_delay, service.max_retries) == ("golden-test-model", 1.0, 3)


# ---------------------------------------------------------------------------
# Native structured output path
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("period", sorted(ENTRY_POINTS))
def test_native_structured_output_success(env, snapshot, period):
    """Native dict returned verbatim (no validation); pydantic class passed as json_schema."""
    provider = FakeStructuredProvider([{"anything": "goes", "not": ["validated"]}])
    snapshot(f"llm_{period}_native_success", _run(env, period, provider))


@pytest.mark.parametrize("period", sorted(ENTRY_POINTS))
def test_native_none_falls_back_to_text(env, snapshot, period):
    """None from native output -> text generation with the schema+example appended."""
    provider = FakeStructuredProvider([None], text_responses=[TEXT_RESPONSES["fenced_json"]])
    snapshot(f"llm_{period}_native_none_text_fallback", _run(env, period, provider))


def test_native_exception_falls_back_to_text(env, snapshot):
    provider = FakeStructuredProvider([RuntimeError("native boom")], text_responses=[VALID_JSON])
    snapshot("llm_weekly_native_exception_text_fallback", _run(env, "weekly", provider))


@pytest.mark.parametrize("period", sorted(ENTRY_POINTS))
def test_native_with_default_custom_format(env, snapshot, period):
    """use_custom_format=True with no format: the built-in template is converted to a flat
    JSON schema (lists -> array of strings, dicts -> bare object) and passed as json_schema."""
    provider = FakeStructuredProvider([None], text_responses=[VALID_JSON])
    snapshot(f"llm_{period}_custom_format_default", _run(env, period, provider, use_custom_format=True))


def test_num_ctx_is_forwarded(env):
    provider = FakeStructuredProvider([{"ok": True}])
    _run(env, "monthly", provider, num_ctx=1234)
    assert provider.calls[0]["num_ctx"] == 1234


# ---------------------------------------------------------------------------
# Text path: JSON extraction from raw responses
# ---------------------------------------------------------------------------

def test_text_path_response_parsing_table(env, snapshot):
    """Weekly entry point, provider without native support: raw text -> returned value."""
    table = {}
    for name, raw in TEXT_RESPONSES.items():
        provider = FakeTextProvider([raw])
        run = _run(env, "weekly", provider)
        table[name] = {"result": run["result"], "num_provider_calls": len(provider.calls)}
    snapshot("llm_text_path_parsing_table", table)


@pytest.mark.parametrize("period", sorted(ENTRY_POINTS))
def test_text_path_full_call(env, snapshot, period):
    provider = FakeTextProvider([TEXT_RESPONSES["extra_text_around_braces"]])
    snapshot(f"llm_{period}_text_path", _run(env, period, provider))


def test_text_path_provider_always_raises(env, snapshot):
    """3 attempts with exponential sleeps 1.0 then 2.0, then the error is returned as a failure (B6 fixed)."""
    provider = FakeTextProvider([ConnectionError("down")] * 5)
    snapshot("llm_weekly_text_path_provider_always_raises", _run(env, "weekly", provider))


def test_text_path_provider_recovers_after_retry(env, snapshot):
    provider = FakeTextProvider([TimeoutError("slow"), VALID_JSON])
    snapshot("llm_weekly_text_path_retry_then_success", _run(env, "weekly", provider))


def test_native_raises_then_text_always_raises(env, snapshot):
    provider = FakeStructuredProvider([RuntimeError("native boom")], text_responses=[OSError("x")] * 3)
    snapshot("llm_quarterly_all_paths_fail", _run(env, "quarterly", provider))


# ---------------------------------------------------------------------------
# Error handling and lower-level helpers
# ---------------------------------------------------------------------------

def test_invalid_custom_format_returns_error_dict(env, snapshot):
    provider = FakeStructuredProvider([{"never": "reached"}])
    out = {}
    for period in sorted(ENTRY_POINTS):
        run = _run(env, period, provider, use_custom_format=True, custom_format=["not", "a", "dict"])
        out[period] = run["result"]
    assert provider.calls == []
    snapshot("llm_invalid_custom_format_error", out)


def test_get_structured_response_requires_a_format(env):
    service = env.make(FakeTextProvider())
    with pytest.raises(ValueError, match="Either response_format or pydantic_model must be provided"):
        service.get_structured_response("prompt")


def test_get_structured_response_simple_template_conversion(env, snapshot):
    """Flat template -> JSON schema. Note: bool values hit the number branch first."""
    provider = FakeStructuredProvider([None], text_responses=['{"ok": 1}'])
    service = env.make(provider)
    template = {"text": "s", "items": ["a"], "count": 3, "ratio": 0.5, "flag": True, "nested": {"k": "v"}, "nothing": None}
    result = service.get_structured_response("TASK", response_format=template, temperature=0.9, max_tokens=77)
    snapshot("llm_simple_template_conversion", {"result": result, "provider_calls": describe_calls(provider.calls, "TASK")})


def test_get_structured_response_schema_example_generation(env, snapshot):
    """JSON-schema input -> example_format generation by property type."""
    provider = FakeTextProvider(['{"ok": 1}'])
    service = env.make(provider)
    schema = {
        "type": "object",
        "properties": {
            "arr": {"type": "array"},
            "num": {"type": "number"},
            "int": {"type": "integer"},
            "flag": {"type": "boolean"},
            "obj": {"type": "object", "properties": {"a": {}, "b": {}}},
            "bare_obj": {"type": "object"},
            "ref": {"$ref": "#/$defs/X"},
        },
    }
    result = service.get_structured_response("TASK", response_format=schema)
    snapshot("llm_schema_example_generation", {"result": result, "provider_calls": describe_calls(provider.calls, "TASK")})


@pytest.mark.parametrize("model", [EmployeeAnalysis, MonthlyAnalysis, QuarterlyAnalysis])
def test_text_fallback_format_instructions_per_model(env, snapshot, model):
    """Exact instructions appended to the task prompt when native output is unavailable."""
    provider = FakeTextProvider(['{"ok": true}'])
    service = env.make(provider)
    service.get_structured_response("TASK", pydantic_model=model)
    call = provider.calls[0]
    assert call["prompt"].startswith("TASK\n\n")
    snapshot(f"llm_format_instructions_{model.__name__}", call["prompt"][len("TASK\n\n"):])


def test_generate_text_retries_argument(env, snapshot):
    """retries=None or 0 -> self.max_retries (3); retries=1 -> no sleep at all. The last error is raised."""
    out = {}
    for retries in (None, 0, 1, 2):
        env.sleeps.clear()
        provider = FakeTextProvider([RuntimeError("x")] * 5)
        service = env.make(provider)
        with pytest.raises(RuntimeError) as raised:
            service.generate_text("p", retries=retries)
        out[str(retries)] = {"raised": repr(raised.value), "attempts": len(provider.calls), "sleeps": list(env.sleeps)}
    snapshot("llm_generate_text_retries", out)


def test_generate_text_defaults(env, snapshot):
    provider = FakeTextProvider(["raw"])
    service = env.make(provider)
    assert service.generate_text("p") == "raw"
    snapshot("llm_generate_text_defaults", describe_calls(provider.calls, "p"))


def test_prompts_are_not_logged(env):
    """B13 fixed: prompts carry report text, so only their length is logged, at any level."""
    provider = FakeStructuredProvider([{"r": 1}, {"r": 2}, {"r": 3}])
    service = env.make(provider)
    service.analyze_report(**weekly_full_kwargs())
    service.analyze_monthly_reports(monthly_full_data())
    service.analyze_quarterly_reports(quarterly_full_data())
    prompts = [_weekly_prompt(), StructuredPrompts.monthly_analysis_prompt(monthly_full_data()),
               StructuredPrompts.quarterly_analysis_prompt(quarterly_full_data())]
    logged = [str(arg) for level in ("debug", "info", "warning", "error")
              for call in getattr(env.logger, level).call_args_list for arg in call.args]
    report_text = weekly_full_kwargs()["report_text"]
    assert not any(report_text in message for message in logged)
    assert not any(prompt[:200] in message for prompt in prompts for message in logged)
    info_messages = [c.args[0] for c in env.logger.info.call_args_list]
    assert f"Generated prompt: {len(prompts[0])} characters" in info_messages
    assert f"Generated prompt: {len(prompts[1])} characters" in info_messages
