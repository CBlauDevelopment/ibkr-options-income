"""Rules Engine roll scoping (roll redesign Task 7).

A roll is exempt from the entry-selection IV floors, judged on earnings only by whether its new
expiry runs into them, and held to the chain's roll and extension limits.
"""

from __future__ import annotations

from datetime import date, timedelta

from src.common.schemas import OptionRight, RollOrigin, Strategy, TradeCandidate, Verdict
from src.engine.risk_engine import validate_candidates
from tests.test_engine import _account, _candidate

_TODAY = date.today()


def roll_from(seq: int = 1, original_days: int = 3) -> RollOrigin:
    return RollOrigin(
        con_id=1,
        candidate_id="c-old",
        strike=150.0,
        expiry=_TODAY + timedelta(days=3),
        right=OptionRight.PUT,
        contracts=1,
        chain_id="c-old",
        seq=seq,
        original_expiry=_TODAY + timedelta(days=original_days),
        old_mid=5.0,
        new_mid=5.4,
    )


def _roll(**update: object) -> TradeCandidate:
    base = _candidate(strategy=Strategy.ROLL, underlying="MARA", dte=10).model_copy(
        update={"roll_from": roll_from(), "roc_pct": 0.0, "annualized_yield_pct": 0.0}
    )
    return base.model_copy(update=update)


def _reasons(cand: TradeCandidate) -> list[str]:
    return validate_candidates([cand], _account(), [])[0].reasons


def test_a_roll_ignores_the_entry_iv_floors() -> None:
    reasons = _reasons(_roll(iv_rank=5.0, iv_rv_ratio=0.8))
    assert "iv_rank_below_minimum" not in reasons and "iv_rv_below_minimum" not in reasons
    csp = _candidate(strategy=Strategy.CASH_SECURED_PUT).model_copy(
        update={"iv_rank": 5.0, "iv_rv_ratio": 0.8}
    )
    assert {"iv_rank_below_minimum", "iv_rv_below_minimum"} <= set(_reasons(csp))


def test_a_roll_expiring_before_earnings_is_not_blacked_out() -> None:
    soon = _TODAY + timedelta(days=12)  # inside the 14-day proximity clause, after expiry
    assert "earnings_blackout" not in _reasons(_roll(next_earnings=soon))
    csp = _candidate(strategy=Strategy.CASH_SECURED_PUT, dte=10).model_copy(
        update={"next_earnings": soon}
    )
    assert "earnings_blackout" in _reasons(csp)


def test_a_roll_into_earnings_is_blacked_out() -> None:
    assert "earnings_blackout" in _reasons(_roll(next_earnings=_TODAY + timedelta(days=9)))


def test_a_second_roll_breaks_the_chain_limit() -> None:
    assert "roll_limit_reached" in _reasons(_roll(roll_from=roll_from(seq=2)))


def test_an_extension_past_the_cap_is_rejected() -> None:
    # new expiry 10 days out, original 3 days ago-equivalent anchor −20 → 30 days of extension
    assert "roll_extension_cap" in _reasons(_roll(roll_from=roll_from(original_days=-20)))


def test_a_roll_without_its_origin_fails_closed() -> None:
    assert "roll_origin_missing" in _reasons(_roll(roll_from=None))


def test_a_well_formed_roll_passes() -> None:
    verdict = validate_candidates([_roll()], _account(), [])[0]
    assert verdict.verdict == Verdict.PASS, verdict.reasons
