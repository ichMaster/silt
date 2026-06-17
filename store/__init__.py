"""Silt store — persistence behind a swappable ``Store`` interface.

Periodic snapshots (field + organisms + lineage) plus an append-only event log; replay
(:mod:`store.replay`, from v0.2) reconstructs any tick from a snapshot + the log. The v0 backend is
SQLite + ``.npy`` blobs (:class:`store.sqlite_store.SqliteStore`). Substrate-agnostic — it persists
opaque field grids and the :mod:`world.records` shapes, never the automaton.
"""

from store.base import Snapshot, Store
from store.replay import replay
from store.sqlite_store import SqliteStore

__all__ = ["Snapshot", "SqliteStore", "Store", "replay"]
