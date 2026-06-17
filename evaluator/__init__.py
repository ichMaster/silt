"""Silt evaluator — metrics (and, from v2, predict + classify) over a recorded run.

Pure functions, substrate-agnostic: the evaluator reads a recorded run of opaque field frames and
never knows which automaton produced them. v0 ships the minimal display subset (``mass``, ``age``,
``alive``) plus the observe/history payload; selection-grade metrics arrive in v1.2.
"""

from evaluator.metrics import Frame, History, evaluate, observe

__all__ = ["Frame", "History", "evaluate", "observe"]
