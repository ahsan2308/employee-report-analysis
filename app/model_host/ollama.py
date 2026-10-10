"""Compatibility alias: this module is app.integrations.llm.ollama."""
import sys

import app.integrations.llm.ollama as _module

sys.modules[__name__] = _module
