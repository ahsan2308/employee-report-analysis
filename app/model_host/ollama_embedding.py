"""Compatibility alias: this module is app.integrations.embeddings.ollama."""
import sys

import app.integrations.embeddings.ollama as _module

sys.modules[__name__] = _module
