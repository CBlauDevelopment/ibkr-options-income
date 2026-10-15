"""The runner's headless invocation after the 2026-10-15 token-weight work: the slim command, the
clean workdir, a model per call kind, no retry on a usage-limit rejection, and a usage log line.
All tests mock subprocess.run — no live Claude CLI needed."""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.claude import runner
from src.common.config import ClaudeCfg, get_config

_LIMIT = json.dumps({"is_error": True, "result": "You've hit your session limit · resets 7:40am"})
_OK = json.dumps(
    {
        "result": "{}",
        "total_cost_usd": 0.001,
        "usage": {
            "input_tokens": 2,
            "cache_creation_input_tokens": 500,
            "cache_read_input_tokens": 646,
            "output_tokens": 300,
        },
        "modelUsage": {"claude-haiku-5-5": {}},
    }
)


def _proc(stdout: str, returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode, m.stdout, m.stderr = returncode, stdout, ""
    return m


@pytest.fixture
def claude_cfg(monkeypatch, tmp_path):
    def make(**over) -> ClaudeCfg:
        c = ClaudeCfg(
            cli_command="claude", workdir=str(tmp_path / "work"), model="sonnet-x", **over
        )
        monkeypatch.setattr(get_config(), "claude", c)
        return c

    return make


def _slim_ns(**over) -> SimpleNamespace:
    base = dict(
        slim_context=True,
        cli_command="claude",
        output_format="json",
        max_turns=1,
        model="m",
        effort="medium",
        disallowed_tools="Bash",
    )
    return SimpleNamespace(**{**base, **over})


# --- the command ---------------------------------------------------------------------------


def test_build_cmd_slim_strips_the_ambient_context() -> None:
    cmd = runner._build_cmd(_slim_ns())
    for flag in (
        "-p",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--strict-mcp-config",
    ):
        assert flag in cmd
    assert cmd[cmd.index("--tools") + 1] == ""
    assert cmd[cmd.index("--model") + 1] == "m"
    assert cmd[cmd.index("--effort") + 1] == "medium"


def test_build_cmd_model_override_applies_slim_or_not() -> None:
    assert (
        runner._build_cmd(_slim_ns(), model="h")[
            runner._build_cmd(_slim_ns(), model="h").index("--model") + 1
        ]
        == "h"
    )
    legacy = runner._build_cmd(_slim_ns(slim_context=False), model="h")
    assert legacy[legacy.index("--model") + 1] == "h"
    assert "--disable-slash-commands" not in legacy and "-p" not in legacy


# --- where it runs -------------------------------------------------------------------------


def test_cli_outcome_runs_in_the_workdir_and_creates_it(claude_cfg, tmp_path) -> None:
    claude_cfg()
    with patch("src.claude.runner.subprocess.run", return_value=_proc(_OK)) as run:
        runner._run_cli_outcome("p", "claude roll", lambda out: out)
    assert run.call_args.kwargs["cwd"] == tmp_path / "work"
    assert (tmp_path / "work").is_dir()


def test_cli_outcome_keeps_the_repo_cwd_when_not_slim(claude_cfg) -> None:
    claude_cfg(slim_context=False)
    with patch("src.claude.runner.subprocess.run", return_value=_proc(_OK)) as run:
        runner._run_cli_outcome("p", "claude roll", lambda out: out)
    assert run.call_args.kwargs.get("cwd") is None


# --- a usage limit is not retried ------------------------------------------------------------


def test_cli_outcome_does_not_retry_a_usage_limit(claude_cfg) -> None:
    claude_cfg(max_retries=2)
    with patch("src.claude.runner.subprocess.run", return_value=_proc(_LIMIT, 1)) as run:
        parsed, error = runner._run_cli_outcome("p", "claude roll", lambda out: None)
    assert (parsed, error) == (None, "cli_error")
    assert run.call_count == 1  # three attempts could not succeed; each is a wasted spawn


def test_cli_outcome_still_retries_other_failures(claude_cfg) -> None:
    claude_cfg(max_retries=1)
    with patch("src.claude.runner.subprocess.run", return_value=_proc("", 1)) as run:
        runner._run_cli_outcome("p", "claude roll", lambda out: None)
    assert run.call_count == 2


# --- usage is logged per call kind ---------------------------------------------------------------


def test_cli_outcome_logs_a_usage_line_with_the_call_kind(claude_cfg, caplog) -> None:
    claude_cfg()
    with caplog.at_level(logging.INFO, logger="src.claude.runner"):
        with patch("src.claude.runner.subprocess.run", return_value=_proc(_OK)):
            runner._run_cli_outcome("p", "claude roll", lambda out: out)
    line = next(r.message for r in caplog.records if "claude usage:" in r.message)
    assert "kind=claude roll" in line and "model=claude-haiku-5-5" in line
    assert "ctx=1148" in line and "out=300" in line
    # the older cost line is kept for anything already grepping it
    assert any("call cost" in r.message for r in caplog.records)


# --- a model per call kind -----------------------------------------------------------------------


def _model_flag(cmd: list[str]) -> str:
    return cmd[cmd.index("--model") + 1]


def test_roll_review_uses_roll_model_else_the_shared_model(claude_cfg) -> None:
    claude_cfg(roll_model="roll-x")
    seen: dict = {}

    def fake(prompt, prefix, parse_fn, *, cmd=None, **kw):
        seen["cmd"] = cmd
        return None, None

    with (
        patch.object(runner, "_run_cli_outcome", fake),
        patch.object(runner, "build_roll_prompt", return_value="p"),
    ):
        runner._review_roll_cli(None, None, None)  # type: ignore[arg-type]
    assert _model_flag(seen["cmd"]) == "roll-x"

    claude_cfg()  # roll_model empty -> claude.model
    with (
        patch.object(runner, "_run_cli_outcome", fake),
        patch.object(runner, "build_roll_prompt", return_value="p"),
    ):
        runner._review_roll_cli(None, None, None)  # type: ignore[arg-type]
    assert _model_flag(seen["cmd"]) == "sonnet-x"


def test_eod_journal_uses_eod_model(claude_cfg) -> None:
    claude_cfg(eod_model="eod-x")
    seen: dict = {}

    def fake(prompt, prefix, parse_fn, *, cmd=None, **kw):
        seen["cmd"] = cmd
        return None, None

    with (
        patch.object(runner, "_run_cli_outcome", fake),
        patch.object(runner, "build_eod_prompt", return_value="p"),
    ):
        runner._write_journal_narrative_cli(None)  # type: ignore[arg-type]
    assert _model_flag(seen["cmd"]) == "eod-x"


def test_scan_review_uses_review_model_runs_in_workdir_and_skips_limit_retries(
    claude_cfg, tmp_path
) -> None:
    from tests.test_claude import _make_account, _make_candidate

    claude_cfg(review_model="haiku-x", max_retries=2)
    with patch("src.claude.runner.subprocess.run", return_value=_proc(_LIMIT, 1)) as run:
        reviews, error = runner._review_candidates_cli_outcome([_make_candidate()], _make_account())
    assert (reviews, error) == ([], "cli_error")
    assert run.call_count == 1
    assert _model_flag(run.call_args.args[0]) == "haiku-x"
    assert run.call_args.kwargs["cwd"] == tmp_path / "work"


def test_news_model_still_comes_from_the_news_config(claude_cfg) -> None:
    """news.llm.model is the news thread's own pin; it must override claude.* models."""
    claude_cfg(review_model="haiku-x")
    from src.news import llm

    seen: dict = {}

    def fake(prompt, prefix, parse_fn, *, cmd=None, **kw):
        seen["cmd"] = cmd
        return None, None

    news_cfg = SimpleNamespace(model="news-x", timeout_seconds=5)
    with patch.object(runner, "_run_cli_outcome", fake):
        llm._cli("p", "news:test", news_cfg)  # type: ignore[arg-type]
    assert _model_flag(seen["cmd"]) == "news-x"
