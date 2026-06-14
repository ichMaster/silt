"""Placeholder skeleton test — proves the toolchain (uv + ruff + pytest) and the engine import.

Replaced/joined by real engine tests in SILT-002 onward.
"""

import importlib


def test_engine_imports() -> None:
    engine = importlib.import_module("engine")
    assert engine is not None
