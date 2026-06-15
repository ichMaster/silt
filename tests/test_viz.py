"""Tests for the dev viewer's pure helpers — no matplotlib import, so CI stays hermetic/lean.

The GUI animation itself (``tools.viz.animate``) is not unit-tested; only the field construction
and argument parsing, which is the part that can break silently.
"""

from __future__ import annotations

import argparse

import pytest

from engine import live_count
from tools.viz import PATTERNS, build_field, build_field_multi, main, parse_seed


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


# --- multiple seeds at different positions ------------------------------------------------------


def test_parse_seed_with_position() -> None:
    assert parse_seed("glider@5,7") == ("glider", (5, 7))


def test_parse_seed_without_position_centers() -> None:
    assert parse_seed("pulsar") == ("pulsar", None)


def test_parse_seed_rejects_unknown_pattern() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="unknown pattern"):
        parse_seed("nope@1,2")


def test_build_field_multi_places_each_seed() -> None:
    field = build_field_multi([("blinker", (2, 2)), ("block", (10, 10))], 20, 20)
    assert field[2, 2] == 1 and field[2, 3] == 1 and field[2, 4] == 1  # blinker
    assert field[10, 10] == 1 and field[11, 11] == 1  # block
    assert live_count(field) == 3 + 4  # blinker + block, no overlap


def test_build_field_multi_allows_repeated_pattern() -> None:
    field = build_field_multi([("glider", (1, 1)), ("glider", (40, 40))], 60, 60)
    assert live_count(field) == 10  # two gliders, 5 cells each


def test_main_accepts_repeated_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    """--seed is repeatable and overrides --pattern; verified without opening a window."""
    captured = {}

    def fake_animate(field, **kwargs):
        captured["field"] = field
        captured["title"] = kwargs.get("title", "")

    monkeypatch.setattr("tools.viz.animate", fake_animate)
    main(["--seed", "glider@5,5", "--seed", "lwss@20,30", "--size", "50"])

    assert live_count(captured["field"]) == 5 + 12  # glider + lwss
    assert "glider" in captured["title"] and "lwss" in captured["title"]
