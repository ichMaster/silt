"""Named seed patterns and placement.

The canonical Life figures — ``glider``, ``blinker``, ``gosper_glider_gun`` — as small binary
grids, plus :func:`place`, which stamps a pattern onto a field at a ``(row, col)`` position with
**toroidal wrap** (matching the engine's edge topology). Used to seed tests now and the UI/client
later. These figures double as the v0.1 living-behavior pins: the glider translates, the blinker
oscillates, and the Gosper gun emits gliders under :func:`engine.step.step`.

Patterns are plain numpy ``uint8`` arrays (0 = dead, 1 = alive); coordinates are ``(row, col)``
with row 0 at the top. The position passed to :func:`place` is the pattern's top-left corner.
"""

from __future__ import annotations

import numpy as np

from engine.field import DTYPE, Field


def _pattern(rows: list[str]) -> np.ndarray:
    """Build a binary pattern from ASCII rows where ``O`` (or any non-space, non-``.``) is alive."""
    height = len(rows)
    width = max(len(r) for r in rows)
    grid = np.zeros((height, width), dtype=DTYPE)
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch not in (".", " "):
                grid[r, c] = 1
    return grid


# A glider — translates diagonally by (1, 1) every 4 ticks.
glider = _pattern(
    [
        ".O.",
        "..O",
        "OOO",
    ]
)

# A blinker — a period-2 oscillator (horizontal <-> vertical).
blinker = _pattern(["OOO"])

# Gosper glider gun — a period-30 gun that emits a glider every 30 ticks (Bill Gosper, 1970).
gosper_glider_gun = _pattern(
    [
        "........................O...........",
        "......................O.O...........",
        "............OO......OO............OO",
        "...........O...O....OO............OO",
        "OO........O.....O...OO..............",
        "OO........O...O.OO....O.O...........",
        "..........O.....O.......O...........",
        "...........O...O....................",
        "............OO......................",
    ]
)

# --- still lifes (unchanging under step) -------------------------------------------------------

block = _pattern(["OO", "OO"])
beehive = _pattern([".OO.", "O..O", ".OO."])
loaf = _pattern([".OO.", "O..O", ".O.O", "..O."])
boat = _pattern(["OO.", "O.O", ".O."])

# --- oscillators -------------------------------------------------------------------------------

# Toad — period 2.
toad = _pattern([".OOO", "OOO."])

# Beacon — period 2.
beacon = _pattern(["OO..", "OO..", "..OO", "..OO"])

# Pulsar — a large, striking period-3 oscillator.
pulsar = _pattern(
    [
        "..OOO...OOO..",
        ".............",
        "O....O.O....O",
        "O....O.O....O",
        "O....O.O....O",
        "..OOO...OOO..",
        ".............",
        "..OOO...OOO..",
        "O....O.O....O",
        "O....O.O....O",
        "O....O.O....O",
        ".............",
        "..OOO...OOO..",
    ]
)

# Pentadecathlon — a period-15 oscillator.
pentadecathlon = _pattern(["..O....O..", "OO.OOOO.OO", "..O....O.."])

# --- spaceships --------------------------------------------------------------------------------

# Lightweight spaceship (LWSS) — period 4, travels orthogonally at c/2.
lwss = _pattern([".OO..", "OOOO.", "OO.OO", "..OO."])

# --- methuselahs (small seeds with long, chaotic lifespans) ------------------------------------

# R-pentomino — 5 cells that stay active for over a thousand generations.
r_pentomino = _pattern([".OO", "OO.", ".O."])

# Acorn — 7 cells that grow explosively for thousands of generations.
acorn = _pattern([".O.....", "...O...", "OO..OOO"])

# Diehard — 7 cells that vanish completely after exactly 130 generations.
diehard = _pattern(["......O.", "OO......", ".O...OOO"])

# Registry of every named figure — the single source of truth for callers (e.g. tools.viz).
PATTERNS: dict[str, np.ndarray] = {
    "glider": glider,
    "blinker": blinker,
    "gosper_glider_gun": gosper_glider_gun,
    "block": block,
    "beehive": beehive,
    "loaf": loaf,
    "boat": boat,
    "toad": toad,
    "beacon": beacon,
    "pulsar": pulsar,
    "pentadecathlon": pentadecathlon,
    "lwss": lwss,
    "r_pentomino": r_pentomino,
    "acorn": acorn,
    "diehard": diehard,
}


def place(field: Field, pattern: np.ndarray, position: tuple[int, int]) -> Field:
    """Stamp ``pattern`` onto a copy of ``field`` at ``position`` (top-left), with toroidal wrap.

    Live cells in the pattern are OR-ed onto the field (existing live cells are never cleared), so
    patterns may overlap. Indices wrap around the field edges, matching the engine's toroidal
    topology — a pattern placed near an edge re-enters the opposite side.

    Args:
        field: the destination field (not mutated).
        pattern: a 2D binary pattern.
        position: ``(row, col)`` of the pattern's top-left cell on the field.

    Returns:
        a new field with the pattern stamped in.
    """
    field = np.asarray(field)
    if field.ndim != 2:
        raise ValueError(f"field must be 2D, got {field.ndim}D")
    pattern = np.asarray(pattern)
    if pattern.ndim != 2:
        raise ValueError(f"pattern must be 2D, got {pattern.ndim}D")

    out = field.copy()
    fh, fw = out.shape
    ph, pw = pattern.shape
    top, left = position

    rows = (np.arange(ph) + top) % fh
    cols = (np.arange(pw) + left) % fw
    # Outer-index the wrapped destination block and OR the pattern's live cells in.
    block = np.ix_(rows, cols)
    out[block] = (out[block] != 0) | (pattern != 0)
    return out.astype(DTYPE)
