from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime

import src.spreads_ai.context as ctx
from src.common.schemas import MarketConditions, TechnicalStats

NOW = datetime(2026, 10, 7, 15, 5, tzinfo=UTC)


@contextmanager
def _no_db():
    yield None


def test_degrades_field_by_field_and_says_what_failed(monkeypatch) -> None:
    monkeypatch.setattr(
        ctx, "get_market_conditions", lambda: MarketConditions(vix=17.8, vix_term_ratio=0.91)
    )

    def boom(symbol: str):
        raise RuntimeError("yfinance down")

    monkeypatch.setattr(ctx, "get_technical_stats", boom)
    monkeypatch.setattr(ctx, "read_only_session", _no_db)
    monkeypatch.setattr(ctx, "compute_realized_vol", lambda symbol, window: None)
    snap = ctx.market_snapshot(NOW, symbol="SPY", max_headlines=20)
    assert snap.vix == 17.8 and snap.vix_term_ratio == 0.91
    assert snap.spy_vs_sma20_pct is None and snap.headlines == []
    assert snap.hv30 is None
    assert snap.unavailable == ["technicals", "realized_vol", "news"]


def test_technicals_become_percent_distances(monkeypatch) -> None:
    monkeypatch.setattr(ctx, "get_market_conditions", lambda: MarketConditions())
    monkeypatch.setattr(
        ctx,
        "get_technical_stats",
        lambda symbol: TechnicalStats(
            symbol="SPY", price=663.0, sma_20=650.0, sma_50=680.0, rsi_14=52.0
        ),
    )
    monkeypatch.setattr(ctx, "read_only_session", _no_db)
    monkeypatch.setattr(ctx, "compute_realized_vol", lambda symbol, window: 18.5)
    snap = ctx.market_snapshot(NOW, symbol="SPY", max_headlines=0)
    assert (
        round(snap.spy_vs_sma20_pct or 0, 2) == 2.0 and round(snap.spy_vs_sma50_pct or 0, 2) == -2.5
    )
    assert snap.rsi14 == 52.0 and "news" not in snap.unavailable  # max_headlines 0 = not asked
    assert snap.hv30 == 18.5 and snap.unavailable == []


def test_a_macro_failure_leaves_the_other_sources_intact(monkeypatch) -> None:
    def boom():
        raise RuntimeError("fred down")

    calls: list[tuple[str, int]] = []

    def hv(symbol: str, window: int) -> float:
        calls.append((symbol, window))
        return 14.2

    monkeypatch.setattr(ctx, "get_market_conditions", boom)
    monkeypatch.setattr(
        ctx,
        "get_technical_stats",
        lambda symbol: TechnicalStats(symbol="SPY", price=663.0, sma_20=650.0, rsi_14=52.0),
    )
    monkeypatch.setattr(ctx, "compute_realized_vol", hv)
    monkeypatch.setattr(ctx, "read_only_session", _no_db)
    snap = ctx.market_snapshot(NOW, symbol="SPY", max_headlines=0)
    assert snap.unavailable == ["macro"]
    assert snap.vix is None and snap.rsi14 == 52.0 and snap.hv30 == 14.2
    assert calls == [("SPY", 30)]


def test_a_realized_vol_exception_is_named_not_raised(monkeypatch) -> None:
    def boom(symbol: str, window: int):
        raise RuntimeError("no bars")

    monkeypatch.setattr(ctx, "get_market_conditions", lambda: MarketConditions())
    monkeypatch.setattr(
        ctx, "get_technical_stats", lambda symbol: TechnicalStats(symbol="SPY", price=663.0)
    )
    monkeypatch.setattr(ctx, "compute_realized_vol", boom)
    monkeypatch.setattr(ctx, "read_only_session", _no_db)
    snap = ctx.market_snapshot(NOW, symbol="SPY", max_headlines=0)
    assert snap.hv30 is None and snap.unavailable == ["realized_vol"]
