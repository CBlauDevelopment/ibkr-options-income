"""ClaudePicker — the spreads service's ``Picker``, backed by ``claude -p``.

Never raises: a CLI failure, an unreadable reply or a crashing context source comes back as a
``fallback_reason`` (pick) or a plan of None (brief). The service decides what a fallback
means; this module never sees the trading path.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from src.claude.cli import CliResult, run_claude
from src.common.config import Config, SpreadsCfg
from src.common.schemas import (
    SpreadBriefRequest,
    SpreadBriefResult,
    SpreadLlmCall,
    SpreadMarketSnapshot,
    SpreadPick,
    SpreadPickRequest,
)
from src.spreads_ai.context import market_snapshot
from src.spreads_ai.parse import parse_day_plan, parse_pick
from src.spreads_ai.prompts import build_brief_prompt, build_pick_prompt

log = logging.getLogger(__name__)
_SNAPSHOT_TIMEOUT_SECONDS = 15.0
_MIN_FALLBACK_SECONDS = 5.0  # less left than this: no fallback call, the cli_error stands

Runner = Callable[..., Awaitable[CliResult]]
Snapshotter = Callable[..., SpreadMarketSnapshot]


class ClaudePicker:
    def __init__(
        self,
        cfg: SpreadsCfg,
        *,
        cli_command: str,
        disallowed_tools: str,
        workdir: Path,
        run: Runner = run_claude,
        snapshot: Snapshotter = market_snapshot,
    ) -> None:
        self.cfg = cfg
        self.cli_command = cli_command
        self.disallowed_tools = disallowed_tools
        self.workdir = workdir
        self._run = run
        self._snapshot = snapshot

    @classmethod
    def from_config(cls, cfg: Config) -> ClaudePicker:
        return cls(
            cfg.spreads,
            cli_command=cfg.claude.cli_command,
            disallowed_tools=cfg.claude.disallowed_tools,
            workdir=cfg.spreads_ai_workdir(),
        )

    async def _market(self, now: datetime) -> SpreadMarketSnapshot:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._snapshot,
                    now,
                    symbol=self.cfg.underlying,
                    max_headlines=self.cfg.ai.max_headlines,
                ),
                _SNAPSHOT_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 — a missing snapshot never blocks a pick
            log.warning("spreads_ai: market snapshot failed: %s", exc)
            return SpreadMarketSnapshot(unavailable=["snapshot"])

    async def _call(
        self, prompt: str, *, model: str, effort: str, timeout: float
    ) -> tuple[CliResult, str, str]:
        """One call, plus one retry on ``ai.fallback_model`` when the first ends in cli_error
        (a usage limit surfaces that way) and enough of *timeout* is left. Returns the result
        and the model/effort that produced it; latency and cost cover both calls."""

        async def once(m: str, e: str, t: float) -> CliResult:
            kwargs: dict[str, Any] = {
                "cli_command": self.cli_command,
                "model": m,
                "effort": e,
                "timeout_seconds": t,
                "cwd": self.workdir,
                "disallowed_tools": self.disallowed_tools,
            }
            return await self._run(prompt, **kwargs)

        res = await once(model, effort, timeout)
        ai = self.cfg.ai
        left = timeout - res.latency_ms / 1000
        if (
            res.error != "cli_error"
            or not ai.fallback_model
            or ai.fallback_model == model
            or left < _MIN_FALLBACK_SECONDS
        ):
            return res, model, effort
        log.warning("spreads_ai: %s failed (cli_error); retrying on %s", model, ai.fallback_model)
        second = await once(ai.fallback_model, ai.fallback_effort, left)
        costs = [c for c in (res.cost_usd, second.cost_usd) if c is not None]
        merged = CliResult(
            second.text,
            second.error,
            res.latency_ms + second.latency_ms,
            sum(costs) if costs else None,
            second.raw,
        )
        return merged, ai.fallback_model, ai.fallback_effort

    async def brief(self, req: SpreadBriefRequest) -> SpreadBriefResult:
        ai = self.cfg.ai
        market = await self._market(req.now)
        prompt = ""
        try:
            prompt = build_brief_prompt(req, market)
            res, model, effort = await self._call(
                prompt,
                model=ai.brief_model,
                effort=ai.brief_effort,
                timeout=ai.brief_timeout_seconds,
            )
            plan = parse_day_plan(res.text) if res.text is not None else None
            error = res.error or (None if plan is not None else "unparseable")
            call = SpreadLlmCall(
                model=model,
                effort=effort,
                latency_ms=res.latency_ms,
                cost_usd=res.cost_usd,
                prompt_text=prompt,
                raw_response=res.text if res.text is not None else res.raw or None,
                error=error,
            )
            return SpreadBriefResult(plan=plan, market=market, call=call)
        except Exception:  # noqa: BLE001
            log.exception("spreads_ai: brief failed")
            return SpreadBriefResult(
                plan=None,
                market=market,
                call=SpreadLlmCall(
                    model=ai.brief_model,
                    effort=ai.brief_effort,
                    prompt_text=prompt,
                    error="picker_error",
                ),
            )

    async def pick(self, req: SpreadPickRequest) -> SpreadPick:
        ai = self.cfg.ai
        market = await self._market(req.now)
        prompt = ""
        try:
            prompt = build_pick_prompt(req, market)
            res, model, effort = await self._call(
                prompt, model=ai.pick_model, effort=ai.pick_effort, timeout=ai.pick_timeout_seconds
            )
            call = SpreadLlmCall(
                model=model,
                effort=effort,
                latency_ms=res.latency_ms,
                cost_usd=res.cost_usd,
                prompt_text=prompt,
                raw_response=res.text if res.text is not None else res.raw or None,
                error=res.error,
            )
            parsed = parse_pick(res.text) if res.text is not None else None
            if parsed is None:
                reason = res.error or "unparseable"
                return SpreadPick(
                    choice="skip",
                    fallback_reason=reason,
                    market=market,
                    call=call.model_copy(update={"error": reason}),
                )
            return SpreadPick(choice=parsed[0], reason=parsed[1], market=market, call=call)
        except Exception:  # noqa: BLE001
            log.exception("spreads_ai: pick failed")
            return SpreadPick(
                choice="skip",
                fallback_reason="picker_error",
                market=market,
                call=SpreadLlmCall(
                    model=ai.pick_model,
                    effort=ai.pick_effort,
                    prompt_text=prompt,
                    error="picker_error",
                ),
            )
