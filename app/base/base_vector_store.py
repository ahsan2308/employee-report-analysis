"""Compatibility alias: this module is app.integrations.vector_store.base."""
import sys

import app.integrations.vector_store.base as _module

sys.modules[__name__] = _module
