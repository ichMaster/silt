"""Tests for SILT-008 — minimal display metrics + the observe/history payload.

Pins mass/age/alive against fixed recorded runs, that the observe payload bundles metrics + the run
and is JSON-serializable, and that evaluate is pure (no mutation). The metrics are substrate-agnostic
— computed over recorded frames, with no genome/automaton assumptions.
"""

from __future__ import annotations

import json

import numpy as np

from engine import empty, place, step
from engine.patterns import block, glider
from evaluator import Frame, History, evaluate, observe
from world.records import Event


def _history(initial: np.ndarray, n_ticks: int, events: list[Event] | None = None) -> History:
    """Record a run: frames for ticks 0..n_ticks, stepping the engine each tick."""
    frames = []
    f = initial
    for t in range(n_ticks + 1):
        frames.append(Frame(tick=t, field=f.copy()))
        f = step(f)
    return History(frames=frames, events=events or [])


def test_mass_is_final_live_cell_total() -> None:
    history = _history(place(empty(8, 8), block, (2, 2)), n_ticks=5)  # block: 4 cells, still life
    assert evaluate(history)["mass"] == 4


def test_glider_run_is_pinned() -> None:
    history = _history(place(empty(20, 20), glider, (2, 2)), n_ticks=8)  # 9 frames, always alive
    assert evaluate(history) == {"mass": 5, "age": 9, "alive": True}


def test_dying_run_reports_dead_and_counts_only_alive_ticks() -> None:
    one_cell = empty(5, 5)
    one_cell[2, 2] = 1  # a lone live cell dies on the next tick
    history = _history(one_cell, n_ticks=1)  # frame0 alive (mass 1), frame1 dead (mass 0)
    assert evaluate(history) == {"mass": 0, "age": 1, "alive": False}


def test_empty_history_is_dead() -> None:
    assert evaluate(History()) == {"mass": 0, "age": 0, "alive": False}


def test_observe_bundles_metrics_and_run_and_is_json_serializable() -> None:
    events = [Event(tick=0, type="seed", data={"pattern": "glider", "position": [2, 2]})]
    history = _history(place(empty(12, 12), glider, (2, 2)), n_ticks=4, events=events)

    payload = observe(history)
    assert payload["metrics"] == evaluate(history)
    assert len(payload["run"]["frames"]) == 5  # ticks 0..4
    assert payload["run"]["events"][0]["type"] == "seed"

    json.dumps(payload)  # must not raise — the chosen client return is JSON-serializable


def test_evaluate_does_not_mutate_history() -> None:
    history = _history(place(empty(8, 8), block, (2, 2)), n_ticks=3)
    before = [f.field.copy() for f in history.frames]
    evaluate(history)
    for f, snap in zip(history.frames, before, strict=True):
        assert np.array_equal(f.field, snap)
