# Architecture — Silt

The authoritative vision is [vision/SILT_SPEC.md](vision/SILT_SPEC.md); this document is the
implementation contract derived from it. Read [MISSION.md](MISSION.md) for the *why* and
[ROADMAP.md](ROADMAP.md) for the *when*.

## Overview

Silt is a single always-on server holding one shared world, fronted by a REST + WebSocket API. Two
kinds of client consume that API — a static web UI (the human gardener) and a thin client library
(Лілі). The server is **five parts behind one engine seam**: an **Engine** that advances the field,
an **Evaluator** that reads metrics from history, a **Store** that persists the world, a **Tick loop**
that drives the world in real time, and an **API facade** that exposes actions, queries, and a live
stream. The engine is `step(field, genome) -> field` and nothing else in the system knows which
automaton runs inside it.

```
┌─────────────────────────────────────────────────────┐
│  Silt server (always-on)                            │
│   Engine ──▶ Evaluator        Store                 │
│   (step)     (metrics)        (persist)             │
│     ▲ real-time tick loop                           │
│     │                                               │
│   API facade  (REST actions/queries + WS stream)    │
└──────┬───────────────────────────────┬──────────────┘
       │ WS + REST                      │ REST (tools)
   Web UI (human canvas)            Лілі (Lumi) client
```

## Components

- **Engine** — pure, framework-agnostic, headless, unit-testable. Exposes `step(field, genome) -> field`
  and the genetic operations `mutate(genome, strength)` / `cross(a, b)`. **Game of Life (v0–v2)** runs
  on an integer grid — vanilla Conway first (v0), then a parametrized Life-like genome (v1+); **Lenia
  (v3)** runs on a float grid. This is the *only* component (plus the genome type and the render
  shader) that changes when the substrate is swapped.
- **Evaluator** — pure functions over a recorded run: `evaluate(history) -> Metrics` and the `predict`
  hit/miss check. Substrate-agnostic — it reads field history, so it is identical for GOL and Lenia.
- **Store** — persistence behind a swappable `Store` interface: periodic field snapshots + an
  append-only event log; replay reconstructs any tick. Start with SQLite + blob snapshots.
- **Tick loop** — advances the world in real time (`step` → persist on interval → sleep), even with no
  clients connected. Applies queued action events at tick boundaries. Clock is injected (real on the
  server, frozen in tests).
- **API facade** — FastAPI: REST for write actions and read queries, WebSocket for the live field
  stream. Authenticates gardeners; serializes world/organism/lineage/history responses.

The **Web UI** and **Лілі** are both just clients of this API; neither holds world logic.

## The engine seam (`step`) — the central invariant

Everything outside `step()` and the genome format is **substrate-agnostic** and must be written so the
Lenia swap touches nothing else. Concretely, these are identical across the Game-of-Life versions
(v0–v2) and Lenia (v3): the server, the Store (snapshots + event log + replay), the tick loop and its
determinism model, the REST/WebSocket API, lineage, the Evaluator and every metric, the challenges,
the web UI shell, and the client tools. **Changes only:** `step()`, the genome type, and the render
shader.

**Game of Life (v0–v2).** v0 runs **vanilla Conway** (a fixed `B3/S23` rule, no genome) to stand up
the whole platform; from v1 the rule becomes a genome — a Life-like automaton whose genome is the rule
itself:

```
GolGenome { birth: [int], survive: [int], radius: int, seed_pattern: [[0|1]],
            parents: [uuid], author: str, name: str }       # Conway = B3/S23 (the v0 fixed rule)
step: count live neighbors within radius → a cell is born if count ∈ birth,
      a live cell survives if count ∈ survive, else it dies.
mutate(g, strength) → flip membership in birth/survive, or nudge radius.   # v1+
cross(a, b)         → mix the birth/survive sets.                          # v1+
```

Integer grid → determinism is free (no floats, no FFT, no precision issues); the rule is ~5 lines;
known figures (glider, Gosper gun) seed the first tests; binary cells render on a plain canvas.

**Lenia (v3).** A continuous-state automaton (one tick, deterministic):

```
U      = convolve(field, kernel)                     # neighborhood potential (FFT or direct)
field' = clamp(field + dt * (growth(U) - field*decay), 0, 1)
```

`kernel` is a radial ring kernel from genome params; `growth(U)` is a bell centered at μ with width σ;
`dt` is the time step; `decay` the per-cell decay. This is what makes Lenia organisms look alive
(gliders, self-healing rings, dividing blobs). FFT/precision mode is pinned for reproducibility.

## The world (field + organisms)

The field is **one shared, toroidal grid** (wraps at edges so organisms drift without hitting walls).
It is one canvas, but the world tracks **organisms** as connected live regions, each tagged with its
seeding genome and owner. Multiple organisms — different genomes, different gardeners — coexist on the
same field and interact at their boundaries. An organism's bounding box, birth tick, last metrics, and
status are tracked; its membership is recomputed (connected-component over live cells) as the field
evolves.

## Genome

A genome is a compact, serializable parameter vector — the DNA a gardener writes. The **GOL genome**
(from v1; v0 runs the fixed Conway rule with no genome) is the integer rule above; the **Lenia genome**
(v3) is:

```
Genome {
  id: uuid,
  kernel_radius: int(4..24), kernel_rings: [float](1..3), kernel_peaks: [float](0..1),  # body plan
  growth_mu: float(0..1), growth_sigma: float(0..0.3), dt: float(0.02..0.5), decay: float(0..0.2), # metabolism
  seed_pattern: [[float]] | "random:R",                                                  # starting body
  parents: [uuid], author: str, name: str                                                # meta
}
```

The genome→phenotype link is **chaotic** by design: a small change in `growth_mu`/`sigma` can flip a
stable ring into a wandering glider or into chaos. Gardeners **breed and select**; they do not design
the result. Both genetic operations are **pure** and deterministic under a seeded RNG: `mutate(genome,
strength)` perturbs params (Gaussian noise for Lenia; flip rule membership / nudge radius for GOL), and
`cross(a, b)` mixes params per-param and records `parents=[a, b]`.

## Evaluator (metrics + predict)

`evaluate(history) -> Metrics`, computed purely from a recorded run of N ticks; the model and UI never
compute metrics. The starter set (extensible):

```
Metrics { age:int, alive:bool, mass:float, mass_trend:float, chaos:float(0..1),
          movement:float, complexity:float, resilience:float, period:int|0 }
```

- `age` — ticks alive (mass > ε); `mass` — final live-cell total; `mass_trend` — growing/stable/shrinking.
- `chaos` — entropy of change (0 ordered/periodic … 1 turbulent); `period` — detected oscillation period.
- `movement` — net center-of-mass displacement per tick (glider-ness); `complexity` — compressed-size proxy.
- `resilience` — survival after a **seeded perturbation replay** (poke N cells → does it recover?); the
  "is it really alive" test, run as a small separate replay.

**Predict.** A client may submit `predict(genome|organism_id, {metric: expected})` before/around a run;
the evaluator returns the measured value and a hit/miss. This is the objective self-calibrator — the
world catches a wrong mental model independently of any human.

## Challenges (the research scaffold, from v2)

A **challenge** is not a new subsystem but a *workflow* over the existing primitives: a stated intent
(`/goal`) + a checkable claim (`/predict`) + a measured outcome (`/observe`, `/events`). It turns the
garden into a research program — rule-space travel, Wolfram-style behavior classification (dies /
freezes / periodic / chaotic / complex), fragility (poke → repair limit), form-hunting, and
machine-building — where Лілі (and the human) ask questions they **answer by experiment** and close with
a real hit-rate, not "looked nice." v2 may add a thin `Challenge` aggregate tying a goal to its
prediction(s) and result, plus a metrics-based **classifier**; both are pure and substrate-agnostic, so
they carry from Game of Life (v2) into Lenia (v3) unchanged. See [ROADMAP.md](ROADMAP.md) §v2.

## World state & persistence

```
World    { field: grid, tick: int, seed: int, organisms: [Organism], lineage: Graph,
           events: [Event], gardeners: [{id, name}] }
Organism { id, genome, owner, bbox, birth_tick, last_metrics, status, note }
Event    { tick, type, organism_id, owner, data }   # type: seed|mutate|cross|cull|death|record|goal|...
```

**Persistence** lives behind a swappable `Store` interface. The full field is heavy, so the Store writes
**periodic snapshots** (field + organisms + lineage) and an **append-only event log**, replaying events
between snapshots to reconstruct any point. Start with a single embedded DB (SQLite + blob snapshots).

**Full run history** is the chosen client return: observing an organism yields **metrics + the recorded
tick-by-tick run** (downsampled field frames + the event slice), so a client can replay/visualize
exactly what happened.

## Real-time tick loop & determinism (non-negotiable)

The world ticks continuously (`while running: step(); persist_on_interval(); sleep(tick_interval)`),
even with no clients. Real-time and reproducibility are reconciled by one rule:

- **The world is a pure function of `(seed, initial_field, ordered_event_log)`.** Wall time decides only
  *when* a tick fires, never *what* it computes.
- **Every gardener action enters as a timestamped event in the ordered log, applied at a tick boundary**
  (never mid-tick). The event log is the sole source of mutation.
- From any snapshot + the event log, the exact world state is **replayable** — real-time on the server,
  **frozen-clock in tests** (inject the clock, as Lumi already does).
- **Weak natural pressure** (between-visit decay) is part of the deterministic `step` — organisms below
  a fitness/mass floor fade per the rule, *not* a separate random cull — so it stays replayable.
- **No model calls, no paid APIs, no randomness outside the seeded RNG** anywhere in the server.

## API (the contract — same for both clients)

**Auth.** Each gardener has an `id` + token; equal capabilities. Auth isolates *identity/authorship*,
**not** the shared field.

**REST — actions (write):**
```
POST /seed    { genome, position }                       -> organism_id
POST /mutate  { organism_id, strength }                  -> new organism_id
POST /cross   { organism_id_a, organism_id_b }           -> new organism_id
POST /cull    { organism_id }                            -> ok
POST /predict { genome|organism_id, metric, expected }   -> prediction_id
POST /goal    { text }                                   -> ok          # a gardener's stated intent (annotation)
```

**REST — queries (read):**
```
GET /world                 -> { tick, bounds, organisms summary, gardeners }
GET /organism/{id}         -> { genome, metrics, lineage, note }
GET /organism/{id}/history -> metrics + full tick-by-tick run            # the chosen return
GET /lineage/{id}          -> ancestry / descendants
GET /events?since=tick     -> event slice (what happened while away)
GET /prediction/{id}       -> { measured, hit }
```

**WebSocket — live:** `WS /stream` → downsampled field frames + events, in real time, for the web UI
and any client that wants to watch.

**Лілі's six tools** map straight onto REST — `seed, mutate, cross, observe (= organism/history), cull,
set_goal` — plus `predict`. She polls `GET /events?since=` on session start to learn "what happened
while I was away" (the world-backed version of Lumi's between-session away-gap).

## Human web UI

A static web app (canvas/WebGL) served by the same server:

- **Live field** — render the field 60fps from the WS stream (binary canvas in the Game-of-Life
  versions; float WebGL heat/organic colormap in the Lenia version); pan/zoom; organisms outlined and
  labeled by owner (you vs Лілі in different hues).
- **Act** — click to place a seed; select an organism to mutate/cross/cull; a small genome editor
  (sliders) to author DNA by hand.
- **Inspect** — click an organism → metrics, lineage tree, and a history scrubber (replay its life).
- **Feed** — a timeline of world events (births, deaths, records, who did what), so each gardener sees
  the other's traces.

WebGL matters in v3 because the Lenia field is per-cell float — shader rendering keeps it smooth at
scale. The Game-of-Life versions' binary cells need only a plain canvas.

## Boundary with Lumi (clean separation)

- Silt knows **nothing** about Лілі's personality, needs, or maturity. It exposes a world + API; all
  meaning-making lives in Lumi, on top of Silt's raw metrics/history.
- The two calibrators are honored here: the human gardener (via the UI) and the **objective `predict`
  hit/miss** (the world itself). Lumi reads both.
- **No Lumi state leaks into Silt; no Silt code depends on Lumi.** Either runs without the other. The
  Lumi repo is context, never an import — see [CLAUDE.md](../CLAUDE.md) §Relationship to Lumi.

## Stack & repository layout (intended, not yet created)

Python + numpy for the engine/evaluator; FastAPI for REST + WebSocket; a static canvas/WebGL web UI on
the same server. The engine stays framework-agnostic (importable as a library, unit-testable headless).
Tooling mirrors Lumi: `uv` (env), `ruff` (lint), `pytest` (tests); document the exact commands here once
scaffolded. Suggested layout:

```
/engine    # step() + genome + mutate/cross — Conway (v0) → parametrized GOL (v1) → Lenia (v3) behind one interface; numpy, headless
/evaluator # evaluate(history) -> Metrics + predict; pure, substrate-agnostic
/store     # Store interface + SQLite/blob impl: snapshots + append-only event log + replay
/world     # World state, organisms (connected-components), lineage, the tick loop (injected clock)
/api       # FastAPI: REST actions/queries + WS stream; auth; serialization
/web       # static canvas/WebGL UI (live field, act, inspect, feed)
/client    # thin client library: the six tools + predict + events-since (Лілі connects through this)
/tests     # pytest: engine determinism, evaluator pinning, replay equivalence, API contract
```

## Testing & CI

Determinism is the thing under test (vision §10):

- **Engine** — pin field state after K ticks from a fixed `(seed, genome)` (exact match; pin
  FFT/precision mode for Lenia). `mutate`/`cross` deterministic under a seeded RNG.
- **Evaluator** — pin every metric against fixed recorded runs; the `resilience` perturbation is seeded.
- **Replay** — snapshot + event log reconstructs the *exact* world state (real-time decoupled from
  computation).
- **API / contract** — action events apply at tick boundaries; auth isolates identity but not the shared
  field; `predict` returns a stable hit/miss; request/response shapes are pinned.
- **No paid calls, no model, no live network** anywhere in CI — the server is pure simulation, so tests
  are fully hermetic.
