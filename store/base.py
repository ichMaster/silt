"""The ``Store`` interface — persistence behind a swappable seam (SILT-006).

A Store keeps two things: **periodic snapshots** (field + organisms + lineage) and an
**append-only event log**. Together they let replay (SILT-007) reconstruct any tick exactly: load
the nearest snapshot at or before the target, then re-advance applying the logged events. The
interface is backend-agnostic; :mod:`store.sqlite_store` is the v0 SQLite/blob implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from world.records import Event, Organism


@dataclass
class Snapshot:
    """A persisted world state at one tick — the anchor replay re-advances from."""

    tick: int
    field: Any  # a numpy grid; kept opaque so this layer stays substrate-agnostic
    organisms: list[Organism]
    lineage: dict[str, list[str]]


class Store(ABC):
    """Persistence for the world: an append-only event log + periodic snapshots."""

    @abstractmethod
    def append_event(self, event: Event) -> None:
        """Append one event to the log. The log is **append-only** — never updated or deleted."""

    @abstractmethod
    def save_snapshot(
        self,
        tick: int,
        field: Any,
        organisms: list[Organism],
        lineage: dict[str, list[str]] | None = None,
    ) -> None:
        """Persist a full world snapshot at ``tick``."""

    @abstractmethod
    def load_snapshot(self, at_tick: int) -> Snapshot | None:
        """Return the nearest snapshot at or before ``at_tick``, or ``None`` if there is none."""

    @abstractmethod
    def events(self, since_tick: int = 0) -> list[Event]:
        """Return events with ``tick >= since_tick``, totally ordered by ``(tick, seq)``."""

    @abstractmethod
    def events_between(self, start_tick: int, end_tick: int) -> list[Event]:
        """Return events with ``start_tick <= tick <= end_tick``, ordered by ``(tick, seq)``."""

    def close(self) -> None:  # noqa: B027 — intentional no-op default (cf. io.IOBase); backends override
        """Release backend resources. Default no-op; backends override as needed."""
