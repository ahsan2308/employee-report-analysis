"""Compatibility alias: this module is app.integrations.llm.base."""
import sys

import app.integrations.llm.base as _module

sys.modules[__name__] = _module
