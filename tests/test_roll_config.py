"""Roll policy config (2026-10-11 roll redesign, Task 1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.common.config import RollCfg, get_config


def test_example_config_carries_the_operator_rulings() -> None:
    r = get_config().roll
    assert r.csp.when_assignable == "roll_if_credit"
    assert r.cc.keep_shares is True and r.cc.max_debit == 0.25
    assert r.limits.max_rolls_per_chain == 1
    assert r.new_leg.max_quote_lines <= 20  # fits the monitor's reserved lines


def test_defaults_are_conservative() -> None:
    r = RollCfg()
    assert r.csp.when_assignable == "assign" and r.cc.keep_shares is False


@pytest.mark.parametrize(
    "bad",
    [
        {"trigger": {"breach_delta": 1.2}},
        {"new_leg": {"min_net_credit": -0.1}},
        {"csp": {"when_assignable": "maybe"}},
        {"limits": {"max_rolls_per_chain": -1}},
    ],
)
def test_bad_values_fail_at_load(bad: dict) -> None:
    with pytest.raises(ValidationError):
        RollCfg(**bad)


def test_monitor_roll_defensive_is_gone() -> None:
    assert not hasattr(get_config().monitor, "roll_defensive")
