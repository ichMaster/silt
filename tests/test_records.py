"""Contract tests for SILT-004 — the Event / Organism / World record shapes.

Pins the field sets, the event-type vocabulary, and that each record round-trips through
(de)serialization. The World field is heavy and travels via the Store blob path, so it
round-trips alongside ``to_dict()`` rather than inside it.
"""

from __future__ import annotations

import numpy as np

from world.records import EVENT_TYPES, Event, Organism, World


def test_event_roundtrips() -> None:
    e = Event(
        tick=7,
        type="seed",
        organism_id="org-000001",
        owner="lili",
        data={"pattern": "glider", "position": [3, 4]},
    )
    assert Event.from_dict(e.to_dict()) == e


def test_event_type_vocabulary_covers_core_mutations() -> None:
    for t in ("seed", "mutate", "cross", "cull", "death", "record", "goal"):
        assert t in EVENT_TYPES


def test_organism_roundtrips_and_genome_is_nullable() -> None:
    o = Organism(
        id="org-000002",
        genome=None,  # v0 has no genome
        owner="human",
        bbox=(2, 3, 3, 3),
        birth_tick=5,
        last_metrics={"mass": 5},
        status="alive",
        note="glider",
    )
    assert o.genome is None
    restored = Organism.from_dict(o.to_dict())
    assert restored == o
    assert restored.bbox == (2, 3, 3, 3)  # bbox survives the list<->tuple hop


def test_world_metadata_roundtrips_field_via_blob_path() -> None:
    field = (np.arange(9, dtype=np.uint8).reshape(3, 3) % 2)
    w = World(
        field=field,
        tick=12,
        seed=42,
        organisms=[Organism(id="org-1", birth_tick=0)],
        events=[Event(tick=1, type="seed")],
        gardeners=[{"id": "lili", "name": "Lili"}],
    )
    restored = World.from_dict(w.to_dict(), field=field)

    assert restored.tick == w.tick
    assert restored.seed == w.seed
    assert restored.organisms == w.organisms
    assert restored.events == w.events
    assert restored.gardeners == w.gardeners
    assert np.array_equal(restored.field, w.field)


def test_world_to_dict_excludes_heavy_field() -> None:
    w = World(field=np.ones((4, 4), dtype=np.uint8))
    assert "field" not in w.to_dict()  # the field travels via the Store blob, not inline
