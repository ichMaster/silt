# Version v0 Issues — Pure Game of Life (the platform on vanilla Conway)

Derived from [ROADMAP.md](../../ROADMAP.md) §v0. Issue prefix `SILT-xxx`; labels `v0::…`. Generated 2026-06-15.

> Currently covers **phase v0.1** (Engine: vanilla Conway). Phases v0.2–v0.5 will be appended as they
> are generated; `SILT-xxx` numbering continues from the highest ID here.

## Issues Summary Table

| ID | Title | Size | Area | Phase | Dependencies |
|----|-------|------|------|-------|--------------|
| SILT-001 | Project skeleton + engine package + tooling | S | engine | v0.1 | — |
| SILT-002 | Conway `step()` over a toroidal binary grid | M | engine | v0.1 | SILT-001 |
| SILT-003 | Named seed patterns + placement | S | engine | v0.1 | SILT-002 |

---

## SILT-001: Project skeleton + engine package + tooling

### Description
Stand up the repository skeleton and the `engine` package so every later issue has a home, a test
runner, and a linter. This is the dependency-zero foundation of the whole project.

### What needs to be done
- Create `pyproject.toml` configured for `uv` with `ruff` + `pytest` + `numpy` — mirror the sibling
  Lumi project's tooling (`uv sync --extra dev`, `uv run ruff check .`, `uv run pytest`).
- Create the `engine/` package (`engine/__init__.py`) and a `tests/` package (with a `conftest.py` if useful).
- Add a minimal CI workflow (`.github/workflows/ci.yml`) running `ruff check .` + `pytest` on every
  push/PR. CI is **hermetic** — Silt is pure simulation, so there are no model/paid-API/network calls anywhere.
- (Optional) a short `README.md` stub pointing at `specfication/`.

### Dependencies
None.

### Expected result
`uv sync --extra dev` creates the environment; `uv run ruff check .` and `uv run pytest` both run green
(a placeholder test is fine); the `engine` package imports cleanly.

### Acceptance criteria
- [ ] `pyproject.toml` configures `uv` + `ruff` + `pytest` + `numpy`; `uv sync --extra dev` succeeds.
- [ ] `uv run ruff check .` passes; `uv run pytest` runs green against at least a placeholder test.
- [ ] `engine` and `tests` packages exist and import cleanly (`python -m py_compile`).
- [ ] CI workflow runs ruff + pytest on push/PR with no network/paid calls.
- [ ] The chosen build/lint/test commands are documented in `CLAUDE.md` (replacing the "not yet created" note).

## SILT-002: Conway `step()` over a toroidal binary grid

### Description
Implement the engine core — one deterministic Game-of-Life tick over a toroidal binary field, behind the
`step()` seam that v1.1 will later fill with a genome. This is the substrate the whole platform runs on in v0.

### What needs to be done
- Define the field representation: a 2D binary grid (numpy `uint8`/`bool`) with toroidal (wrap-around)
  neighbor semantics. Suggested: `engine/field.py` (empty/create/from-pattern helpers).
- Implement `step(field, genome=None) -> field` (suggested `engine/step.py`): fixed Conway **B3/S23** — a
  live cell survives on 2–3 live neighbors, a dead cell is born on exactly 3 — counting the 8 Moore
  neighbors with **toroidal wrap** (e.g. via `numpy.roll`). The `genome` parameter is **accepted but
  ignored in v0** — it is the seam shape that v1.1 fills (do not let anything outside `step` assume a genome).
- Keep the function **pure and deterministic**: no RNG, no global/mutable state; same input → same output.

### Dependencies
SILT-001.

### Expected result
Calling `step` repeatedly evolves a field deterministically; from a fixed initial field the grid after K
ticks is byte-for-byte reproducible.

### Acceptance criteria
- [ ] `step(field, genome=None) -> field` applies Conway B3/S23 with 8-neighbor **toroidal** counting; `genome` is accepted and ignored.
- [ ] From a fixed initial field, the grid after K ticks is **exactly reproducible** (pinned in a test).
- [ ] Toroidal wrap is verified — a pattern crossing an edge re-enters the opposite side.
- [ ] Hand-checked rule cases pass (a lone live cell dies; a dead cell with exactly 3 neighbors is born; a live cell survives on 2–3 and dies on 4+).
- [ ] `pytest` + `ruff` green; the engine stays pure (no RNG/global state).

## SILT-003: Named seed patterns + placement

### Description
Provide the canonical Life figures (glider, blinker, Gosper glider gun) and a way to place a pattern onto a
field at a position — for tests now and for seeding from the UI/client later. These figures also pin the
engine's correctness as living behavior (the v0.1 DoD).

### What needs to be done
- A small pattern library (suggested `engine/patterns.py`): `glider`, `blinker`, `gosper_glider_gun` as
  binary grids, plus `place(field, pattern, position)` that stamps a pattern at `(row, col)` with toroidal wrap.
- Tests exercising the v0.1 DoD figures against the engine from SILT-002.

### Dependencies
SILT-002.

### Expected result
A field can be seeded with a named figure at a position; the figures behave correctly under `step` (glider
moves, blinker oscillates, gun emits).

### Acceptance criteria
- [ ] `glider`, `blinker`, `gosper_glider_gun` patterns exist; `place(field, pattern, position)` stamps with toroidal wrap.
- [ ] **Glider translates** diagonally by (1,1) after 4 ticks (pinned).
- [ ] **Blinker oscillates** with period 2 (pinned).
- [ ] **Gosper gun emits** a glider — a new glider appears downstream after the gun's period (pinned).
- [ ] `pytest` + `ruff` green.
