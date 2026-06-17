"""Silt world — state, organisms, lineage, and (from v0.3) the tick loop.

Substrate-agnostic: the world knows nothing about which automaton runs inside ``engine.step``.
This package owns the record shapes (:mod:`world.records`) the Store persists and the Evaluator
reads, and organism tracking (:mod:`world.organisms`) over the shared field.
"""

from world.organisms import OrganismTracker, label_components, toroidal_bbox
from world.records import EVENT_TYPES, Event, Organism, World

__all__ = [
    "EVENT_TYPES",
    "Event",
    "Organism",
    "OrganismTracker",
    "World",
    "label_components",
    "toroidal_bbox",
]
