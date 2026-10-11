# Roll Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the wheel's roll subsystem produce correct, evidence-based roll / assign / close decisions end to end: breach- and ex-dividend-triggered, credit-floored, same-or-better strike, limited to one roll per chain, priced from a targeted fetch, shown in full on the approval card, and executed against the exact alerted contract.

**Architecture:** A pure decision layer (`src/strategies/roll_policy.py` + a rewritten `src/strategies/rolling.py`) turns a position, its live quote and a small targeted chain into a `RollDecision`. `src/execution/roll_pipeline.py` orchestrates: targeted fetch → decision → decision-time Rules Engine pass → PENDING approval. The intraday monitor gates every alert to RTH (+15 min), keeps the timers as information-only, and re-evaluates breached positions every 30 min. The executor resolves the short by conId, applies the same `RollCfg` floor as the generator, and walks the combo toward the natural price within that floor.

**Tech Stack:** Python 3.12, ib_async, Pydantic v2, SQLAlchemy/SQLite, python-telegram-bot, pytest.

**Spec:** `docs/research/2026-10-11-rolling-short-options.md` (research report) — redesign §"A deterministic roll policy the Rules Engine can own" and the 15-row roadmap. Operator rulings 2026-10-11 override the report's defaults where they differ (see Global Constraints).

## Global Constraints

- The Rules Engine (`src/engine/risk_engine.py`) stays the only path to an order; no LLM output reaches a roll decision, candidate, gate or size. Claude only annotates.
- Every roll still needs a human tap (and the LIVE `[CONFIRM LIVE]` tap); a CLOSE decision needs a tap too.
- Operator ruling: `roll.csp.when_assignable: roll_if_credit` — a breached would-own CSP is rolled for a net credit when one exists; assignment is the fallback.
- Operator ruling: `roll.cc.keep_shares: true` — a breached covered call is rolled up-and-out, allowing a debit up to `roll.cc.max_debit` ($0.25/sh); letting it be called away is the fallback when strike ≥ adjusted basis.
- Operator ruling: the 21-DTE (`manage_dte`) and 7-DTE (`dte`) timers, `delta_drift`, `iv_spike`, `assignment_risk` and the non-leveraged `loss_multiple` line are **information-only alerts** — no roll proposal, no Approve button.
- Leveraged ETFs (`universe.yaml → leveraged_etfs`) never roll; the 2× auto-buyback stays their exit.
- Every threshold lives in `config/settings.yaml → roll:` (template `config/examples/settings.yaml`); nothing learned may move it (eval fence).
- Roll chain-fetch must fit the monitor's reserved lines: batch ≤ `roll.construct.max_quote_lines` (10). No new line budget.
- `req_fresh_mkt_data` only; `LimitOrder` only; BAG combo never legged.
- Quality gate per task: `python -m pytest -q`, `ruff check .`, `ruff format --check` on touched files, `mypy src`.
- Docs per CLAUDE.md trigger table; STATUS.md entry; keep this plan's Progress log current.

## Review Focus

1. **Two shorts on the same underlying and right** (GOOGL 330P + 335P) — the executor must buy back the alerted contract (conId), never the nearest-dated one. Test in Task 9.
2. **An ITM short and a short at ≤ 6 DTE** — the targeted fetch must price the alerted contract itself even though it is ITM / outside the entry window. Test in Task 4.
3. **A debit roll approved, then re-gated** — the generator and executor must agree (CC keep-shares debit within cap passes both; a CSP debit fails both). Test in Task 9.
4. **Triggers outside RTH or in the first 15 minutes** — no evaluation, no message; retried on the next eligible cycle. Test in Task 10.
5. **A position already rolled once** — a second roll is refused at construction and in the Rules Engine; profit-take measures the chain credit, not the new leg's gross premium. Tests in Tasks 3, 5, 7.

---

## File structure

| File | Responsibility |
|---|---|
| `src/common/config.py` | `RollCfg` (+ nested models); `Config.roll`; remove `MonitorCfg.roll_defensive` |
| `config/examples/settings.yaml` | `roll:` block; delete `monitor.roll_defensive` |
| `config/examples/risk_limits.yaml` | `events.ex_dividend_assignment_guard` now read (roll ex-div trigger master switch) |
| `src/common/schemas.py` | `PositionSnapshot.con_id`, `FundamentalStats.dividend_per_share`, `RollOrigin`, `TradeCandidate.roll_from`, `RollDecision`, `CloseReason.DEFENSIVE` |
| `src/ibkr/portfolio.py` | populate `con_id` |
| `src/analytics/fundamentals.py` | populate `dividend_per_share` |
| `src/storage/roll_chains.py` (new) | read-only chain state + chain net credit from CandidateRow/FillRow |
| `src/execution/profit_take.py` | profit-take / loss line on chain credit |
| `src/ibkr/market_data.py` | `get_roll_chain_quotes_async` targeted fetch |
| `src/strategies/rolling.py` (rewrite) | `construct_roll` — lexicographic candidate construction with reason codes |
| `src/strategies/roll_policy.py` (new) | `roll_trigger` + `decide` decision tree |
| `src/engine/risk_engine.py` | roll scoping: IV floors skipped, roll earnings rule, roll limits |
| `src/execution/roll_pipeline.py` | `evaluate_roll` orchestration, decision-time gate, approval queueing |
| `src/execution/roll_executor.py` | conId resolution, size check, shared floor, bounded reprice walk, campaign attach |
| `src/monitor/intraday.py` / `src/monitor/triggers.py` | RTH gate, info-only timers, breach/ex-div evaluation loop |
| `src/notify/formatters.py` / `src/notify/approval_service.py` | `format_roll_decision`; `close_short:` callback |
| `src/claude/prompts/roll.py` / `src/claude/runner.py` / `src/claude/ollama_runner.py` | pass the proposal text to the reviewer |
| `src/notify/command_drain.py` | `roll_request` through `evaluate_roll(manual=True)` |
| `src/backtest/roll_arms.py` (new), `scripts/roll_backtest.py` (new) | offline assign / roll / close comparison |

---

### Task 1: Roll config block

**Files:**
- Modify: `src/common/config.py` (MonitorCfg ~522-547, Config ~1086, loader ~1246)
- Modify: `config/examples/settings.yaml` (monitor block ~450-478)
- Test: `tests/test_roll_config.py` (new)

**Interfaces:**
- Produces: `RollCfg` with `.trigger.breach_delta: float`, `.trigger.evaluate_within_dte: int`, `.trigger.min_extrinsic: float`, `.trigger.min_minutes_after_open: int`, `.trigger.reevaluate_minutes: int`, `.ex_div.days_ahead: int`, `.ex_div.buffer: float`, `.csp.when_assignable: Literal["roll_if_credit","assign"]`, `.cc.keep_shares: bool`, `.cc.max_debit: float`, `.construct.max_expiries: int`, `.construct.target_dte_max: int`, `.construct.strikes_outward: int`, `.construct.max_quote_lines: int`, `.construct.min_net_credit: float`, `.limits.max_rolls_per_chain: int`, `.limits.max_extension_days: int`, `.exec.reprice_steps: int`; `get_config().roll`.

- [ ] **Step 1: Failing test** — `tests/test_roll_config.py`:

```python
from pydantic import ValidationError
import pytest
from src.common.config import RollCfg, get_config

def test_example_config_carries_the_operator_rulings() -> None:
    r = get_config().roll
    assert r.csp.when_assignable == "roll_if_credit"
    assert r.cc.keep_shares is True and r.cc.max_debit == 0.25
    assert r.limits.max_rolls_per_chain == 1
    assert r.construct.max_quote_lines <= 20  # fits the monitor's reserved lines

def test_defaults_are_conservative() -> None:
    r = RollCfg()
    assert r.csp.when_assignable == "assign" and r.cc.keep_shares is False

@pytest.mark.parametrize("bad", [{"trigger": {"breach_delta": 1.2}}, {"construct": {"min_net_credit": -0.1}},
                                 {"csp": {"when_assignable": "maybe"}}, {"limits": {"max_rolls_per_chain": -1}}])
def test_bad_values_fail_at_load(bad: dict) -> None:
    with pytest.raises(ValidationError):
        RollCfg(**bad)

def test_monitor_roll_defensive_is_gone() -> None:
    assert not hasattr(get_config().monitor, "roll_defensive")
```

- [ ] **Step 2:** `python -m pytest tests/test_roll_config.py -q` → FAIL (no `RollCfg`).
- [ ] **Step 3: Implement** in `config.py` above `MonitorCfg`:

```python
class RollTriggerCfg(BaseModel):
    breach_delta: float = Field(0.50, gt=0, lt=1)  # |Δ| at/above which a short counts as breached
    evaluate_within_dte: int = Field(10, ge=0)  # breach is acted on only at/inside this DTE …
    min_extrinsic: float = Field(0.10, ge=0)  # … or once extrinsic ($/sh) is this thin
    min_minutes_after_open: int = Field(15, ge=0)
    reevaluate_minutes: int = Field(30, ge=1)

class RollExDivCfg(BaseModel):
    days_ahead: int = Field(5, ge=0)
    buffer: float = Field(0.05, ge=0)  # extrinsic must exceed dividend + buffer

class RollCspCfg(BaseModel):
    when_assignable: Literal["roll_if_credit", "assign"] = "assign"

class RollCcCfg(BaseModel):
    keep_shares: bool = False
    max_debit: float = Field(0.25, ge=0)  # $/sh, read only when keep_shares

class RollConstructCfg(BaseModel):
    max_expiries: int = Field(3, ge=1)
    target_dte_max: int = Field(35, ge=1)
    strikes_outward: int = Field(5, ge=0)
    max_quote_lines: int = Field(10, ge=2, le=40)
    min_net_credit: float = Field(0.05, ge=0)

class RollLimitsCfg(BaseModel):
    max_rolls_per_chain: int = Field(1, ge=0)
    max_extension_days: int = Field(28, ge=0)

class RollExecCfg(BaseModel):
    reprice_steps: int = Field(3, ge=0)

class RollCfg(BaseModel):
    """Roll policy (2026-10-11 redesign). Human-edited; nothing learned may move it."""
    trigger: RollTriggerCfg = Field(default_factory=RollTriggerCfg)
    ex_div: RollExDivCfg = Field(default_factory=RollExDivCfg)
    csp: RollCspCfg = Field(default_factory=RollCspCfg)
    cc: RollCcCfg = Field(default_factory=RollCcCfg)
    construct: RollConstructCfg = Field(default_factory=RollConstructCfg)
    limits: RollLimitsCfg = Field(default_factory=RollLimitsCfg)
    exec: RollExecCfg = Field(default_factory=RollExecCfg)
```

Delete `roll_defensive` from `MonitorCfg`; fix the stale "Entries are 21-45 DTE" comment on `manage_at_dte`. Add `roll: RollCfg = Field(default_factory=RollCfg)` to `Config` and `roll=RollCfg(**settings.get("roll", {}))` in the loader. In `config/examples/settings.yaml` replace `monitor.roll_defensive` with a top-level `roll:` block carrying the operator rulings (`csp.when_assignable: roll_if_credit`, `cc.keep_shares: true`), every key commented with its evidence grade (E/C/I) from the report.

- [ ] **Step 4:** Run the test + `grep -rn roll_defensive src tests` — callers fail to type-check until Task 5 rewrites `rolling.py`; leave `rolling.py` reading `get_config().roll` defaults temporarily (`roll_cfg = {}`) so the suite stays green.
- [ ] **Step 5:** Commit `feat(roll): roll config block (Task 1)`.

### Task 2: Schemas — conId, dividend amount, roll origin, roll decision

**Files:**
- Modify: `src/common/schemas.py`, `src/ibkr/portfolio.py:125-150`, `src/analytics/fundamentals.py:66-90`
- Test: `tests/test_roll_schemas.py` (new)

**Interfaces:**
- Produces:
  - `PositionSnapshot.con_id: int | None = None`
  - `FundamentalStats.dividend_per_share: float | None = None` (next cash dividend $/sh)
  - `CloseReason.DEFENSIVE = "defensive"` (operator-tapped close from a roll decision)
  - `RollOrigin(BaseModel)`: `con_id: int | None`, `candidate_id: str | None`, `strike: float`, `expiry: date`, `right: OptionRight`, `contracts: int`, `chain_id: str`, `seq: int`, `original_expiry: date`, `old_mid: float`, `new_mid: float`, `allow_debit: bool = False`
  - `TradeCandidate.roll_from: RollOrigin | None = None`
  - `RollAction = Literal["roll","assign","let_called_away","close","hold","defer"]`; `RollDecision(BaseModel)`: `action: RollAction`, `reason: str`, `candidate: TradeCandidate | None = None`, `rejections: dict[str, int] = {}`, `detail: str = ""`

- [ ] **Step 1: Failing tests**: `RollOrigin` round-trips through `TradeCandidate.model_dump(mode="json")`/`model_validate`; a `TradeCandidate` without `roll_from` validates (old snapshots); `get_positions` maps `item.contract.conId` to `con_id` (MagicMock portfolio item); `get_fundamental_stats` maps `lastDividendValue` → `dividend_per_share`, falling back to `dividendRate / 4`, `None` when neither.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement.** In `portfolio.py` add `con_id=int(c.conId) if getattr(c, "conId", 0) else None`. In `fundamentals.py` (non-ETF branch):

```python
last_div = _safe_float(info.get("lastDividendValue"))
rate = _safe_float(info.get("dividendRate"))
dividend_per_share = last_div if last_div and last_div > 0 else (rate / 4 if rate and rate > 0 else None)
```

- [ ] **Step 4:** run → PASS; regenerate `docs/web/openapi.json` + `web/lib/api-types.ts` (`TradeCandidate`/`PositionSnapshot` reach the API).
- [ ] **Step 5:** Commit `feat(roll): schemas for roll origin, decision, conId, dividend (Task 2)`.

### Task 3: Roll chain state and chain-credit profit-take

**Files:**
- Create: `src/storage/roll_chains.py`
- Modify: `src/execution/profit_take.py` (`check_profit_takes`, `check_loss_exits`), `src/monitor/intraday.py::_load_entry_credit`
- Test: `tests/test_roll_chains.py` (new)

**Interfaces:**
- Consumes: `RollOrigin` (Task 2) stored in `CandidateRow.payload["roll_from"]`.
- Produces:
  - `RollChainState(seq: int, chain_id: str, original_expiry: date, current_candidate_id: str | None)` (frozen dataclass)
  - `chain_state(session, pos: PositionSnapshot) -> RollChainState`
  - `chain_entry_credit_per_share(session, pos: PositionSnapshot) -> float | None`

- [ ] **Step 1: Failing tests** (isolated `db` fixture): (a) a plain CSP → `seq 0`, `chain_id == its candidate id`, `original_expiry == pos.expiry`, chain credit == `net_entry_credit_per_share`; (b) a rolled short whose candidate payload carries `roll_from(seq=1, candidate_id="c-old", chain_id="c-old", original_expiry=...)`, with fills SELL c-old 1@1.00, BUY c-old 1@3.00 (close_reason roll), SELL c-new 1@3.20 → `seq 1`, chain credit = (1.00 − 3.00 + 3.20 − commissions/100) = 1.20 − comm; (c) a position with no system candidate → `seq 0`, synthetic `chain_id`, `chain_entry_credit_per_share is None`; (d) `check_profit_takes` on (b) at mid 0.50 closes (1 − 0.50/1.20 ≥ 50%) while the leg-only basis (3.20) would have closed at 1.60.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement** `src/storage/roll_chains.py`:

```python
"""Roll-chain bookkeeping read from candidates + fills (2026-10-11 roll redesign). Read-only.

A roll's new candidate carries `payload["roll_from"]` (a RollOrigin) naming the short it closed,
so a chain is walked backwards through candidate ids. No table of its own: the chain is derived.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.common.schemas import PositionSnapshot, RollOrigin
from src.storage.models import CandidateRow, FillRow

_MAX_WALK = 20  # a malformed self-referencing payload must not loop forever

@dataclass(frozen=True)
class RollChainState:
    seq: int
    chain_id: str
    original_expiry: date
    current_candidate_id: str | None

def _sold_candidate(session: Session, pos: PositionSnapshot) -> CandidateRow | None:
    assert pos.strike is not None and pos.expiry is not None and pos.right is not None
    rows = session.execute(
        select(CandidateRow).join(FillRow, FillRow.candidate_id == CandidateRow.candidate_id)
        .where(CandidateRow.underlying == (pos.underlying or pos.symbol),
               CandidateRow.right == pos.right.value, CandidateRow.expiry == pos.expiry,
               FillRow.action == "SELL")
        .order_by(FillRow.filled_at.desc())
    ).scalars().all()
    return next((c for c in rows if abs((c.strike or 0.0) - pos.strike) < 1e-3), None)

def _origin(row: CandidateRow) -> RollOrigin | None:
    raw = (row.payload or {}).get("roll_from")
    return RollOrigin.model_validate(raw) if raw else None

def chain_state(session: Session, pos: PositionSnapshot) -> RollChainState:
    assert pos.expiry is not None
    row = _sold_candidate(session, pos)
    if row is None:
        synthetic = f"chain:{pos.underlying or pos.symbol}:{pos.expiry:%Y%m%d}:{pos.strike:g}"
        return RollChainState(0, synthetic, pos.expiry, None)
    origin = _origin(row)
    if origin is None:
        return RollChainState(0, row.candidate_id, pos.expiry, row.candidate_id)
    return RollChainState(origin.seq, origin.chain_id, origin.original_expiry, row.candidate_id)

def chain_entry_credit_per_share(session: Session, pos: PositionSnapshot) -> float | None:
    """Net credit per share collected over the whole chain (all SELLs − all BUYs − commissions),
    spread over the current position's contracts. None when the short has no system SELL fill."""
    row = _sold_candidate(session, pos)
    if row is None:
        return None
    ids: list[str] = []
    cur: CandidateRow | None = row
    while cur is not None and len(ids) < _MAX_WALK and cur.candidate_id not in ids:
        ids.append(cur.candidate_id)
        origin = _origin(cur)
        cur = session.get(CandidateRow, origin.candidate_id) if origin and origin.candidate_id else None
    fills = session.execute(select(FillRow).where(FillRow.candidate_id.in_(ids))).scalars().all()
    dollars = sum((-1 if f.action == "BUY" else 1) * f.avg_price * f.filled_qty * 100 for f in fills)
    dollars -= sum(f.commission or 0.0 for f in fills)
    qty = sum(f.filled_qty for f in fills if f.action == "SELL" and f.candidate_id == row.candidate_id)
    if qty <= 0:
        return None
    per_share = dollars / (qty * 100)
    return per_share if per_share > 0 else None
```

(`CandidateRow` primary key is `candidate_id` — confirm with `session.get`; otherwise query by column.) In `profit_take.py` replace the `net_entry_credit_per_share(...)` calls in both checks with `chain_entry_credit_per_share(s, pos)` (fall back to `net_entry_credit_per_share` only when that returns None for a non-roll — identical for seq 0). Same in `intraday._load_entry_credit`.

- [ ] **Step 4:** run → PASS; `tests/test_loss_exits.py`, `tests/test_profit_take_schedule.py` still pass (they patch `net_entry_credit_per_share` — update their patch targets to `chain_entry_credit_per_share`).
- [ ] **Step 5:** Commit `feat(roll): chain state + chain-credit profit-take (Task 3)`.

### Task 4: Targeted roll fetch

**Files:**
- Modify: `src/ibkr/market_data.py` (new function after `get_option_chain_quotes_async`)
- Modify: `src/execution/roll_pipeline.py::fetch_roll_inputs`
- Test: `tests/test_roll_fetch.py` (new)

**Interfaces:**
- Produces: `async def get_roll_chain_quotes_async(ib, pos: PositionSnapshot, *, max_expiries: int, target_dte_max: int, strikes_outward: int, batch_size: int) -> list[OptionQuote]` — the alerted contract (any moneyness, any DTE) plus `pos.right` contracts at the next `max_expiries` listed expirations after `pos.expiry` with DTE ≤ `target_dte_max`, at the current strike and the next `strikes_outward` listed strikes **away from the money** (lower for puts, higher for calls). Batched at `batch_size`.
- Produces: `fetch_roll_inputs(ib, pos) -> tuple[list[OptionQuote], IVStats, TechnicalStats, FundamentalStats]` (adds fundamentals; signature change ripples to command_drain and the monitor in Tasks 8/10/13).

- [ ] **Step 1: Failing tests** with a mocked IB (follow the `qualify_options_async` / `_batch_quotes_async` mocking in `tests/test_market_data*.py`): (a) a put at strike 335 with spot 320 (ITM) and 5 DTE → the built contracts include `(pos.expiry, 335, P)`; (b) strikes for a put are `[335, 330, 325, …]` (≤ 335) and for a call `≥ strike`; (c) no expiration ≤ `pos.expiry` other than the position's own, at most `max_expiries` later ones, none beyond `target_dte_max`; (d) total contracts ≤ `1 + max_expiries × (strikes_outward + 1)`; (e) `_batch_quotes_async` is called with `batch_size`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement** a pure builder `_roll_contract_specs(chain, pos, today, *, max_expiries, target_dte_max, strikes_outward) -> list[tuple[date, float]]` plus the async wrapper reusing `qualify_stock_async`, `ib.reqSecDefOptParamsAsync`, `_select_chain`, `build_option(..., trading_class)`, `qualify_options_async(chunk_size=batch_size, ...)`, `_batch_quotes_async(ib, qualified, batch_size, md.request_throttle_seconds)`, then the same BS-greeks fill as the scan (`_bs_fill_spot_async` + `_enrich_greeks_from_ibkr_iv`; skip the yfinance fallback — the roll path must stay fast). `fetch_roll_inputs` calls it with `cfg.roll.construct.*` and also loads `get_fundamental_stats(underlying)` in the executor.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat(roll): targeted roll chain fetch (Task 4)`.

### Task 5: Roll construction rewrite

**Files:**
- Rewrite: `src/strategies/rolling.py`
- Test: `tests/test_rolling_construct.py` (new; replaces the generator tests in `tests/test_roll_pipeline.py` that assert the old defensive/income branches)

**Interfaces:**
- Consumes: `RollCfg` (Task 1), `RollOrigin` (Task 2), `RollChainState` (Task 3).
- Produces:
  - `RollContext` (frozen dataclass): `position: PositionSnapshot`, `current: OptionQuote` (alerted leg), `spot: float | None`, `chain: RollChainState`, `closed_candidate_id: str | None`, `next_earnings: date | None`, `ex_div_date: date | None`, `dividend: float | None`, `allow_debit: bool`, `today: date`
  - `construct_roll(ctx, quotes, iv_stats, tech_stats, cfg: RollCfg) -> tuple[TradeCandidate | None, dict[str, int]]` — the chosen candidate (or None) and reason-code counts for every rejected quote.

- [ ] **Step 1: Failing tests** — build quotes with a helper `q(strike, expiry_days, bid, ask, delta)`:
  1. same-strike credit roll chosen when it is the only credit: short 335P @ mid 6.00 Δ−0.62, next week 335P mid 6.40 Δ−0.58 → candidate strike 335, premium 0.40, `roll_from.seq == 1`;
  2. most favourable strike wins inside the nearest expiry: next week 335P (+0.40) and 330P (+0.06) both ≥ floor 0.05 → 330;
  3. nearest expiry wins over a farther one with a better strike;
  4. debit roll rejected for a CSP (`net_below_floor`), accepted for a CC with `allow_debit` within 0.25, rejected beyond it;
  5. `|new Δ| > |old Δ|` rejected (`delta_increases`); new delta missing → `delta_missing`;
  6. new expiry on/after earnings → `earnings_before_expiry`;
  7. call with ex-div ≤ new expiry and new extrinsic < dividend + buffer → `ex_div_assignment_risk`;
  8. strike in the wrong direction (higher put / lower call) → `strike_worse`;
  9. `chain.seq >= max_rolls_per_chain` → `(None, {"roll_limit_reached": 1})`, no quotes inspected;
  10. extension beyond `original_expiry + max_extension_days` → `extension_cap`;
  11. current leg has no mid → `(None, {"current_unpriced": 1})`;
  12. contracts == `abs(position)`; `candidate_id` = `make_candidate_id(Strategy.ROLL, …)`; `next_earnings` set from ctx.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement** (keep the existing `ideal`/`ScoreCard` population for the card; drop `defensive`/`income` branches and the hard-coded 21/0.40 gate):

```python
def construct_roll(ctx, quotes, iv_stats, tech_stats, cfg):
    rej: Counter[str] = Counter()
    pos, cur = ctx.position, ctx.current
    if ctx.chain.seq >= cfg.limits.max_rolls_per_chain:
        return None, {"roll_limit_reached": 1}
    old_mid = cur.mid
    if old_mid is None or old_mid <= 0:
        return None, {"current_unpriced": 1}
    old_delta = abs(cur.delta) if cur.delta is not None else None
    floor = -cfg.cc.max_debit if ctx.allow_debit else cfg.construct.min_net_credit
    is_put = pos.right == OptionRight.PUT
    latest = ctx.chain.original_expiry + timedelta(days=cfg.limits.max_extension_days)
    by_expiry: dict[date, list[OptionQuote]] = defaultdict(list)
    for q in quotes:
        if q.right == pos.right and q.expiry > pos.expiry:
            by_expiry[q.expiry].append(q)
    for expiry in sorted(by_expiry):
        if expiry > latest:
            rej["extension_cap"] += len(by_expiry[expiry]); continue
        if (expiry - ctx.today).days > cfg.construct.target_dte_max:
            rej["dte_cap"] += len(by_expiry[expiry]); continue
        if ctx.next_earnings is not None and ctx.next_earnings <= expiry:
            rej["earnings_before_expiry"] += len(by_expiry[expiry]); continue
        # most favourable first: lowest put strike / highest call strike
        for q in sorted(by_expiry[expiry], key=lambda x: x.strike, reverse=not is_put):
            reason = _reject_reason(q, ctx, old_mid, old_delta, floor, cfg)
            if reason:
                rej[reason] += 1; continue
            return _candidate(q, ctx, old_mid, iv_stats, tech_stats), dict(rej)
    return None, dict(rej)
```

`_reject_reason` checks, in order: `strike_worse` (put strike > old / call strike < old), `unpriced` (mid None/≤0), `illiquid` (`passes_liquidity_gates`), `net_below_floor` (`q.mid - old_mid < floor`), `delta_missing`, `delta_increases` (`abs(q.delta) > old_delta + 1e-9`; when `old_delta` is None require strike strictly better), and for calls `ex_div_assignment_risk` (`ex_div_date` ≤ expiry and `dividend` known and `q.mid - max(0, spot - strike) < dividend + cfg.ex_div.buffer`). `_candidate` builds the `TradeCandidate(strategy=ROLL, premium=round(q.mid - old_mid, 4), roc_pct=0.0, annualized_yield_pct=0.0, next_earnings=ctx.next_earnings, roll_from=RollOrigin(con_id=pos.con_id, candidate_id=ctx.closed_candidate_id, strike=pos.strike, expiry=pos.expiry, right=pos.right, contracts=abs(int(pos.position)), chain_id=ctx.chain.chain_id, seq=ctx.chain.seq + 1, original_expiry=ctx.chain.original_expiry, old_mid=old_mid, new_mid=q.mid, allow_debit=ctx.allow_debit), …)` with breakeven = `strike − net` (put) / `strike + net` (call).

- [ ] **Step 4:** run → PASS; delete obsolete generator assertions in `tests/test_roll_pipeline.py` / `tests/test_drain_roll.py` that pin `defensive=True` behaviour (they are rewritten in Tasks 8/13).
- [ ] **Step 5:** Commit `feat(roll): lexicographic credit-floored roll construction (Task 5)`.

### Task 6: Decision tree and trigger

**Files:**
- Create: `src/strategies/roll_policy.py`
- Test: `tests/test_roll_policy.py` (new)

**Interfaces:**
- Consumes: `construct_roll`, `RollContext` (Task 5); `RollCfg`.
- Produces:
  - `roll_trigger(pos, quote, fund: FundamentalStats | None, cfg: RollCfg, *, ex_div_guard: bool, today: date) -> str | None` — `"strike_breach"`, `"ex_div"` or None.
  - `extrinsic(quote, spot) -> float | None`
  - `decide(ctx: RollContext, quotes, iv_stats, tech_stats, cfg: RollCfg, *, is_leveraged: bool, would_own: bool, cc_basis: float | None) -> RollDecision`

- [ ] **Step 1: Failing tests**:
  - trigger: put spot < strike & DTE 8 → breach; spot < strike & DTE 20 & extrinsic 1.50 → None (held: > `evaluate_within_dte` and extrinsic thick); DTE 20 but extrinsic 0.05 → breach; |Δ| 0.55 OTM-by-spot → breach (delta rule); call with ex-div in 3 days ≤ expiry and extrinsic 0.10 < dividend 0.24 + 0.05 → `"ex_div"`; same with `ex_div_guard=False` → None; puts never get `ex_div`.
  - decide: leveraged → `hold/leveraged_etf_no_roll`; CSP not would-own → `close/not_would_own`; CSP would-own with a credit roll → `roll`; CSP would-own no roll → `assign/<top rejection>`; CSP with `when_assignable="assign"` → `assign/assign_preferred` (construction not attempted); CC keep_shares with a roll → `roll` with `allow_debit` True; CC no roll, strike ≥ basis → `let_called_away`; CC no roll, strike < basis → `hold/below_basis_no_roll`; CC `keep_shares=False`, strike ≥ basis → `let_called_away/keep_shares_off` (no construction); unpriced current leg → `defer/current_unpriced`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement**:

```python
def decide(ctx, quotes, iv_stats, tech_stats, cfg, *, is_leveraged, would_own, cc_basis):
    pos = ctx.position
    if ctx.current.mid is None:
        return RollDecision(action="defer", reason="current_unpriced")
    if is_leveraged:
        return RollDecision(action="hold", reason="leveraged_etf_no_roll")
    if pos.right == OptionRight.PUT:
        if not would_own:
            return RollDecision(action="close", reason="not_would_own")
        if cfg.csp.when_assignable == "assign":
            return RollDecision(action="assign", reason="assign_preferred")
        cand, rej = construct_roll(ctx, quotes, iv_stats, tech_stats, cfg)
        if cand is not None:
            return RollDecision(action="roll", reason="credit_roll", candidate=cand, rejections=rej)
        return RollDecision(action="assign", reason=_top(rej, "no_qualifying_roll"), rejections=rej)
    above_basis = cc_basis is None or (pos.strike or 0.0) >= cc_basis
    if not cfg.cc.keep_shares and above_basis:
        return RollDecision(action="let_called_away", reason="keep_shares_off")
    cand, rej = construct_roll(dataclasses.replace(ctx, allow_debit=cfg.cc.keep_shares), quotes,
                               iv_stats, tech_stats, cfg)
    if cand is not None:
        return RollDecision(action="roll", reason="keep_shares_roll" if cand.premium < 0 else "credit_roll",
                            candidate=cand, rejections=rej)
    if above_basis:
        return RollDecision(action="let_called_away", reason=_top(rej, "no_qualifying_roll"), rejections=rej)
    return RollDecision(action="hold", reason="below_basis_no_roll", rejections=rej)
```

`_top(rej, default)` returns the most frequent rejection code (ties → alphabetical) or `default`. Every decision also fills `detail` with a one-line human summary (used by the card).

- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat(roll): roll decision tree + breach/ex-div trigger (Task 6)`.

### Task 7: Rules Engine roll scoping

**Files:**
- Modify: `src/engine/risk_engine.py:150-235`
- Test: `tests/test_risk_engine_roll.py` (new)

**Interfaces:**
- Consumes: `TradeCandidate.roll_from`, `get_config().roll.limits`.

- [ ] **Step 1: Failing tests** (build a ROLL candidate with `roll_from`): IV rank 5 and IV/RV 0.8 → no `iv_rank_below_minimum` / `iv_rv_below_minimum` for ROLL (still present for a CSP); earnings 10 days after today but after the new expiry → no `earnings_blackout` for ROLL (a CSP with the same dates still gets it via the proximity clause); earnings ≤ expiry → `earnings_blackout`; `roll_from.seq = 2` with `max_rolls_per_chain = 1` → `roll_limit_reached`; `expiry > original_expiry + 28d` → `roll_extension_cap`; a ROLL without `roll_from` → `roll_origin_missing`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement**: wrap the IV-rank and IV/RV checks in `if cand.strategy != Strategy.ROLL:` (comment: entry-selection filters, not risk limits); earnings: for ROLL only `cand.next_earnings <= cand.expiry`; add a roll block reading `get_config().roll.limits` (human config) that emits the three reasons above.
- [ ] **Step 4:** run → PASS; full `tests/test_risk_engine*.py` green.
- [ ] **Step 5:** Commit `feat(roll): risk engine roll scoping + roll limits (Task 7)`.

### Task 8: Roll pipeline orchestration

**Files:**
- Modify: `src/execution/roll_pipeline.py`
- Test: rewrite `tests/test_roll_pipeline.py`

**Interfaces:**
- Consumes: Tasks 3-7.
- Produces:
  - `async def evaluate_roll(ib, pos, *, chat_id: str, ttl_minutes: int, manual: bool = False) -> tuple[RollDecision, int | None]` — fetch (Task 4), build `RollContext` (chain state, closed candidate id, earnings/ex-div/dividend from fundamentals, current quote = the alerted contract matched by strike/expiry/right), call `decide`, and for `roll`: decision-time `validate_candidates([cand], account, positions)` — a FAIL turns the decision into `assign`/`let_called_away`/`hold` per the fallback with `reason="rules_engine:<codes>"`; a PASS queues a PENDING approval (existing `queue_roll_for_approval` body, now taking the candidate) and returns its id. Logs one `roll decision:` line per evaluation with action, reason and rejection counts.
  - `queue_roll_for_approval(cand: TradeCandidate, *, chat_id, ttl_minutes) -> int | None` — also returns None when a PENDING roll approval already exists for this `roll_from.con_id`/position (no duplicate proposals).
- Account/positions for the gate: `get_account_snapshot_async(ib)` and `get_positions(ib)`.

- [ ] **Step 1: Failing tests** (patch the fetch + account): breached CSP with a credit roll → `("roll", approval_id)` and one `ApprovalRow` PENDING whose snapshot carries `roll_from`; rules-engine FAIL (earnings) → `assign` with `rules_engine:earnings_blackout`, no approval; second evaluation while the approval is PENDING → no second approval; `manual=True` skips nothing in `decide` but is recorded in the log; empty fetch → `defer/chain_unavailable`.
- [ ] **Step 2-4:** implement, run, PASS.
- [ ] **Step 5:** Commit `feat(roll): evaluate_roll pipeline with decision-time gate (Task 8)`.

### Task 9: Executor — exact contract, one floor, bounded walk, campaigns

**Files:**
- Modify: `src/execution/roll_executor.py`
- Test: extend `tests/test_roll_executor.py`

- [ ] **Step 1: Failing tests**: two shorts GOOGL 330P (10/09) and 335P (10/16), candidate `roll_from.con_id` = 335P's conId → the BUY leg is 335P; `roll_from.contracts=2` but the position now holds 1 → REJECTED `position_size_changed`; CSP candidate with live net −0.02 → REJECTED `roll_net_below_floor`; CC `allow_debit` candidate with live net −0.20 (cap 0.25) → placed with `lmtPrice = +0.20`; −0.30 → REJECTED; reprice walk with `reprice_steps=3`, mid net 0.40, natural net 0.10, floor 0.05 → limits −0.40, −0.30, −0.20, −0.10 (never past −0.05 i.e. never below the floor credit); both fills call `attach_fill_to_campaign` (strategy `"roll"`); no `roll_from` → resolve falls back to exact strike/expiry/right match (never "nearest-dated").
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement**: `_resolve_short_to_close(positions, candidate)` → match `p.con_id == candidate.roll_from.con_id` when set, else exact `(underlying, right, strike, expiry)` from `roll_from`; size check `abs(short.position) != candidate.roll_from.contracts`; floor: `floor = -cfg.roll.cc.max_debit if roll_from.allow_debit else cfg.roll.construct.min_net_credit`; reject `roll_net_below_floor` when `live_net < floor`; keep the `min_live_premium_ratio` collapse check only when `candidate.premium > 0`; replace the mid-chasing repricer with `_walk_limits(mid_net, natural_net, floor, steps) -> list[float]` (credit-space targets, converted to `lmtPrice = -target`, rounded by `_round_combo_tick`), stepping every `execution.reprice_interval_seconds` regardless of `reprice_enabled` (the roll's own `roll.exec.reprice_steps` governs; 0 disables); `_record_roll_fills` calls `attach_fill_to_campaign` for both legs. Update the pinned `test_roll_executor.py:312` debit test to the new floor semantics.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `fix(roll): exact-contract resolution, shared floor, bounded reprice walk (Task 9)`.

### Task 10: Monitor — RTH gate, info-only timers, breach evaluation loop

**Files:**
- Modify: `src/monitor/intraday.py` (`fire_alerts`, `_review_send_persist`, `_on_pending_tickers`, new `_maybe_evaluate_roll`), `src/monitor/triggers.py` (docstrings; `check_ex_div` stays informational)
- Modify: `src/common/market_hours.py` (add `minutes_since_open(now=None) -> float | None`)
- Test: extend `tests/test_monitor.py`, new `tests/test_monitor_roll_eval.py`

- [ ] **Step 1: Failing tests**: (a) `fire_alerts` at 01:00 ET or 09:40 ET sends nothing and persists nothing; at 10:00 ET sends; (b) info alerts never carry `reply_markup` and never call `evaluate_roll`; (c) `_maybe_evaluate_roll` with a breached put at 10:00 → one `evaluate_roll`; again at 10:10 → skipped (30-min cadence); at 10:31 → evaluated again; (d) a decision with the same `action:reason` as one already sent today → no Telegram message (persisted `RollAlertRow(trigger="roll_decision")` dedupe); a changed decision → message; (e) leveraged ETF breached → `hold` message once, no fetch; (f) not breached → no evaluation.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement**: `_alert_window_open(cfg) -> bool` = `is_rth()` and `minutes_since_open() >= cfg.roll.trigger.min_minutes_after_open`, checked at the top of `fire_alerts` (return early) and of `_maybe_evaluate_roll`. Remove the `_try_queue_roll` branch from `_review_send_persist` (info-only). In `_on_pending_tickers`, after `check_all`, call `_maybe_evaluate_roll(pos, quote, local_sym)` which: computes `roll_trigger(...)` (ex-div guard from `risk.events.ex_dividend_assignment_guard`), honours `self._roll_eval_at[local_sym]` + `reevaluate_minutes`, guards with an in-flight set, short-circuits leveraged ETFs to a `hold` decision without fetching, otherwise `await evaluate_roll(self._ib, pos_with_delta, chat_id=..., ttl_minutes=...)`, then sends `format_roll_decision(...)` (Task 11) with Approve/Reject buttons for `roll` (approval id) or a `close_short:<con_id>` button for `close`, deduped per ET day on `action:reason` via `RollAlertRow(trigger="roll_decision", detail=f"{action}:{reason}")`. Requires `roll_execution_enabled`; when off, the decision card is sent without buttons.
- [ ] **Step 4:** run → PASS.
- [ ] **Step 5:** Commit `feat(roll): RTH-gated monitor, info-only timers, breach evaluation loop (Task 10)`.

### Task 11: Decision card and close button

**Files:**
- Modify: `src/notify/formatters.py` (new `format_roll_decision`), `src/notify/approval_service.py` (new `handle_close_short` + handler registration)
- Modify: `src/common/schemas.py` (already has `CloseReason.DEFENSIVE` from Task 2)
- Test: `tests/test_roll_card.py` (new), extend `tests/test_notify.py`

- [ ] **Step 1: Failing tests**: a `roll` card names the old leg (strike, expiry, mid), the new leg (strike, expiry, mid, Δ), net credit/debit per share and total, contracts, roll # (`seq`/`max`), chain breakeven, trigger and the top rejection codes; an `assign` card says "letting it assign at $K — no credit roll (<reason>)"; a `close` card names the reason; text ≤ 4096 and MarkdownV2-escaped; `handle_close_short` with `close_short:<con_id>` resolves the position by conId, quotes it, calls `close_short_position(..., reason=CloseReason.DEFENSIVE)`; unknown conId → "position no longer open" reply, no order.
- [ ] **Step 2-4:** implement (`contract_label`, `fmt_strike`, `_md` reuse), register `CallbackQueryHandler(handle_close_short, pattern="^close_short:")`, run, PASS.
- [ ] **Step 5:** Commit `feat(roll): decision card + operator close button (Task 11)`.

### Task 12: Claude reviews the proposal, not a guess

**Files:**
- Modify: `src/claude/prompts/roll.py`, `src/claude/runner.py::review_roll/_review_roll_cli`, `src/claude/ollama_runner.py::review_roll`, `src/monitor/intraday.py` (pass the decision summary)
- Test: extend `tests/test_claude*.py` roll prompt test

- [ ] **Step 1: Failing test**: `build_roll_prompt(alert, pos, quote, proposal="ROLL 335P 10/16 → 330P 10/23 for +$0.06")` contains a `=== SYSTEM PROPOSAL ===` block and the instruction that the reviewer may only agree/disagree and explain; omitted when `proposal is None`.
- [ ] **Step 2-4:** add `proposal: str | None = None` keyword through the three functions; the monitor passes `decision.detail`. Run, PASS. `tests/test_eval_skills.py` fence tests stay green (no import changes into engine/execution).
- [ ] **Step 5:** Commit `feat(roll): reviewer sees the system's proposal (Task 12)`.

### Task 13: Web `roll_request` through the new pipeline

**Files:**
- Modify: `src/notify/command_drain.py::_roll_request`, `docs/web/commands.md` roll_request table
- Test: rewrite `tests/test_drain_roll.py`

- [ ] **Step 1: Failing tests**: `roll` decision → `{"approval_id", "candidate_id"}`; `assign`/`let_called_away`/`hold`/`close` → `CommandFailed("no_qualifying_roll", {"decision": action, "reason": reason})`; `defer/chain_unavailable` → `CommandFailed("chain_unavailable")`; an existing PENDING roll approval for the position → `roll_already_working` with its approval id.
- [ ] **Step 2-4:** replace the generate/queue body with `evaluate_roll(ib, position, chat_id=..., ttl_minutes=..., manual=True)`; keep the five reasons (the `no_qualifying_roll` detail now carries the decision). Run, PASS.
- [ ] **Step 5:** Commit `feat(roll): web roll_request uses evaluate_roll (Task 13)`.

### Task 14: Offline assign / roll / close backtest (P2)

**Files:**
- Create: `src/backtest/roll_arms.py`, `scripts/roll_backtest.py`
- Test: `tests/test_roll_arms.py`

**Interfaces:**
- Produces: `simulate_breach_arms(symbol, closes: list[float], dates: list[date], *, right: str, target_delta: float, dte: int, roll_dte: int, breach_dte: int, min_net_credit: float, max_debit: float, risk_free_rate: float, commission: float) -> RollArmsResult` with per-arm lists of `ArmOutcome(entry_date, breach_date, horizon_date, pnl)` for arms `assign` (hold to expiry; if assigned, hold shares and sell a same-delta call to the horizon), `roll` (at breach, same-strike credit roll to `roll_dte` when the BS net ≥ floor, else falls back to `assign`), `close` (buy back at breach, flat to horizon); a `summary()` → per-arm n / mean / median / 5% CVaR / win rate. Black-Scholes at trailing HV30 (European, indicative only — stated in the output).
- [ ] **Step 1: Failing tests**: a synthetic falling series breaches every cycle and produces one outcome per arm per breach on the same horizon; a flat series produces no breaches; `close` P&L equals −(buyback − credit) × 100 − commissions; the `roll` arm falls back to `assign` when the BS net credit < floor.
- [ ] **Step 2-4:** implement; `scripts/roll_backtest.py --symbol AAPL --start 2019-01-01 --end 2026-09-30 [--right P] [--delta 0.25] [--dte 14] [--roll-dte 7] [--breach-dte 10]` reads daily closes through `src/data/` (`get_price_provider()` as `scripts/backtest.py` does) and prints the summary table. Run, PASS.
- [ ] **Step 5:** Commit `feat(backtest): assign vs roll vs close breach arms (Task 14)`.

### Task 15: Docs, STATUS, final gate

**Files:** `ARCHITECTURE.md` (new modules `roll_policy.py`, `roll_chains.py`, `roll_arms.py`, script; `market_data.get_roll_chain_quotes_async`; schemas `RollOrigin`/`RollDecision`/`CloseReason.DEFENSIVE`/`PositionSnapshot.con_id`/`FundamentalStats.dividend_per_share`; settings `roll:` block; executor/pipeline/monitor rows; fix "roll execution off by default" drift), `SETUP.md` (scripts table: `roll_backtest`; roll config + operator rulings; troubleshooting row "roll card shows assign/hold"), `STATUS.md` (Built entry; correct the "approvable since 10-02" claim; live-verification item: first roll = BAG sign check, watch by hand), `README.md` (safety summary line on rolls if present), `docs/web/commands.md` (Task 13), `tests/test_config_keys.py` (remove `ex_dividend_assignment_guard` from `_KNOWN_UNENFORCED`).

- [ ] Full gate: `python -m pytest -q`, `ruff check .`, `mypy src`, web `npx tsc --noEmit` unchanged from baseline.
- [ ] Commit `docs(roll): roll redesign docs + STATUS (Task 15)`.

---

## Progress log

| Task | Status | Commits | Gate | Date | Rulings |
|---|---|---|---|---|---|
| 1 Roll config | done | (this commit) | pytest roll/monitor/config 121 pass; mypy clean | 2026-10-11 | Field `construct` renamed `new_leg` (shadowed BaseModel.construct); cfg path is roll.new_leg.* |
| 2 Schemas | done | (this commit) | full suite 3319 pass; mypy clean | 2026-10-11 | - |
| 3 Chain state | done | (this commit) | roll_chains/loss/profit/monitor/notify pass; mypy clean | 2026-10-11 | CandidateRow looked up by candidate_id column (PK is id) |
| 4 Targeted fetch | done | (this commit) | roll fetch 5 pass; mypy clean | 2026-10-11 | fetch_roll_inputs untouched here; evaluate_roll uses the targeted fetch (T8), old helper removed in T13 |
| 5 Construction | done | (this commit) | construct 13 pass; fences green; mypy clean | 2026-10-11 | old generator kept until T13; roll legs skip volume gate; strict_mid pricing |
| 6 Decision tree | done | (this commit) | policy 19 pass; mypy clean | 2026-10-11 | breach takes precedence over ex_div when both hold |
| 7 Rules Engine | done | (this commit) | full suite 3368 pass; mypy clean | 2026-10-11 | roll without roll_from fails closed; test helper attaches origin |
| 8 Pipeline | done | (this commit) | evaluate 6 pass + roll/fence suites 137 pass; mypy clean | 2026-10-11 | old queue_roll_for_approval wraps queue_roll_candidate until T13; pending roll short-circuits to defer/roll_pending |
| 9 Executor | done | (this commit) | executor 20 pass; mypy clean | 2026-10-11 | roll leg re-gated as ROLL + roll_delta_increases; walk floor = max(policy floor, collapse floor); old nearest-dated + reprice tests replaced |
| 10 Monitor | done | (this commit) | full suite 3397 pass (config_keys fixed after); mypy clean | 2026-10-11 | decisions run as per-tick tasks; roll_decision rows excluded from info-alert policy; allowlist emptied here |
| 11 Card + close | done | (this commit) | card 5 + notify/fences pass; mypy clean | 2026-10-11 | done before T10 (T10 consumes the card) |
| 12 Reviewer | done | (this commit) | reviewer/monitor/claude suites 200 pass; mypy clean | 2026-10-11 | decision cards reviewed with the proposal; monitor tests patch review_roll |
| 13 Web roll_request | done | (this commit) | full suite 3383 pass; mypy clean | 2026-10-11 | drain mocks evaluate_roll; old generator + fetch_roll_inputs + queue_roll_for_approval + their tests deleted; invariants re-pinned |
| 14 Backtest arms | done | (this commit) | arms 6 pass; mypy clean | 2026-10-11 | roll arm = same-strike roll; calls include stock P&L; CLI smoke test added |
| 15 Docs + gate | pending | | | | |
