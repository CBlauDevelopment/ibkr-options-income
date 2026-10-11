from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from src.common.schemas import (
    SpreadCandidate,
    SpreadMarketSnapshot,
    SpreadMenuItem,
    SpreadPickRecord,
    SpreadPickSnapshot,
    SpreadTradeRecord,
)
from src.spreads.report import (
    build_decisions,
    compare_by,
    compute_stats,
    decision_kind,
    decision_rows,
    format_compare,
    format_day,
    format_extras,
    format_stats,
    group_stats,
    tag_breakdowns,
)


def test_stats_expose_the_win_rate_trap() -> None:
    s = compute_stats([30.0, 30.0, -100.0, 30.0])
    assert (s.n, s.wins, s.losses) == (4, 3, 1)
    assert s.win_rate == pytest.approx(0.75)
    assert s.avg_win == pytest.approx(30.0) and s.avg_loss == pytest.approx(-100.0)
    assert s.expectancy == pytest.approx(-2.5)
    assert s.breakeven_win_rate == pytest.approx(100 / 130)
    assert s.total_pnl == pytest.approx(-10.0)
    assert s.max_drawdown == pytest.approx(100.0)


def test_empty_and_all_wins() -> None:
    e = compute_stats([])
    assert e.n == 0 and e.win_rate is None and e.expectancy is None and e.max_drawdown == 0.0
    w = compute_stats([10.0, 5.0])
    assert w.breakeven_win_rate is None and w.max_drawdown == 0.0


def test_group_and_format() -> None:
    g = group_stats([("positive", 20.0), ("negative", -50.0), ("positive", 10.0)])
    assert g["positive"].n == 2 and g["negative"].total_pnl == -50.0
    text = format_stats("shadow", compute_stats([30.0, -100.0]))
    assert "win rate 50.0%" in text and "break-even" in text and "expectancy" in text


def _t(**kw) -> SimpleNamespace:
    base = dict(
        side="put",
        regime="positive",
        trigger="move",
        gap_day=False,
        exit_reason="profit_take",
        pnl_usd=20.0,
        hold_minutes=40.0,
        mae_usd=5.0,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_tag_breakdowns_split_negative_gamma_gap_days_and_sides() -> None:
    trades = [
        _t(),
        _t(regime="negative", pnl_usd=-60.0, exit_reason="stop_loss", mae_usd=80.0),
        _t(regime="negative", gap_day=True, side="call"),
    ]
    b = tag_breakdowns(trades)
    assert set(b) == {"regime", "side", "trigger", "gap", "exit"}
    assert b["regime"]["negative"].n == 2 and b["regime"]["negative"].total_pnl == pytest.approx(
        -40.0
    )
    assert b["gap"]["gap day"].n == 1 and b["gap"]["normal open"].n == 2
    assert b["side"]["call"].n == 1 and b["exit"]["stop_loss"].losses == 1
    extras = format_extras(trades)
    assert "avg hold 40 min" in extras and "worst MAE $80.00" in extras
    assert "avg hold n/a" in format_extras([_t(hold_minutes=None, mae_usd=None)])


T = datetime(2026, 10, 7, 15, 0, tzinfo=UTC)


def _item(letter, position, short):
    c = SpreadCandidate(
        spread_id=letter,
        side="put",
        expiry=date(2026, 10, 7),
        short_strike=short,
        long_strike=short - 5,
        width=5,
        credit_mid=0.5,
        credit_natural=0.46,
        short_delta=-0.1,
        spot=690,
        quote_time=T,
    )
    return SpreadMenuItem(
        letter=letter,
        position=position,
        candidate=c,
        contracts=1,
        credit_after_costs=0.39,
        cost_pct_of_credit=0.2,
        max_loss_per_contract_usd=450,
        dist_spot_pts=11,
        dist_em_multiple=1.9,
        beyond_wall_pts=0.7,
        be_full_loss=0.92,
        be_nominal_exits=0.8,
    )


def _pick(pid, choice, executed, *, fallback=None, vix=17.0, regime="positive"):
    menu = [_item("A", "inside", 680), _item("B", "baseline", 679), _item("C", "outer", 678)]
    return SpreadPickRecord(
        pick_id=pid,
        created_at=T,
        day=date(2026, 10, 7),
        episode_key=f"ep{pid}",
        book_mode="paper",
        menu=menu,
        choice=choice,
        reason="r",
        fallback_reason=fallback,
        executed_letter=executed,
        send_rejected=False,
        send_reasons=[],
        filled=executed is not None,
        model="m",
        effort="high",
        latency_ms=1,
        cost_usd=0.0,
        snapshot=SpreadPickSnapshot(regime=regime, move_em=0.8, side="put"),
        market=SpreadMarketSnapshot(vix=vix),
        prompt_text="P",
        raw_response="R",
    )


def _trade(mode, pnl, *, pick_id=None, episode=None, credit=0.48, status="closed"):
    return SpreadTradeRecord(
        spread_id=f"{mode}{episode}",
        mode=mode,
        side="put",
        status=status,
        opened_at=T,
        closed_at=T if status == "closed" else None,
        short_strike=679,
        long_strike=674,
        width=5,
        contracts=1,
        entry_credit=credit,
        pnl_usd=pnl,
        regime="positive",
        trigger="move",
        pick_id=pick_id,
        episode_key=episode,
    )


def test_decisions_line_the_books_up_and_classify_them() -> None:
    picks = [_pick(1, "C", "C"), _pick(2, "skip", None), _pick(3, "Z", "B", fallback="off_menu")]
    main = [
        _trade("paper", 30.0, pick_id=1, episode="ep1"),
        _trade("paper", 20.0, pick_id=3, episode="ep3"),
    ]
    base = [
        _trade("baseline", -100.0, episode="ep1"),
        _trade("baseline", 25.0, episode="ep2"),
        _trade("baseline", 22.0, episode="ep3"),
    ]
    d1, d2, d3 = build_decisions(picks, main, base)
    assert [d.kind for d in (d1, d2, d3)] == ["took_outer", "skipped", "fallback"]
    assert (d1.diff, d2.diff) == (130.0, -25.0)
    assert decision_kind(_pick(4, "B", "B")) == "took_baseline"


def test_condition_rows_mark_thin_buckets_as_noise() -> None:
    picks = [_pick(i, "skip", None, vix=14.0 if i < 6 else 25.0) for i in range(1, 8)]
    base = [_trade("baseline", 10.0, episode=f"ep{i}") for i in range(1, 8)]
    rows = compare_by(build_decisions(picks, [], base), "vix")
    assert rows["<15"].n == 5 and not rows["<15"].noise
    assert rows["20–30"].n == 2 and rows["20–30"].noise
    assert rows["<15"].diff_mean == -10.0


def test_an_open_trade_keeps_its_decision_out_of_the_comparison() -> None:
    picks = [_pick(1, "B", "B")]
    (d,) = build_decisions(
        picks, [_trade("paper", 0.0, pick_id=1, episode="ep1", status="open")], []
    )
    assert not d.settled
    assert compare_by([d], "regime") == {}


def test_the_compare_text_and_csv_rows() -> None:
    picks = [_pick(1, "C", "C")]
    main = [_trade("paper", 30.0, pick_id=1, episode="ep1", credit=0.44)]
    base = [_trade("baseline", -10.0, episode="ep1")]
    ds = build_decisions(picks, main, base)
    text = "\n".join(format_compare(ds, main, base, "paper", slippage_per_leg=0.02))
    assert "decisions: 1" in text and "fewer than 50 decisions" in text
    assert "took_outer" in text and "fill bias" in text
    (row,) = decision_rows(ds)
    assert row["kind"] == "took_outer" and row["diff_usd"] == 40.0 and row["vix"] == 17.0
    assert str(row["menu"]).startswith("A inside 680/675")


def test_the_day_view_prints_the_plan_prompt_and_reply() -> None:
    picks = [_pick(1, "C", "C")]
    main = [_trade("paper", 30.0, pick_id=1, episode="ep1")]
    base = [_trade("baseline", -10.0, episode="ep1")]
    text = "\n".join(format_day(date(2026, 10, 7), "day plan: none", picks, main, base))
    assert "=== 2026-10-07 ===" in text and "day plan: none" in text
    assert "took_outer" in text and "prompt:\nP" in text and "reply:\nR" in text
    assert "difference $40.00" in text
