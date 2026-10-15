from __future__ import annotations

import ast
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
import pytest

from src.claude.cli import OllamaSettings, run_claude, run_ollama, should_fall_back

ROOT = Path(__file__).resolve().parents[1]


def fake_cli(tmp_path: Path, body: str) -> str:
    # A python shebang breaks when sys.executable's path has a space (this repo's does), so the
    # executable is an sh wrapper that execs the quoted interpreter on a sibling script.
    script = tmp_path / "fake_claude.py"
    script.write_text(
        f"import json, os, sys, time\nprompt = sys.stdin.read()\n{body}\n", encoding="utf-8"
    )
    p = tmp_path / "fake_claude"
    p.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
    p.chmod(0o755)
    return str(p)


async def _run(cli: str, tmp_path: Path, timeout: float = 10.0):
    return await run_claude(
        "hello",
        cli_command=cli,
        model="claude-opus-5-5",
        effort="high",
        timeout_seconds=timeout,
        cwd=tmp_path / "work",
        disallowed_tools="Bash Edit",
    )


async def test_returns_the_reply_and_cost_and_runs_one_turn_in_the_workdir(tmp_path) -> None:
    cli = fake_cli(
        tmp_path,
        'print(json.dumps({"is_error": False, "total_cost_usd": 0.02, '
        '"result": json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "prompt": prompt})}))',
    )
    res = await _run(cli, tmp_path)
    assert res.error is None and res.cost_usd == 0.02 and res.latency_ms >= 0
    seen = json.loads(res.text or "")
    assert seen["prompt"] == "hello"
    assert Path(seen["cwd"]).resolve() == (tmp_path / "work").resolve()
    argv = seen["argv"]
    assert argv[:1] == ["-p"] and "--strict-mcp-config" in argv
    assert argv[argv.index("--max-turns") + 1] == "1"
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert argv[argv.index("--effort") + 1] == "high"
    assert argv[argv.index("--disallowedTools") + 1] == "Bash Edit"


async def test_an_error_envelope_is_a_cli_error(tmp_path) -> None:  # e.g. a usage limit
    cli = fake_cli(
        tmp_path, 'print(json.dumps({"is_error": True, "result": "limit", "total_cost_usd": 0}))'
    )
    res = await _run(cli, tmp_path)
    assert (res.text, res.error) == (None, "cli_error")


async def test_garbage_stdout_is_a_bad_envelope(tmp_path) -> None:
    res = await _run(fake_cli(tmp_path, 'print("not json")'), tmp_path)
    assert res.error == "bad_envelope" and res.raw.strip() == "not json"


async def test_a_failing_exit_with_plain_text_is_a_cli_error_so_the_fallback_runs(tmp_path) -> None:
    res = await _run(fake_cli(tmp_path, 'print("usage limit reached"); sys.exit(1)'), tmp_path)
    assert res.error == "cli_error" and res.raw.strip() == "usage limit reached"


async def test_a_failing_exit_with_no_output_is_a_cli_error(tmp_path) -> None:
    res = await _run(fake_cli(tmp_path, "sys.exit(3)"), tmp_path)
    assert res.error == "cli_error"


async def test_a_slow_cli_times_out_and_is_killed(tmp_path) -> None:
    res = await _run(fake_cli(tmp_path, "time.sleep(10)"), tmp_path, timeout=0.5)
    assert res.error == "timeout" and res.latency_ms < 5000


async def test_cancelling_the_run_kills_the_child(tmp_path) -> None:
    pidfile = tmp_path / "pid"
    cli = fake_cli(tmp_path, f'open({str(pidfile)!r}, "w").write(str(os.getpid()))\ntime.sleep(30)')
    task = asyncio.create_task(_run(cli, tmp_path, timeout=30))
    for _ in range(100):  # wait until the child is up and has written its pid
        if pidfile.exists() and pidfile.read_text():
            break
        await asyncio.sleep(0.05)
    pid = int(pidfile.read_text())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    for _ in range(100):  # the kill is delivered synchronously; give the OS a moment to reap
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        await asyncio.sleep(0.05)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


async def test_a_kill_race_with_an_exited_child_does_not_replace_the_outcome(
    tmp_path, monkeypatch
) -> None:
    class Gone:
        returncode = None

        async def communicate(self, _: bytes) -> tuple[bytes, bytes]:
            await asyncio.sleep(30)
            return b"", b""

        def kill(self) -> None:
            raise ProcessLookupError

        async def wait(self) -> int:
            return 0

    async def spawn(*_a, **_k):
        return Gone()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    res = await _run("x", tmp_path, timeout=0.2)
    assert res.error == "timeout"
    task = asyncio.create_task(_run("x", tmp_path, timeout=30))
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_a_missing_binary_is_cli_missing(tmp_path) -> None:
    res = await _run(str(tmp_path / "nope"), tmp_path)
    assert res.error == "cli_missing"


def test_cli_module_imports_nothing_from_src() -> None:
    tree = ast.parse((ROOT / "src" / "claude" / "cli.py").read_text(encoding="utf-8"))
    mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert [m for m in mods if m == "src" or m.startswith("src.")] == []


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (None, False),
        ("timeout", False),
        ("disabled", False),
        ("cli_missing", True),
        ("cli_error", True),
        ("bad_envelope", True),
    ],
)
def test_should_fall_back(error, expected) -> None:
    assert should_fall_back(error) is expected


OLLAMA = OllamaSettings("http://x:1", "m", "2m", 0.2, 4096)
REQ = httpx.Request("POST", "http://x:1/api/generate")


def _patch_post(monkeypatch, outcome, sent: dict | None = None):
    async def post(self, url, json=None, **kw):
        if sent is not None:
            sent.update(json)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(httpx.AsyncClient, "post", post)


async def test_run_ollama_returns_the_response_text_and_sends_the_schema(monkeypatch) -> None:
    sent: dict = {}
    _patch_post(monkeypatch, httpx.Response(200, json={"response": '{"a":1}'}, request=REQ), sent)
    res = await run_ollama("p", settings=OLLAMA, schema={"type": "object"}, timeout_seconds=5)
    assert (res.text, res.error) == ('{"a":1}', None)
    assert sent["model"] == "m" and sent["format"] == {"type": "object"}
    assert sent["stream"] is False and sent["think"] is False
    assert sent["options"] == {"temperature": 0.2, "num_ctx": 4096}


@pytest.mark.parametrize(
    ("outcome", "error"),
    [
        (httpx.ConnectError("down"), "cli_error"),
        (httpx.ReadTimeout("slow"), "timeout"),
        (httpx.Response(500, request=REQ), "cli_error"),
        (httpx.Response(200, json={"nope": 1}, request=REQ), "bad_envelope"),
    ],
)
async def test_run_ollama_never_raises(monkeypatch, outcome, error) -> None:
    _patch_post(monkeypatch, outcome)
    res = await run_ollama("p", settings=OLLAMA, schema={}, timeout_seconds=5)
    assert (res.text, res.error) == (None, error)
