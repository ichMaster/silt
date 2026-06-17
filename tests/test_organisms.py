"""Tests for SILT-005 — organism tracking via toroidal connected components.

Pins: connected-component membership (8-connectivity, toroidal), a stable identity + translating
bbox under a moving glider, ``birth_tick`` set once, and tracker restore (for replay) preserving
ids/birth. Determinism: ids are assigned deterministically, no RNG.
"""

from __future__ import annotations

import numpy as np

from engine import empty, place, step
from engine.patterns import blinker, block, glider
from world.organisms import OrganismTracker, label_components, toroidal_bbox


def test_block_is_one_organism_with_tight_bbox() -> None:
    field = place(empty(8, 8), block, (3, 3))
    orgs = OrganismTracker().update(field, tick=0)
    assert len(orgs) == 1
    assert orgs[0].bbox == (3, 3, 2, 2)
    assert orgs[0].birth_tick == 0
    assert orgs[0].genome is None  # v0 has no genome


def test_two_separate_regions_are_two_organisms() -> None:
    field = place(place(empty(16, 16), block, (1, 1)), blinker, (9, 9))
    orgs = OrganismTracker().update(field, tick=0)
    assert len(orgs) == 2


def test_edge_straddling_region_is_a_single_organism() -> None:
    # A horizontal 3-cell bar at columns {15, 0, 1} wraps the right/left edge -> one organism.
    field = empty(8, 16)
    for c in (15, 0, 1):
        field[4, c] = 1
    comps = label_components(field)
    assert len(comps) == 1
    # Toroidal bbox is the tight wrapped box: starts at col 15, width 3 (15 -> 0 -> 1).
    assert toroidal_bbox(comps[0], field.shape) == (4, 15, 1, 3)


def test_glider_stays_one_organism_with_translating_bbox() -> None:
    field = place(empty(20, 20), glider, (2, 2))
    tracker = OrganismTracker()
    ids: list[str] = []
    bboxes = []
    f = field
    for t in range(9):  # two full glider periods (8 ticks) + the start
        orgs = tracker.update(f, t)
        assert len(orgs) == 1  # membership stays a single organism every tick
        ids.append(orgs[0].id)
        bboxes.append(orgs[0].bbox)
        f = step(f)

    assert len(set(ids)) == 1  # identity carried forward the whole way
    # After 8 ticks (2 periods) the glider has translated by (2, 2) and resumed its shape.
    assert bboxes[8] == (bboxes[0][0] + 2, bboxes[0][1] + 2, 3, 3)


def test_birth_tick_is_set_once_and_preserved() -> None:
    field = place(empty(20, 20), glider, (2, 2))
    tracker = OrganismTracker()
    f = field
    births = []
    for t in range(6):
        orgs = tracker.update(f, t)
        births.append(orgs[0].birth_tick)
        f = step(f)
    assert births == [0, 0, 0, 0, 0, 0]  # born at tick 0, never reset


def test_tracker_restore_continues_identity_and_birth() -> None:
    f = place(empty(20, 20), glider, (2, 2))
    tracker = OrganismTracker()
    snap_field = None
    snap_orgs = None
    for t in range(4):
        orgs = tracker.update(f, t)
        if t == 3:
            snap_field, snap_orgs = f, orgs
        f = step(f)

    original_id = snap_orgs[0].id
    original_birth = snap_orgs[0].birth_tick

    # A fresh tracker restored from the snapshot continues the same identity on the next tick.
    restored = OrganismTracker.restore(snap_orgs, snap_field)
    cont = restored.update(step(snap_field), tick=4)
    assert len(cont) == 1
    assert cont[0].id == original_id
    assert cont[0].birth_tick == original_birth


def test_ids_are_deterministic_across_runs() -> None:
    field = place(place(empty(16, 16), block, (1, 1)), glider, (8, 8))
    a = [o.id for o in OrganismTracker().update(field, 0)]
    b = [o.id for o in OrganismTracker().update(field, 0)]
    assert a == b  # no RNG — same field, same ids


def test_label_components_does_not_mutate_input() -> None:
    field = place(empty(8, 8), block, (2, 2))
    snapshot = field.copy()
    label_components(field)
    assert np.array_equal(field, snapshot)
