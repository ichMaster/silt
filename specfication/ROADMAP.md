# Roadmap — Silt

Four self-contained versions, built in order — the platform is stood up on the *simplest* engine
first, the biology is made interesting next, and the substrate is swapped last:

- **v0 — Pure Game of Life.** The whole stack (engine, store, tick loop, REST API, WebSocket, web UI,
  client) on **vanilla Conway (B3/S23)** — a single fixed rule, **no genome, no evolution**. Prove and
  debug the entire platform end-to-end on the dead-simplest engine.
- **v1 — Parametrized GOL + evolution.** Turn the fixed rule into a **genome** (the Life-like
  birth/survive rule itself), add `mutate`/`cross`, lineage, the selection-grade metrics, and the weak
  natural pressure — so the gardeners breed and select.
- **v2 — Challenges for parametrized GOL.** Turn the world into a **research scaffold**: `predict` +
  hit/miss, rule-space travel and Wolfram classification, fragility, form-hunting, and machine-building
  — challenges that yield a *checkable* prediction, closing cognition with a real hit-rate.
- **v3 — Lenia.** Swap `step()` for **Lenia** so phenotypes turn organic and alive; re-validate the
  metrics on continuous fields; upgrade the binary canvas to a float WebGL field.

Everything around the engine is built and debugged once across v0–v2 (on Game of Life) and carries
straight into v3 (Lenia); **only `step()`, the genome format, and the render shader change** (see
[ARCHITECTURE.md](ARCHITECTURE.md) §The engine seam). Versions are numbered from 0; phases inside a
version are `vA.B` (A = version, B = phase), e.g. `v1.2`. Each phase lists a **Goal**, a short
description, a **Tasks** list, and a **Definition of Done (DoD)**, and ships with the automated tests
that encode its DoD (see [ARCHITECTURE.md](ARCHITECTURE.md) §Testing and CI).

**The engine seam is honored from v0.1 and never violated:** nothing outside `step()` and the genome
may know which automaton runs inside. Complexity is added only by phase, never all at once.

**Transport (decided).** Лілі connects over the same **REST + WebSocket** API as the web UI — REST for
the request/response tools, `WS /stream` for the live field, `GET /events?since=` polling for the
session-start away-gap. **No bespoke TCP server** — HTTP/WS already provide framing, reconnection, and
auth; the only hard requirement is that Silt runs **always-on and reachable** (a daemon/service).

**Versioning (`A.B.C`).** `A` = roadmap version (v0…v3), `B` = phase within it (`v1.2` → `1.2.0`), `C`
= a post-release fix on that phase. Roadmap phase `vA.B` → semver `A.B.0`. Releases are cut per phase.
Never bump the version without explicit confirmation.

---

## v0 — Pure Game of Life: the whole stack on vanilla Conway (no genome yet)

Stand up and debug the **entire platform** — engine, store, tick loop, REST API, WebSocket stream, web
UI, and the client library — on the **simplest possible engine: vanilla Conway (fixed B3/S23)**. There
is no genome, no `mutate`/`cross`, and no selection metrics yet; the point is to prove the
infrastructure end-to-end (seed → tick → persist → replay → stream → render → act → observe) before any
biology. Every contract the later engines reuse is fixed here: the `step()` seam (shaped to take a
genome it ignores for now), the event log, the organism model, and the REST/WS API. Depends on:
nothing — this is the foundation.

### v0.1 — Engine: vanilla Conway

**Goal:** a deterministic, headless Conway engine behind the `step()` seam.

Project skeleton (`uv` + `ruff` + `pytest`, numpy) and the `engine` package. Implement `step(field, …)`
as fixed Conway B3/S23 over a **toroidal binary grid** (a live cell survives on 2–3 live neighbors, a
dead cell is born on exactly 3). The seam is shaped to accept a genome from v1.1, but v0 ignores it.
Ship named seed patterns (glider, blinker, Gosper gun) for tests and for seeding from the UI.

**Tasks:**
- Repo skeleton + `engine` package; `pyproject.toml` (ruff + pytest), numpy.
- `step(field, …)` — fixed Conway B3/S23 over a toroidal binary grid; the seam shape that v1.1 fills with a genome.
- Named seed patterns (glider, blinker, Gosper gun) + placing a pattern onto a field at a position.

**DoD:** from a fixed initial field the grid after K ticks is exactly reproducible; the glider
translates, the blinker has period 2, and the Gosper gun emits gliders.

**Tests:** unit — known figures (glider translation, blinker period 2, gun emission); the field pinned
exactly after K ticks from a fixed initial field.

### v0.2 — Store, organisms, basic metrics

**Goal:** persist the world, reconstruct any tick exactly, and track live regions.

The `Store` interface (SQLite + blob snapshots): **periodic snapshots** (field + organisms) plus an
**append-only event log**, with **replay** reconstructing any point. Track **organisms** as connected
live regions (connected-components → `bbox`, `birth_tick`, `status`). Compute a **minimal display
metrics** set only — `mass`, `age`, `alive` — enough for the UI/observe; the selection-grade metrics
arrive in v1.2. Define the `Event`/`Organism`/`World` record shapes here.

**Tasks:**
- `Store` interface + SQLite/blob backend; append-only event log; periodic snapshots; replay from snapshot + log.
- Organism tracking via connected components (`bbox`, `birth_tick`, `status`); `Event`/`Organism`/`World` shapes.
- Minimal display metrics (`mass`, `age`, `alive`) over a recorded run.

**DoD:** a world advanced N ticks with interleaved events, snapshotted and replayed from an earlier
snapshot + log, reconstructs **byte-for-byte identical** state; organisms are tracked across ticks;
observe/history returns the basic metrics + the run.

**Tests:** contract — `Event`/`Organism`/`World` shapes; integration — replay-equivalence across a
snapshot boundary; organism membership stable under a moving glider.

### v0.3 — Tick loop + REST API

**Goal:** the world ticks in real time, deterministically, and gardeners act on it over REST.

The real-time tick loop (`while running: step(); persist_on_interval(); sleep(tick_interval)`) with an
**injected clock** (real on the server, frozen in tests). Every action enters as a **timestamped event
applied at a tick boundary** — never mid-tick — so the world stays a pure function of
`(seed, initial_field, ordered_event_log)`. FastAPI facade with auth (gardener id + token; equal
capabilities; isolates identity, not the shared field). v0 actions are only those without a genome:
`/seed` (a named pattern at a position), `/cull`, `/goal`; queries: `/world`, `/organism/{id}`,
`/organism/{id}/history`, `/events?since=`. (`/mutate`, `/cross`, `/predict`, `/lineage` arrive with the
genome in v1–v2.)

**Tasks:**
- Tick loop with an **injected clock**; actions queued as events, applied at tick boundaries; wired to the Store.
- FastAPI app + auth (id + token per gardener; equal capabilities).
- REST actions `/seed`, `/cull`, `/goal`; queries `/world`, `/organism/{id}`, `/organism/{id}/history`, `/events?since=`.

**DoD:** the server ticks continuously with no clients; a `/seed` then later `/cull` reproduces an
identical world when the same event log is replayed on a frozen clock; auth distinguishes gardeners
while they share one field.

**Tests:** integration — action events apply at tick boundaries (frozen clock) and replay identically;
contract — each REST endpoint's request/response shape; auth isolates identity but not the field.

### v0.4 — WebSocket stream + web UI

**Goal:** watch the world live and tend it from a browser.

`WS /stream` (downsampled **binary** frames + events, live). The static web UI on the same server, in
layers: **render** (live binary canvas — no WebGL needed — pan/zoom, organisms outlined and labeled by
owner in distinct hues), **act** (click-to-seed, select-to-cull), **inspect** (metrics, a history
scrubber that replays a run), and a **feed** of world events so each gardener sees the other's traces.

**Tasks:**
- `WS /stream`: downsampled binary frames + events, pushed live.
- Render: binary-canvas field at 60fps, pan/zoom, owner-colored organism outlines/labels.
- Act: click-to-seed (named pattern), select-to-cull. Inspect: organism metrics + a history scrubber. Feed: event timeline.

**DoD:** the field renders live from the WS stream and stays smooth under pan/zoom; a human can seed and
cull from the UI; clicking an organism shows its metrics and a replayable history; the feed shows both
gardeners' actions.

**Tests:** integration — the WS stream emits frames + events on tick; a UI action issues the right REST
call and appears in the feed; the scrubber replays a recorded run.

### v0.5 — Client library (the connection for Лілі)

**Goal:** a non-UI client connects to the world as an equal gardener through the same API.

The thin `client` library wrapping REST for the v0 tools — `seed`, `observe` (= organism/history),
`cull`, `set_goal` — plus `events_since(tick)` for the session-start away-gap catch-up. The client
holds **no world logic** and Silt holds **no Lumi state** — Лілі is just one authenticated HTTP client
(REST + optional `WS /stream`); the boundary stays clean. `mutate`/`cross` (v1) and `predict` (v2) are
added to the client as those tools land. This is the wiring point into Lumi, kept on the Lumi side.

**Tasks:**
- `client` library: `seed`, `observe`, `cull`, `set_goal`, each a thin call onto REST with the gardener's token.
- `events_since(tick)` away-gap catch-up; optional `watch()` over `WS /stream`.
- A reference example: connect → seed a pattern → observe metrics + history → catch up on events.

**DoD:** a non-UI client can seed/observe/cull/set_goal against the live server and, on connect,
reconstruct what changed since a given tick — all over the same API the web UI uses, with no Silt→Lumi
dependency.

**Tests:** integration — the client drives a full seed→observe→events loop against the server;
`events_since` returns the correct slice; auth scoping is enforced. **No Silt module imports Lumi (pinned).**

---

## v1 — Parametrized GOL + evolution: genome, mutate/cross, lineage, selection

Turn the fixed Conway rule into a **genome** and make evolution work — the gardeners breed and select.
The Life-like rule becomes the DNA (`GolGenome`); `mutate`/`cross` operate on it; the evaluator gains
the selection-grade metrics; the lineage graph and the weak natural pressure come online. Everything
slots in behind the v0 seams — the store, tick loop, API, UI, and client are extended, not rewritten.
Depends on: all of v0.

### v1.1 — Parametrized engine + genome

**Goal:** the rule becomes a genome with the two genetic operations, behind the same `step()` seam.

Generalize `step(field, genome)` to a Life-like automaton whose genome **is** the rule: `GolGenome`
(`birth: [int]`, `survive: [int]`, `radius: int`, `seed_pattern: [[0|1]]`, `parents`, `author`, `name`)
— Conway becomes simply the `B3/S23` genome. Implement the pure, seeded genetic operations: `mutate`
(flip membership in `birth`/`survive`, or nudge `radius`) and `cross` (mix the rule sets, `parents=[a,b]`).

**Tasks:**
- `GolGenome` type; generalize `step(field, genome)` to count neighbors within `radius` and apply `birth`/`survive`.
- Re-express vanilla Conway as the `B3/S23` genome (the v0 behavior is now one point in genome-space).
- `mutate(genome, strength)` and `cross(a, b)` — pure, deterministic under a seeded RNG; `seed_pattern` from the genome.

**DoD:** a fixed `(seed, genome)` reproduces the field exactly after K ticks; the `B3/S23` genome
reproduces v0's Conway behavior; `mutate`/`cross` are deterministic under a fixed RNG seed.

**Tests:** unit — `B3/S23` matches the v0 Conway engine; a non-Conway rule (e.g. HighLife `B36/S23`)
behaves as expected; `mutate`/`cross` reproducible under a fixed seed.

### v1.2 — Evaluator: selection metrics, lineage, natural pressure

**Goal:** measure a run well enough to *select* on it, track ancestry, and let unfit forms fade.

Extend the substrate-agnostic evaluator to the full `Metrics` set over recorded runs — `mass_trend`,
`chaos`, `movement`, `complexity`, `resilience` (a **seeded perturbation replay**), `period`. Build the
**lineage** parentage graph (who descends from whom). Fold the **weak natural pressure** (between-visit
decay: organisms below a mass/fitness floor fade) into the deterministic `step` — *not* a random cull,
so it stays replayable.

**Tasks:**
- Full `Metrics` (`mass_trend`, `chaos`, `movement`, `complexity`, `resilience`, `period`) as pure functions of a run.
- `resilience` as a seeded perturbed replay; `period`/`chaos` from the change-history.
- Lineage parentage graph; weak natural pressure as part of the deterministic `step`.

**DoD:** every metric is pinned against fixed recorded runs (a glider → non-zero `movement`, a still
life → `chaos≈0`, an oscillator → its `period`); `resilience` reproducible under a fixed perturbation
seed; an organism below the floor fades deterministically; lineage records parentage.

**Tests:** unit — each metric pinned on a fixed run; `resilience` deterministic under a seeded poke;
weak-pressure decay is replayable; lineage edges correct after `mutate`/`cross`.

### v1.3 — Evolution in the API, UI, and client

**Goal:** breed and select from the browser and from the client.

Add the genome actions/queries: `/mutate`, `/cross`, `/lineage`. In the UI: a **genome editor**
(sliders/toggles over the rule + seed), a **lineage tree**, and select-to-mutate/cross. Extend the
client with `mutate`/`cross` — completing the six tools (`seed, mutate, cross, observe, cull,
set_goal`). The gardener can now keep a bloodline ("five mutations in, this line heals itself").

**Tasks:**
- REST `/mutate`, `/cross`, `/lineage`; genome carried through events and organism records.
- UI: genome editor (author a rule by hand), lineage tree, select-to-mutate/cross.
- Client: add `mutate`/`cross` (the six tools complete).

**DoD:** a gardener (UI or client) can author/seed a genome, mutate and cross organisms, and trace a
lineage; bloodlines persist and replay; both gardeners' breeding shows in the feed.

**Tests:** integration — an author→seed→mutate→cross→observe loop over the API; lineage query returns
correct ancestry/descendants; the genome editor round-trips a rule.

---

## v2 — Challenges for parametrized GOL: the research scaffold

Turn the world into a **research program**, not just a garden. A *challenge* is a stated intent plus a
**checkable prediction** plus a measured outcome — built on the existing primitives (`set_goal` +
`predict` + `observe`/`events`), optionally tied together by a thin `Challenge` aggregate. This is the
cognition layer: Лілі (and the human) ask questions they **answer by experiment** and close them with a
real hit-rate, not "looked nice." Depends on: v1 (genome, evolution, metrics).

### v2.1 — Predict + hit/miss (the objective calibrator)

**Goal:** a client can predict a metric before a run; the world judges it.

`POST /predict { genome|organism_id, metric, expected }` → `prediction_id`; `GET /prediction/{id}` →
`{measured, hit}`, with per-metric tolerance. Add `predict` to the client tools. Surface predictions and
their hit/miss in the feed and on the organism inspector — the **second calibrator** (the world itself)
alongside the human gardener. A wrong mental model is caught independently of any human.

**Tasks:**
- `/predict` + `/prediction/{id}`; per-metric tolerance; stable hit/miss.
- Client `predict` tool; predictions + outcomes shown in the feed and the inspector.

**DoD:** a client predicts a metric for a genome/organism, runs it, and gets a stable measured-vs-expected
hit/miss; predictions and outcomes are visible to both gardeners.

**Tests:** unit/contract — `predict` hit/miss stable for matching and mismatching expectations; the
prediction round-trips through the API and appears in the event slice.

### v2.2 — Rule-space travel & behavior classification

**Goal:** explore the space of Life-like rules and sort their character — answered by prediction.

Tooling for the main cognitive draw: **travel rule-space** (Conway `B3/S23` → HighLife `B36/S23`, which
has a replicator → `B2/S`, which explodes) and **classify behavior** into Wolfram-style classes (dies /
freezes / periodic / chaotic / complex) from the run's metrics. The edge-of-chaos questions ("where is
the line between all-dies and all-chaos? which rules give stable complexity?") become challenges with a
predicted class and a measured one.

**Tasks:**
- A rule-space sweep helper (vary `birth`/`survive`/`radius`); a classifier mapping a run's metrics → a Wolfram class.
- Challenge framing: a goal + a predicted class/metric + the measured outcome (a thin `Challenge` record over `goal`+`predict`).
- Surface a rule's character (class + key metrics) in the inspector/feed.

**DoD:** a gardener can sweep a region of rule-space, predict each rule's class, and read the measured
class + hit-rate; complex-class rules (e.g. Conway, HighLife) are distinguished from dead/chaotic ones.

**Tests:** unit — the classifier assigns known rules to the right class (Conway → complex, `B2/S` →
chaotic, a `S`-less rule → dies); a sweep is deterministic; challenge hit-rate computed correctly.

### v2.3 — Fragility, form-hunting & machines

**Goal:** the remaining research challenges — destruction, discovery, and construction.

**Fragility** (cognition via destruction): poke a stable form (remove cells) and measure `resilience` —
some self-repair, some collapse; find the repair limit. **Form-hunting** (creation): seed configurations
and keep what survives — still lifes, oscillators (period N), spaceships, the rare unbounded growth.
**Machines** (advanced creation): compose constructions from parts — glider guns, reflectors, delays,
even logic gates. Each is a challenge with a predicted outcome and a measured one.

**Tasks:**
- Fragility challenge: a seeded poke of N cells → `resilience` measured against a predicted recover/collapse.
- Form-hunting helpers: classify a survivor (still life / oscillator-period-N / spaceship / unbounded) from its metrics.
- Machine-building: place/compose known constructions; verify behavior (a gun emits, two streams cancel).

**DoD:** a gardener can poke a form and read whether it self-repaired (matching or missing a prediction),
hunt and auto-classify surviving forms, and assemble a known machine and confirm it works — each closing
a challenge with a hit/miss.

**Tests:** unit — `resilience` deterministic under a seeded poke; survivor classification correct on
known figures; a placed Gosper gun is detected as emitting; challenge outcomes recorded.

---

## v3 — Lenia: swap `step()` for continuous, organic life

With the whole stack proven and the research scaffold exercised on Game of Life, swap the engine for
**Lenia**: the field becomes continuous floats in `[0,1]`, phenotypes turn organic and alive (gliders,
self-healing rings, dividing blobs), and the genome becomes the richer Lenia vector. **Nothing else
changes** — server, store, tick loop, determinism model, REST/WebSocket API, lineage, evaluator,
challenges, and the web UI shell are reused; the metrics are re-validated on organic runs, and rendering
upgrades from the binary canvas to a float WebGL field. Depends on: all of v0–v2.

### v3.1 — Lenia engine behind the same seam

**Goal:** continuous Lenia phenotypes with the same `step()` contract and the same determinism guarantees.

Implement the Lenia `step`: `U = convolve(field, kernel)`, then `field' = clamp(field + dt*(growth(U) -
field*decay), 0, 1)`, with a radial ring `kernel`, a bell-shaped `growth` (μ/σ), `dt`, and `decay` — all
from the **Lenia `Genome`** (`kernel_radius`, `kernel_rings`, `kernel_peaks`, `growth_mu`, `growth_sigma`,
`dt`, `decay`, `seed_pattern`, meta). Reimplement `mutate` (Gaussian perturbation × `strength`) and `cross`
(per-param pick/blend) for the float genome. **Pin FFT/precision mode** so float runs match exactly. The
seam, world, store, tick loop, API, and challenges are untouched.

**Tasks:**
- Lenia `step(field, genome)` over a float toroidal field (FFT or direct convolution; pinned precision mode).
- The Lenia `Genome` type + ring-kernel and bell-growth construction from its params.
- `mutate` (Gaussian × `strength`) and `cross` (per-param) on the float genome; seeded RNG.
- Swap the engine binding behind the existing `step()` seam — **no change to store/tick-loop/API/world/challenges**.

**DoD:** a fixed `(seed, Lenia genome)` reproduces the float field exactly after K ticks (pinned
precision); a known Lenia organism (e.g. an Orbium glider) translates as expected; the rest of the v0–v2
stack runs unchanged on the new engine; `mutate`/`cross` deterministic.

**Tests:** unit — a known Lenia organism's behavior; the float field pinned exactly after K ticks under
the fixed precision mode; `mutate`/`cross` reproducible. Integration — the unchanged
store/tick-loop/API/replay/challenge tests pass against the Lenia engine.

### v3.2 — Metrics & challenges on organic phenotypes

**Goal:** confirm the substrate-agnostic evaluator and challenges read Lenia runs meaningfully.

The evaluator reads field history, so it runs on Lenia unchanged — but `mass`, `chaos`, `movement`, and
especially `resilience` (a perturbation on a *float* field) and `period` need re-validation and threshold
tuning for continuous values (`mass` as summed aliveness, `alive` via a float ε). Re-pin every metric and
the classifier against fixed Lenia runs; confirm `predict` hit/miss and the v2 challenges stay stable.

**Tasks:**
- Re-validate each metric on recorded Lenia runs; tune ε/thresholds for the float field (no contract change).
- Adapt the `resilience` perturbation to a float field (seeded magnitude) and re-pin it.
- Confirm `predict` tolerances and the Wolfram-style classifier make sense for continuous metrics.

**DoD:** every metric is pinned against fixed Lenia runs (a glider → non-zero `movement`, a stable ring →
low `chaos`, a divider → rising `mass_trend`); `resilience` reproducible under a seeded float poke;
`predict` and the challenges stable — all without changing the `Metrics` contract.

**Tests:** unit — each metric pinned on a fixed Lenia run; `resilience` deterministic under a seeded
float poke; the v1/v2 evaluator + challenge contract tests still hold.

### v3.3 — WebGL float-field rendering

**Goal:** render the continuous field smoothly at scale; keep the rest of the UI as-is.

Upgrade the render layer from the binary canvas to a **float WebGL shader**: a heat/organic colormap over
the per-cell aliveness, smooth at 60fps under pan/zoom, organisms still outlined and labeled by owner. The
act/inspect/feed layers and the WS stream contract are unchanged — only the render shader changes.

**Tasks:**
- WebGL float-field renderer (heat/organic colormap) over the WS stream; pan/zoom at scale.
- Keep owner-colored organism outlines/labels; reuse the act/inspect/feed layers unchanged.
- Tune stream downsampling for float frames (bandwidth vs. fidelity).

**DoD:** the Lenia float field renders smoothly via WebGL at 60fps under pan/zoom; organisms read clearly
by owner; acting, inspecting, and the feed work exactly as before — only the field rendering changed.

**Tests:** integration — the WS float-frame stream drives the renderer; act/inspect/feed still issue the
correct REST calls. (Shader output smoke-tested; UI logic unit-tested.)
