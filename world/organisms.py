"""Organism tracking — connected live regions of the shared field (SILT-005).

An **organism** is a connected component of live cells under **8-connectivity** (Moore adjacency,
matching the engine's neighbor topology), with **toroidal wrap** so a region straddling an edge is a
single organism. :class:`OrganismTracker` recomputes membership each tick and **carries identity
forward by cell overlap**, so a drifting glider stays the *same* organism with a translating bbox;
``birth_tick`` is set once when it first appears.

IDs are **deterministic** (``org-000001`` assigned in sorted component order) — never random — so the
world stays a pure function of ``(seed, initial_field, ordered_event_log)`` (the determinism
contract). Connected components use a small pure-numpy union-find, so the only dependency is numpy.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from world.records import BBox, Organism

Cell = tuple[int, int]

# The 8 Moore offsets (organism connectivity matches the engine's neighbor topology).
_NEIGHBORS: list[Cell] = [
    (dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if not (dr == 0 and dc == 0)
]


def label_components(field: object) -> list[frozenset[Cell]]:
    """Connected components of live cells under toroidal 8-connectivity.

    Returns a list of frozensets of ``(row, col)`` cells, deterministically ordered by each
    component's smallest cell.
    """
    alive = np.asarray(field) != 0
    h, w = alive.shape
    live: list[Cell] = [(int(r), int(c)) for r, c in zip(*np.nonzero(alive), strict=False)]
    index = {cell: i for i, cell in enumerate(live)}
    parent = list(range(len(live)))

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression
            parent[x], x = root, parent[x]
        return root

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for cell, i in index.items():
        r, c = cell
        for dr, dc in _NEIGHBORS:
            j = index.get(((r + dr) % h, (c + dc) % w))
            if j is not None:
                union(i, j)

    groups: dict[int, list[Cell]] = defaultdict(list)
    for cell, i in index.items():
        groups[find(i)].append(cell)
    comps = [frozenset(cells) for cells in groups.values()]
    comps.sort(key=min)
    return comps


def _toroidal_extent(coords: list[int], size: int) -> tuple[int, int]:
    """Smallest covering arc on a ring of ``size`` containing all ``coords``.

    Returns ``(start, length)``: the arc starts at ``start`` and spans ``length`` cells forward
    (wrapping). It is the complement of the largest empty run between occupied positions, so a
    region that straddles the edge gets a tight wrapped box rather than a full-width one.
    """
    xs = sorted({int(c) for c in coords})
    n = len(xs)
    if n == 0:
        return 0, 0
    if n == 1:
        return xs[0], 1
    best_run = -1
    start = xs[0]
    for i in range(n):
        a, b = xs[i], xs[(i + 1) % n]
        empty_run = (b - a) % size - 1  # cells strictly between a and b going forward
        if empty_run > best_run:
            best_run = empty_run
            start = b  # the covered arc begins right after the largest gap
    return start, size - best_run


def toroidal_bbox(cells: frozenset[Cell], shape: tuple[int, int]) -> BBox:
    """Toroidal-aware bounding box ``(row, col, height, width)`` of a set of cells."""
    h, w = shape
    r0, height = _toroidal_extent([r for r, _ in cells], h)
    c0, width = _toroidal_extent([c for _, c in cells], w)
    return (r0, c0, height, width)


def _id_number(oid: str) -> int:
    try:
        return int(oid.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class OrganismTracker:
    """Stateful tracker that assigns stable organism IDs across ticks by cell overlap.

    Call :meth:`update` once per tick with the current field; it returns the live organisms with
    identity carried forward. :meth:`restore` rebuilds a tracker from a snapshot's organisms + field
    (matching by bbox) so replay continues the same identities and ``birth_tick``\\ s.
    """

    def __init__(self, owner: str | None = None) -> None:
        self._owner = owner
        self._counter = 0
        self._prev: dict[str, frozenset[Cell]] = {}  # id -> last tick's cells
        self._birth: dict[str, int] = {}  # id -> birth_tick

    def _new_id(self) -> str:
        self._counter += 1
        return f"org-{self._counter:06d}"

    def update(self, field: object, tick: int) -> list[Organism]:
        """Recompute organisms for ``field`` at ``tick``, carrying identity forward by overlap."""
        shape = np.asarray(field).shape
        comps = label_components(field)

        assigned: dict[str, frozenset[Cell]] = {}
        used_prev: set[str] = set()
        for cells in comps:
            best_id, best_overlap = None, 0
            for oid, pcells in self._prev.items():
                if oid in used_prev:
                    continue
                overlap = len(cells & pcells)
                if overlap > best_overlap:
                    best_overlap, best_id = overlap, oid
            if best_id is None:
                oid = self._new_id()
                self._birth[oid] = tick
            else:
                oid = best_id
                used_prev.add(oid)
            assigned[oid] = cells

        organisms = [
            Organism(
                id=oid,
                genome=None,  # no genome in v0
                owner=self._owner,
                bbox=toroidal_bbox(cells, shape),
                birth_tick=self._birth[oid],
                last_metrics={"mass": len(cells)},
                status="alive",
            )
            for oid, cells in assigned.items()
        ]
        organisms.sort(key=lambda o: o.bbox)  # deterministic return order

        self._prev = assigned
        self._birth = {oid: self._birth[oid] for oid in assigned}  # drop the departed
        return organisms

    @classmethod
    def restore(
        cls, organisms: list[Organism], field: object, *, owner: str | None = None
    ) -> OrganismTracker:
        """Rebuild a tracker from a snapshot's ``organisms`` + ``field`` (match by exact bbox)."""
        t = cls(owner=owner)
        shape = np.asarray(field).shape
        by_bbox = {tuple(o.bbox): o for o in organisms if o.bbox is not None}
        max_n = 0
        for cells in label_components(field):
            bbox = toroidal_bbox(cells, shape)
            match = by_bbox.get(bbox)
            if match is not None:
                oid = match.id
                t._birth[oid] = match.birth_tick
                max_n = max(max_n, _id_number(oid))
            else:
                oid = t._new_id()
                t._birth[oid] = 0
            t._prev[oid] = cells
        t._counter = max(t._counter, max_n)
        return t
