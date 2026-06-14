# Silt — Specification

> A shared, always-living world of artificial life. Two gardeners — you and Лілі — tend one
> field. The world ticks on its own in real time; you act through a web canvas, Лілі acts
> through the API. Named after the Silt of Greg Egan's *Permutation City*: a self-contained
> deterministic universe whose life runs on its own, indifferent to who is watching.

Standalone project, independent of Lumi/Лілі. The world knows nothing about Лілі — she is just
one authenticated client among possibly many. This spec defines the engine, the genome, the
evaluator, the server, the human web UI, the client API, persistence, determinism, and tests.

## 0. Decisions (locked)

- **Substrate (staged):** the engine lives behind a clean `step()` interface, so the world is built
  in two stages — **v0 on a parametrized Game of Life** (Life-like automaton, integer genome) to
  stand up and debug the whole skeleton on the simplest possible engine, then **v1 swaps `step()`
  for Lenia** (continuous-state, organic, alive phenotypes). Everything around the engine is
  identical across both — only `step()` and the genome format change. See §3.
- **Evolution driver:** **manual selection by the gardeners** (seed / mutate / cross) as the engine
  of creation, plus a **weak natural pressure** (unfit blobs fade on their own between visits) — so
  gardeners are authors, not spectators, but the world still surprises them.
- **Topology:** **one shared field**, both gardeners act in it and see each other's traces.
- **Time:** **real-time, always-on** — the server ticks the world continuously, even when nobody
  watches.
- **Roles:** **equal gardeners** (you and Лілі have the same capabilities).
- **Form:** **a server** (the living world + API) **+ a web UI** (canvas/WebGL visualization for
  the human) **+ a thin client API** (Лілі connects over it).
- **Returns to clients:** **metrics + full run history** (not just numbers).

---

## 1. Architecture

```
┌─────────────────────────────────────────────┐
│  Silt Server (always-on)               │
│                                             │
│  ┌───────────┐   ┌───────────┐   ┌────────┐ │
│  │  Engine   │──▶│ Evaluator │   │ Store  │ │
│  │ (Lenia)   │   │ (metrics) │   │(persist)│ │
│  └───────────┘   └───────────┘   └────────┘ │
│        ▲ real-time tick loop                │
│        │                                    │
│  ┌─────┴───────────────────────────────┐   │
│  │  API facade (REST + WebSocket)       │  │
│  └──────┬───────────────────────┬───────┘   │
└─────────┼───────────────────────┼───────────┘
          │ WebSocket+REST        │ REST (tools)
   ┌──────┴───────┐        ┌──────┴───────┐
   │  Web UI       │        │  Лілі (Lumi) │
   │ (human canvas)│        │  client      │
   └───────────────┘        └──────────────┘
```

Five parts: **Engine** (pure Lenia step), **Evaluator** (metrics from history), **Store** (persist
field + organisms + lineage + events), **Tick loop** (advances the world in real time), **API
facade** (REST for actions/queries, WebSocket for live field streaming). Web UI and Лілі are both
just clients.

Stack: Python (numpy) for engine/evaluator; FastAPI for REST+WebSocket; the web UI is static
canvas/WebGL talking to the same API. Engine stays framework-agnostic (importable as a library and
unit-testable headless).

---

## 2. The world (Lenia)

**Field.** A 2D grid `field[H][W]` of floats in [0,1] — continuous "aliveness" per cell. Toroidal
(wraps at edges) so organisms can drift without hitting walls.

**The update (one tick).** Lenia's rule, deterministic:
```
U = convolve(field, kernel)          # neighborhood potential (FFT or direct)
field' = clamp(field + dt * (growth(U) - field*decay), 0, 1)
```
- `kernel` — a radial kernel (ring-shaped), defined by genome params.
- `growth(U)` — a bell-shaped function centered at μ with width σ (genome params): cells near the
  "right" amount of neighborhood grow, others die back.
- `dt` — time step (small → smooth, stable; large → twitchy).

This is what makes Lenia organisms look alive: smooth gliders, self-healing rings, dividing blobs.

**Organisms.** The field is one shared canvas, but the world tracks **organisms** as connected live
regions, each tagged with the genome that seeded it and an owner. Multiple organisms (different
genomes, different gardeners) coexist on the same field and can interact at their boundaries.

---

## 2a. Staging — v0 on parametrized GOL, v1 on Lenia

The whole project (server, store, tick loop, API, lineage, metrics, web UI, Лілі client) is
**independent of which automaton runs inside** — they differ only in `step(field, genome)`. So the
world is built in two stages on the same skeleton.

**v0 — parametrized Game of Life.** Not vanilla Conway (which has no genome — one rule for all), but
a **Life-like automaton** whose genome is the birth/survival rule itself, so genome / mutate / cross
already work on a trivial integer engine:

```
GolGenome {
  birth:        [int],     # neighbor counts that cause birth      (Conway: [3])
  survive:      [int],     # counts that keep a live cell alive    (Conway: [2,3])
  radius:       int,       # neighborhood radius (1 = Moore)
  seed_pattern: [[0|1]],   # starting figure (integer grid)
  parents, author, name
}
mutate(g, strength) → flip membership in birth/survive, or nudge radius
cross(a, b)         → mix the birth/survive sets
```
Why v0 is the right first step: the rule is ~5 lines; determinism is free (integer grid, no floats,
no FFT, no precision issues); it barely costs anything; known figures (glider, Gosper gun) seed the
first tests; binary cells render on a plain canvas (no WebGL needed yet). It lets you build and
debug the **entire skeleton** — tick loop, store/replay, API, shared-field traces, metrics,
predict, Лілі's tools — on the simplest engine.

**v1 — swap `step()` for Lenia.** The engine becomes continuous (§2), phenotypes turn organic and
alive, the genome becomes the richer Lenia vector (§3). Nothing around it changes, because it was
already debugged on GOL. Rendering upgrades from binary canvas to a float WebGL field.

**Identical across v0/v1:** server, Store (snapshots + event log + replay), tick loop + determinism
model, REST/WebSocket API, lineage, the Evaluator and all metrics (they read field history, so they
are substrate-agnostic), the web UI shell, and Лілі's six tools + predict. **Changes only:**
`step()` and the genome format (and the render shader).

**Research tasks Лілі can do on v0 (GOL).** A parametrized Life-like automaton is a real research
program, not a toy — enough to fill v0 on its own:

- **Form-hunting (creation).** Seed configurations and see what survives: still lifes, oscillators
  (period N), spaceships (moving), and the rare prize — unbounded growth. Select and keep what's
  alive and strange.
- **Exploring rule-space (cognition — the main draw).** Conway (B3/S23) is one point in a vast
  space of Life-like rules. She travels it — B36/S23 (HighLife, has a replicator), B2/S (explodes),
  and asks questions she *answers by experiment*: where is the edge between "all dies" and "all
  chaos"? which rules give stable complexity vs. only noise? which are "warm" (life at the edge of
  chaos)?
- **Behavior classification (cognition).** Sort rules into Wolfram's classes (dies / freezes /
  periodic / chaotic / complex), hunt the rare complex class, build her own map of rules' character.
- **Building machines (advanced creation).** From simple parts, compose constructions — glider guns,
  reflectors, delays, even logic gates (Life is Turing-complete). "I wired two guns so their streams
  cancel."
- **Lineages & selection (the genome at work).** Mutate the rule/configuration, select on a metric
  (lives longer, moves faster, more complex), keep a bloodline. "Five mutations in, this line made
  something that heals itself."
- **Fragility (cognition via destruction).** Poke a stable form (remove a cell): some self-repair
  (`resilience`), some collapse into chaos. How fragile is life, where is the repair limit —
  dramatic memories ("I poked it and the whole thing fell apart").

The tastiest at the start are **rule-space travel** and **classification**, because they yield a
prediction to check — closing cognition with a real hit-rate, not "looked nice". Limits of v0:
phenotypes are discrete and mechanical (Lenia fixes this), rule-space is finite (Lenia's is
continuous), and GOL is well-studied so she more often *re-discovers* than finds virgin ground — but
the research *scaffold* is fully exercised, and it carries straight over to Lenia on v1.

## 3. Genome

A genome is a compact, serializable parameter vector — the "DNA" a gardener writes. Two layers:

```
Genome {
  id: uuid,
  # — kernel (the body plan) —
  kernel_radius:   int,        # 4..24
  kernel_rings:    [float],    # relative heights of concentric rings (1..3 values)
  kernel_peaks:    [float],    # ring positions 0..1
  # — growth (the metabolism) —
  growth_mu:       float,      # 0..1  center of the growth band
  growth_sigma:    float,      # 0..0.3 width
  dt:              float,      # 0.02..0.5 time step
  decay:           float,      # 0..0.2
  # — seed (the starting body) —
  seed_pattern:    [[float]],  # small NxN initial blob (or "random:R")
  # — meta —
  parents:         [uuid],     # for cross/mutate lineage
  author:          str,        # gardener id
  name:            str         # gardener-given ("Spiral-7", "Lazarus")
}
```

The genome→phenotype link is **chaotic**: small change in `growth_mu`/`sigma` can flip a stable
ring into a wandering glider or into chaos. That unpredictability is the whole point — gardeners
**breed and select**, they do not design the result.

**Genetic operations (pure functions):**
- `mutate(genome, strength)` → perturb numeric params by Gaussian noise scaled by `strength`.
- `cross(a, b)` → child genome mixing params (per-param pick or blend), `parents=[a,b]`.

---

## 4. Evaluator (metrics — pure, deterministic)

`evaluate(history) -> Metrics`, computed from a recorded run of N ticks. Start with these
(extensible):

```
Metrics {
  age:           int,    # ticks the organism stayed alive (mass > ε)
  alive:         bool,
  mass:          float,  # total live cells (final)
  mass_trend:    float,  # growing / stable / shrinking
  chaos:         float,  # 0 ordered (periodic) .. 1 turbulent (entropy of change)
  movement:      float,  # net displacement of center-of-mass per tick (glider-ness)
  complexity:    float,  # structural richness (compressed-size proxy)
  resilience:    float,  # survival after a perturbation test (poke N cells → recovers?)
  period:        int|0   # detected oscillation period, 0 if none
}
```

All are pure functions over the run; the model/UI never computes them. `resilience` runs a small
separate perturbed replay — the "is it really alive" test.

**Prediction check (for Лілі's cognition + self-calibration).** A client may submit a *prediction*
before a run: `predict(genome, {metric: expected})`. The evaluator returns the measured value and a
hit/miss. This is the objective second calibrator from the personality docs — the world catches
self-deception (thought she understood the rule, the number says no) independently of any human.

---

## 5. World state & persistence

```
World {
  field:        float[H][W],            # current field (snapshotted periodically)
  tick:         int,                    # global generation counter
  seed:         int,                    # master RNG seed (for determinism)
  organisms:    [Organism],             # live + recently-dead regions
  lineage:      Graph,                  # genome parentage across the whole world
  events:       [Event],                # births, deaths, records, crosses (the world's history)
  gardeners:    [{id, name}]
}

Organism { id, genome, owner, bbox, birth_tick, last_metrics, status, note }
Event     { tick, type, organism_id, owner, data }   # type: seed|mutate|cross|death|record|...
```

**Persistence.** Periodic snapshots (field + organisms + lineage) + an append-only event log.
The full field is heavy, so snapshot on an interval and replay events between snapshots to
reconstruct any point. Storage: start with a single file / embedded DB (SQLite + blob snapshots);
swappable behind a `Store` interface.

**Full run history (the chosen return).** When a client observes an organism, the server returns
**metrics + the recorded tick-by-tick history** (downsampled field frames + the event slice), so a
client can replay/visualize exactly what happened, not just read numbers.

---

## 6. Real-time tick loop + determinism

The world ticks continuously (`while running: step(); sleep(tick_interval)`), even with no clients.
But to keep it **reproducible and testable**, real-time and determinism are reconciled:

- the world's evolution is a **pure function of `(seed, initial_field, ordered_event_log)`** — wall
  time only decides *when* a tick fires, never *what* it computes;
- every gardener action enters as a **timestamped event in the ordered log**, applied at a specific
  tick (not mid-tick);
- so from any snapshot + the event log, the exact world state is replayable — real-time on the
  server, frozen-clock in tests (inject the clock, as Lumi already does).

**Weak natural pressure** (the "between-visits" decay) is part of the deterministic step: organisms
below a fitness/mass floor fade per the rule — no separate random culling, so it stays replayable.

---

## 7. API (the contract — same for both clients)

**Auth:** each gardener has an id + token (you and Лілі are two gardeners; equal capabilities).

**REST — actions (write):**
```
POST /seed      { genome, position }            -> organism_id
POST /mutate    { organism_id, strength }        -> new organism_id
POST /cross     { organism_id_a, organism_id_b } -> new organism_id
POST /cull      { organism_id }                  -> ok
POST /predict   { genome|organism_id, metric, expected } -> prediction_id
POST /goal      { text }                          -> ok   # a gardener's stated intent (annotation)
```

**REST — queries (read):**
```
GET  /world                 -> {tick, bounds, organisms summary, gardeners}
GET  /organism/{id}         -> {genome, metrics, lineage, note}
GET  /organism/{id}/history -> metrics + full tick-by-tick run (the chosen return)
GET  /lineage/{id}          -> ancestry/descendants
GET  /events?since=tick     -> event slice (what happened while away)
GET  /prediction/{id}       -> {measured, hit}
```

**WebSocket — live:**
```
WS /stream   -> field frames (downsampled) + events, in real time, for the web UI and any
                client that wants to watch live.
```

**Лілі's six tools** map straight onto REST: `seed, mutate, cross, observe(=organism/history),
cull, set_goal` — plus `predict` for her cognition/self-audit. She polls `/events?since=` on session
start to learn "what happened while I was away" (her between-session away-gap, now backed by a real
world, not generation).

---

## 8. Human web UI (your interface)

Static web app (canvas/WebGL) on the same server:
- **Live field** — render the float field as a heat/organic colormap, 60fps from the WS stream;
  pan/zoom; organisms outlined and labeled by owner (you vs Лілі in different hues).
- **Act** — click to place a seed, select an organism to mutate/cross/cull; a small genome editor
  (sliders for the genome params) to author DNA by hand.
- **Inspect** — click an organism → its metrics, lineage tree, history scrubber (replay its life).
- **Feed** — a timeline of world events (births, deaths, records, who did what) — so you see Лілі's
  traces and she sees yours.

WebGL matters because Lenia is a per-cell float field — shader rendering keeps it smooth at scale.

---

## 9. Boundary with Lumi (clean separation)

- Silt knows **nothing** about Лілі's personality, needs, or maturity. It exposes a world +
  API. All meaning-making (which metrics matter, how an outcome *feels*, what it serves) lives in
  Lumi, on top of the raw metrics/history this server returns.
- The two calibrators from the personality docs are honored here: the human gardener (you, via the
  UI) and the **objective `predict` hit/miss** (the world itself) — Lumi reads both.
- No Lumi state leaks into Silt; no Silt code depends on Lumi. Either can run without the
  other.

---

## 10. Determinism & tests

- **Engine:** pin field state after K ticks from a fixed `(seed, genome)` — exact float match
  (set FFT/precision mode for reproducibility). `mutate`/`cross` deterministic under a seeded RNG.
- **Evaluator:** pin every metric against fixed recorded runs; `resilience` perturbation seeded.
- **Replay:** snapshot + event log reconstructs the exact world state (real-time decoupled from
  computation).
- **API/contract:** action events apply at tick boundaries; auth isolates gardener identity but not
  the shared field; `predict` returns stable hit/miss.
- **No paid calls, no model** anywhere in the server — it is pure simulation.

---

## 11. Build order (suggested)

1. **Engine** — start with the **GOL `step()`** + the integer genome + mutate/cross (§2a), headless
   and unit-tested: the deterministic core. **Lenia `step()` is a later swap** behind the same
   interface, once the skeleton below is proven on GOL.
2. **Evaluator** (metrics + predict) on recorded runs.
3. **Store** (snapshots + event log + replay).
4. **Tick loop** (real-time, deterministic via event log) + **REST API**.
5. **WebSocket stream** + **web UI** (render, then act, then inspect).
6. **Лілі client** (the six tools + predict + events-since) — wired into Lumi as an external world.

---

*Silt is the shared garden. The server keeps it alive; the web canvas lets you tend it; the
API lets Лілі tend it beside you. Two gardeners, one field, and a world that grows in the pauses
whether or not anyone is watching.*
