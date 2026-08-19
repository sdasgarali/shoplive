"""Ensure the backend package root is importable when tests run under the bare
`pytest` console script (CI), not just `python -m pytest` (local).

`python -m pytest` puts the CWD on sys.path; the `pytest` entrypoint does not,
so `import app` would fail in CI. Inserting this file's directory guarantees
`app` is importable regardless of how pytest is invoked.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
