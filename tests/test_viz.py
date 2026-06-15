"""Tests for the dev viewer's pure helpers — no matplotlib import, so CI stays hermetic/lean.

The GUI animation itself (``tools.viz.animate``) is not unit-tested; only the field construction
and argument parsing, which is the part that can break silently.
"""

from __future__ import annotations

import pytest

from engine import live_count
from tools.viz import PATTERNS, build_field


def test_build_field_centers_pattern_by_default() -> None:
    field = build_field("glider", 20, 20)
    assert field.shape == (20, 20)
    assert live_count(field) == 5  # the glider, intact


def test_build_field_respects_explicit_position() -> None:
    field = build_field("blinker", 10, 10, position=(4, 5))
    assert field[4, 5] == 1 and field[4, 6] == 1 and field[4, 7] == 1
    assert live_count(field) == 3


def test_build_field_rejects_unknown_pattern() -> None:
    with pytest.raises(ValueError, match="unknown pattern"):
        build_field("not_a_pattern", 10, 10)


def test_pattern_registry_matches_engine_figures() -> None:
    # viz draws from the engine's single source of truth — every figure must be selectable.
    from engine.patterns import PATTERNS as ENGINE_PATTERNS

    assert PATTERNS is ENGINE_PATTERNS
    assert {"glider", "pulsar", "acorn", "lwss", "diehard"} <= set(PATTERNS)
    assert live_count(build_field("gosper_glider_gun", 60, 60)) == 36
