"""World record shapes — the data contract ``Event`` / ``Organism`` / ``World``.

These are **pure data**: the Store persists them, organism tracking populates them, and the
Evaluator reads them. They carry no behavior beyond (de)serialization and import nothing from
``engine`` / ``store`` / ``evaluator``, so they never form an import cycle. The field grid is left
opaque (typed ``Any``) here precisely so this layer stays substrate-agnostic.

In v0 there is **no genome** (none before v1.1) — :class:`Organism` keeps the ``genome`` field but
it is nullable, so the v1.1 genome slots in without a shape change. The heavy :attr:`World.field`
grid is **not** serialized inline: it travels via the Store's blob path (see
:mod:`store.sqlite_store`). :meth:`World.to_dict` serializes the world's *metadata* only, and the
field is round-tripped alongside it via :meth:`World.from_dict`.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

# The vocabulary of world mutations — the sole source of field change (extensible).
EVENT_TYPES: tuple[str, ...] = (
    "seed",
    "mutate",
    "cross",
    "cull",
    "death",
    "record",
    "goal",
)

# A toroidal bounding box: (row, col) top-left corner + (height, width) arc lengths.
BBox = tuple[int, int, int, int]


@dataclass
class Event:
    """A timestamped world mutation applied at a tick boundary (never mid-tick).

    The ordered event log is the only source of mutation, so the world is a pure function of
    ``(seed, initial_field, ordered_event_log)``. ``data`` carries type-specific payload (e.g. a
    seed's pattern + position).
    """

    tick: int
    type: str
    organism_id: str | None = None
    owner: str | None = None
    data: dict[str, Any] = dc_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "type": self.type,
            "organism_id": self.organism_id,
            "owner": self.owner,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Event:
        return cls(
            tick=d["tick"],
            type=d["type"],
            organism_id=d.get("organism_id"),
            owner=d.get("owner"),
            data=dict(d.get("data") or {}),
        )


@dataclass
class Organism:
    """A connected live region of the field, tracked across ticks.

    ``genome`` is ``None`` in v0 (no genome before v1.1) and forward-compatible with the v1.1
    genome. ``bbox`` is toroidal-aware; ``birth_tick`` is set once when the organism first appears.
    """

    id: str
    genome: Any | None = None
    owner: str | None = None
    bbox: BBox | None = None
    birth_tick: int = 0
    last_metrics: dict[str, Any] = dc_field(default_factory=dict)
    status: str = "alive"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "genome": self.genome,
            "owner": self.owner,
            "bbox": list(self.bbox) if self.bbox is not None else None,
            "birth_tick": self.birth_tick,
            "last_metrics": self.last_metrics,
            "status": self.status,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Organism:
        bbox = d.get("bbox")
        return cls(
            id=d["id"],
            genome=d.get("genome"),
            owner=d.get("owner"),
            bbox=tuple(bbox) if bbox is not None else None,
            birth_tick=d.get("birth_tick", 0),
            last_metrics=dict(d.get("last_metrics") or {}),
            status=d.get("status", "alive"),
            note=d.get("note", ""),
        )


@dataclass
class World:
    """The shared world: one toroidal field plus the records describing it.

    ``lineage`` maps ``child_id -> [parent_ids]``; it is empty in v0 and populated in v1.2. The
    ``field`` is heavy and is excluded from :meth:`to_dict` — it is persisted as a Store blob and
    round-tripped via :meth:`from_dict`.
    """

    field: Any
    tick: int = 0
    seed: int = 0
    organisms: list[Organism] = dc_field(default_factory=list)
    lineage: dict[str, list[str]] = dc_field(default_factory=dict)
    events: list[Event] = dc_field(default_factory=list)
    gardeners: list[dict[str, Any]] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the world's metadata only — the field travels via the Store blob path."""
        return {
            "tick": self.tick,
            "seed": self.seed,
            "organisms": [o.to_dict() for o in self.organisms],
            "lineage": {k: list(v) for k, v in self.lineage.items()},
            "events": [e.to_dict() for e in self.events],
            "gardeners": [dict(g) for g in self.gardeners],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any], field: Any) -> World:
        return cls(
            field=field,
            tick=d.get("tick", 0),
            seed=d.get("seed", 0),
            organisms=[Organism.from_dict(o) for o in d.get("organisms", [])],
            lineage={k: list(v) for k, v in (d.get("lineage") or {}).items()},
            events=[Event.from_dict(e) for e in d.get("events", [])],
            gardeners=[dict(g) for g in d.get("gardeners", [])],
        )
