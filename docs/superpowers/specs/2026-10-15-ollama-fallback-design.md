# Ollama fallback for every `claude -p` call — design

Date: 2026-10-15 · Status: approved in conversation, awaiting written-spec review
Builds on: `src/claude/runner.py` (`claude.backend`), `src/news/llm.py`, `src/research/summary/`,
`src/spreads_ai/` (`docs/superpowers/specs/2026-10-12-spreads-claude-picker-design.md`)

## 1. Intent

The operator regularly uses up the 5-hour and weekly `claude -p` limits. When that happens every
AI feature goes dark at once. They want **every AI call to fall back to the local Ollama model
whenever `claude -p` cannot answer**, so the features keep working (on a weaker model) until the
limit resets.

**Success:** with `claude -p` failing the way a usage limit makes it fail, the wheel's strategist
review, roll review and EOD journal, the news explanations, the ticker-page summary and the
spreads picker all still produce output from Ollama, with no config edit and no restart at the
moment the limit is hit. Each result says which model wrote it.

**Not a goal:** making Ollama as good as Claude, or changing what any AI output is allowed to
influence (§6).

## 2. What exists today

| Path | Where | Ollama fallback today |
|---|---|---|
| Strategist review, roll review, EOD journal | `src/claude/runner.py` dispatchers | `claude.backend: cli_then_ollama` exists; **live config is `cli`** |
| News explanations | `src/news/llm.py::call_llm` | `news.llm.backend: cli_then_ollama` exists; **ships `cli`** |
| Ticker-page AI summary | `src/research/summary/` | none — one backend at a time |
| Spreads picker (day plan + pick) | `src/spreads_ai/picker.py`, `src/claude/cli.py` | none — Opus→Sonnet retry, then the baseline pick |

The live `settings.yaml` rejects `cli_then_ollama` because a CLI that **hangs** (120 s × 2
attempts = 240 s) plus an Ollama fallback (up to 300 s) overruns the 15-minute scan cycle. A
usage limit is not a hang: SETUP.md §16 records an Opus limit failing in a second or two. The
existing fallback cannot tell the two apart — every dispatcher sees only "the CLI returned
nothing".

No real usage-limit output from the CLI is recorded anywhere in the repo (the tests use fakes),
so **the design keys on how the call ended, never on the limit message text.**

## 3. The rule

A CLI call ends in one of these. They reuse `CliResult.error` from `src/claude/cli.py`:

| `error` | Meaning | Falls back? |
|---|---|---|
| `None` | a parsed reply | no — nothing failed |
| `timeout` | the CLI hung past its budget | **no** — the budget is spent (see below) |
| `cli_missing` | binary not found / not executable | yes |
| `cli_error` | non-zero exit, `is_error` envelope, or empty output (a usage limit, auth expiry, overload) | yes |
| `bad_envelope` | exit 0 but the reply did not parse | yes |
| `disabled` | `claude.enabled: false` | no — the operator turned Claude off; `ollama_runner` also returns nothing when disabled |

**Fall back to Ollama on every failure except `timeout` and `disabled`.** One helper owns the rule:

```python
# src/claude/cli.py — imports nothing from src/
def should_fall_back(error: str | None) -> bool:
    return error is not None and error not in ("timeout", "disabled")
```

Why timeouts are excluded: they are what overruns the scan cycle, and on the other paths they
have already used the call's whole window (a spreads pick has 45 s; a ticker-page summary is
triggered live from a page load and should fail fast). This is **uniform across all four paths.**

Two consequences to know about:

- News' existing `cli_then_ollama` also fell back on a timeout. Under the uniform rule it no
  longer does.
- A `cli_error` that is a transient network blip also falls back. That is intended: the local
  model is the retry.

**Retries are unchanged.** The wheel's `max_retries` loop still retries a refusal (about 2 s per
spawn). Dropping it would change plain-`cli` behaviour for no real gain.

## 4. Per-path design

### 4.1 Wheel — `src/claude/runner.py`

The CLI helpers currently return only the parsed value, which hides *why* a call failed. Each
gets an outcome-reporting sibling; the old name stays as a thin wrapper so existing callers and
tests keep their seam:

- `_run_cli_outcome(...) -> tuple[T | None, str | None]` — the current loop, additionally
  tracking the failure kind. **A timeout in any attempt makes the outcome `timeout`** (the budget
  is spent, whatever the last attempt did); otherwise the last attempt's kind decides. `_run_cli`
  becomes `return _run_cli_outcome(...)[0]`.
- `_review_candidates_cli_outcome`, `_review_roll_cli_outcome`,
  `_write_journal_narrative_cli_outcome` — same shape. `_review_candidates_cli` and friends
  remain as wrappers (`tests/test_claude.py` imports `_review_candidates_cli` directly).
- The three dispatchers (`review_candidates`, `review_roll`, `write_journal_narrative`) call the
  outcome variants. For `backend == "cli_then_ollama"` they fall back when
  `should_fall_back(error)`. `backend == "ollama"` and `"cli"` are unchanged.
- The fallback logs one `WARNING`: `claude unavailable (<error>) — using ollama`.

The existing sync loops map onto the §3 vocabulary like this: `claude.enabled: false` →
`disabled`; `FileNotFoundError` → `cli_missing`; `TimeoutExpired` → `timeout`; non-zero exit
(with or without stdout), or an `is_error` envelope → `cli_error`; exit 0 with a parse of `None`
→ `bad_envelope`.

### 4.2 News — `src/news/llm.py`

`_cli` calls `runner._run_cli_outcome` and returns `(text, error)`. In `call_llm`, the loop moves
from the `cli` backend to `ollama` when `should_fall_back(error)`. Every attempt still counts
toward `news.llm.max_calls_per_day`, so a flapping CLI stays visible in `news_state` and
`GET /news/status`. `LlmResult.backend` already records who answered.

### 4.3 Ticker-page summary — `src/research/summary/`

- `research.summary.backend` accepts a fifth value, **`claude_cli_then_ollama`**
  (`ResearchSummaryCfg._known_backend`).
- `ClaudeCliSummaryProvider` gains `generate_with_error(ctx) -> tuple[Summary | None, str | None]`;
  `generate` returns its first element, so the single-backend behaviour is unchanged.
- A small chain provider (in `factory.py`'s neighbourhood) calls the CLI provider and, when the
  summary is `None` and `should_fall_back(error)`, calls the existing `OllamaSummaryProvider`.
  `get_summary_provider` returns it for the new value.
- **Attribution:** the provider's self-reported `Summary.model` is already shown on the panel, so
  an Ollama-written summary says `qwen3.5:4b`. The cache key stays config-derived (existing
  contract in `service._provider_model_name`), so an Ollama-written summary is cached under the
  same key as a Claude one and stays "ready" for `cache_ttl_hours` (24 h) after the limit
  resets. Accepted: the Generate button regenerates it on demand. No cache-key change.

### 4.4 Spreads picker — `src/claude/cli.py`, `src/spreads_ai/picker.py`

`src/spreads_ai/` may import only `src.claude.cli`, and `cli.py` imports nothing from `src/` (the
caller passes every setting). The Ollama call therefore lives in `cli.py` and the fence test
(`assert claude == ["src.claude.cli"]`) is untouched.

- **`run_ollama`** in `cli.py`: an async `httpx.AsyncClient` POST to `/api/generate` with
  `format: <schema>`, `stream: false`, `think: false`, plus `keep_alive`, `temperature` and
  `num_ctx` passed in. It returns a `CliResult` (`error`: `None`, `timeout`, `cli_error` for
  connect/HTTP failures, `bad_envelope` for a malformed body) and **never raises** except
  `CancelledError`. A small frozen dataclass `OllamaSettings(host, model, keep_alive,
  temperature, num_ctx)` carries the settings.
- **`ClaudePicker._call`** gains a `schema` argument and a third step: after the existing Opus
  call and the Sonnet retry, if `should_fall_back(res.error)`, `self.ollama` is set and at least
  `_MIN_FALLBACK_SECONDS` (15 s) of the timeout remains, it calls `run_ollama` with what is left.
  `ClaudePicker.from_config` builds `OllamaSettings` from `cfg.claude.ollama_*` when
  `cfg.spreads.ai.ollama_fallback` is true.
- **Schemas:** pick → `{choice: string, reason: string}` (both required); day plan → the
  `SpreadDayPlan` shape (`bias` enum `bullish|neutral|bearish`, `risk_flags`, `skip_conditions`,
  `preferred_distance`, `summary`). `parse_pick` / `parse_day_plan` are unchanged: the reply is
  parsed and shape-checked exactly as a Claude reply is.
- **Attribution:** the stored `SpreadLlmCall.model` is `ollama:<model>` and `effort` is `""`, so
  `scripts.spreads_report --compare` (which already splits decisions by model) groups Ollama's
  picks separately from Claude's. PICK / DAY PLAN records show who answered.
- **Failure:** if Ollama also fails, the picker returns `skip` with a `fallback_reason`, and the
  service trades the baseline item exactly as it does today. `max_pick_calls_per_day` is
  unchanged — the fallback is part of one decision.
- **Off-switch:** `spreads.ai.ollama_fallback: bool = True` in `SpreadsAiCfg`.

## 5. Configuration and rollout

New or changed keys (committed examples first; private copies are git-ignored):

| Key | Change |
|---|---|
| `spreads.ai.ollama_fallback` | **new**, default `true` — `config/examples/spreads.yaml` and the private `config/spreads.yaml` |
| `research.summary.backend` | new allowed value `claude_cli_then_ollama` — `config/research.yaml` (committed) is set to it |
| `claude.backend` | private `config/settings.yaml` set to `cli_then_ollama`; its comment (the budget argument against it) rewritten to say limits fall back and timeouts do not |
| `news.llm.backend` | private `config/news.yaml` set to `cli_then_ollama`; the `NewsLlmCfg` default comment ("claude -p only, operator preference 2026-10-14") updated |
| `config/examples/settings.yaml`, `config/examples/news.yaml` | the documented recommended value becomes `cli_then_ollama` |

**Startup warning.** `scripts/start.py::_check_ollama` and `scripts/healthcheck.py` probe Ollama
only when `claude.backend` uses it. They will probe whenever **any** chain includes Ollama
(`claude.backend`, `news.llm.backend`, `research.summary.backend`, or
`spreads.ai.enabled and spreads.ai.ollama_fallback`), and warn when `ollama serve` is down or the
model is not pulled. It stays a warning, never fatal.

**Restart.** Daemons do not hot-reload. The operator restarts `./ibkr` after the config edit; the
final report says so rather than doing it.

**Prerequisite.** `ollama serve` running with `claude.ollama_model` (`qwen3.5:4b`) pulled — already
documented in SETUP.md §14.

## 6. Safety and fences

- The Rules Engine remains the only path to an order. Nothing here touches `engine/`,
  `execution/`, `strategies/`, sizing or the spreads gate. Ollama output is enrichment: a review,
  a roll opinion, a journal paragraph, a news explanation, a summary, and — for spreads — a
  **letter from the same gate-approved menu** that the service validates and re-gates on a fresh
  quote before any order, exactly as for a Claude reply. An off-menu letter from Ollama maps to
  the baseline item.
- `src/claude/cli.py` still imports nothing from `src/`; it gains `httpx` (third-party, already a
  dependency). `src/spreads_ai/` still imports only `src.claude.cli`.
- `tests/test_spreads_fence.py`, `tests/test_eval_skills.py`, `tests/test_news_fence.py` and
  `tests/test_web_fence.py` stay green and unmodified in intent.
- No new state file, no new table, no new Telegram message.

## 7. Testing

- **`should_fall_back`:** every `error` value in the §3 table.
- **`_run_cli_outcome`:** limit-shaped failure (non-zero exit with an `is_error` envelope) →
  `cli_error`; missing binary → `cli_missing`; one timeout and one refusal → `timeout`; exit 0
  with garbage → `bad_envelope`; success → `None`. `_run_cli` still returns only the value.
- **Wheel dispatchers:** `cli_then_ollama` + `cli_error` → Ollama runs; + `timeout` → Ollama
  does not run; + success → Ollama does not run; `cli` and `ollama` backends unchanged.
- **News:** `call_llm` falls to Ollama on `cli_error`, not on `timeout`; both attempts count
  toward the daily cap; `LlmResult.backend` is `ollama`.
- **Summary:** the chain returns Ollama's summary on `cli_error`, none on `timeout`; the
  validator accepts the new value and still rejects an unknown one.
- **`run_ollama`:** success, timeout, connection refused, malformed body — all return a
  `CliResult`, none raise; cancellation propagates.
- **Picker:** Opus fails → Sonnet fails → Ollama answers (call record `ollama:<model>`);
  under 15 s left → no Ollama call; `ollama_fallback: false` → no Ollama call; Ollama also fails
  → `skip` + `fallback_reason`; an off-menu Ollama letter is still rejected by the service.
- **Probe:** `_check_ollama` probes when only `news.llm.backend` (or the summary, or spreads)
  uses Ollama.
- **Existing seams to update:** `tests/test_news_llm.py` monkeypatches `runner._run_cli`;
  `tests/test_roll_review_proposal.py` patches `_run_cli`. They move to the outcome variant.
- Full gate: `python -m pytest -q`, `ruff check .`, `mypy src`.

## 8. Documentation

Per the CLAUDE.md trigger table: `ARCHITECTURE.md` (config section; `src/claude/`,
`src/research/summary/`, `src/spreads_ai/` entries), `SETUP.md` (§14 Ollama — the new rule and
the rewritten backend note; §16 spreads — the third fallback step and `ollama_fallback`; the
summary-backend paragraph and its troubleshooting row), `STATUS.md` (built / known limitations:
Ollama picks are a weaker model; a summary written by Ollama stays cached for 24 h),
`config/examples/*.yaml`, and `How the scan works.md` only if the scan loop's behaviour text
changes (it should not).

## 9. Rulings recorded here

1. **Timeouts never fall back**, on all four paths (user approved the uniform rule).
2. **Retries are kept**, replacing the earlier "skip retries on a refusal" idea.
3. **No shared cooldown** (approach 3 was declined): a limited CLI is re-tried on every call at
   about 1–4 s per call. Revisit only if that proves costly or noisy.
4. **Spreads is included**, behind `spreads.ai.ollama_fallback` (user choice).

## 10. Open assumptions to verify

- A real usage-limit failure surfaces as a non-zero exit or an `is_error` envelope (SETUP.md §16
  says it does for an Opus limit). The first real limit event confirms it; the design does not
  depend on the message text.
- `qwen3.5:4b` can answer the spreads pick schema inside a ~40 s window, including a cold model
  load. The plan measures this against a real pick prompt before the feature is enabled.
