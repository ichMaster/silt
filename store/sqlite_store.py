"""SQLite + blob implementation of the ``Store`` interface (SILT-006).

Events live in an **append-only** table totally ordered by ``(tick, seq)`` (``seq`` is a monotonic
auto-increment, so events sharing a tick keep insertion order). Field snapshots are stored as
``.npy`` blobs (via :func:`numpy.save`), which preserve dtype + shape exactly, so a snapshot
round-trips **byte-for-byte**. Organisms and lineage are JSON. The default path ``":memory:"`` keeps
tests hermetic — no file, no network.
"""

from __future__ import annotations

import io
import json
import sqlite3
from typing import Any

import numpy as np

from store.base import Snapshot, Store
from world.records import Event, Organism

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    tick        INTEGER NOT NULL,
    type        TEXT    NOT NULL,
    organism_id TEXT,
    owner       TEXT,
    data        TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_tick ON events (tick, seq);
CREATE TABLE IF NOT EXISTS snapshots (
    tick      INTEGER PRIMARY KEY,
    field     BLOB    NOT NULL,
    organisms TEXT    NOT NULL,
    lineage   TEXT    NOT NULL
);
"""


def _field_to_blob(field: Any) -> bytes:
    buf = io.BytesIO()
    np.save(buf, np.asarray(field), allow_pickle=False)  # .npy: exact dtype + shape
    return buf.getvalue()


def _blob_to_field(blob: bytes) -> np.ndarray:
    return np.load(io.BytesIO(blob), allow_pickle=False)


class SqliteStore(Store):
    """A single embedded SQLite DB holding the event log and snapshot blobs."""

    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def append_event(self, event: Event) -> None:
        self._conn.execute(
            "INSERT INTO events (tick, type, organism_id, owner, data) VALUES (?, ?, ?, ?, ?)",
            (event.tick, event.type, event.organism_id, event.owner, json.dumps(event.data)),
        )
        self._conn.commit()

    def save_snapshot(
        self,
        tick: int,
        field: Any,
        organisms: list[Organism],
        lineage: dict[str, list[str]] | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO snapshots (tick, field, organisms, lineage) VALUES (?, ?, ?, ?)",
            (
                tick,
                _field_to_blob(field),
                json.dumps([o.to_dict() for o in organisms]),
                json.dumps(lineage or {}),
            ),
        )
        self._conn.commit()

    def load_snapshot(self, at_tick: int) -> Snapshot | None:
        row = self._conn.execute(
            "SELECT tick, field, organisms, lineage FROM snapshots "
            "WHERE tick <= ? ORDER BY tick DESC LIMIT 1",
            (at_tick,),
        ).fetchone()
        if row is None:
            return None
        tick, blob, organisms_json, lineage_json = row
        return Snapshot(
            tick=tick,
            field=_blob_to_field(blob),
            organisms=[Organism.from_dict(o) for o in json.loads(organisms_json)],
            lineage=json.loads(lineage_json),
        )

    def events(self, since_tick: int = 0) -> list[Event]:
        rows = self._conn.execute(
            "SELECT tick, type, organism_id, owner, data FROM events "
            "WHERE tick >= ? ORDER BY tick, seq",
            (since_tick,),
        ).fetchall()
        return [_row_to_event(r) for r in rows]

    def events_between(self, start_tick: int, end_tick: int) -> list[Event]:
        rows = self._conn.execute(
            "SELECT tick, type, organism_id, owner, data FROM events "
            "WHERE tick >= ? AND tick <= ? ORDER BY tick, seq",
            (start_tick, end_tick),
        ).fetchall()
        return [_row_to_event(r) for r in rows]

    def close(self) -> None:
        self._conn.close()


def _row_to_event(row: tuple[Any, ...]) -> Event:
    tick, type_, organism_id, owner, data = row
    return Event(
        tick=tick,
        type=type_,
        organism_id=organism_id,
        owner=owner,
        data=json.loads(data),
    )
