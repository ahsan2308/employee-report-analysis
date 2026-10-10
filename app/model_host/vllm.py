"""Compatibility alias: this module is app.integrations.llm.vllm."""
import sys

import app.integrations.llm.vllm as _module

sys.modules[__name__] = _module
