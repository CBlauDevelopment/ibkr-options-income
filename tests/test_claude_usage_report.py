"""scripts/claude_usage.py - per-call-kind token report from the `claude usage:` log lines.

Before 2026-10-15 nothing recorded tokens by call kind; the first breakdown had to be rebuilt
from Claude Code's session transcripts. `--no-session-persistence` (the slim call) removes
those transcripts, so this log line is now the only record."""

from __future__ import annotations

from scripts import claude_usage as cu

PLAIN = (
    "2026-10-15 22:49:13 | INFO     | src.claude.runner | claude usage: kind=claude roll "
    "model=claude-sonnet-5-5 ctx=1148 out=304 cost=0.007500"
)
ANSI = (
    "\x1b[2m2026-10-15 21:53:29\x1b[0m  \x1b[32mINFO    \x1b[0m  \x1b[2msrc.claude.runner\x1b[0m  "
    "claude usage: kind=claude review model=claude-haiku-5-5 ctx=11080 out=697 cost=?"
)


def test_parses_the_plain_and_the_coloured_log_formats() -> None:
    plain, ansi = cu.parse_lines([PLAIN, ANSI, "2026-10-15 22:00:00 | INFO | x | unrelated"])
    assert (plain.day, plain.kind, plain.model) == (
        "2026-10-15",
        "claude roll",
        "claude-sonnet-5-5",
    )
    assert (plain.ctx, plain.out, plain.cost) == (1148, 304, 0.0075)
    assert (ansi.kind, ansi.ctx, ansi.cost) == ("claude review", 11080, None)


def test_a_kind_with_colons_and_spaces_survives() -> None:
    line = PLAIN.replace("claude roll", "news:ticker_move x")
    assert cu.parse_lines([line])[0].kind == "news:ticker_move x"


def test_the_same_event_in_two_files_counts_once() -> None:
    """system.log aggregates what the per-process logs also hold."""
    a = cu.parse_lines([PLAIN, PLAIN])  # two real calls inside one file
    b = cu.parse_lines([PLAIN])  # the aggregate copy of one of them
    assert len(cu.merge_files([a, b])) == 2
    assert len(cu.merge_files([b, b])) == 1


def test_summarise_groups_by_kind_biggest_context_first() -> None:
    events = cu.parse_lines(
        [PLAIN, PLAIN.replace("22:49:13", "22:50:00"), ANSI.replace("cost=?", "cost=0.002")]
    )
    rows = cu.summarise(events)
    assert [r.kind for r in rows] == ["claude review", "claude roll"]
    roll = rows[1]
    assert (roll.calls, roll.ctx, roll.out) == (2, 2296, 608)
    assert rows[0].cost == 0.002


def test_summarise_filters_by_first_day() -> None:
    events = cu.parse_lines([PLAIN.replace("2026-10-15", "2026-10-01"), PLAIN])
    assert sum(r.calls for r in cu.summarise(events, since="2026-10-10")) == 1


def test_by_day_splits_rows() -> None:
    events = cu.parse_lines([PLAIN.replace("2026-10-15", "2026-10-14"), PLAIN])
    rows = cu.summarise(events, by_day=True)
    assert sorted(r.day for r in rows) == ["2026-10-14", "2026-10-15"]


def test_main_reads_log_files_and_prints_a_table(tmp_path, capsys) -> None:
    (tmp_path / "system.log").write_text(PLAIN + "\n")
    (tmp_path / "monitor.log").write_text(ANSI + "\n" + PLAIN + "\n")
    assert cu.main(["--logs", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "claude roll" in out and "claude review" in out and "TOTAL" in out


def test_main_with_no_usage_lines_says_so(tmp_path, capsys) -> None:
    (tmp_path / "system.log").write_text("2026-10-15 22:00:00 | INFO | x | nothing here\n")
    assert cu.main(["--logs", str(tmp_path)]) == 0
    assert "no `claude usage:` lines" in capsys.readouterr().out
