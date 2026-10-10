"""Compatibility alias: this module is app.integrations.embeddings.vllm."""
import sys

import app.integrations.embeddings.vllm as _module

sys.modules[__name__] = _module
