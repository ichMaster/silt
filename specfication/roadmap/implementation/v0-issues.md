# Version v0 Issues — Pure Game of Life (the platform on vanilla Conway)

Derived from [ROADMAP.md](../../ROADMAP.md) §v0. Issue prefix `SILT-xxx`; labels `v0::…`. Generated 2026-06-15.

> Currently covers **phases v0.1–v0.2** (Engine: vanilla Conway; Store, organisms, basic metrics).
> Phases v0.3–v0.5 will be appended as they are generated; `SILT-xxx` numbering continues from the
> highest ID here.

## Issues Summary Table

| ID | Title | Size | Area | Phase | Dependencies |
|----|-------|------|------|-------|--------------|
| SILT-001 | Project skeleton + engine package + tooling | S | engine | v0.1 | — |
| SILT-002 | Conway `step()` over a toroidal binary grid | M | engine | v0.1 | SILT-001 |
| SILT-003 | Named seed patterns + placement | S | engine | v0.1 | SILT-002 |
| SILT-004 | World record shapes — `Event` / `Organism` / `World` | S | world | v0.2 | SILT-003 |
| SILT-005 | Organism tracking via connected components | M | world | v0.2 | SILT-004 |
| SILT-006 | `Store` interface + SQLite/blob backend | M | store | v0.2 | SILT-004 |
| SILT-007 | Replay — reconstruct any tick from snapshot + event log | M | store | v0.2 | SILT-006, SILT-005 |
| SILT-008 | Minimal display metrics + observe/history payload | S | evaluator | v0.2 | SILT-005, SILT-007 |

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

---

## SILT-004: World record shapes — `Event` / `Organism` / `World`

### Description
Define the core record types the rest of v0.2 (and the whole platform) serializes and reconstructs:
`Event`, `Organism`, and `World`. They are the data contract the Store persists, organism tracking
populates, and the Evaluator reads — pinned here once so every later seam shares one shape.

### What needs to be done
- Define `Event { tick, type, organism_id, owner, data }` with `type` an extensible set covering at
  least `seed|mutate|cross|cull|death|record|goal` — the single source of world mutation (suggested
  `world/records.py`).
- Define `Organism { id, genome, owner, bbox, birth_tick, last_metrics, status, note }`. In v0 there is
  **no genome** (none before v1.1) — keep the field but make it nullable so the v1.1 genome slots in
  without a shape change.
- Define `World { field, tick, seed, organisms, lineage, events, gardeners }` (`lineage` may be an empty
  graph in v0; it is populated in v1.2).
- Make the records **serializable** (dataclasses + to/from dict) and **pure data** — the heavy `field`
  grid serializes via the Store's blob path (SILT-006), not inline; no engine/store imports that would
  create an import cycle.

### Dependencies
SILT-003.

### Expected result
The three record types exist, round-trip through (de)serialization, and are importable by
`store`/`world`/`evaluator` without circular imports.

### Acceptance criteria
- [ ] `Event`, `Organism`, `World` defined with the ARCHITECTURE field sets; `Event.type` covers at least `seed|mutate|cross|cull|death|record|goal`.
- [ ] `Organism.genome` is **nullable** (v0 has no genome) and forward-compatible with the v1.1 genome — no later-version scope pulled in.
- [ ] Each record **round-trips through serialization** (to/from dict) — a contract test pins the three shapes.
- [ ] Records are pure data (no import cycle with `engine`/`store`); no Silt→Lumi import. `pytest` + `ruff` green.

---

## SILT-005: Organism tracking via connected components

### Description
Track organisms as connected live regions of the shared field — recomputing membership
(connected-components over live cells, with **toroidal adjacency**) each tick and tagging each region
with `bbox`, `birth_tick`, and `status`, carrying identity forward as the field evolves.

### What needs to be done
- Connected-component labeling over the binary field that honors **toroidal wrap** — a region straddling
  an edge is a single organism. Use `scipy.ndimage.label` (add `scipy` as a dependency) or a numpy
  BFS/union-find; if using `scipy.label`, stitch wrap-around components across opposite edges (suggested
  `world/organisms.py`).
- For each component compute a toroidal-aware `bbox`, set `birth_tick` when first seen, and maintain
  `status` across ticks; **match components tick-to-tick by overlap** so a drifting glider stays the
  *same* organism (identity carried forward).
- Populate the `Organism` records from SILT-004 (`genome=None` in v0).

### Dependencies
SILT-004. (Uses the engine `step` + glider from SILT-002/003, already closed.)

### Expected result
Advancing the engine yields a stable set of tracked organisms; a glider remains one organism with an
updating bbox as it drifts and wraps.

### Acceptance criteria
- [ ] Connected-component tracking yields `Organism` records with `bbox`, `birth_tick`, `status`; **toroidal adjacency** is honored (an edge-straddling region is one organism).
- [ ] **Organism membership is stable under a moving glider** — the glider stays a single organism with a translating bbox across ticks (pinned integration test using the SILT-003 glider).
- [ ] Identity carries forward tick-to-tick (overlap match); `birth_tick` is set once and preserved.
- [ ] Pure/deterministic (no RNG); no Silt→Lumi import. `pytest` + `ruff` green.

---

## SILT-006: `Store` interface + SQLite/blob backend

### Description
Persist the world behind a **swappable `Store` interface**: periodic field+organism snapshots as blobs
plus an **append-only event log**, on an embedded SQLite backend — the write path the replay (SILT-007)
reconstructs from.

### What needs to be done
- Define the abstract `Store` interface (suggested `store/base.py`): `append_event(event)`,
  `save_snapshot(tick, field, organisms, lineage)`, `load_snapshot(at_tick)` (nearest snapshot ≤ tick),
  and an ordered `events(since_tick)` / `events_between(a, b)`. Keep it backend-agnostic so the impl is
  swappable.
- Implement a **SQLite + blob** backend (suggested `store/sqlite_store.py`): events in an **append-only**
  log table totally ordered by `(tick, seq)`; field snapshots as compressed blobs (numpy `.npy`/`savez`
  bytes); organisms/lineage serialized via the SILT-004 records.
- Snapshots are **periodic** (every K ticks); between snapshots the event log is the sole mutation record.

### Dependencies
SILT-004.

### Expected result
A world's snapshots and events persist to SQLite and load back identically; the event log is append-only
and totally ordered.

### Acceptance criteria
- [ ] `Store` is an abstract interface with a SQLite/blob implementation; snapshots (field + organisms) and events **round-trip byte-identically** (the field blob restores exactly).
- [ ] The event log is **append-only** and totally ordered by `(tick, seq)`; `events(since_tick)` returns the correct ordered slice.
- [ ] `load_snapshot(at_tick)` returns the nearest snapshot **at or before** the tick.
- [ ] Hermetic (local SQLite only, no network/paid calls); no Silt→Lumi import. `pytest` + `ruff` green.

---

## SILT-007: Replay — reconstruct any tick from snapshot + event log

### Description
Reconstruct the **exact** world state at any tick by loading the nearest earlier snapshot and
re-advancing the engine, applying logged events at tick boundaries — the v0.2 determinism centerpiece
(`World` is a pure function of `(seed, initial_field, ordered_event_log)`).

### What needs to be done
- Implement `replay(store, target_tick) -> World` (suggested `store/replay.py`): load the nearest
  snapshot ≤ target, then `step()` forward to `target_tick`, applying each logged event **at its tick
  boundary, never mid-tick**, recomputing organisms (SILT-005) along the way.
- Guarantee replay from *any* snapshot reproduces **byte-for-byte identical** field + organism state.
  (The real-time tick loop that *generates* these events arrives in v0.3; here replay is exercised
  headlessly with a frozen clock.)

### Dependencies
SILT-006, SILT-005.

### Expected result
A world advanced N ticks with interleaved events, snapshotted, replays from an earlier snapshot + the log
to byte-for-byte identical state.

### Acceptance criteria
- [ ] `replay(store, target_tick)` reconstructs the field **byte-for-byte identical** to the live run — pinned integration test **across a snapshot boundary** with interleaved events.
- [ ] Events apply **at tick boundaries** (never mid-tick); the ordered event log is the sole source of mutation.
- [ ] Replayed organisms match the live run's organisms at the target tick.
- [ ] Deterministic/pure (no randomness outside any seeded path); no Silt→Lumi import. `pytest` + `ruff` green.

---

## SILT-008: Minimal display metrics + observe/history payload

### Description
Compute the **minimal** display-metric subset — `mass`, `age`, `alive` — purely over a recorded run, and
assemble the observe/history payload (metrics + the tick-by-tick run). The selection-grade metrics arrive
in v1.2; this is just enough for the UI/observe.

### What needs to be done
- Implement the minimal subset of `evaluate(history)` (suggested `evaluator/metrics.py`): `mass` (final
  live-cell total), `age` (ticks alive, mass > ε), `alive` (mass > ε) — per organism and/or world,
  computed **purely** over a recorded run (the model/UI never compute metrics).
- Assemble the **history/observe return**: metrics + the recorded tick-by-tick run (downsampled field
  frames + the event slice) as a serializable structure. The HTTP `GET /organism/{id}/history` endpoint
  that surfaces it arrives with the API in v0.3 — here it is a data structure only.

### Dependencies
SILT-005, SILT-007.

### Expected result
Observing a recorded run yields `{mass, age, alive}` plus the tick-by-tick run; the metric values are
pinned and reproducible.

### Acceptance criteria
- [ ] `evaluate(history)` returns the minimal subset `mass`, `age`, `alive`, computed **purely** over a recorded run (no later-version metrics pulled forward).
- [ ] Metric values are **pinned against a fixed recorded run** (deterministic).
- [ ] The history/observe payload bundles metrics + the recorded run (frames + event slice) and serializes.
- [ ] Pure/substrate-agnostic (no genome/automaton assumptions); no Silt→Lumi import. `pytest` + `ruff` green.
