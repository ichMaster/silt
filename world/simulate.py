"""Forward simulation semantics — the deterministic rule replay re-runs (SILT-007 support).

The world is a pure function of ``(seed, initial_field, ordered_event_log)``. This module fixes the
single canonical rule for advancing it, so the live run and replay are byte-for-byte identical:

    state[t].field = step(apply_events(state[t-1].field, events_where_tick == t))

i.e. events timestamped for tick ``t`` are applied **at the tick boundary** (before the step that
produces tick ``t``), never mid-tick. The genesis state (tick 0) applies any tick-0 events to the
initial field without stepping. Organisms are recomputed each tick by the tracker.

In v0 only ``seed`` (place a pattern) and ``cull`` (clear cells) mutate the field; ``record`` /
``goal`` are annotations, and ``mutate`` / ``cross`` / ``death`` are v1 genome concerns (no-ops on
the v0 field).
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from engine import place, step
from engine.patterns import PATTERNS
from world.organisms import OrganismTracker
from world.records import Event, World


def _pattern_from(value: object) -> np.ndarray:
    """Resolve a seed payload to a binary pattern — a named figure or a literal 2D grid."""
    if isinstance(value, str):
        return PATTERNS[value]
    return np.asarray(value)


def apply_events(field: np.ndarray, events: Iterable[Event]) -> np.ndarray:
    """Apply boundary events to (a copy of, when needed) ``field``. Pure: never mutates the input."""
    out = field
    for e in events:
        if e.type == "seed":
            out = place(out, _pattern_from(e.data["pattern"]), tuple(e.data.get("position", (0, 0))))
        elif e.type == "cull":
            cells = e.data.get("cells") or []
            if cells:
                out = out.copy()
                h, w = out.shape
                for r, c in cells:
                    out[r % h, c % w] = 0
    return out


def genesis(
    field: np.ndarray,
    *,
    tracker: OrganismTracker,
    events: Iterable[Event] = (),
    seed: int = 0,
) -> World:
    """Build the tick-0 world: apply any tick-0 events to ``field`` (no step) and track organisms."""
    f = apply_events(field, events)
    return World(field=f, tick=0, seed=seed, organisms=tracker.update(f, 0))


def step_world(world: World, events: Iterable[Event], tracker: OrganismTracker) -> World:
    """Advance one tick: apply this tick's boundary events, step, then recompute organisms."""
    field = step(apply_events(world.field, events))
    tick = world.tick + 1
    return World(
        field=field,
        tick=tick,
        seed=world.seed,
        organisms=tracker.update(field, tick),
        lineage=world.lineage,
    )
