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

### Dev viewer (optional)

A throwaway live viewer for the engine — *not* the v0.4 web UI; it imports `engine` directly and
touches nothing else. Needs the optional `viz` extra (matplotlib):

```bash
uv sync --extra viz
uv run python -m tools.viz --pattern gosper_glider_gun --size 80 --fps 12
uv run python -m tools.viz --pattern pulsar           # striking period-3 oscillator
uv run python -m tools.viz --pattern r_pentomino --size 120   # a methuselah erupting
uv run python -m tools.viz --pattern acorn --size 150 --fps 20 # explosive growth
```

A matplotlib window opens and animates `engine.step` from the seeded field until you close it
(or `--ticks N` stops it).

#### Seeding several patterns at once

Repeat `--seed NAME@ROW,COL` to place multiple figures on the **one shared toroidal field**, each
at its own spot. They are stamped in order and then evolve together — colliding, merging, and
wrapping into each other once stepping begins (the whole point of a shared world).

```bash
# aim a glider gun's stream at a pulsar, with a lightweight spaceship cruising past:
uv run python -m tools.viz --size 80 \
  --seed gosper_glider_gun@2,2 --seed pulsar@40,40 --seed lwss@60,5
```

- **Repeatable** — pass as many `--seed` flags as you like, including the same figure twice
  (`--seed glider@5,5 --seed glider@40,40`).
- **Position is optional** — `--seed pulsar` (no `@ROW,COL`) centers it; give `@ROW,COL` (the
  figure's top-left corner) to place it precisely. With several centered seeds they'll overlap, so
  positions are recommended when seeding more than one.
- **Overrides `--pattern`** — if any `--seed` is given, the single-pattern path is ignored.

#### Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--pattern NAME` | `glider` | single figure to seed (centered) |
| `--seed NAME@ROW,COL` | — | place a figure (repeatable; omit `@ROW,COL` to center); overrides `--pattern` |
| `--size N` | `80` | square field size |
| `--width N` / `--height N` | `--size` | non-square field (override `--size`) |
| `--pos ROW,COL` | centered | top-left for the single `--pattern` |
| `--ticks N` | run until closed | stop after N ticks |
| `--fps N` | `12` | animation speed (ticks drawn per second; display-only) |

#### Available figures

- **Still lifes:** `block`, `beehive`, `loaf`, `boat`
- **Oscillators:** `blinker`, `toad`, `beacon`, `pulsar`, `pentadecathlon`
- **Spaceships:** `glider`, `lwss`
- **Gun:** `gosper_glider_gun`
- **Methuselahs:** `r_pentomino`, `acorn`, `diehard`


## Status

Greenfield, building by phase. Current phase: **v0.1 — Engine: vanilla Conway** (see the ROADMAP).
