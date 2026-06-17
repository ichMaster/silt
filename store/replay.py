"""Replay — reconstruct any tick from a snapshot + the event log (SILT-007).

The v0.2 determinism centerpiece: load the nearest snapshot at or before the target tick, restore
the organism tracker from it, then re-advance with :func:`world.simulate.step_world` — applying the
logged events at each tick boundary — up to the target. Because the live run used the *same*
:func:`step_world` rule, the reconstructed field is **byte-for-byte identical** to the recorded
state. Real time is fully decoupled from computation: replay runs on a frozen clock.
"""

from __future__ import annotations

from store.base import Store
from world.organisms import OrganismTracker
from world.records import World
from world.simulate import step_world


def replay(store: Store, target_tick: int) -> World:
    """Reconstruct the exact world state at ``target_tick`` from snapshot + event log.

    Raises:
        LookupError: if no snapshot exists at or before ``target_tick``.
    """
    snap = store.load_snapshot(target_tick)
    if snap is None:
        raise LookupError(f"no snapshot at or before tick {target_tick}")

    # Restore identity/birth so replayed organisms match the live run; the field is the snapshot's.
    tracker = OrganismTracker.restore(snap.organisms, snap.field)
    world = World(
        field=snap.field,
        tick=snap.tick,
        organisms=snap.organisms,
        lineage=snap.lineage,
    )

    for tick in range(snap.tick + 1, target_tick + 1):
        world = step_world(world, store.events_between(tick, tick), tracker)
    return world
