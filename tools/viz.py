"""Live matplotlib viewer for the v0 engine — a dev-only debug tool (not the v0.4 web UI).

Seeds a named pattern onto a toroidal field and animates ``engine.step`` in an interactive
window. It imports the engine directly and touches nothing else (no store, tick loop, REST/WS,
or persistence), so it is independent of the platform phases and can't create contracts the real
web UI (v0.4) must honor. Binary rendering only — fine for the Game-of-Life versions (v0–v2).

Usage::

    uv sync --extra viz
    uv run python -m tools.viz --pattern gosper_glider_gun --size 80 --fps 12
    uv run python -m tools.viz --pattern glider --pos 5,5 --ticks 200

matplotlib is imported lazily so this module stays importable (and testable) without it.
"""

from __future__ import annotations

import argparse

from engine import Field, empty, live_count, step
from engine.patterns import PATTERNS, place


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
        description="Live matplotlib viewer for the Silt v0 engine (dev tool).",
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
    return parser


def animate(field: Field, *, fps: float = 12.0, ticks: int | None = None, title: str = "") -> None:
    """Open an interactive window animating ``step`` from ``field`` (lazy matplotlib import)."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation
    except ImportError as exc:  # noqa: B904
        raise SystemExit(
            "matplotlib is not installed — run `uv sync --extra viz` to use tools.viz"
        ) from exc

    state = {"field": field, "tick": 0}

    fig, ax = plt.subplots()
    im = ax.imshow(field, cmap="binary", vmin=0, vmax=1, interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])

    def _title() -> str:
        return f"{title}tick={state['tick']}  live={live_count(state['field'])}"

    ax.set_title(_title())

    def update(_frame: int):
        state["field"] = step(state["field"])
        state["tick"] += 1
        im.set_data(state["field"])
        ax.set_title(_title())
        return (im,)

    # Kept on the figure so the animation isn't garbage-collected while the window is open.
    fig._silt_anim = FuncAnimation(  # type: ignore[attr-defined]
        fig,
        update,
        frames=ticks,
        interval=1000.0 / fps,
        blit=False,
        repeat=False,
    )
    plt.show()


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    height = args.height if args.height is not None else args.size
    width = args.width if args.width is not None else args.size
    if args.seed:
        field = build_field_multi(args.seed, height, width)
        names = [name for name, _ in args.seed]
        label = ", ".join(names) if len(names) <= 3 else f"{len(names)} seeds"
    else:
        field = build_field(args.pattern, height, width, args.pos)
        label = args.pattern
    animate(field, fps=args.fps, ticks=args.ticks, title=f"{label}  ")


if __name__ == "__main__":
    main()
