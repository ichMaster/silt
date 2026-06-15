"""The engine seam — ``step(field, genome) -> field``.

This is the *only* place in Silt that knows which automaton runs inside. v0 implements vanilla
Conway (a fixed ``B3/S23`` rule, no genome) over a toroidal binary grid:

- a live cell **survives** if it has 2 or 3 live neighbors, else it dies;
- a dead cell is **born** if it has exactly 3 live neighbors.

Neighbors are the 8 Moore neighbors, counted with **toroidal wrap** (via ``numpy.roll``), so the
grid has no walls. The function is **pure and deterministic**: no RNG, no global/mutable state —
the same input field always yields the same output.

The ``genome`` parameter is the seam shape that v1.1 fills with a Life-like rule. In v0 it is
**accepted and ignored**; nothing outside this module may assume a genome exists yet.
"""

from __future__ import annotations

import numpy as np

from engine.field import DTYPE, Field

# Vanilla Conway, fixed for v0 (genome arrives in v1).
_BIRTH = frozenset({3})
_SURVIVE = frozenset({2, 3})


def _neighbor_counts(field: Field) -> np.ndarray:
    """Count the 8 Moore neighbors of every cell with toroidal wrap.

    Summing eight shifted copies (via ``numpy.roll``, which wraps) gives each cell its live-neighbor
    count without an explicit boundary case — the wrap *is* the toroidal topology.
    """
    counts = np.zeros(field.shape, dtype=np.uint8)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            counts += np.roll(field, shift=(dr, dc), axis=(0, 1))
    return counts


def step(field: Field, genome: object | None = None) -> Field:
    """Advance ``field`` one Conway tick over a toroidal binary grid.

    Args:
        field: a 2D binary (uint8/bool) grid; values are read as alive (non-zero) / dead.
        genome: accepted for seam compatibility with v1+, **ignored in v0**.

    Returns:
        a new field (the input is never mutated) of the same shape and dtype.
    """
    field = np.asarray(field)
    if field.ndim != 2:
        raise ValueError(f"field must be 2D, got {field.ndim}D")

    alive = field != 0
    counts = _neighbor_counts(alive.astype(DTYPE))

    born = np.isin(counts, list(_BIRTH)) & ~alive
    survives = np.isin(counts, list(_SURVIVE)) & alive

    return (born | survives).astype(DTYPE)
