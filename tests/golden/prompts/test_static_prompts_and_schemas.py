"""Golden master for the small static prompt helpers and the LLM output schemas."""
import inspect

import pydantic
import pytest

import app.models.structured_models_llm as llm_models
from app.prompts.structured_prompts import StructuredPrompts

SIMPLE_EXAMPLE = {"summary": "example value", "tags": ["example item"], "score": 30}
SCHEMA = {"type": "object", "properties": {"summary": {"type": "string"}, "score": {"type": "number"}}}


def test_general_json_instruction(snapshot):
    snapshot("static_general_json_instruction", StructuredPrompts.general_json_instruction())


def test_format_schema_prompt(snapshot):
    snapshot("static_format_schema_prompt", StructuredPrompts.format_schema_prompt(SCHEMA, SIMPLE_EXAMPLE))


def test_format_simple_prompt(snapshot):
    snapshot("static_format_simple_prompt", StructuredPrompts.format_simple_prompt(SIMPLE_EXAMPLE))


def test_combine_prompt():
    assert StructuredPrompts.combine_prompt("TASK", "FORMAT") == "TASK\n\nFORMAT"


def test_public_prompt_api_surface(snapshot):
    """Names and signatures of every StructuredPrompts helper (all static)."""
    surface = {}
    for name, member in vars(StructuredPrompts).items():
        if isinstance(member, staticmethod):
            surface[name] = str(inspect.signature(member.__func__))
        elif not name.startswith("__"):
            surface[name] = f"<non-static {type(member).__name__}>"
    snapshot("static_api_surface", surface)


LLM_MODELS = sorted(
    name
    for name, obj in vars(llm_models).items()
    if inspect.isclass(obj)
    and issubclass(obj, pydantic.BaseModel)
    and obj is not pydantic.BaseModel
    and obj.__module__ == llm_models.__name__
)


def test_llm_model_inventory(snapshot):
    snapshot("schema__inventory", LLM_MODELS)


@pytest.mark.parametrize("model_name", LLM_MODELS)
def test_llm_model_json_schema(snapshot, model_name):
    snapshot(f"schema_{model_name}", getattr(llm_models, model_name).model_json_schema())
