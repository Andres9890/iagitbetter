import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Ensure the lightweight requests_mock stub is importable when the third-party
# dependency is unavailable in this execution environment.
try:
    import requests_mock  # noqa: F401
except ModuleNotFoundError:
    # Fallback to the vendored stub package shipped with the repository.
    from importlib import import_module

    module = import_module("requests_mock")
    sys.modules.setdefault("requests_mock", module)
