"""Tests for SILT-006 — the Store interface + SQLite/blob backend.

Pins: the event log is append-only and totally ordered by ``(tick, seq)``; ``events(since_tick)``
slices correctly; snapshots round-trip **byte-for-byte** (field blob restores exactly);
``load_snapshot`` returns the nearest snapshot at or before a tick; and ``Store`` is abstract.
Hermetic: an in-memory SQLite DB, no file, no network.
"""

from __future__ import annotations

import numpy as np
import pytest

from engine import empty, place
from engine.patterns import block, glider
from store import SqliteStore, Store
from world.records import Event, Organism


def _store() -> SqliteStore:
    return SqliteStore(":memory:")


def test_store_is_abstract() -> None:
    with pytest.raises(TypeError):
        Store()  # type: ignore[abstract]


def test_event_log_is_append_only_and_ordered() -> None:
    store = _store()
    # Append out of tick order; two share tick 5 to check seq tie-breaking.
    store.append_event(Event(tick=5, type="seed", data={"n": 1}))
    store.append_event(Event(tick=1, type="seed", data={"n": 2}))
    store.append_event(Event(tick=5, type="cull", data={"n": 3}))

    out = store.events()
    assert [(e.tick, e.type) for e in out] == [(1, "seed"), (5, "seed"), (5, "cull")]
    # The two tick-5 events keep insertion order (seq), not append order of all events.
    assert [e.data["n"] for e in out] == [2, 1, 3]


def test_events_since_returns_correct_slice() -> None:
    store = _store()
    for t in (0, 2, 4, 6):
        store.append_event(Event(tick=t, type="record"))
    assert [e.tick for e in store.events(since_tick=4)] == [4, 6]
    assert [e.tick for e in store.events_between(2, 4)] == [2, 4]


def test_event_payload_roundtrips() -> None:
    store = _store()
    store.append_event(
        Event(tick=3, type="seed", organism_id="org-1", owner="lili", data={"pos": [1, 2]})
    )
    (e,) = store.events()
    assert e == Event(tick=3, type="seed", organism_id="org-1", owner="lili", data={"pos": [1, 2]})


def test_snapshot_roundtrips_byte_identical() -> None:
    store = _store()
    field = place(place(empty(12, 12), block, (1, 1)), glider, (6, 6))
    organisms = [Organism(id="org-000001", bbox=(1, 1, 2, 2), birth_tick=0, last_metrics={"mass": 4})]
    lineage = {"org-000002": ["org-000001"]}

    store.save_snapshot(tick=10, field=field, organisms=organisms, lineage=lineage)
    snap = store.load_snapshot(10)

    assert snap is not None
    assert snap.tick == 10
    assert snap.field.dtype == field.dtype
    assert snap.field.shape == field.shape
    assert snap.field.tobytes() == field.tobytes()  # byte-for-byte
    assert np.array_equal(snap.field, field)
    assert snap.organisms == organisms
    assert snap.lineage == lineage


def test_load_snapshot_returns_nearest_at_or_before() -> None:
    store = _store()
    f = empty(4, 4)
    for t in (0, 5, 10):
        store.save_snapshot(tick=t, field=f, organisms=[])
    assert store.load_snapshot(7).tick == 5
    assert store.load_snapshot(10).tick == 10
    assert store.load_snapshot(3).tick == 0


def test_load_snapshot_before_first_is_none() -> None:
    store = _store()
    store.save_snapshot(tick=5, field=empty(4, 4), organisms=[])
    assert store.load_snapshot(4) is None


def test_default_lineage_is_empty() -> None:
    store = _store()
    store.save_snapshot(tick=0, field=empty(4, 4), organisms=[])
    assert store.load_snapshot(0).lineage == {}
