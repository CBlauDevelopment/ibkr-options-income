"""Async, single-shot ``claude -p`` for callers that must not load the wheel's prompt stack.

src/spreads_ai/ (the spreads picker) uses this rather than src/claude/runner.py, which imports
the strategist/roll/EOD prompts and the Ollama runner at module load. It imports nothing from
src/: the caller passes every setting. The prompt goes in on stdin; the command runs in *cwd*
(the caller picks a directory with no CLAUDE.md in any ancestor: claude walks up from its cwd),
for one turn, with no MCP servers and
every tool in *disallowed_tools* refused. Never raises for a CLI failure: the result says why.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CliResult:
    text: str | None  # the model's reply (the envelope's "result"); None on any failure
    error: str | None  # None | cli_missing | timeout | cli_error | bad_envelope
    latency_ms: int
    cost_usd: float | None = None  # notional, from the envelope
    raw: str = ""  # stdout as received, kept for the record


def build_cmd(cli_command: str, *, model: str, effort: str, disallowed_tools: str) -> list[str]:
    cmd = [cli_command, "-p", "--output-format", "json", "--max-turns", "1", "--strict-mcp-config"]
    if disallowed_tools:
        cmd += ["--disallowedTools", disallowed_tools]
    if model:
        cmd += ["--model", model]
    if effort:
        cmd += ["--effort", effort]
    return cmd


async def run_claude(
    prompt: str,
    *,
    cli_command: str,
    model: str,
    effort: str,
    timeout_seconds: float,
    cwd: Path,
    disallowed_tools: str,
) -> CliResult:
    start = time.monotonic()

    def elapsed() -> int:
        return int((time.monotonic() - start) * 1000)

    cwd.mkdir(parents=True, exist_ok=True)
    cmd = build_cmd(cli_command, model=model, effort=effort, disallowed_tools=disallowed_tools)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except (FileNotFoundError, PermissionError):
        log.warning("claude cli: %s not found or not executable", cli_command)
        return CliResult(None, "cli_missing", elapsed())
    try:
        out, err = await asyncio.wait_for(proc.communicate(prompt.encode()), timeout_seconds)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):  # the child may have just exited
            proc.kill()
        await proc.wait()
        log.warning("claude cli: timed out after %.0fs", timeout_seconds)
        return CliResult(None, "timeout", elapsed())
    except asyncio.CancelledError:
        with contextlib.suppress(ProcessLookupError):  # a race here must not replace the cancel
            proc.kill()  # the caller gave up: never leave the subprocess running
        await proc.wait()  # SIGKILL: reaps at once, and closes the transport
        raise
    raw = out.decode("utf-8", errors="replace")
    if proc.returncode != 0 and not raw.strip():
        log.warning(
            "claude cli: rc=%s stderr=%s", proc.returncode, err.decode(errors="replace")[:200]
        )
        return CliResult(None, "cli_error", elapsed(), raw=raw)
    # a non-zero exit is a cli_error even when stdout is not an envelope: a usage limit may be
    # printed as plain text, and the caller retries only on cli_error
    unreadable = "cli_error" if proc.returncode != 0 else "bad_envelope"
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError:
        return CliResult(None, unreadable, elapsed(), raw=raw)
    if not isinstance(envelope, dict):
        return CliResult(None, unreadable, elapsed(), raw=raw)
    cost_raw = envelope.get("total_cost_usd")
    cost = float(cost_raw) if isinstance(cost_raw, int | float) else None
    reply = envelope.get("result")
    if envelope.get("is_error") or not isinstance(reply, str):
        return CliResult(None, "cli_error", elapsed(), cost, raw)
    return CliResult(reply, None, elapsed(), cost, raw)
