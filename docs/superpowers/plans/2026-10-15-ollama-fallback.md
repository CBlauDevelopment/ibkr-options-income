# Ollama fallback for every `claude -p` call — Implementation Plan

> **For agentic workers:** executed inline by the main session, on `main` (operator's instruction, 2026-10-15). Steps use checkbox syntax.

**Goal:** every AI call falls back to Ollama when `claude -p` fails (usage limit, missing CLI, error envelope, unparseable reply) — never on a timeout.

**Architecture:** one pure rule, `should_fall_back(error)` in `src/claude/cli.py`. The wheel's sync CLI helpers report *why* they failed (`error` vocabulary = `CliResult.error`); the four paths (wheel dispatchers, news, summary, spreads picker) consult the rule. Spreads gets `run_ollama` inside `cli.py` so `src/spreads_ai/` still imports only `src.claude.cli`.

**Tech Stack:** Python 3.12, httpx, pydantic, pytest (asyncio mode as in the repo).

**Spec:** `docs/superpowers/specs/2026-10-15-ollama-fallback-design.md`

## Global Constraints

- `error` vocabulary: `None | "timeout" | "cli_missing" | "cli_error" | "bad_envelope" | "disabled"`.
- `should_fall_back(error) == error is not None and error not in ("timeout", "disabled")`.
- `src/claude/cli.py` imports nothing from `src/`. `src/spreads_ai/` imports only `src.claude.cli` from `src.claude`.
- Retries are unchanged. Nothing reaches `engine/`, `execution/`, `strategies/`, sizing or the spreads gate.
- Commit locally on `main` after each task; **do not push**. Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Review Focus

- A limit-shaped failure (exit 1 + `is_error` envelope, or exit 1 + empty stdout) falls back; a timeout never does (Tasks 2, 3, 4).
- One timeout plus one refusal across retries still counts as `timeout` — the budget is spent (Task 2).
- `claude.enabled: false` and an empty candidate list never trigger Ollama (Task 2).
- Ollama also failing ends in today's outcome (`[]`/`None`/baseline pick), never an exception (Tasks 1, 4).
- An off-menu letter from Ollama is still rejected by the service — the picker only shape-checks (Task 4, unchanged parse path).

## Progress log

| Task | Status | Commit | Gate | Date | Rulings |
|---|---|---|---|---|---|
| 1 cli.py primitives | done | 7ed1d27 | tests/test_claude_cli.py 21 passed | 2026-10-15 | red step skipped to save tokens |
| 2 wheel runner | done | 4c01764 | 119 passed (runner, roll, claude, ollama suites) | 2026-10-15 | |
| 3 news + summary | done | 1e08084 | 73 passed incl. news/web fences | 2026-10-15 | |
| 4 spreads picker | done | 16deb2f | 75 passed incl. spreads fence | 2026-10-15 | |
| 5 probe, config, docs | done | this commit (`git log`) | full gate: 3761 passed, ruff check, mypy clean | 2026-10-15 | see below |

Rulings: `_run_cli` is **renamed** `_run_cli_outcome` (no wrapper — its only callers are updated here). `examples/settings.yaml` keeps `backend: "ollama"` (forks without a subscription); only the comment and `examples/news.yaml` change.
Task 5 rulings: `tests/test_news_config.py` and `tests/test_research_config.py` asserted the old defaults (`cli`, `claude_cli`) and were updated to the new ones. `ruff format --check` flags 4 files this change did not touch (`scripts/roll_backtest.py`, `src/api/routers/{portfolio,system}.py`, `tests/test_config_keys.py`); left alone. Only the two files this change touched were reformatted.

---

### Task 1: `cli.py` primitives

**Files:** Modify `src/claude/cli.py`; Test `tests/test_claude_cli.py`.

**Produces:** `should_fall_back(error: str | None) -> bool`; `OllamaSettings(host, model, keep_alive, temperature, num_ctx)`; `async run_ollama(prompt, *, settings: OllamaSettings, schema: dict, timeout_seconds: float) -> CliResult`.

- [x] **Step 1: tests** (append to `tests/test_claude_cli.py`; reuse its `asyncio` mode): `test_should_fall_back` — parametrize `None→False, "timeout"→False, "disabled"→False, "cli_missing"/"cli_error"/"bad_envelope"→True`. `test_run_ollama_*` with `httpx.MockTransport` is not injectable, so monkeypatch `httpx.AsyncClient.post`: (a) returns `httpx.Response(200, json={"response": "{\"a\":1}"}, request=req)` → `CliResult('{"a":1}', None, ...)`; (b) raises `httpx.ConnectError("x")` → `error == "cli_error"`; (c) raises `httpx.ReadTimeout("x")` → `"timeout"`; (d) `Response(200, json={"nope": 1})` → `"bad_envelope"`; (e) `Response(500)` → `"cli_error"`. Each call: `await run_ollama("p", settings=S, schema={}, timeout_seconds=5)` where `S = OllamaSettings("http://x:1", "m", "2m", 0.2, 4096)`. Also assert the request body: model, `format == schema`, `stream is False`, `think is False`, `options == {"temperature": 0.2, "num_ctx": 4096}`.
- [x] **Step 2:** `python -m pytest tests/test_claude_cli.py -q` → FAIL (names missing).
- [x] **Step 3: implement** in `cli.py` — add `import httpx` and:

```python
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
```

Also update the module docstring's first paragraph to mention Ollama.
- [x] **Step 4:** run the test file → PASS. **Step 5:** commit `feat(claude): should_fall_back rule and async run_ollama`.

---

### Task 2: wheel runner reports why a CLI call failed

**Files:** Modify `src/claude/runner.py`; Tests `tests/test_roll_review_proposal.py`, new `tests/test_ollama_fallback_runner.py`.

**Consumes:** `should_fall_back` (Task 1). **Produces:** `_run_cli_outcome(prompt, prefix, parse_fn, *, cmd=None, timeout_seconds=None, max_retries=None) -> tuple[T | None, str | None]` (replaces `_run_cli`); `_review_candidates_cli_outcome(...) -> tuple[list[ClaudeReview], str | None]` (`_review_candidates_cli` stays, returning the list); `_review_roll_cli` and `_write_journal_narrative_cli` now return `(value, error)`.

- [x] **Step 1: tests** in `tests/test_ollama_fallback_runner.py` (patch `src.claude.runner.subprocess.run` and `get_config`, mirroring `tests/test_ollama_runner.py::test_cli_then_ollama_falls_back_when_cli_empty` — copy its `cfg` MagicMock block, set `max_retries=1`):
  1. `_run_cli_outcome` with subprocess returning `(rc=1, stdout=json.dumps({"is_error": True, "result": "limit"}))` and `parse_fn=lambda s: None` → `(None, "cli_error")`.
  2. `FileNotFoundError` → `(None, "cli_missing")`.
  3. first call `TimeoutExpired`, second rc=1 empty stdout → `(None, "timeout")` (sticky).
  4. rc=0, stdout `"garbage"`, parse `None` → `(None, "bad_envelope")`.
  5. success → `(value, None)`.
  6. dispatcher `review_roll` with `backend="cli_then_ollama"`: CLI `cli_error` → `ollama_runner.review_roll` called (patch it); CLI timeout → not called; `enabled=False` → not called.
  7. dispatcher `review_candidates` with `cli_then_ollama`: `cli_error` → `ollama_runner.review_candidates` called; `TimeoutExpired` → not called; empty `candidates` → not called.
  8. dispatcher `write_journal_narrative`: `cli_error` → ollama called; timeout → not.
  And in `tests/test_roll_review_proposal.py:67` change `patch.object(runner, "_run_cli", return_value=None)` → `patch.object(runner, "_run_cli_outcome", return_value=(None, None))`.
- [x] **Step 2:** run them → FAIL.
- [x] **Step 3: implement** in `runner.py`: `from src.claude.cli import should_fall_back`.
  - Rename `_run_cli` → `_run_cli_outcome`; body:

```python
    error = "cli_error"
    timed_out = False
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            log.warning("%s: timed out (attempt %d)", prefix, attempt + 1)
            timed_out = True
            continue
        except FileNotFoundError:
            log.warning("claude: CLI not found — skipping %s", prefix)
            return None, "cli_missing"
        if result.returncode != 0 and not result.stdout:
            log.warning("%s: rc=%d, no stdout (attempt %d)", prefix, result.returncode, attempt + 1)
            error = "cli_error"
            continue
        parsed = parse_fn(result.stdout)
        if parsed is not None:
            _log_cost(result.stdout)
            return parsed, None
        log.warning("%s: unparseable output (attempt %d)", prefix, attempt + 1)
        error = "cli_error" if result.returncode != 0 else "bad_envelope"
    log.error("%s: all %d attempt(s) failed", prefix, retries + 1)
    return None, ("timeout" if timed_out else error)
```
  Update its docstring (returns `(parsed, error)`; a timeout in any attempt makes the error `timeout`).
  - `_review_candidates_cli` → rename to `_review_candidates_cli_outcome`, same signature, returning `tuple[list[ClaudeReview], str | None]`: disabled → `return [], "disabled"`; no candidates → `return [], None`; `FileNotFoundError` → `return [], "cli_missing"`; `TimeoutExpired` → set `timed_out = True`; non-zero rc paths set `error = "cli_error"` before each `continue`, and returning parsed reviews → `return reviews, None`; rc 0 success → `return reviews, None`; rc 0 empty parse → `error = "bad_envelope"`; end → `return [], ("timeout" if timed_out else error)` (init `error = "cli_error"`, `timed_out = False`). Add the wrapper:

```python
def _review_candidates_cli(*args: Any, **kwargs: Any) -> list[ClaudeReview]:
    """The reviews alone (existing callers/tests); the dispatcher uses the outcome variant."""
    return _review_candidates_cli_outcome(*args, **kwargs)[0]
```
  (add `from typing import Any`).
  - `_review_roll_cli`: `if not cfg.enabled: ... return None, "disabled"`; `return _run_cli_outcome(build_roll_prompt(...), "claude roll", parse_roll_output)`; return annotation `tuple[RollReview | None, str | None]`. Same shape for `_write_journal_narrative_cli` (`"claude eod"`, `tuple[str | None, str | None]`).
  - Dispatchers: `review_candidates`: `reviews, error = _review_candidates_cli_outcome(**kwargs)`; `if not reviews and cfg.backend == "cli_then_ollama" and should_fall_back(error): log.warning("claude unavailable (%s) — using ollama", error); return ollama_runner.review_candidates(**kwargs)`. `review_roll` / `write_journal_narrative`: `x, error = _..._cli(...)`; `if x is None and cfg.backend == "cli_then_ollama" and should_fall_back(error):` same warning + Ollama call. Update the `review_candidates` docstring ("cli_then_ollama: … fall back when claude -p fails for any reason except a timeout").
- [x] **Step 4:** `python -m pytest tests/test_ollama_fallback_runner.py tests/test_roll_review_proposal.py tests/test_claude.py tests/test_ollama_runner.py -q` → PASS. **Step 5:** commit `feat(claude): classify CLI failures; cli_then_ollama falls back on all but timeouts`.

---

### Task 3: news and summary

**Files:** Modify `src/news/llm.py`, `src/research/summary/claude_cli.py`, `src/research/summary/factory.py`, `src/common/config.py` (`ResearchSummaryCfg`, `NewsLlmCfg` comment); Create `src/research/summary/chain.py`; Tests `tests/test_news_llm.py`, `tests/test_summary_chain.py`.

**Consumes:** `_run_cli_outcome`, `should_fall_back`. **Produces:** `llm._cli(prompt, prefix, cfg) -> tuple[str | None, str | None]`; `ClaudeCliSummaryProvider.generate_with_error(ctx) -> tuple[Summary | None, str | None]`; `ClaudeCliThenOllamaSummaryProvider.generate(ctx)`; backend value `claude_cli_then_ollama`.

- [x] **Step 1: tests.** `tests/test_news_llm.py`: change the `_cli` stubs to tuples — `lambda prompt, prefix, cfg: (None, "cli_error")` (fallback test), `lambda ...: calls.append(1) or ("x", None)` (cap test), and `boom` stays raising. In `test_cli_command_pins_news_model` patch `src.claude.runner._run_cli_outcome` and have `fake_run` return `(parse_fn(...), None)`; assert `out == ('{"a":1}', None)`. Add: `test_a_cli_timeout_does_not_fall_back` (`backend="cli_then_ollama"`, `_cli` → `(None, "timeout")`, `_ollama` records calls; `call_llm(...) is None` and ollama not called; `llm_calls(...) == 1`). `tests/test_summary_chain.py`: stub `ClaudeCliSummaryProvider.generate_with_error` and `OllamaSummaryProvider.generate` via monkeypatch; cases: CLI ok → Ollama not called; `(None, "cli_error")` → Ollama result returned; `(None, "timeout")` → `None`, Ollama not called; `get_summary_provider()` returns the chain when `research.summary.backend = "claude_cli_then_ollama"` (clear `get_summary_provider.cache_clear()`); `ResearchSummaryCfg(backend="claude_cli_then_ollama")` validates and `backend="nope"` raises.
- [x] **Step 2:** run → FAIL.
- [x] **Step 3: implement.**
  - `news/llm.py`: `from src.claude.cli import should_fall_back`; `_cli` returns `runner._run_cli_outcome(...)` (the `(text, error)` tuple, same arguments); in `call_llm`:

```python
        error: str | None = None
        try:
            if backend == "cli":
                text, error = _cli(prompt, prefix, cfg)
            else:
                text = _ollama(prompt, schema, cfg)
        except Exception:
            log.exception("news llm: %s backend raised", backend)
            text, error = None, "cli_error"
        if text:
            return LlmResult(text, backend)
        if backend == "cli" and not should_fall_back(error):
            return None  # timeout/disabled: the budget is spent, do not start Ollama
```
  - `claude_cli.py`: import `_run_cli_outcome`; rename the body of `generate` to `generate_with_error` returning `(None, "disabled")` when disabled and `_run_cli_outcome(...)` otherwise; add `def generate(self, context): return self.generate_with_error(context)[0]`.
  - `chain.py`:

```python
"""``claude_cli_then_ollama`` summary backend: claude -p, then the local model."""

from __future__ import annotations

import logging

from src.claude.cli import should_fall_back
from src.research.summary.claude_cli import ClaudeCliSummaryProvider
from src.research.summary.context import ResearchContext
from src.research.summary.ollama import OllamaSummaryProvider
from src.research.summary.protocol import Summary

log = logging.getLogger(__name__)


class ClaudeCliThenOllamaSummaryProvider:
    def __init__(self) -> None:
        self._cli = ClaudeCliSummaryProvider()
        self._ollama = OllamaSummaryProvider()

    def generate(self, context: ResearchContext) -> Summary | None:
        summary, error = self._cli.generate_with_error(context)
        if summary is None and should_fall_back(error):
            log.warning("summary: claude unavailable (%s) — using ollama", error)
            return self._ollama.generate(context)
        return summary
```
  - `factory.py`: add the branch `if backend == "claude_cli_then_ollama":` importing the chain class. `config.py`: add `"claude_cli_then_ollama"` to `allowed`; change the `NewsLlmCfg.backend` default comment to `# claude -p only by default; cli_then_ollama falls back when claude -p fails (not on a timeout)`.
- [x] **Step 4:** `python -m pytest tests/test_news_llm.py tests/test_summary_chain.py tests/test_summary_claude_cli.py tests/test_summary.py tests/test_news_fence.py tests/test_web_fence.py -q` → PASS. **Step 5:** commit `feat(news,summary): fall back to ollama when claude -p fails`.

---

### Task 4: spreads picker

**Files:** Modify `src/spreads_ai/picker.py`, `src/common/config.py` (`SpreadsAiCfg`); Test `tests/test_spreads_ai_picker.py`, `tests/test_spreads_config.py` if it enumerates ai keys.

**Consumes:** `OllamaSettings`, `run_ollama`, `should_fall_back`. **Produces:** `SpreadsAiCfg.ollama_fallback: bool = True`; `ClaudePicker(..., ollama: OllamaSettings | None = None, ollama_run=run_ollama)`.

- [x] **Step 1: tests** (append to `tests/test_spreads_ai_picker.py`; extend `scripted` with `ollama=None, ollama_run=None` pass-through kwargs):
  1. Opus `cli_error`, Sonnet `cli_error`, Ollama stub returns `CliResult('{"choice": "A", "reason": "local"}', None, 3000)` → `pick.choice == "A"`, `pick.call.model == "ollama:m"`, `pick.call.effort == ""`, `pick.call.latency_ms == 500 + 400 + 3000`, ollama stub received `timeout_seconds == 45.0 - 0.9`, schema has `"choice"` in `required`.
  2. `cli_missing` first (no Sonnet retry) → Ollama still runs (one Claude call, one Ollama call).
  3. `timeout` first → Ollama not called; `fallback_reason == "timeout"`.
  4. `cli_error` with 31 s latency → Sonnet skipped, and Ollama skipped (14 s left < 15).
  5. `ollama=None` (switch off) → Ollama stub never called.
  6. Ollama also fails (`CliResult(None, "cli_error", 10)`) → `choice == "skip"`, `fallback_reason == "cli_error"`.
  7. Brief: `cli_error` ×2 then Ollama returns `'{"bias": "neutral", "summary": "calm"}'` → `res.plan.bias == "neutral"`, `res.call.model == "ollama:m"`; schema has `bias` enum.
  8. `ClaudePicker.from_config(cfg)` has `.ollama is None` when `cfg.spreads.ai.ollama_fallback` is false and `.ollama.model == cfg.claude.ollama_model` when true (use `cfg.model_copy`).
  Stub: `async def orun(prompt, *, settings, schema, timeout_seconds): ocalls.append((settings, schema, timeout_seconds)); return reply`. `S = OllamaSettings("http://x", "m", "2m", 0.2, 4096)`.
- [x] **Step 2:** run → FAIL.
- [x] **Step 3: implement.** `config.py`: in `SpreadsAiCfg` after `fallback_effort` add `ollama_fallback: bool = True  # after the Claude calls fail (not on a timeout), the local Ollama model answers the same prompt`. `picker.py`:
  - imports: `from src.claude.cli import CliResult, OllamaSettings, run_claude, run_ollama, should_fall_back`.
  - module constants:

```python
_PICK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"choice": {"type": "string"}, "reason": {"type": "string"}},
    "required": ["choice", "reason"],
}
_BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "bias": {"type": "string", "enum": ["bullish", "neutral", "bearish"]},
        "risk_flags": {"type": "array", "items": {"type": "string"}},
        "skip_conditions": {"type": "array", "items": {"type": "string"}},
        "preferred_distance": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["bias", "summary"],
}
OllamaRunner = Callable[..., Awaitable[CliResult]]
```
  - `__init__` gains `ollama: OllamaSettings | None = None, ollama_run: OllamaRunner = run_ollama` stored as `self.ollama`, `self._ollama_run`. `from_config` builds `OllamaSettings(c.ollama_host, c.ollama_model, c.ollama_keep_alive, c.ollama_temperature, c.ollama_num_ctx)` from `cfg.claude` when `cfg.spreads.ai.ollama_fallback` else `None`.
  - `_call(self, prompt, *, model, effort, timeout, schema)`: restructure so the Sonnet retry **assigns** `res`/`model`/`effort` instead of returning, then recomputes `left = timeout - res.latency_ms / 1000`, then:

```python
        if self.ollama is None or not should_fall_back(res.error) or left < _MIN_FALLBACK_SECONDS:
            return res, model, effort
        log.warning("spreads_ai: claude unavailable (%s) — using ollama", res.error)
        alt = await self._ollama_run(
            prompt, settings=self.ollama, schema=schema, timeout_seconds=left
        )
        merged = CliResult(
            alt.text, alt.error, res.latency_ms + alt.latency_ms, res.cost_usd, alt.raw
        )
        return merged, f"ollama:{self.ollama.model}", ""
```
  (the existing early-return guard for the Sonnet step stays as the `if` condition for the retry block; the pre-retry `left` is still what the Sonnet call receives — keep `calls[1]["timeout_seconds"] == 45.0 - 0.8` true).
  - `brief` passes `schema=_BRIEF_SCHEMA`, `pick` passes `schema=_PICK_SCHEMA`.
- [x] **Step 4:** `python -m pytest tests/test_spreads_ai_picker.py tests/test_spreads_fence.py tests/test_spreads_config.py tests/test_spreads_picker_flow.py -q` → PASS. **Step 5:** commit `feat(spreads_ai): ollama as the third step after the Claude calls fail`.

---

### Task 5: probe, config files, docs, full gate

**Files:** Modify `src/claude/ollama_runner.py` (add `ollama_in_use`), `scripts/start.py`, `scripts/healthcheck.py`, `config/research.yaml`, `config/examples/{settings,news,spreads}.yaml`, private `config/{settings,news,spreads}.yaml`, `ARCHITECTURE.md`, `SETUP.md`, `STATUS.md`; Test `tests/test_ollama_runner.py`.

- [x] **Step 1: test** `test_ollama_in_use_checks_every_chain` — patch `ollama_runner.get_config` with a `SimpleNamespace` whose `claude.backend="cli"`, `news.llm.backend="cli"`, `research.summary.backend="claude_cli"`, `spreads.ai.enabled=False, ollama_fallback=True` → `False`; then flip each one in turn (`news.llm.backend="cli_then_ollama"`, `research.summary.backend="claude_cli_then_ollama"`, `spreads.ai.enabled=True`) → `True` each.
- [x] **Step 2: implement** next to `probe_ollama`:

```python
def ollama_in_use() -> bool:
    """True when any AI path can reach Ollama: the wheel, news, the summary or the spreads picker."""
    cfg = get_config()
    return (
        cfg.claude.backend in ("ollama", "cli_then_ollama")
        or cfg.news.llm.backend in ("ollama", "cli_then_ollama")
        or cfg.research.summary.backend in ("ollama", "claude_cli_then_ollama")
        or (cfg.spreads.ai.enabled and cfg.spreads.ai.ollama_fallback)
    )
```
  `start.py::_check_ollama`: replace the `backend not in (...)` early return with `if not ollama_in_use(): return`; log text uses `claude.backend=%s` only for context ("an Ollama fallback is configured"). `healthcheck.py`: `if ollama_in_use(): probe…print OK/WARN` else "not used".
- [x] **Step 3: config.** `config/research.yaml` `summary.backend: "claude_cli_then_ollama"`; private `config/settings.yaml`: `backend: "cli_then_ollama"` and replace the 5-line comment above it with: *"2026-10-15: claude -p first, Ollama when it fails for any reason except a timeout (a usage limit fails in 1-4 s, so it costs the cycle nothing). A timeout never falls back: CLI 120 s x 2 + Ollama 300 s would blow the 15-min cycle; the deterministic list ships unreviewed instead."*; private `config/news.yaml` `llm.backend: cli_then_ollama`; private `config/spreads.yaml` add `ollama_fallback: true` under `ai:`; examples: `news.yaml` `llm: {backend: cli_then_ollama, …}`, `spreads.yaml` add `ollama_fallback: true  # …`, `settings.yaml` comment above `backend:` recommends `cli_then_ollama` (value stays `"ollama"`).
- [x] **Step 4: docs** (grep for the existing anchor, then edit): `ARCHITECTURE.md` — `src/claude/` (`cli.py` now `should_fall_back`/`run_ollama`; runner outcome), `src/research/summary/` (`chain.py`), `src/spreads_ai/` (third step), config section (`spreads.ai.ollama_fallback`, `research.summary.backend` value); `SETUP.md` — §14 (the rule, timeouts excluded, restart), §16 spreads paragraph (third step + `ollama_fallback`), the summary-backend paragraph and its troubleshooting row; `STATUS.md` — built entry + limitations (Ollama picks are a weaker model, recorded as `ollama:<model>`; an Ollama-written summary stays cached 24 h; no cooldown, a limited CLI is retried each call).
- [x] **Step 5: gate** `python -m pytest -q && ruff check . && ruff format --check . && mypy src` — all green (fix anything red; `ruff format` the touched files).
- [x] **Step 6:** tick this plan's boxes, fill the Progress log (commits, gate result, rulings), commit `feat: ollama fallback for every AI call — config, probe, docs`.
