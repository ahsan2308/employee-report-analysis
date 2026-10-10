"""Compatibility alias: this module is app.integrations.sqlserver.connector."""
import sys

import app.integrations.sqlserver.connector as _module

sys.modules[__name__] = _module
