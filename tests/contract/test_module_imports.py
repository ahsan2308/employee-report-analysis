"""Every module under app/ and what importing it does today.

For example, app.api.main connects to the database and prints at import.
Any change to these outcomes is an intentional, reviewed snapshot change.
"""


def test_import_outcome_of_every_app_module(run_probe, snapshot):
    snapshot("module_import_outcomes", run_probe("imports", {}))
