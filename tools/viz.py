"""Live matplotlib viewer for the v0 stack — a dev-only debug tool (not the v0.4 web UI).

Seeds named patterns onto a toroidal field and animates ``engine.step`` in an interactive window,
now with the v0.2 stack layered in as optional overlays/modes:

- **organisms** — each tick the :class:`world.organisms.OrganismTracker` finds connected live regions
  and their bounding boxes are drawn over the field (red rectangles) with a live count.
- **record** (``--record PATH --ticks N``) — drive the world headlessly through
  :mod:`world.simulate` and persist periodic snapshots + the event log to a :class:`store.SqliteStore`.
- **replay** (``--replay PATH --at TICK``) — reconstruct an exact tick from a recorded store via
  :func:`store.replay`, print its :mod:`evaluator` metrics, and animate forward from there.

It only *consumes* the public library APIs (engine/world/store/evaluator) — it owns no contracts the
real web UI (v0.4) must honor, and binary rendering keeps it honest for the Game-of-Life versions
(v0–v2). matplotlib is imported lazily, so record/replay summaries and all helpers work (and test)
without it.

Usage::

    uv sync --extra viz
    uv run python -m tools.viz --pattern gosper_glider_gun --size 80 --fps 12
    uv run python -m tools.viz --seed glider@5,5 --seed lwss@20,30 --no-organisms
    uv run python -m tools.viz --seed glider@2,2 --record /tmp/run.db --ticks 60 --snap-every 10
    uv run python -m tools.viz --replay /tmp/run.db --at 37
"""

from __future__ import annotations

import argparse
from typing import Any

from engine import Field, empty, live_count, step
from engine.patterns import PATTERNS, place
from evaluator import Frame, History, evaluate
from store import SqliteStore, replay
from world import OrganismTracker, genesis, step_world

# A drawable organism box: (bbox=(row, col, height, width), short_label, mass).
BoxSpec = tuple[tuple[int, int, int, int], str, int]


def build_field(
    pattern: str,
    height: int,
    width: int,
    position: tuple[int, int] | None = None,
) -> Field:
    """Seed a single ``pattern`` onto an empty field (centered unless ``position`` set)."""
    return build_field_multi([(pattern, position)], height, width)


def build_field_multi(
    seeds: list[tuple[str, tuple[int, int] | None]],
    height: int,
    width: int,
) -> Field:
    """Seed several patterns onto one field, each at its own position (centered if ``None``).

    Patterns are OR-ed on in order (see :func:`engine.patterns.place`), so they may overlap and
    will interact once stepping begins.
    """
    field = empty(height, width)
    for pattern, position in seeds:
        if pattern not in PATTERNS:
            raise ValueError(f"unknown pattern {pattern!r}; choose from {sorted(PATTERNS)}")
        fig = PATTERNS[pattern]
        pos = position
        if pos is None:
            ph, pw = fig.shape
            pos = ((height - ph) // 2, (width - pw) // 2)
        field = place(field, fig, pos)
    return field


def _short_id(organism_id: str) -> str:
    """``org-000007`` -> ``7`` — a compact label for crowded overlays."""
    tail = organism_id.rsplit("-", 1)[-1]
    return tail.lstrip("0") or "0"


def organism_boxes(tracker: OrganismTracker, field: Field, tick: int) -> list[BoxSpec]:
    """Advance ``tracker`` one frame and return drawable box specs for the field's organisms."""
    return [
        (o.bbox, _short_id(o.id), int(o.last_metrics.get("mass", 0)))
        for o in tracker.update(field, tick)
        if o.bbox is not None
    ]


def record_run(initial_field: Field, n_ticks: int, store: SqliteStore, *, snap_every: int = 10) -> dict[str, Any]:
    """Headlessly simulate ``n_ticks`` from ``initial_field``, persisting snapshots to ``store``.

    Saves a snapshot at tick 0 and every ``snap_every`` ticks (the event log stays the sole record
    in between), so :func:`store.replay` can reconstruct any tick exactly. Returns a summary.
    """
    tracker = OrganismTracker()
    world = genesis(initial_field, tracker=tracker)
    store.save_snapshot(world.tick, world.field, world.organisms)
    snapshots = [world.tick]
    for _ in range(1, n_ticks + 1):
        world = step_world(world, [], tracker)
        if world.tick % snap_every == 0:
            store.save_snapshot(world.tick, world.field, world.organisms)
            snapshots.append(world.tick)
    return {
        "ticks": n_ticks,
        "snapshots": snapshots,
        "final_tick": world.tick,
        "final_mass": live_count(world.field),
        "organisms": len(world.organisms),
    }


def replay_summary(store: SqliteStore, tick: int) -> dict[str, Any]:
    """Reconstruct ``tick`` from ``store`` and report its metrics + organisms (uses the evaluator)."""
    world = replay(store, tick)
    metrics = evaluate(History(frames=[Frame(tick=world.tick, field=world.field)]))
    return {
        "tick": world.tick,
        "metrics": metrics,
        "organisms": len(world.organisms),
        "bboxes": [o.bbox for o in world.organisms],
    }


def _parse_pos(text: str) -> tuple[int, int]:
    try:
        row, col = (int(p) for p in text.split(","))
    except ValueError as exc:  # noqa: B904 — argparse wants a clean message
        raise argparse.ArgumentTypeError(f"position must be 'row,col', got {text!r}") from exc
    return row, col


def parse_seed(spec: str) -> tuple[str, tuple[int, int] | None]:
    """Parse a ``NAME`` or ``NAME@ROW,COL`` seed spec into ``(name, position|None)``."""
    name, _, pos = spec.partition("@")
    if name not in PATTERNS:
        raise argparse.ArgumentTypeError(
            f"unknown pattern {name!r}; choose from {sorted(PATTERNS)}"
        )
    position = _parse_pos(pos) if pos else None
    return name, position


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tools.viz",
        description="Live matplotlib viewer for the Silt v0 stack (dev tool).",
    )
    parser.add_argument(
        "--pattern", choices=sorted(PATTERNS), default="glider", help="seed figure (default: glider)"
    )
    parser.add_argument(
        "--seed",
        action="append",
        type=parse_seed,
        metavar="NAME[@ROW,COL]",
        help="place a figure (repeatable, e.g. --seed glider@5,5 --seed lwss@20,30); "
        "overrides --pattern. Omit @ROW,COL to center.",
    )
    parser.add_argument("--size", type=int, default=80, help="square field size (default: 80)")
    parser.add_argument("--height", type=int, default=None, help="field height (overrides --size)")
    parser.add_argument("--width", type=int, default=None, help="field width (overrides --size)")
    parser.add_argument(
        "--pos", type=_parse_pos, default=None, help="'row,col' top-left (default: centered)"
    )
    parser.add_argument(
        "--ticks", type=int, default=None, help="stop after N ticks (default: run until closed)"
    )
    parser.add_argument("--fps", type=float, default=12.0, help="frames per second (default: 12)")
    parser.add_argument(
        "--no-organisms", action="store_true", help="hide the organism bounding-box overlay"
    )
    parser.add_argument(
        "--record", metavar="PATH", default=None,
        help="headlessly record snapshots + event log to a SQLite store (requires --ticks)",
    )
    parser.add_argument(
        "--replay", metavar="PATH", default=None,
        help="reconstruct a tick from a recorded store (with --at) and animate forward",
    )
    parser.add_argument(
        "--at", type=int, default=None, help="tick to reconstruct in --replay mode"
    )
    parser.add_argument(
        "--snap-every", type=int, default=10, help="snapshot interval for --record (default: 10)"
    )
    return parser


def animate(
    field: Field,
    *,
    fps: float = 12.0,
    ticks: int | None = None,
    title: str = "",
    show_organisms: bool = True,
    start_tick: int = 0,
) -> None:
    """Open an interactive window animating ``step`` from ``field`` (lazy matplotlib import).

    When ``show_organisms`` is set, each tick's tracked organisms are outlined and counted.
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation
        from matplotlib.patches import Rectangle
    except ImportError as exc:  # noqa: B904
        raise SystemExit(
            "matplotlib is not installed — run `uv sync --extra viz` to use tools.viz"
        ) from exc

    state = {"field": field, "tick": start_tick}
    tracker = OrganismTracker() if show_organisms else None
    boxes: list[Any] = []

    fig, ax = plt.subplots()
    im = ax.imshow(field, cmap="binary", vmin=0, vmax=1, interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])

    def _redraw_boxes(specs: list[BoxSpec]) -> None:
        for patch in boxes:
            patch.remove()
        boxes.clear()
        for (r, c, h, w), label, _mass in specs:
            rect = Rectangle((c - 0.5, r - 0.5), w, h, fill=False, edgecolor="red", linewidth=1.0)
            ax.add_patch(rect)
            boxes.append(rect)
            boxes.append(ax.text(c - 0.5, r - 0.8, label, color="red", fontsize=7, va="bottom"))

    def _title(n_orgs: int | None) -> str:
        base = f"{title}tick={state['tick']}  live={live_count(state['field'])}"
        return base if n_orgs is None else f"{base}  organisms={n_orgs}"

    n0 = None
    if tracker is not None:
        specs0 = organism_boxes(tracker, field, start_tick)
        _redraw_boxes(specs0)
        n0 = len(specs0)
    ax.set_title(_title(n0))

    def update(_frame: int):
        state["field"] = step(state["field"])
        state["tick"] += 1
        im.set_data(state["field"])
        n_orgs = None
        if tracker is not None:
            specs = organism_boxes(tracker, state["field"], state["tick"])
            _redraw_boxes(specs)
            n_orgs = len(specs)
        ax.set_title(_title(n_orgs))
        return (im, *boxes)

    # Kept on the figure so the animation isn't garbage-collected while the window is open.
    fig._silt_anim = FuncAnimation(  # type: ignore[attr-defined]
        fig,
        update,
        frames=ticks,
        interval=1000.0 / fps,
        blit=False,
        repeat=False,
        cache_frame_data=False,  # live sim — no need to cache frames (silences the frames=None warning)
    )
    plt.show()


def _print_summary(header: str, summary: dict[str, Any]) -> None:
    print(header)
    for key, value in summary.items():
        print(f"  {key}: {value}")


def _field_from_args(args: argparse.Namespace, height: int, width: int) -> tuple[Field, str]:
    if args.seed:
        field = build_field_multi(args.seed, height, width)
        names = [name for name, _ in args.seed]
        label = ", ".join(names) if len(names) <= 3 else f"{len(names)} seeds"
    else:
        field = build_field(args.pattern, height, width, args.pos)
        label = args.pattern
    return field, label


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    height = args.height if args.height is not None else args.size
    width = args.width if args.width is not None else args.size
    show_organisms = not args.no_organisms

    if args.replay:
        if args.at is None:
            raise SystemExit("--replay requires --at TICK")
        store = SqliteStore(args.replay)
        _print_summary(f"replay @ tick {args.at}", replay_summary(store, args.at))
        world = replay(store, args.at)
        store.close()
        animate(
            world.field,
            fps=args.fps,
            ticks=args.ticks,
            title=f"replay@{args.at}  ",
            show_organisms=show_organisms,
            start_tick=args.at,
        )
        return

    field, label = _field_from_args(args, height, width)

    if args.record:
        if args.ticks is None:
            raise SystemExit("--record requires --ticks N")
        store = SqliteStore(args.record)
        summary = record_run(field, args.ticks, store, snap_every=args.snap_every)
        store.close()
        _print_summary(f"recorded {label} -> {args.record}", summary)
        return

    animate(
        field,
        fps=args.fps,
        ticks=args.ticks,
        title=f"{label}  ",
        show_organisms=show_organisms,
    )


if __name__ == "__main__":
    main()
