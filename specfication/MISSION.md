# Mission — Silt

## In one sentence

Silt is an always-on, shared world of artificial life — one field tended by two equal gardeners (a
human through a web canvas, an API client through REST) — that ticks in real time on its own,
indifferent to who is watching.

## What we are building

A standalone server hosting a 2D cellular-automata world, plus a web UI for the human gardener and a
thin client API for the other. The world is built **behind one `step()` seam**, on Game of Life
first and Lenia last, in four versions (see [ROADMAP.md](ROADMAP.md)): **v0** stands up the entire
platform (engine, store, tick loop, REST API, WebSocket, web UI, client) on **vanilla Conway** — a
single fixed rule, no genome — to prove the infrastructure on the simplest possible engine; **v1**
turns the rule into a **genome** (a Life-like automaton whose genome *is* the birth/survive rule) and
adds evolution (`mutate`/`cross`, lineage, selection metrics); **v2** turns the world into a
**research scaffold** of challenges (predict + rule-space travel, classification, fragility,
machines); **v3** swaps `step()` for **Lenia** (a continuous-state automaton) so phenotypes become
organic and alive. Everything around the engine — server, store, tick loop, API, lineage, metrics,
challenges, web UI, client — is identical across the Game-of-Life versions (v0–v2) and the Lenia
version (v3); **only `step()`, the genome format, and the render shader change.**

Gardeners drive evolution by **manual selection** — they `seed`, `mutate`, and `cross` genomes and
keep what is alive and strange — under a **weak natural pressure** (unfit blobs fade on their own
between visits). So gardeners are authors, not spectators, yet the world still surprises them. When a
client observes an organism, the server returns **metrics plus the full tick-by-tick run history**,
not just numbers — enough to replay exactly what happened.

Named after the Silt of Greg Egan's *Permutation City*: a self-contained deterministic universe
whose life runs on its own, indifferent to who is watching.

## For whom

A private project for two gardeners — you, and **Лілі** (the [Lumi](../CLAUDE.md) project). The world
knows nothing about Лілі: she is just one authenticated client among possibly many, with the same
capabilities as the human. This is not a public service.

## Principles

- **Substrate behind a seam.** The automaton lives behind a clean `step(field, genome)` interface.
  Build the whole world on the trivial GOL engine first; swap in Lenia once the skeleton is proven.
  Nothing outside `step()` and the genome may know which automaton runs inside.
- **Manual selection is the engine of creation.** Evolution is driven by the gardeners (seed / mutate
  / cross), not by an automatic fitness function. A **weak natural pressure** (between-visit decay)
  adds surprise without taking authorship away.
- **One shared field.** Both gardeners act in the same field and see each other's traces; identity
  isolates *authorship*, never the canvas.
- **Real-time, always-on.** The server ticks the world continuously, even when nobody is watching —
  it grows in the pauses.
- **Determinism is sacred.** The world is a pure function of `(seed, initial_field, ordered_event_log)`.
  Wall time decides only *when* a tick fires, never *what* it computes. Any state is replayable from a
  snapshot plus the event log.
- **Metrics + full history, not just numbers.** Observing an organism returns its measured metrics
  *and* the recorded run, so a client can replay and visualize, not merely read a score.
- **Pure simulation.** No model, no paid API calls, no randomness outside the seeded RNG anywhere in
  the server. The world is deterministic physics.
- **Prediction as an objective calibrator.** A client may `predict` a metric before a run; the
  evaluator returns measured-vs-expected as a hit/miss — an honest second judge, independent of any
  human, that catches self-deception.
- **Clean boundary with Lumi.** Silt depends on no Lumi code and holds no Lumi state; either runs
  without the other. All meaning-making lives in Lumi, on top of Silt's raw metrics/history.

## Non-goals

- **Not a Lumi component.** Silt is a standalone world server; it must never import from or depend on
  Lumi (see [ARCHITECTURE.md](ARCHITECTURE.md) §Boundary with Lumi).
- **No meaning-making in Silt.** Which metrics matter, how an outcome *feels*, what it serves — all of
  that lives in the client (Lumi). Silt returns raw metrics and history only.
- **Not automatic evolution.** There is no global fitness function optimizing the field. Gardeners
  select; the only autonomous pressure is the weak deterministic decay.
- **No paid calls, no model, no LLM** inside the server — it is pure simulation.
- **No public sign-up.** Auth is a small set of known gardeners with tokens.

## Glossary

- **Field** — the 2D toroidal grid that *is* the world. Binary cells in the Game-of-Life versions
  (v0–v2); floats in `[0,1]` ("aliveness") in the Lenia version (v3).
- **Tick** — one application of `step()` to the whole field; the global generation counter.
- **`step(field, genome) -> field`** — the engine seam. The only thing (with the genome and the
  render shader) that differs between the Game-of-Life versions (v0–v2) and Lenia (v3).
- **Organism** — a connected live region, tagged with the genome that seeded it and an owner.
  Multiple organisms coexist on the one field and interact at their boundaries.
- **Genome** — the compact, serializable parameter vector a gardener authors (the "DNA"). The GOL
  genome is the birth/survive rule + seed pattern; the Lenia genome is the kernel/growth/seed vector.
- **`mutate` / `cross`** — the two pure genetic operations; deterministic under a seeded RNG.
- **Gardener** — an authenticated client (the human via the web UI, or Лілі via REST) with an id +
  token; equal capabilities.
- **Evaluator** — the pure function `evaluate(history) -> Metrics` and the `predict` hit/miss check.
- **Metrics** — measured properties of a run (age, mass, chaos, movement, complexity, resilience,
  period, …), computed only by the evaluator, never by the model or UI.
- **Predict** — a client's pre-run claim about a metric; the evaluator returns measured-vs-expected.
- **Store** — persistence behind a swappable interface: periodic field snapshots + an append-only
  event log; replay reconstructs any point.
- **Event log** — the ordered, timestamped record of every gardener action; the sole source of
  mutation and the backbone of determinism.
- **Snapshot** — a periodic full dump of field + organisms + lineage, between which events replay.
- **Replay** — reconstructing exact world state from a snapshot plus the subsequent event log.
- **Lineage** — the genome parentage graph across the whole world (who descends from whom).
- **Weak natural pressure** — the deterministic between-visit decay: organisms below a fitness/mass
  floor fade per the rule (not a random cull), so the world stays replayable.
- **Лілі** — the [Lumi](../CLAUDE.md) project; the API-client gardener. Silt knows nothing about her.
