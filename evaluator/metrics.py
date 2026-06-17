"""Minimal display metrics + the observe/history payload (SILT-008).

The Evaluator computes metrics **purely over a recorded run** — the model and UI never compute
metrics. v0 ships only the minimal display subset needed for observe/UI:

- ``mass``  — final live-cell total of the run's last frame.
- ``age``   — ticks alive: the number of recorded frames in which the entity had mass > ε.
- ``alive`` — whether the final frame has mass > ε.

The selection-grade metrics (chaos, movement, complexity, resilience, period, …) arrive in v1.2.
:func:`observe` assembles the chosen client return — the metrics **plus** the recorded tick-by-tick
run — as a JSON-serializable structure (the ``GET /organism/{id}/history`` endpoint that surfaces it
lands with the API in v0.3). Substrate-agnostic: it reads opaque field frames, never the automaton.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

import numpy as np

from world.records import Event

# Alive threshold. Binary fields (v0–v2): alive == at least one live cell. Lenia (v3) uses a small ε.
EPSILON = 0


@dataclass
class Frame:
    """One recorded tick of a run: the tick number and the (possibly downsampled) field."""

    tick: int
    field: Any

    def to_dict(self) -> dict[str, Any]:
        return {"tick": self.tick, "field": np.asarray(self.field).tolist()}


@dataclass
class History:
    """A recorded run: tick-by-tick field frames + the event slice that drove them."""

    frames: list[Frame] = dc_field(default_factory=list)
    events: list[Event] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frames": [f.to_dict() for f in self.frames],
            "events": [e.to_dict() for e in self.events],
        }


def _mass(field: Any) -> int:
    return int(np.count_nonzero(field))


def evaluate(history: History) -> dict[str, Any]:
    """Minimal display metrics over a recorded run: ``{mass, age, alive}``. Pure — no mutation."""
    frames = history.frames
    if not frames:
        return {"mass": 0, "age": 0, "alive": False}
    final_mass = _mass(frames[-1].field)
    age = sum(1 for f in frames if _mass(f.field) > EPSILON)
    return {"mass": final_mass, "age": age, "alive": final_mass > EPSILON}


def observe(history: History) -> dict[str, Any]:
    """The observe/history return: metrics + the recorded run, JSON-serializable."""
    return {"metrics": evaluate(history), "run": history.to_dict()}
