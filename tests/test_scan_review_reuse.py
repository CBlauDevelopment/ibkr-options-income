"""Tests for S5 — skip the Claude LLM review when the top-candidate set is unchanged.

The 15-min intraday loop re-runs the scan ~26×/session; when the top candidates + their signal
vectors are identical to the prior cycle, the `claude -p` subprocess would return the same review,
so it is skipped and the persisted ClaudeReview is reused. Enrichment-only — never gates anything
(the fence). Manual /scan always reviews fresh. No TWS/Gateway required.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.common.schemas import (
    AccountSnapshot,
    ClaudeReview,
    IVStats,
    MarketConditions,
    OptionRight,
    ScoreCard,
    Strategy,
    TradeCandidate,
)
from src.strategies._evaluation import ScreenResult


def _db_setup(tmp_path, monkeypatch) -> None:
    import src.storage.db as dbmod
    from src.common.config import Config

    monkeypatch.setattr(dbmod, "_engine", None)
    monkeypatch.setattr(dbmod, "_SessionLocal", None)
    monkeypatch.setattr(Config, "db_url_abs", lambda self: f"sqlite:///{tmp_path / 't.db'}")
    dbmod.init_db()


def _candidate(candidate_id: str = "c-001", blended_score: float = 90.0) -> TradeCandidate:
    return TradeCandidate(
        candidate_id=candidate_id,
        strategy=Strategy.CASH_SECURED_PUT,
        underlying="AAPL",
        right=OptionRight.PUT,
        strike=180.0,
        expiry=date(2026, 7, 17),
        contracts=1,
        premium=1.50,
        collateral=18_000.0,
        roc_pct=0.83,
        annualized_yield_pct=18.5,
        breakeven=178.5,
        prob_otm=0.72,
        delta=-0.25,
        iv_rank=65.0,
        dte=48,
        scores=ScoreCard(symbol="AAPL", iv_score=70.0),
        blended_score=blended_score,
    )


def _review(candidate_id: str = "c-001") -> ClaudeReview:
    return ClaudeReview(
        candidate_id=candidate_id,
        priority=1,
        recommendation="sell",
        why_attractive="x",
        risks="y",
        tradeoffs="z",
        assignment_considerations="w",
    )


# ---------------------------------------------------------------------------
# _candidates_review_hash / _load_prior_reviews
# ---------------------------------------------------------------------------


class TestReviewHash:
    def test_stable_for_same_input(self):
        from src.orchestrator.scan import _candidates_review_hash

        top = [_candidate()]
        assert _candidates_review_hash(top, 15.0) == _candidates_review_hash(top, 15.0)

    def test_changes_when_a_signal_changes(self):
        from src.orchestrator.scan import _candidates_review_hash

        h1 = _candidates_review_hash([_candidate(blended_score=90.0)], 15.0)
        h2 = _candidates_review_hash([_candidate(blended_score=80.0)], 15.0)
        assert h1 != h2

    def test_changes_with_vix(self):
        from src.orchestrator.scan import _candidates_review_hash

        top = [_candidate()]
        assert _candidates_review_hash(top, 15.0) != _candidates_review_hash(top, 30.0)


class TestLoadPriorReviews:
    def test_returns_persisted_review(self, tmp_path, monkeypatch):
        _db_setup(tmp_path, monkeypatch)
        from src.orchestrator.scan import _load_prior_reviews
        from src.storage.db import session_scope
        from src.storage.models import ClaudeReviewRow

        with session_scope() as s:
            s.add(
                ClaudeReviewRow(
                    candidate_id="c-001",
                    priority=1,
                    recommendation="sell",
                    payload=_review().model_dump(mode="json"),
                )
            )
        got = _load_prior_reviews(["c-001", "c-002"])
        assert "c-002" not in got
        assert got["c-001"].recommendation == "sell"

    def test_returns_most_recent_per_candidate(self, tmp_path, monkeypatch):
        _db_setup(tmp_path, monkeypatch)
        from src.orchestrator.scan import _load_prior_reviews
        from src.storage.db import session_scope
        from src.storage.models import ClaudeReviewRow

        with session_scope() as s:
            for prio in (3, 1):  # later row has priority=1
                r = _review()
                r.priority = prio
                s.add(
                    ClaudeReviewRow(
                        candidate_id="c-001",
                        priority=prio,
                        recommendation="sell",
                        payload=r.model_dump(mode="json"),
                    )
                )
        assert _load_prior_reviews(["c-001"])["c-001"].priority == 1


# ---------------------------------------------------------------------------
# End-to-end: run_scan(intraday=True) reuses, intraday=False always reviews
# ---------------------------------------------------------------------------


def _make_account() -> AccountSnapshot:
    return AccountSnapshot(
        account="DU1",
        net_liquidation=200_000.0,
        total_cash=150_000.0,
        buying_power=120_000.0,
        maintenance_margin=10_000.0,
        excess_liquidity=110_000.0,
    )


def _stub_pipeline(scanmod, monkeypatch, review_counter):
    """Stub a one-CSP-candidate pipeline so step 8 (Claude review) always has a stable top set."""
    cand = _candidate()

    monkeypatch.setattr(
        scanmod, "get_account_snapshot_async", AsyncMock(return_value=_make_account())
    )
    monkeypatch.setattr(scanmod, "get_positions", lambda ib: [])
    monkeypatch.setattr(scanmod, "get_market_conditions", lambda: MarketConditions(vix=15.0))

    async def _all_material(all_syms, holds, wheeling, dip, **kwargs):
        return set(all_syms), {}

    monkeypatch.setattr(scanmod, "_compute_material_symbols", _all_material)

    async def _chain(ib, symbol):
        return [SimpleNamespace(mid=None, greeks_source="ibkr")]  # non-empty so CSP generation runs

    monkeypatch.setattr(scanmod, "get_option_chain_quotes_async", _chain)
    monkeypatch.setattr(scanmod, "get_iv_stats", lambda symbol, quotes=None: IVStats(symbol=symbol))
    monkeypatch.setattr(
        scanmod,
        "get_technical_stats",
        lambda symbol, **_: SimpleNamespace(symbol=symbol, price=100.0, price_source="yfinance"),
    )
    monkeypatch.setattr(scanmod, "get_fundamental_stats", lambda symbol: SimpleNamespace())

    class _Sent:
        def __init__(self, **k):
            pass

        def score(self, s):
            return None

    monkeypatch.setattr(scanmod, "SentimentScorer", _Sent)
    monkeypatch.setattr(scanmod, "screen_cc_candidates", lambda *a, **k: ScreenResult())
    monkeypatch.setattr(
        scanmod, "screen_csp_candidates", lambda *a, **k: ScreenResult(passed=[cand])
    )
    monkeypatch.setattr(scanmod, "generate_buy_candidates", lambda *a, **k: [])
    monkeypatch.setattr(scanmod, "score_candidates", lambda cands: cands)
    monkeypatch.setattr(
        scanmod,
        "validate_candidates",
        lambda scored, account, positions, **kwargs: [
            SimpleNamespace(candidate_id=c.candidate_id, verdict=SimpleNamespace(value="pass"))
            for c in scored
        ],
    )
    monkeypatch.setattr(scanmod, "select_top_candidates_detailed", lambda passed: (passed, []))
    monkeypatch.setattr(scanmod, "_persist_memory", lambda *a, **k: None)
    monkeypatch.setattr(scanmod, "_persist_ledger", lambda *a, **k: None)
    monkeypatch.setattr(scanmod, "_load_memory", lambda syms: [])
    monkeypatch.setattr(scanmod, "send_candidates", AsyncMock())
    monkeypatch.setattr(scanmod, "send_buy_list", AsyncMock())
    monkeypatch.setattr(scanmod, "send_account_snapshot", AsyncMock())

    def _fake_review(*a, **k):
        review_counter["n"] += 1
        return [_review()]

    monkeypatch.setattr(scanmod, "review_candidates", _fake_review)
    return cand


@pytest.mark.asyncio
async def test_intraday_reuses_review_when_unchanged(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    import src.orchestrator.scan as scanmod
    from src.common.config import get_config

    monkeypatch.setattr(get_config(), "universe", {"would_own": ["AAPL"], "sectors": {"AAPL": "t"}})
    counter = {"n": 0}
    _stub_pipeline(scanmod, monkeypatch, counter)

    from unittest.mock import MagicMock

    await scanmod.run_scan(MagicMock(), bot=object(), chat_id="1", intraday=True)
    await scanmod.run_scan(MagicMock(), bot=object(), chat_id="1", intraday=True)

    assert counter["n"] == 1  # second cycle reused the persisted review, skipped the LLM


@pytest.mark.asyncio
async def test_full_sweep_always_reviews(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    import src.orchestrator.scan as scanmod
    from src.common.config import get_config

    monkeypatch.setattr(get_config(), "universe", {"would_own": ["AAPL"], "sectors": {"AAPL": "t"}})
    counter = {"n": 0}
    _stub_pipeline(scanmod, monkeypatch, counter)

    from unittest.mock import MagicMock

    await scanmod.run_scan(MagicMock(), bot=object(), chat_id="1")  # intraday=False
    await scanmod.run_scan(MagicMock(), bot=object(), chat_id="1")

    assert counter["n"] == 2  # full sweeps never reuse


# ---------------------------------------------------------------------------
# 2026-10-15: coarsened fingerprint + a time-bounded log of recent reviews. The old hash covered
# premium/delta/VIX at full float precision against only the immediately preceding cycle, so any
# tick defeated it: in one week 10 contracts were reviewed 2-4 times (PLTR $192.50 four times).
# ---------------------------------------------------------------------------

from datetime import UTC, datetime, timedelta  # noqa: E402


class TestCoarseHash:
    def _h(self, **update):
        from src.orchestrator.scan import _candidates_review_hash

        return _candidates_review_hash([_candidate().model_copy(update=update)], 15.0)

    def test_sub_bucket_ticks_keep_the_hash(self):
        # compare two values inside one bucket (the fixture's own values sit on bucket edges)
        assert self._h(premium=1.50) == self._h(premium=1.52)  # a 2-cent tick on the mid
        assert self._h(delta=-0.26) == self._h(delta=-0.262)
        assert self._h(iv_rank=64.0) == self._h(iv_rank=64.6)
        assert self._h(blended_score=90.0) == self._h(blended_score=90.4)

    def test_buckets_are_edges_not_noise(self):
        """A tick that crosses a bucket edge changes the hash - bounded, because the reuse log
        remembers both states, so a value hovering on an edge reviews at most twice."""
        assert self._h(delta=-0.26) != self._h(delta=-0.28)

    def test_derived_and_noisy_fields_do_not_matter(self):
        base = self._h()
        assert self._h(roc_pct=0.84, annualized_yield_pct=18.7) == base

    def test_a_real_move_changes_it(self):
        base = self._h()
        assert self._h(premium=1.75) != base
        assert self._h(delta=-0.31) != base
        assert self._h(iv_rank=72.0) != base

    def test_the_contract_is_part_of_it(self):
        from src.orchestrator.scan import _candidates_review_hash

        assert _candidates_review_hash([_candidate("c-001")], 15.0) != _candidates_review_hash(
            [_candidate("c-002")], 15.0
        )

    def test_small_vix_wiggle_is_ignored_a_regime_move_is_not(self):
        from src.orchestrator.scan import _candidates_review_hash

        top = [_candidate()]
        assert _candidates_review_hash(top, 15.0) == _candidates_review_hash(top, 15.1)
        assert _candidates_review_hash(top, 15.0) != _candidates_review_hash(top, 17.0)


class TestReuseLog:
    T0 = datetime(2026, 10, 15, 14, 0, tzinfo=UTC)

    def test_a_noted_hash_is_reusable_inside_the_window(self, tmp_path, monkeypatch):
        _db_setup(tmp_path, monkeypatch)
        from src.orchestrator.scan import _note_fresh_review, _review_is_reusable

        _note_fresh_review("h1", self.T0)
        assert _review_is_reusable("h1", self.T0 + timedelta(minutes=119), 120)
        assert not _review_is_reusable("h1", self.T0 + timedelta(minutes=121), 120)
        assert not _review_is_reusable("other", self.T0, 120)

    def test_zero_window_disables_reuse(self, tmp_path, monkeypatch):
        _db_setup(tmp_path, monkeypatch)
        from src.orchestrator.scan import _note_fresh_review, _review_is_reusable

        _note_fresh_review("h1", self.T0)
        assert not _review_is_reusable("h1", self.T0, 0)

    def test_noting_again_refreshes_the_time(self, tmp_path, monkeypatch):
        _db_setup(tmp_path, monkeypatch)
        from src.orchestrator.scan import _note_fresh_review, _review_is_reusable

        _note_fresh_review("h1", self.T0)
        _note_fresh_review("h1", self.T0 + timedelta(minutes=100))
        assert _review_is_reusable("h1", self.T0 + timedelta(minutes=200), 120)

    def test_keeps_the_newest_entries_only(self, tmp_path, monkeypatch):
        _db_setup(tmp_path, monkeypatch)
        from src.orchestrator.scan import _note_fresh_review, _review_is_reusable

        for i in range(20):
            _note_fresh_review(f"h{i}", self.T0 + timedelta(minutes=i))
        now = self.T0 + timedelta(minutes=20)
        assert _review_is_reusable("h19", now, 120)
        assert not _review_is_reusable("h0", now, 120)  # fell off the end of the bounded log

    def test_a_corrupt_log_is_treated_as_empty(self, tmp_path, monkeypatch):
        _db_setup(tmp_path, monkeypatch)
        from src.orchestrator.scan import _review_is_reusable
        from src.storage.system_settings import set_setting

        for junk in ("not json", "{}", '[1, "x", {"h": 1}]', '[{"h": "h1", "t": "nope"}]'):
            set_setting("review_reuse_log", junk)
            assert not _review_is_reusable("h1", self.T0, 120)


def _clock(monkeypatch, scanmod, start):
    now = {"t": start}
    monkeypatch.setattr(scanmod, "_utcnow", lambda: now["t"])
    return now


def _varying_pipeline(scanmod, monkeypatch, counter):
    """Like _stub_pipeline, but the screened candidate and its review follow ``holder['id']``."""
    holder = {"id": "c-001"}
    _stub_pipeline(scanmod, monkeypatch, counter)

    monkeypatch.setattr(
        scanmod,
        "screen_csp_candidates",
        lambda *a, **k: ScreenResult(passed=[_candidate(holder["id"])]),
    )

    def _fake_review(cands, *a, **k):
        counter["n"] += 1
        return [_review(c.candidate_id) for c in cands]

    monkeypatch.setattr(scanmod, "review_candidates", _fake_review)
    return holder


async def _cycle(scanmod):
    from unittest.mock import MagicMock

    await scanmod.run_scan(MagicMock(), bot=object(), chat_id="1", intraday=True)


@pytest.mark.asyncio
async def test_reuse_survives_an_intervening_different_set(tmp_path, monkeypatch):
    """A, B, A: the third cycle reuses A's review (the old code only compared with B's)."""
    _db_setup(tmp_path, monkeypatch)
    import src.orchestrator.scan as scanmod
    from src.common.config import get_config

    monkeypatch.setattr(get_config(), "universe", {"would_own": ["AAPL"], "sectors": {"AAPL": "t"}})
    counter = {"n": 0}
    holder = _varying_pipeline(scanmod, monkeypatch, counter)
    _clock(monkeypatch, scanmod, TestReuseLog.T0)

    await _cycle(scanmod)  # A: fresh
    holder["id"] = "c-002"
    await _cycle(scanmod)  # B: fresh
    holder["id"] = "c-001"
    await _cycle(scanmod)  # A again: reused
    assert counter["n"] == 2


@pytest.mark.asyncio
async def test_a_reused_review_does_not_extend_its_own_life(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    import src.orchestrator.scan as scanmod
    from src.common.config import get_config

    monkeypatch.setattr(get_config(), "universe", {"would_own": ["AAPL"], "sectors": {"AAPL": "t"}})
    counter = {"n": 0}
    _varying_pipeline(scanmod, monkeypatch, counter)
    clock = _clock(monkeypatch, scanmod, TestReuseLog.T0)

    await _cycle(scanmod)  # fresh at t0
    clock["t"] = TestReuseLog.T0 + timedelta(minutes=100)
    await _cycle(scanmod)  # inside the 120 min window: reused
    assert counter["n"] == 1
    clock["t"] = TestReuseLog.T0 + timedelta(minutes=130)
    await _cycle(scanmod)  # 130 min after the LAST FRESH review: reviewed again
    assert counter["n"] == 2


@pytest.mark.asyncio
async def test_zero_window_never_reuses(tmp_path, monkeypatch):
    _db_setup(tmp_path, monkeypatch)
    import src.orchestrator.scan as scanmod
    from src.common.config import get_config

    monkeypatch.setattr(get_config(), "universe", {"would_own": ["AAPL"], "sectors": {"AAPL": "t"}})
    monkeypatch.setattr(get_config().claude, "review_reuse_minutes", 0)
    counter = {"n": 0}
    _varying_pipeline(scanmod, monkeypatch, counter)
    _clock(monkeypatch, scanmod, TestReuseLog.T0)

    await _cycle(scanmod)
    await _cycle(scanmod)
    assert counter["n"] == 2
