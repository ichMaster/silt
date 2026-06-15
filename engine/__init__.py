"""Silt engine — the automaton step seam.

The engine is the *only* component (plus the genome type and the render shader) that knows
which automaton runs inside. Everything else in Silt is substrate-agnostic and depends only
on the ``step(field, genome) -> field`` seam exposed here.

v0 runs vanilla Conway (a fixed ``B3/S23`` rule, no genome). The ``genome`` parameter is part
of the seam shape that v1 fills; v0 accepts and ignores it. See ``specfication/ARCHITECTURE.md``
(§The engine seam) and ``specfication/ROADMAP.md`` (§v0).
"""

from engine.field import Field, empty, from_pattern, live_count
from engine.patterns import PATTERNS, place
from engine.step import step

__all__ = ["PATTERNS", "Field", "empty", "from_pattern", "live_count", "place", "step"]
