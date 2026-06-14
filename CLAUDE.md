# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Building v0 (phase v0.1).** The repository is scaffolded — `pyproject.toml` (`uv` + `ruff` +
`pytest` + `numpy`), the `engine` package, a `tests` package, and hermetic CI — and the first engine
work has begun. The spec is still authoritative for everything not yet built.

### Build / lint / test commands

```bash
uv sync --extra dev      # create the environment (mirrors Lumi's tooling)
uv run ruff check .      # lint
uv run pytest            # tests
```

The spec lives in `specfication/` (note: the directory name is misspelled on disk — reference it
as-is). Read it before implementing — the sections below summarize the load-bearing decisions, but
the spec is authoritative:

- [specfication/vision/SILT_SPEC.md](specfication/vision/SILT_SPEC.md) — the original vision (the
  ground truth all else is derived from).
- [specfication/MISSION.md](specfication/MISSION.md) — what Silt is, principles, non-goals, glossary.
- [specfication/ARCHITECTURE.md](specfication/ARCHITECTURE.md) — the five components, the engine seam,
  genome, evaluator, persistence, determinism, the API contract, layout, and testing.
- [specfication/ROADMAP.md](specfication/ROADMAP.md) — four versions (v0 pure-Conway platform → v1
  parametrized GOL + evolution → v2 challenges → v3 Lenia) as phases `vA.B`, each with Goal / Tasks /
  DoD / Tests.

When asked to "implement v1.2" or "start v0", treat that phase's **DoD** as the acceptance criteria,
its **Tasks** as the work list, and the ARCHITECTURE contracts (the `step` seam, genome, metrics,
event log, API) as the interfaces to honor. Build by phase — do not pull later versions forward (no
genome in v0; no Lenia/WebGL until v3).

## What Silt is

An always-on server hosting a shared 2D artificial-life world (Lenia / Life-like cellular automata).
Two "gardeners" tend one field: a human via a web canvas, and an API client (Лілі). The world ticks
in real time on its own. Gardeners drive evolution by manual selection (seed / mutate / cross), with
weak natural decay between visits. Silt is standalone and knows nothing about its API clients — they
are just authenticated clients.

## Architecture (five parts behind one `step()`)

1. **Engine** — pure automaton step: `step(field, genome) -> field`. Framework-agnostic, importable
   as a library, unit-testable headless.
2. **Evaluator** — `evaluate(history) -> Metrics`, pure functions over a recorded run. Also handles
   `predict(genome, {metric: expected})` returning a measured value + hit/miss.
3. **Store** — persistence: periodic field snapshots + an append-only event log; replay reconstructs
   any point. Behind a swappable `Store` interface (start with SQLite + blob snapshots).
4. **Tick loop** — advances the world in real time, even with no clients connected.
5. **API facade** — REST for actions/queries, WebSocket for live field streaming.

The Web UI (human canvas) and Лілі are both just clients of the same API. Intended stack: Python +
numpy (engine/evaluator), FastAPI (REST + WebSocket), static canvas/WebGL web UI. The `.gitignore` is
Python-oriented; tests are expected under pytest.

## The most important architectural invariant: the `step()` seam

Everything in the system is **substrate-agnostic** — it does not know which automaton runs inside.
The engine is swapped on Game of Life first, Lenia last, across four versions (see ROADMAP):

- **v0 — vanilla Conway** (fixed `B3/S23`, **no genome**). Integer binary grid, ~5-line rule,
  determinism is free (no floats/FFT). Used to stand up and debug the **entire platform** — tick loop,
  store/replay, REST API, WebSocket, web UI, client — on the simplest possible engine, before any
  biology. Renders on a plain binary canvas.
- **v1 — parametrized GOL + evolution.** The rule becomes a genome (a Life-like automaton whose genome
  *is* the birth/survive rule); add `mutate`/`cross`, lineage, the selection-grade metrics, and the
  weak natural pressure.
- **v2 — challenges.** The research scaffold: `predict` + hit/miss, rule-space travel, Wolfram
  classification, fragility, form-hunting, machines — built on `goal`+`predict`+`observe`.
- **v3 — swap `step()` for Lenia** (continuous float field, organic phenotypes, the richer Lenia
  genome). Rendering upgrades to a float WebGL shader.

**Only `step()`, the genome format, and the render shader change** across the substrate swap. The
server, Store, tick loop, determinism model, REST/WebSocket API, lineage, Evaluator, all metrics, the
challenges, the web UI shell, and the client tools are **identical** across the Game-of-Life versions
(v0–v2) and Lenia (v3). When implementing anything outside `step()` and the genome, write it
substrate-agnostically so the Lenia swap touches nothing else. **Build each version fully before the
next; the genome does not exist until v1, Lenia not until v3.**

## Determinism contract (non-negotiable, the heart of the system)

The world's evolution must be a **pure function of `(seed, initial_field, ordered_event_log)`**. Wall
time only decides *when* a tick fires, never *what* it computes. Concretely:

- Every gardener action enters as a **timestamped event applied at a tick boundary** (never
  mid-tick). The ordered event log is the only source of mutation.
- From any snapshot + the event log, the exact world state must be replayable — real-time on the
  server, frozen-clock in tests (inject the clock).
- **Weak natural pressure** (between-visit decay) is part of the deterministic `step`, not a separate
  random cull — so it stays replayable.
- `mutate` / `cross` are pure functions, deterministic under a seeded RNG. `resilience` uses a seeded
  perturbation replay.
- For Lenia, pin FFT/precision mode so float runs match exactly.
- **No model calls, no paid APIs, no randomness outside the seeded RNG** anywhere in the server — it
  is pure simulation.

Tests pin: engine field state after K ticks from fixed `(seed, genome)`; every metric against fixed
recorded runs; replay equivalence (snapshot + log reconstructs exact state); action events applying
at tick boundaries; stable `predict` hit/miss.

## Genetic operations

Pure functions on the genome: `mutate(genome, strength)` perturbs params (Gaussian noise scaled by
strength for Lenia; flip birth/survive membership or nudge radius for GOL), and `cross(a, b)` mixes
params with `parents=[a, b]`. The genome→phenotype link is intentionally chaotic — gardeners breed
and select, they do not design results.

## API surface (same contract for both clients)

REST writes: `POST /seed`, `/mutate`, `/cross`, `/cull`, `/predict`, `/goal`. REST reads:
`GET /world`, `/organism/{id}`, `/organism/{id}/history` (metrics + full tick-by-tick run — the
chosen return), `/lineage/{id}`, `/events?since=tick`, `/prediction/{id}`. Live: `WS /stream`
(downsampled field frames + events). Auth: each gardener has an id + token; equal capabilities;
auth isolates identity but **not** the shared field. The API client's six tools map straight onto
REST: `seed, mutate, cross, observe (=organism/history), cull, set_goal`, plus `predict`.

## Relationship to Lumi (Лілі)

Лілі — the API client the spec keeps referencing — is the **Lumi** project, a separate, mature
codebase at `/Users/Vitalii_Bondarenko2/development/lumi` (its own git repo). Lumi is a private text
persona; Silt is the shared world it will tend over the API as one authenticated gardener.

**The boundary is hard (spec §9): Silt knows nothing about Lumi and no Silt code may depend on it.**
Either runs without the other. Lumi consumes Silt's raw metrics/history and does all meaning-making
on top. So treat the Lumi repo as **context, not a dependency** — useful for understanding the client
side and for mirroring proven conventions, never to import from.

Worth borrowing from Lumi (it solved the same problems first):

- **Tooling:** `uv` for the environment, `ruff` for lint, `pytest` for tests — e.g. `uv sync --extra
  dev`, `uv run ruff check .`, `uv run pytest`. Adopted as of v0.1 — see the **Build / lint / test
  commands** under Project status above.
- **Injected clock for determinism.** The spec says to reconcile real-time with reproducibility "as
  Lumi already does" — Lumi injects the clock so tests run on a frozen clock. Mirror that pattern in
  the tick loop (§6).
- **Mock-only CI.** Lumi never calls paid APIs in tests. Silt is even stricter — it has no model at
  all (§10), pure simulation — so this is free, but keep CI hermetic.
- **The six tools + predict** map onto Silt's REST surface (§7); Лілі polls `/events?since=` on
  session start to learn "what happened while away" — the world-backed version of Lumi's between-
  session "away gap."

## Build order (see ROADMAP for phase DoDs)

- **v0 — pure Conway platform:** engine (fixed `B3/S23`) → store + organisms + basic metrics → tick
  loop + REST API → WebSocket + web UI → client library. The whole stack on the simplest engine, no
  genome.
- **v1 — parametrized GOL + evolution:** genome + `mutate`/`cross` → selection metrics + lineage +
  natural pressure → evolution in the API/UI/client (the six tools complete).
- **v2 — challenges:** `predict` + hit/miss → rule-space travel + classification → fragility +
  form-hunting + machines.
- **v3 — Lenia:** engine swap (float field, Lenia genome, pinned precision) → metrics/challenges
  re-validated → WebGL float rendering.

**Transport:** Лілі connects over the same REST + WebSocket API as the web UI (REST tools, `WS /stream`
live, `/events?since=` away-gap polling). No bespoke TCP server — the only hard requirement is that
Silt runs always-on and reachable.

## Workflow skills (spec → issues → execute pipeline)

A three-stage pipeline lives in `.claude/skills/` (ported from the sibling Lumi project, retargeted to
Silt — issue prefix `SILT-xxx`, areas `engine/evaluator/store/world/api/web/client/tests`, Python-only
validation with `pytest` + `ruff`, pure-simulation CI):

- **`/generate-issues <version>`** — derive `specfication/roadmap/implementation/v{N}-issues.md` from a
  ROADMAP version's phases (each phase's Goal / Tasks / DoD / Tests → one or more `SILT-xxx` issues with
  sizes, areas, dependencies, and DoD-aligned acceptance criteria).
- **`/upload-issues <version-issues-file>`** — split that file into `SILT-xxx` GitHub issues with
  `vN::` labels and dependencies; writes `specfication/roadmap/implementation/vN-github-report.md`.
- **`/execute-issues <label>`** — implement each issue in dependency order: code → `pytest` + `ruff`
  validation (incl. the determinism contract tests: pinned engine state, pinned metrics, replay
  equivalence, the no-Silt→Lumi-import boundary) → one commit per issue → close → `vN-execution-report.md`.

Issue files live under `specfication/roadmap/implementation/`, derived from the ROADMAP phases. The
pipeline uses the `gh` CLI and a GitHub remote (create one with `gh repo create` if the repo has none).
Lumi also ships a `/release-version` skill for the version bump; it was not imported here — `execute-issues`
carries the inline release steps (never bump the version without explicit confirmation).
