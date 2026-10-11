"""Roll-redesign schema additions (Task 2): roll origin, roll decision, conId, dividend."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from src.common.schemas import (
    CloseReason,
    OptionRight,
    RollDecision,
    RollOrigin,
    ScoreCard,
    Strategy,
    TradeCandidate,
)

_EXP = date.today() + timedelta(days=14)


def _candidate(**extra: object) -> TradeCandidate:
    return TradeCandidate(
        candidate_id="roll-1",
        strategy=Strategy.ROLL,
        underlying="GOOGL",
        right=OptionRight.PUT,
        strike=330.0,
        expiry=_EXP,
        premium=0.06,
        collateral=33_000.0,
        roc_pct=0.0,
        annualized_yield_pct=0.0,
        breakeven=329.94,
        dte=14,
        scores=ScoreCard(symbol="GOOGL"),
        **extra,  # type: ignore[arg-type]
    )


def _origin() -> RollOrigin:
    return RollOrigin(
        con_id=123,
        candidate_id="c-old",
        strike=335.0,
        expiry=_EXP - timedelta(days=7),
        right=OptionRight.PUT,
        contracts=1,
        chain_id="c-old",
        seq=1,
        original_expiry=_EXP - timedelta(days=7),
        old_mid=6.00,
        new_mid=6.06,
    )


def test_roll_origin_round_trips_through_the_frozen_snapshot() -> None:
    cand = _candidate(roll_from=_origin())
    again = TradeCandidate.model_validate(cand.model_dump(mode="json"))
    assert again.roll_from == cand.roll_from
    assert again.roll_from is not None and again.roll_from.allow_debit is False


def test_an_old_snapshot_without_roll_from_still_validates() -> None:
    dumped = _candidate().model_dump(mode="json")
    dumped.pop("roll_from", None)
    assert TradeCandidate.model_validate(dumped).roll_from is None


def test_roll_decision_carries_action_reason_and_candidate() -> None:
    d = RollDecision(action="roll", reason="credit_roll", candidate=_candidate())
    assert d.rejections == {} and d.detail == ""
    assert CloseReason.DEFENSIVE.value == "defensive"


def test_get_positions_maps_the_contract_conid() -> None:
    from src.ibkr.portfolio import get_positions

    item = MagicMock()
    item.contract.symbol = "GOOGL"
    item.contract.localSymbol = "GOOGL 261016P00335000"
    item.contract.secType = "OPT"
    item.contract.right = "P"
    item.contract.strike = 335.0
    item.contract.lastTradeDateOrContractMonth = "20261016"
    item.contract.conId = 765432
    item.position = -1.0
    item.averageCost = 298.0
    item.marketPrice = item.marketValue = item.unrealizedPNL = 0.0
    ib = MagicMock()
    ib.portfolio.return_value = [item]
    (pos,) = get_positions(ib)
    assert pos.con_id == 765432


def _fundamentals(symbol: str, info: dict) -> object:
    from src.analytics.fundamentals import get_fundamental_stats

    provider = MagicMock()
    provider.get_info.return_value = {"quoteType": "EQUITY", **info}
    provider.get_calendar.return_value = {}
    with patch("src.analytics.fundamentals.get_fundamentals_provider", return_value=provider):
        return get_fundamental_stats(symbol)


def test_dividend_per_share_prefers_the_last_dividend(db: object) -> None:
    stats = _fundamentals("DIVA", {"lastDividendValue": 0.26, "dividendRate": 1.00})
    assert stats.dividend_per_share == 0.26  # type: ignore[attr-defined]


def test_dividend_per_share_falls_back_to_a_quarter_of_the_rate(db: object) -> None:
    stats = _fundamentals("DIVB", {"dividendRate": 1.00})
    assert stats.dividend_per_share == 0.25  # type: ignore[attr-defined]


def test_no_dividend_is_none(db: object) -> None:
    assert _fundamentals("DIVC", {}).dividend_per_share is None  # type: ignore[attr-defined]
