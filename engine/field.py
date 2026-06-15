"""Field representation — a 2D binary grid with toroidal (wrap-around) semantics.

The field is the shared world's substrate. In v0 it is a binary grid (a cell is dead/alive);
``step`` (see :mod:`engine.step`) advances it under fixed Conway rules with toroidal wrap, so a
pattern that drifts off one edge re-enters the opposite side.

Cells are stored as numpy ``uint8`` (0 = dead, 1 = alive). Helpers here only *construct* and
*shape* fields; they never embed rules — the automaton lives behind the ``step`` seam alone.
"""

from __future__ import annotations

import numpy as np

# A field is a 2D numpy array of uint8 with values in {0, 1}.
Field = np.ndarray

DTYPE = np.uint8


def empty(height: int, width: int) -> Field:
    """Return an all-dead ``height x width`` field."""
    if height <= 0 or width <= 0:
        raise ValueError(f"field dimensions must be positive, got {height}x{width}")
    return np.zeros((height, width), dtype=DTYPE)


def from_pattern(pattern: np.ndarray) -> Field:
    """Return a field that is a copy of ``pattern``, normalized to the field dtype.

    Any non-zero cell becomes a live (1) cell, so callers may pass bool or int patterns.
    """
    arr = np.asarray(pattern)
    if arr.ndim != 2:
        raise ValueError(f"pattern must be 2D, got {arr.ndim}D")
    return (arr != 0).astype(DTYPE)


def live_count(field: Field) -> int:
    """Number of live cells (the field's mass) — a small convenience for tests/metrics."""
    return int(np.count_nonzero(field))
