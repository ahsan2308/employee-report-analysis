"""Every module under app/ and what importing it does today.

Dead modules are recorded as they behave now (e.g. app.core.config raises
FileNotFoundError, app.config.config prints at import). Deleting them later is
an intentional, reviewed snapshot change.
"""


def test_import_outcome_of_every_app_module(run_probe, snapshot):
    snapshot("module_import_outcomes", run_probe("imports", {}))
