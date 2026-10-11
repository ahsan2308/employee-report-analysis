"""The API analysis response models mirror the LLM output models field for field.

They differ on purpose in types (the API accepts any stored value) and descriptions,
but a field added to one and not the other means the API and the stored analyses drift.
"""
import inspect

from pydantic import BaseModel

import app.models.structured_models_llm as llm_models
import app.schemas.analysis_schema as api_models

# API model -> LLM model it mirrors, where the names differ
RENAMED = {"RiskAssessment": "QuarterlyRiskAssessment"}
API_ONLY = {"AnalysisResponse", "MonthlyAnalysisResponse", "MonthlyAnalysisSummary", "QuarterlyAnalysisResponse"}


def _models(module):
    return {
        name: cls for name, cls in vars(module).items()
        if inspect.isclass(cls) and issubclass(cls, BaseModel) and cls.__module__ == module.__name__
    }


def test_every_nested_api_model_has_an_llm_counterpart():
    api, llm = _models(api_models), _models(llm_models)
    missing = sorted(name for name in set(api) - API_ONLY if RENAMED.get(name, name) not in llm)
    assert missing == []


def test_api_models_have_the_llm_models_fields():
    api, llm = _models(api_models), _models(llm_models)
    drifted = {
        name: sorted(set(api[name].model_fields) ^ set(llm[RENAMED.get(name, name)].model_fields))
        for name in set(api) - API_ONLY
        if set(api[name].model_fields) != set(llm[RENAMED.get(name, name)].model_fields)
    }
    assert drifted == {}
