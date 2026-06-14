# Silt

An always-on server hosting a shared 2D artificial-life world (Life-like cellular automata → Lenia).
Two "gardeners" tend one field — a human via a web canvas and an API client (Лілі) — and drive
evolution by manual selection, with weak natural decay between visits.

The design lives in [`specfication/`](specfication/) (the directory name is misspelled on disk and
kept as-is):

- [`specfication/MISSION.md`](specfication/MISSION.md) — what Silt is, principles, non-goals.
- [`specfication/ARCHITECTURE.md`](specfication/ARCHITECTURE.md) — the five components, the `step()`
  seam, genome, evaluator, persistence, determinism, the API contract.
- [`specfication/ROADMAP.md`](specfication/ROADMAP.md) — four versions (v0 pure Conway → v1
  parametrized GOL + evolution → v2 challenges → v3 Lenia).

## Development

Tooling mirrors the sibling Lumi project: [`uv`](https://docs.astral.sh/uv/) for the environment,
[`ruff`](https://docs.astral.sh/ruff/) for lint, [`pytest`](https://docs.pytest.org/) for tests.

```bash
uv sync --extra dev      # create the environment
uv run ruff check .      # lint
uv run pytest            # tests
```

CI is hermetic by construction — Silt is pure simulation, with no model, no paid APIs, and no live
network anywhere in the test suite.

## Status

Greenfield, building by phase. Current phase: **v0.1 — Engine: vanilla Conway** (see the ROADMAP).
