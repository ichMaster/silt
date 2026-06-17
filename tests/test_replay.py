"""Integration tests for SILT-007 — replay reconstructs any tick exactly.

Pins the v0.2 determinism DoD: a world advanced N ticks with interleaved events, snapshotted
periodically, replays from an earlier snapshot + the log to **byte-for-byte identical** state —
including across a snapshot boundary. Also pins that events apply at tick boundaries and that
replayed organisms match the live run.
"""

from __future__ import annotations

import numpy as np

from engine import empty, place, step
from engine.patterns import glider
from store import SqliteStore
from store.replay import replay
from world.organisms import OrganismTracker
from world.records import Event
from world.simulate import genesis, step_world

SNAP_EVERY = 5
N_TICKS = 25

# Interleaved gardener actions (the ordered event log), keyed by the tick they apply at.
_EVENTS: dict[int, list[Event]] = {
    7: [Event(tick=7, type="seed", owner="lili", data={"pattern": "blinker", "position": [3, 14]})],
    15: [Event(tick=15, type="seed", owner="human", data={"pattern": "block", "position": [20, 20]})],
}


def _run_reference(store: SqliteStore) -> dict[int, object]:
    """Live run: a glider plus interleaved seeds; record every tick, snapshot every SNAP_EVERY."""
    tracker = OrganismTracker()
    initial = place(empty(30, 30), glider, (2, 2))
    world = genesis(initial, tracker=tracker)

    states = {0: world}
    store.save_snapshot(world.tick, world.field, world.organisms)
    for tick in range(1, N_TICKS + 1):
        events = _EVENTS.get(tick, [])
        for e in events:
            store.append_event(e)
        world = step_world(world, events, tracker)
        states[tick] = world
        if tick % SNAP_EVERY == 0:
            store.save_snapshot(world.tick, world.field, world.organisms)
    return states


def test_replay_reconstructs_across_a_snapshot_boundary() -> None:
    store = SqliteStore(":memory:")
    states = _run_reference(store)

    # 23 lies past the tick-20 snapshot, so replay must re-advance across that boundary,
    # re-applying nothing (no events in 21..23) but reproducing the field exactly.
    target = 23
    rebuilt = replay(store, target)
    reference = states[target]

    assert rebuilt.tick == target
    assert rebuilt.field.tobytes() == reference.field.tobytes()  # byte-for-byte
    assert np.array_equal(rebuilt.field, reference.field)


def test_replay_reconstructs_across_an_interleaved_event() -> None:
    store = SqliteStore(":memory:")
    states = _run_reference(store)

    # 17 sits past the tick-15 snapshot (which already baked in the tick-15 seed); replay 16..17.
    rebuilt = replay(store, 17)
    assert rebuilt.field.tobytes() == states[17].field.tobytes()


def test_replayed_organisms_match_the_live_run() -> None:
    store = SqliteStore(":memory:")
    states = _run_reference(store)

    rebuilt = replay(store, 23)
    reference = states[23]

    def by_bbox(orgs: object) -> list[tuple[str, tuple[int, int, int, int]]]:
        return sorted((o.id, o.bbox) for o in orgs)

    assert by_bbox(rebuilt.organisms) == by_bbox(reference.organisms)


def test_replay_at_a_snapshot_tick_is_exact() -> None:
    store = SqliteStore(":memory:")
    states = _run_reference(store)
    rebuilt = replay(store, 20)  # exactly on a snapshot boundary -> no re-advance
    assert rebuilt.tick == 20
    assert rebuilt.field.tobytes() == states[20].field.tobytes()


def test_seed_event_applies_at_tick_boundary() -> None:
    """An event timestamped for tick t is applied before the step that produces tick t."""
    tracker = OrganismTracker()
    f = empty(20, 20)
    world = genesis(f, tracker=tracker)  # empty at tick 0
    event = Event(tick=1, type="seed", data={"pattern": "glider", "position": [5, 5]})

    advanced = step_world(world, [event], tracker)
    expected = step(place(f, glider, (5, 5)))  # apply-then-step at the boundary

    assert advanced.tick == 1
    assert np.array_equal(advanced.field, expected)


def test_replay_without_a_snapshot_raises() -> None:
    store = SqliteStore(":memory:")
    store.save_snapshot(tick=5, field=empty(8, 8), organisms=[])
    try:
        replay(store, 3)  # nothing at or before tick 3
    except LookupError:
        pass
    else:
        raise AssertionError("expected LookupError when no snapshot is at or before the target")
