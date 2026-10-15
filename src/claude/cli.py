"""Async, single-shot ``claude -p`` for callers that must not load the wheel's prompt stack.

src/spreads_ai/ (the spreads picker) uses this rather than src/claude/runner.py, which imports
the strategist/roll/EOD prompts and the Ollama runner at module load. It imports nothing from
src/: the caller passes every setting. The prompt goes in on stdin; the command runs in *cwd*
(the caller picks a directory with no CLAUDE.md in any ancestor: claude walks up from its cwd),
for one turn, with no MCP servers and
every tool in *disallowed_tools* refused. Never raises for a CLI failure: the result says why.

It also holds the fallback rule (``should_fall_back``) and ``run_ollama``, the local-model call
the spreads picker uses when ``claude -p`` cannot answer, so the picker still imports only this
module from ``src.claude``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

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


def should_fall_back(error: str | None) -> bool:
    """Ollama is tried on every CLI failure except a timeout (the budget is spent) and
    ``disabled`` (the operator turned Claude off)."""
    return error is not None and error not in ("timeout", "disabled")


@dataclass(frozen=True)
class OllamaSettings:
    host: str
    model: str
    keep_alive: str
    temperature: float
    num_ctx: int


async def run_ollama(
    prompt: str, *, settings: OllamaSettings, schema: dict, timeout_seconds: float
) -> CliResult:
    """One schema-constrained ``/api/generate`` call. Never raises (cancellation propagates)."""
    start = time.monotonic()

    def elapsed() -> int:
        return int((time.monotonic() - start) * 1000)

    url = f"{settings.host.rstrip('/')}/api/generate"
    body = {
        "model": settings.model,
        "prompt": prompt,
        "format": schema,
        "stream": False,
        "think": False,
        "keep_alive": settings.keep_alive,
        "options": {"temperature": settings.temperature, "num_ctx": settings.num_ctx},
    }

    async def post() -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            return resp

    try:
        resp = await asyncio.wait_for(post(), timeout_seconds)
    except (TimeoutError, httpx.TimeoutException):
        log.warning("ollama: timed out after %.0fs", timeout_seconds)
        return CliResult(None, "timeout", elapsed())
    except httpx.HTTPError as exc:
        log.warning("ollama: request to %s failed: %s", url, exc)
        return CliResult(None, "cli_error", elapsed())
    try:
        text = resp.json()["response"]
    except (ValueError, KeyError, TypeError):
        return CliResult(None, "bad_envelope", elapsed(), raw=resp.text[:2000])
    if not isinstance(text, str):
        return CliResult(None, "bad_envelope", elapsed(), raw=resp.text[:2000])
    return CliResult(text, None, elapsed(), raw=text)
