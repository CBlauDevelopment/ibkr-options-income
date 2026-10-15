"""The wheel's CLI helpers report why `claude -p` failed, and `cli_then_ollama` falls back on
everything except a timeout (docs/superpowers/specs/2026-10-15-ollama-fallback-design.md)."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.claude import ollama_runner, runner

LIMIT = json.dumps({"type": "result", "is_error": True, "result": "usage limit reached"})


def _cfg(backend="cli_then_ollama", enabled=True, retries=1):
    return SimpleNamespace(
        backend=backend,
        enabled=enabled,
        max_retries=retries,
        timeout_seconds=5.0,
        cli_command="claude",
        output_format="json",
        max_turns=1,
        model="",
        effort="",
        disallowed_tools="",
        model_for=lambda kind: "",  # ClaudeCfg.model_for: no per-kind override
    )


def _proc(rc, out=""):
    return subprocess.CompletedProcess([], rc, stdout=out, stderr="")


def _outcome(side_effect, parse=lambda s: None):
    with (
        patch.object(runner, "get_config") as cfg,
        patch.object(runner.subprocess, "run", side_effect=side_effect),
    ):
        cfg.return_value.claude = _cfg()
        return runner._run_cli_outcome("p", "t", parse)


def test_a_limit_shaped_failure_is_a_cli_error() -> None:
    assert _outcome([_proc(1, LIMIT)] * 2) == (None, "cli_error")
    assert _outcome([_proc(1, "")] * 2) == (None, "cli_error")


def test_a_missing_binary_is_cli_missing() -> None:
    assert _outcome(FileNotFoundError()) == (None, "cli_missing")


def test_one_timeout_makes_the_outcome_a_timeout_whatever_the_last_attempt_did() -> None:
    boom = subprocess.TimeoutExpired("claude", 5)
    assert _outcome([boom, _proc(1, "")]) == (None, "timeout")


def test_garbage_on_exit_zero_is_a_bad_envelope_and_success_has_no_error() -> None:
    assert _outcome([_proc(0, "garbage")] * 2) == (None, "bad_envelope")
    assert _outcome([_proc(0, "ok")], parse=lambda s: s.upper()) == ("OK", None)


@pytest.mark.parametrize(
    ("outcome", "ollama_called"),
    [
        ((None, "cli_error"), True),
        ((None, "cli_missing"), True),
        ((None, "bad_envelope"), True),
        ((None, "timeout"), False),
        ((None, "disabled"), False),
    ],
)
def test_roll_and_eod_dispatchers_follow_the_rule(outcome, ollama_called) -> None:
    with (
        patch.object(runner, "get_config") as cfg,
        patch.object(runner, "_review_roll_cli", return_value=outcome),
        patch.object(runner, "_write_journal_narrative_cli", return_value=outcome),
        patch.object(ollama_runner, "review_roll", return_value="local") as roll,
        patch.object(ollama_runner, "write_journal_narrative", return_value="local") as eod,
    ):
        cfg.return_value.claude = _cfg()
        r = runner.review_roll(MagicMock(), MagicMock(), MagicMock())
        e = runner.write_journal_narrative(MagicMock())
    assert roll.called is ollama_called and eod.called is ollama_called
    assert (r, e) == (("local", "local") if ollama_called else (None, None))


def test_a_cli_success_never_touches_ollama() -> None:
    with (
        patch.object(runner, "get_config") as cfg,
        patch.object(runner, "_review_roll_cli", return_value=("review", None)),
        patch.object(ollama_runner, "review_roll") as roll,
    ):
        cfg.return_value.claude = _cfg()
        assert runner.review_roll(MagicMock(), MagicMock(), MagicMock()) == "review"
    roll.assert_not_called()


def _review(side_effect, candidates, enabled=True):
    with (
        patch.object(runner, "get_config") as cfg,
        patch.object(runner, "build_prompt", return_value="p"),
        patch.object(runner.subprocess, "run", side_effect=side_effect),
        patch.object(ollama_runner, "review_candidates", return_value=["local"]) as local,
    ):
        cfg.return_value.claude = _cfg(enabled=enabled)
        out = runner.review_candidates(candidates, MagicMock())
    return out, local.called


def test_review_candidates_falls_back_on_a_limit_but_not_a_timeout() -> None:
    cands = [MagicMock(candidate_id="c1")]
    assert _review([_proc(1, LIMIT)] * 2, cands) == (["local"], True)
    assert _review([subprocess.TimeoutExpired("claude", 5)] * 2, cands) == ([], False)
    assert _review([subprocess.TimeoutExpired("claude", 5), _proc(1, "")], cands) == ([], False)


def test_review_candidates_does_not_fall_back_when_disabled_or_empty() -> None:
    assert _review([], [MagicMock(candidate_id="c1")], enabled=False) == ([], False)
    assert _review([], []) == ([], False)
