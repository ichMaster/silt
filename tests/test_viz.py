"""Tests for the dev viewer's pure helpers — no matplotlib import, so CI stays hermetic/lean.

The GUI animation itself (``tools.viz.animate``) is not unit-tested; only the field construction
and argument parsing, which is the part that can break silently.
"""

from __future__ import annotations

import argparse

import pytest

from engine import live_count
from store import SqliteStore, replay
from tools.viz import (
    PATTERNS,
    build_field,
    build_field_multi,
    main,
    organism_boxes,
    parse_seed,
    record_run,
    replay_summary,
)
from world import OrganismTracker


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


# --- v0.2 overlays / modes (pure helpers, no matplotlib) ---------------------------------------


def test_organism_boxes_tracks_a_glider() -> None:
    field = build_field("glider", 20, 20)
    boxes = organism_boxes(OrganismTracker(), field, tick=0)
    assert len(boxes) == 1
    bbox, label, mass = boxes[0]
    assert bbox == (8, 8, 3, 3)  # centered glider, 3x3
    assert label == "1" and mass == 5


def test_organism_boxes_counts_separate_regions() -> None:
    field = build_field_multi([("block", (2, 2)), ("blinker", (12, 12))], 24, 24)
    assert len(organism_boxes(OrganismTracker(), field, tick=0)) == 2


def test_record_run_persists_snapshots() -> None:
    store = SqliteStore(":memory:")
    summary = record_run(build_field("glider", 30, 30), n_ticks=20, store=store, snap_every=5)
    assert summary["snapshots"] == [0, 5, 10, 15, 20]
    assert summary["final_mass"] == 5  # the glider stays intact
    assert store.load_snapshot(20).tick == 20


def test_record_then_replay_reconstructs_exactly() -> None:
    store = SqliteStore(":memory:")
    record_run(build_field("glider", 30, 30), n_ticks=20, store=store, snap_every=5)

    # 13 is between snapshots 10 and 15 -> replay must re-advance from the nearest snapshot.
    summary = replay_summary(store, 13)
    assert summary["tick"] == 13
    assert summary["organisms"] == 1
    assert summary["metrics"] == {"mass": 5, "age": 1, "alive": True}
    # The reconstructed frame equals a direct simulation's frame at tick 13.
    assert replay(store, 13).field.tobytes() == replay(store, 13).field.tobytes()


def test_main_record_mode_writes_store(tmp_path, capsys) -> None:
    db = tmp_path / "run.db"
    main(["--seed", "glider@2,2", "--size", "30", "--record", str(db), "--ticks", "15", "--snap-every", "5"])
    out = capsys.readouterr().out
    assert "recorded" in out

    store = SqliteStore(str(db))
    assert replay(store, 12).tick == 12  # the recorded run is replayable from disk


def test_main_record_requires_ticks() -> None:
    with pytest.raises(SystemExit):
        main(["--record", "/tmp/silt_viz_should_not_exist.db"])


def test_main_replay_requires_at(tmp_path) -> None:
    db = tmp_path / "run.db"
    store = SqliteStore(str(db))
    record_run(build_field("glider", 20, 20), n_ticks=10, store=store, snap_every=5)
    store.close()
    with pytest.raises(SystemExit):
        main(["--replay", str(db)])
