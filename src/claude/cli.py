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
import re
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


# The system prompt a slim call uses instead of Claude Code's default (~6K tokens of coding-agent
# instructions). Every caller's own prompt already says exactly what to return.
HEADLESS_SYSTEM_PROMPT = "You are a concise assistant. Follow the user's output format exactly."


def build_cmd(
    cli_command: str,
    *,
    model: str,
    effort: str,
    disallowed_tools: str,
    max_turns: int = 1,
    output_format: str = "json",
    slim: bool = True,
) -> list[str]:
    """The headless ``claude -p`` command. *slim* (the default) strips the interactive session's
    ambient context: skills, user settings and plugin hooks, tool definitions, the default system
    prompt, and the on-disk transcript. Measured 2026-10-15 on CLI 2.1.295, a trivial call went
    from 37.7K context tokens (repo cwd, everything loaded) to 0.6K with these flags; the real
    roll/news/scan prompts replayed identically (docs: STATUS.md, "Headless call weight").
    The caller must also run it from a directory with no CLAUDE.md in any ancestor (see
    ``ClaudeCfg.workdir``): ``--setting-sources project`` would otherwise load the repo's."""
    cmd = [cli_command, "-p", "--output-format", output_format]
    if max_turns:
        cmd += ["--max-turns", str(max_turns)]
    cmd.append("--strict-mcp-config")
    if slim:
        cmd += [
            "--disable-slash-commands",
            "--setting-sources",
            "project",
            "--tools",
            "",
            "--no-session-persistence",
            "--system-prompt",
            HEADLESS_SYSTEM_PROMPT,
        ]
    if disallowed_tools:
        cmd += ["--disallowedTools", disallowed_tools]
    if model:
        cmd += ["--model", model]
    if effort:
        cmd += ["--effort", effort]
    return cmd


@dataclass(frozen=True)
class Usage:
    """What one call consumed, read from the envelope: context tokens are input + cache writes +
    cache reads (what the call carried), output includes any thinking."""

    model: str
    ctx_tokens: int
    out_tokens: int
    cost_usd: float | None  # notional, from the envelope
    duration_ms: int | None


def _envelope(raw: str) -> dict | None:
    try:
        env = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return env if isinstance(env, dict) else None


def usage_summary(raw: str) -> Usage | None:
    """The token/cost summary of an envelope, or None when it carries no ``usage``. Never raises."""
    env = _envelope(raw)
    usage = env.get("usage") if env else None
    if not isinstance(usage, dict):
        return None

    def n(key: str) -> int:
        v = usage.get(key)
        return int(v) if isinstance(v, int | float) else 0

    models = env.get("modelUsage") if env else None
    model = "+".join(models) if isinstance(models, dict) and models else "?"
    cost = env.get("total_cost_usd") if env else None
    dur = env.get("duration_ms") if env else None
    return Usage(
        model=model,
        ctx_tokens=n("input_tokens")
        + n("cache_creation_input_tokens")
        + n("cache_read_input_tokens"),
        out_tokens=n("output_tokens"),
        cost_usd=float(cost) if isinstance(cost, int | float) else None,
        duration_ms=int(dur) if isinstance(dur, int | float) else None,
    )


def format_usage(kind: str, u: Usage) -> str:
    """The one-line record ``scripts/claude_usage.py`` aggregates — keep the key=value shape."""
    cost = f"{u.cost_usd:.6f}" if u.cost_usd is not None else "?"
    return (
        f"claude usage: kind={kind} model={u.model} ctx={u.ctx_tokens} out={u.out_tokens} "
        f"cost={cost}"
    )


def log_usage(logger: logging.Logger, kind: str, raw: str) -> None:
    """Log what a call consumed, by call kind. Best-effort: never raises."""
    try:
        u = usage_summary(raw)
        if u is not None:
            logger.info(format_usage(kind, u))
    except Exception:  # noqa: BLE001 — observability must never fail a call
        pass


_LIMIT_RE = re.compile(r"hit your .{0,24}limit|usage limit|rate.?limit", re.IGNORECASE)


def is_usage_limit(raw: str) -> bool:
    """True when stdout is an error envelope saying the plan's limit was reached. A retry cannot
    succeed, so callers skip it."""
    env = _envelope(raw)
    if not env or not env.get("is_error"):
        return False
    # The real envelope (2026-10-14): api_error "usage_limit_reached", api_error_status 429, result
    # "You've hit your session limit · resets 10:30pm (Asia/Singapore)". Structured fields first;
    # the text is the fallback for a CLI that stops sending them.
    if env.get("api_error") == "usage_limit_reached" or env.get("api_error_status") == 429:
        return True
    result = env.get("result")
    return isinstance(result, str) and _LIMIT_RE.search(result) is not None


async def run_claude(
    prompt: str,
    *,
    cli_command: str,
    model: str,
    effort: str,
    timeout_seconds: float,
    cwd: Path,
    disallowed_tools: str,
    slim: bool = True,
    usage_kind: str = "spreads_ai",
) -> CliResult:
    start = time.monotonic()

    def elapsed() -> int:
        return int((time.monotonic() - start) * 1000)

    cwd.mkdir(parents=True, exist_ok=True)
    cmd = build_cmd(
        cli_command, model=model, effort=effort, disallowed_tools=disallowed_tools, slim=slim
    )
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
    log_usage(log, usage_kind, raw)
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
