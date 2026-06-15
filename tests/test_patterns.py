"""Pattern tests for SILT-003 — named seed figures + placement, and the v0.1 living-behavior DoD.

Pins: the glider translates diagonally by (1, 1) every 4 ticks; the blinker oscillates with
period 2; the Gosper glider gun emits a glider each 30-tick period; and ``place`` stamps a
pattern at a position with toroidal wrap.
"""

from __future__ import annotations

import numpy as np

from engine import empty, step
from engine.patterns import blinker, glider, gosper_glider_gun, place

# --- the figures exist with the right shape ----------------------------------------------------


def test_named_patterns_exist() -> None:
    assert glider.shape == (3, 3) and int(glider.sum()) == 5
    assert blinker.shape == (1, 3) and int(blinker.sum()) == 3
    assert gosper_glider_gun.sum() == 36  # the canonical Gosper gun footprint


# --- placement ---------------------------------------------------------------------------------


def test_place_stamps_pattern_at_position() -> None:
    field = place(empty(10, 10), blinker, (4, 5))
    assert field[4, 5] == 1 and field[4, 6] == 1 and field[4, 7] == 1
    assert int(field.sum()) == 3


def test_place_does_not_mutate_input() -> None:
    field = empty(8, 8)
    snapshot = field.copy()
    place(field, glider, (2, 2))
    assert np.array_equal(field, snapshot)


def test_place_wraps_toroidally() -> None:
    """A blinker placed straddling the right edge re-enters on the left."""
    field = place(empty(5, 5), blinker, (2, 4))  # cols 4, 0, 1 via wrap
    assert field[2, 4] == 1 and field[2, 0] == 1 and field[2, 1] == 1
    assert int(field.sum()) == 3


# --- living behavior under the engine (the v0.1 DoD) -------------------------------------------


def test_glider_translates_diagonally_after_four_ticks() -> None:
    field = place(empty(20, 20), glider, (5, 5))
    for _ in range(4):
        field = step(field)
    expected = place(empty(20, 20), glider, (6, 6))  # shifted by (1, 1)
    assert np.array_equal(field, expected)


def test_blinker_oscillates_period_two() -> None:
    field = place(empty(7, 7), blinker, (3, 2))
    one = step(field)
    two = step(one)
    assert not np.array_equal(one, field)  # it actually changed
    assert np.array_equal(two, field)  # back after 2 ticks


def test_gosper_gun_emits_one_glider_per_period() -> None:
    """The gun's population grows by exactly 5 cells (one glider) each 30-tick period."""
    field = place(empty(60, 60), gosper_glider_gun, (1, 1))  # large enough: no wrap for 60 ticks
    base = int(field.sum())
    assert base == 36

    f = field.copy()
    masses = {}
    for t in range(1, 61):
        f = step(f)
        if t in (30, 60):
            masses[t] = int(f.sum())

    assert masses[30] == base + 5  # one glider emitted after the first period
    assert masses[60] == base + 10  # a second glider after the second period


def test_gosper_gun_glider_appears_downstream() -> None:
    """After two periods a full glider sits well below the gun core (empty there initially)."""
    field = place(empty(60, 60), gosper_glider_gun, (1, 1))
    assert int(field[15:, :].sum()) == 0  # nothing downstream at the start

    f = field.copy()
    for _ in range(60):
        f = step(f)
    assert int(f[15:, :].sum()) == 5  # exactly one emitted glider, far from the gun core
