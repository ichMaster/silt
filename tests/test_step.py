"""Engine contract tests for SILT-002 — Conway ``step`` over a toroidal binary grid.

Pins the fixed B3/S23 rule, determinism (same input -> byte-for-byte same output, exactly
reproducible after K ticks), toroidal wrap, and engine purity (no input mutation, no RNG).
"""

from __future__ import annotations

import numpy as np

from engine import empty, step


def _set(field: np.ndarray, cells: list[tuple[int, int]]) -> np.ndarray:
    for r, c in cells:
        field[r, c] = 1
    return field


# --- hand-checked rule cases -------------------------------------------------------------------


def test_lone_live_cell_dies() -> None:
    """A live cell with 0 live neighbors dies (underpopulation)."""
    field = _set(empty(5, 5), [(2, 2)])
    assert step(field).sum() == 0


def test_block_is_a_still_life() -> None:
    """A 2x2 block — every cell has exactly 3 neighbors — survives unchanged forever."""
    field = _set(empty(6, 6), [(2, 2), (2, 3), (3, 2), (3, 3)])
    out = field
    for _ in range(10):
        out = step(out)
        assert np.array_equal(out, field)


def test_dead_cell_with_exactly_three_neighbors_is_born() -> None:
    """A dead cell touching exactly 3 live cells is born; with 2 it is not."""
    # An L of three live cells around the empty corner (2,2).
    field = _set(empty(6, 6), [(1, 2), (2, 1), (1, 1)])
    out = step(field)
    assert out[2, 2] == 1  # (2,2) has exactly 3 live neighbors -> born


def test_live_cell_dies_on_four_or_more_neighbors() -> None:
    """A live cell with 4+ live neighbors dies (overpopulation)."""
    # Center live cell surrounded by 4 orthogonal neighbors.
    field = _set(empty(6, 6), [(2, 2), (1, 2), (3, 2), (2, 1), (2, 3)])
    out = step(field)
    assert out[2, 2] == 0


def test_blinker_oscillates_period_two() -> None:
    """A horizontal blinker flips to vertical and back — pinned exact phases."""
    horizontal = _set(empty(5, 5), [(2, 1), (2, 2), (2, 3)])
    vertical = _set(empty(5, 5), [(1, 2), (2, 2), (3, 2)])

    phase1 = step(horizontal)
    assert np.array_equal(phase1, vertical)  # pinned: exact next state
    phase2 = step(phase1)
    assert np.array_equal(phase2, horizontal)  # period 2


# --- determinism / reproducibility -------------------------------------------------------------


def test_exactly_reproducible_after_k_ticks() -> None:
    """From a fixed initial field, K ticks are byte-for-byte reproducible across runs."""
    initial = _set(empty(8, 8), [(3, 3), (3, 4), (3, 5), (4, 5), (2, 4)])  # an r-pentomino-ish seed
    k = 12

    run_a = initial.copy()
    run_b = initial.copy()
    for _ in range(k):
        run_a = step(run_a)
        run_b = step(run_b)

    assert np.array_equal(run_a, run_b)
    assert run_a.dtype == initial.dtype


# --- toroidal wrap -------------------------------------------------------------------------------


def test_toroidal_wrap_pattern_reenters_opposite_side() -> None:
    """A blinker straddling the left/right edge oscillates across the top/bottom edge.

    Live cells at row 0, columns {4, 0, 1} on a 5x5 torus form a horizontal 3-in-a-row via wrap;
    one Conway tick turns it into a vertical blinker at column 0, rows {4, 0, 1} — proving the
    8-neighbor count and the result both wrap around the edges.
    """
    field = _set(empty(5, 5), [(0, 4), (0, 0), (0, 1)])
    out = step(field)
    expected = _set(empty(5, 5), [(4, 0), (0, 0), (1, 0)])
    assert np.array_equal(out, expected)


# --- purity --------------------------------------------------------------------------------------


def test_step_does_not_mutate_input() -> None:
    field = _set(empty(5, 5), [(2, 1), (2, 2), (2, 3)])
    snapshot = field.copy()
    step(field)
    assert np.array_equal(field, snapshot)  # input untouched


def test_step_is_referentially_transparent() -> None:
    field = _set(empty(6, 6), [(1, 1), (1, 2), (2, 1), (3, 3), (3, 4)])
    assert np.array_equal(step(field), step(field))  # same input -> same output, no hidden state


def test_genome_argument_is_accepted_and_ignored() -> None:
    field = _set(empty(5, 5), [(2, 1), (2, 2), (2, 3)])
    assert np.array_equal(step(field), step(field, genome={"anything": "ignored in v0"}))
