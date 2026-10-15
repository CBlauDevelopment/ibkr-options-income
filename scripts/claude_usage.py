"""Per-call-kind `claude -p` usage, from the `claude usage:` lines the pipeline logs.

Every headless call logs ``claude usage: kind=... model=... ctx=... out=... cost=...``
(src/claude/cli.py::format_usage). This sums them by call kind so you can see which calls
spend the tokens: ``ctx`` is what the call carried (input + cache writes + cache reads), ``out``
includes thinking, ``cost`` is the envelope's notional dollars.

Run:
    python -m scripts.claude_usage                  # all logs under logs/
    python -m scripts.claude_usage --since 2026-10-15 --by-day
    python -m scripts.claude_usage --logs /path/to/logs

system.log aggregates events the per-process logs also hold, so an event seen in more than one
file is counted once. Read-only; touches nothing but the log files it is pointed at.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_LINE = re.compile(
    r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}).*?claude usage: kind=(.+?) model=(\S+) "
    r"ctx=(\d+) out=(\d+) cost=(\S+)"
)
_DEFAULT_LOGS = Path(__file__).resolve().parents[1] / "logs"


@dataclass(frozen=True)
class Event:
    day: str
    time: str
    kind: str
    model: str
    ctx: int
    out: int
    cost: float | None


@dataclass(frozen=True)
class Row:
    day: str  # "" unless grouped by day
    kind: str
    calls: int
    ctx: int
    out: int
    cost: float


def parse_lines(lines: Iterable[str]) -> list[Event]:
    events: list[Event] = []
    for raw in lines:
        m = _LINE.search(_ANSI.sub("", raw))
        if not m:
            continue
        day, time, kind, model, ctx, out, cost = m.groups()
        try:
            c = float(cost)
        except ValueError:
            c = None  # "?" - the envelope carried no cost
        events.append(Event(day, time, kind, model, int(ctx), int(out), c))
    return events


def merge_files(per_file: Sequence[Sequence[Event]]) -> list[Event]:
    """One list from several logs. An event present in more than one file is the same call, so
    each distinct event counts as many times as the file that holds it most often (two real calls
    in the same second inside one file still count twice)."""
    best: Counter[Event] = Counter()
    for events in per_file:
        for event, n in Counter(events).items():
            best[event] = max(best[event], n)
    return list(best.elements())


def summarise(
    events: Iterable[Event], *, since: str | None = None, by_day: bool = False
) -> list[Row]:
    acc: dict[tuple[str, str], list[float]] = {}
    for e in events:
        if since and e.day < since:
            continue
        a = acc.setdefault((e.day if by_day else "", e.kind), [0, 0, 0, 0.0])
        a[0] += 1
        a[1] += e.ctx
        a[2] += e.out
        a[3] += e.cost or 0.0
    rows = [Row(d, k, int(a[0]), int(a[1]), int(a[2]), a[3]) for (d, k), a in acc.items()]
    return sorted(rows, key=lambda r: (r.day, -r.ctx) if by_day else (-r.ctx,))


def render(rows: Sequence[Row], *, by_day: bool = False) -> str:
    head = f"{'day':<11}" if by_day else ""
    out = [
        f"{head}{'kind':<26}{'calls':>6}{'ctx tokens':>13}{'out tokens':>12}{'cost $':>9}{'ctx/call':>10}"
    ]
    for r in rows:
        day = f"{r.day:<11}" if by_day else ""
        out.append(
            f"{day}{r.kind[:25]:<26}{r.calls:>6}{r.ctx:>13,}{r.out:>12,}{r.cost:>9.2f}"
            f"{r.ctx // max(r.calls, 1):>10,}"
        )
    calls, ctx = sum(r.calls for r in rows), sum(r.ctx for r in rows)
    pad = " " * 11 if by_day else ""
    out.append(
        f"{pad}{'TOTAL':<26}{calls:>6}{ctx:>13,}{sum(r.out for r in rows):>12,}"
        f"{sum(r.cost for r in rows):>9.2f}{ctx // max(calls, 1):>10,}"
    )
    return "\n".join(out)


def _read(path: Path) -> list[Event]:
    try:
        return parse_lines(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return []


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Per-call-kind claude -p usage from the logs.")
    ap.add_argument(
        "--logs", type=Path, default=_DEFAULT_LOGS, help="log directory (default: logs/)"
    )
    ap.add_argument("--since", help="first day to include, YYYY-MM-DD")
    ap.add_argument("--by-day", action="store_true", help="one row per day and call kind")
    args = ap.parse_args(argv)

    files = sorted(p for p in args.logs.glob("*.log*") if p.is_file())
    events = merge_files([_read(p) for p in files])
    rows = summarise(events, since=args.since, by_day=args.by_day)
    if not rows:
        print(f"no `claude usage:` lines in {len(files)} file(s) under {args.logs}")
        return 0
    print(render(rows, by_day=args.by_day))
    return 0


if __name__ == "__main__":
    sys.exit(main())
