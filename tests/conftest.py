"""Pytest fixtures shared across tests.

The default tmp path `%TEMP%\\pytest-of-<user>` is sometimes blocked by
Windows ACLs or sandbox policies, causing PermissionError before tests
run. Tests should be invoked with `--basetemp=.pytest-tmp` (configured
in pyproject.toml) to redirect temporary files into a project-local dir.
"""