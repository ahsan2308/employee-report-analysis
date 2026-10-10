"""Compatibility alias: this module is app.integrations.embeddings.base."""
import sys

import app.integrations.embeddings.base as _module

sys.modules[__name__] = _module
