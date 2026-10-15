"""GET /portfolio/positions/{underlying}/{slug} and GET /research/{symbol}/headlines - the
position page's data (web Home follow-ups, 2026-10-15)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from src.storage.models import ApprovalRow, CandidateRow, ClaudeReviewRow, FillRow
from tests.conftest import OWNER, short_put, stock

FAR = date(2099, 1, 15)
SLUG = "2099-01-15_P180"


@pytest.fixture()
def db(api_db):
    return api_db


@pytest.fixture(autouse=True)
def _no_real_spreads_db(tmp_path, monkeypatch):
    import src.api.spreads_db as sdb

    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(tmp_path / "no-spreads.db"))
    sdb.reset_engine()
    yield
    sdb.reset_engine()


def seed_leg(db, cid="c1", *, strike=180.0, closed_at=None, reason=None, symbol="AAPL", right="P"):
    sold_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=12)
    with db() as s:
        s.add(
            CandidateRow(
                candidate_id=cid, run_id="r", strategy="cash_secured_put" if right == "P" else "covered_call",
                underlying=symbol, right=right, strike=strike, expiry=FAR, payload={},
            )
        )  # fmt: skip
        s.add(
            FillRow(order_id=1, candidate_id=cid, action="SELL", filled_qty=1, avg_price=2.35,
                    commission=1.3, filled_at=sold_at)
        )  # fmt: skip
        if closed_at is not None:
            s.add(
                FillRow(order_id=2, candidate_id=cid, action="BUY", filled_qty=1, avg_price=0.62,
                        commission=1.3, close_reason=reason, filled_at=closed_at)
            )  # fmt: skip
        s.add(ApprovalRow(candidate_id=cid, status="approved"))
        s.add(ClaudeReviewRow(candidate_id=cid, recommendation="sell",
                              payload={"why_attractive": "IV rank 62.", "summary": "Fine."}))  # fmt: skip


def held(seed_portfolio_snapshot, **over):
    seed_portfolio_snapshot(
        positions=[short_put(symbol="AAPL  990115P00180000", strike=180.0, expiry=FAR, underlying="AAPL"),
                   stock(symbol="AAPL", shares=100, avg_cost=181.0, market_price=184.0)]
    )  # fmt: skip


def get(client, underlying, slug):
    return client.get(f"/portfolio/positions/{underlying}/{slug}", headers=OWNER)


def test_a_held_contract_gives_its_live_leg_and_the_trade_that_opened_it(
    client, db, seed_portfolio_snapshot
) -> None:
    seed_leg(db)
    held(seed_portfolio_snapshot)
    r = get(client, "AAPL", SLUG)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["kind"], body["held"], body["underlying"], body["slug"]) == (
        "option",
        True,
        "AAPL",
        SLUG,
    )
    assert (
        body["option"]["strike"] == 180.0
        and body["option"]["short"] is True
        and body["option"]["contracts"] == 1
    )
    assert body["stock"]["shares"] == 100  # the shares held beside it
    opened = body["opened"]
    assert opened["action"] == "opened" and opened["kind"] == "csp"
    assert opened["premium"] == pytest.approx(235.0) and opened["commissions"] == pytest.approx(1.3)
    assert opened["capital"] == pytest.approx(18_000.0)
    assert opened["review"]["why_attractive"] == "IV rank 62."
    assert opened["approval_id"] is not None
    assert body["closed"] is None


def test_a_contract_no_longer_held_says_how_it_ended(client, db, seed_portfolio_snapshot) -> None:
    seed_leg(
        db,
        closed_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
        reason="profit_take",
    )
    seed_portfolio_snapshot(positions=[stock(symbol="AAPL")])
    body = get(client, "AAPL", SLUG).json()
    assert body["held"] is False and body["option"] is None
    assert body["closed"]["action"] == "closed" and body["closed"]["how"] == "bought_back"
    assert "profit" in body["closed"]["reason"]
    assert body["closed"]["net_pnl"] == pytest.approx(235 - 62 - 2.6)
    assert body["opened"]["premium"] == pytest.approx(235.0)


def test_a_held_contract_the_system_never_traded_still_answers_without_an_opening(
    client, seed_portfolio_snapshot
) -> None:
    held(seed_portfolio_snapshot)  # in the snapshot, no fills
    body = get(client, "AAPL", SLUG).json()
    assert body["held"] is True and body["opened"] is None and body["closed"] is None


@pytest.mark.parametrize(
    "slug", ["2099-01-15_P999", "nonsense", "2099-13-45_P180", "2099-01-15_X180", "spread-nope"]
)
def test_an_unknown_or_malformed_slug_is_404(client, db, seed_portfolio_snapshot, slug) -> None:
    seed_leg(db)
    held(seed_portfolio_snapshot)
    assert get(client, "AAPL", slug).status_code in (404, 503)
    assert get(client, "ZZZZ", SLUG).status_code == 404


def test_shares_give_the_stock_leg_and_the_wheel_thread_behind_them(
    client, seed_portfolio_snapshot, seed_assigned_campaign
) -> None:
    seed_assigned_campaign(symbol="AAPL", assignment_price=180.0, adjusted_basis=173.5)
    seed_portfolio_snapshot(
        positions=[stock(symbol="AAPL", shares=100, avg_cost=180.0, market_price=176.0)]
    )
    body = get(client, "AAPL", "shares").json()
    assert body["kind"] == "shares" and body["held"] is True
    assert body["stock"]["shares"] == 100 and body["stock"]["avg_cost"] == 180.0
    assert body["stock"]["adjusted_cost_basis"] == pytest.approx(173.5)
    assert body["campaign"]["assigned"] is True
    assert get(client, "MSFT", "shares").status_code == 404


def test_a_spread_gives_its_row_and_its_opening_and_closing_cards(
    client, monkeypatch, tmp_path
) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    import src.api.spreads_db as sdb
    from src.spreads.store import SpreadPositionRow, SpreadsBase

    path = tmp_path / "spreads.db"
    eng = create_engine(f"sqlite:///{path}")
    SpreadsBase.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(
            SpreadPositionRow(
                spread_id="p1", mode="paper", side="put", expiry=date(2026, 10, 9), short_strike=580.0,
                long_strike=575.0, width=5.0, contracts_opened=2, contracts=0, entry_credit=0.84,
                entry_commission=2.6, opened_at=datetime(2026, 10, 9, 14), status="closed",
                closed_at=datetime(2026, 10, 9, 18), exit_debit=0.2, exit_commission=2.6,
                exit_reason="profit_take", realized_pnl_usd=123.6,
            )
        )  # fmt: skip
        s.commit()
    eng.dispose()
    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(path))
    sdb.reset_engine()

    body = get(client, "SPY", "spread-p1").json()
    assert body["kind"] == "spread" and body["held"] is False
    assert body["spread"]["short_strike"] == 580.0 and body["spread"][
        "realized_pnl_usd"
    ] == pytest.approx(123.6)
    assert body["opened"]["kind"] == "spread" and body["opened"]["premium"] == pytest.approx(168.0)
    assert body["closed"]["how"] == "bought_back" and body["closed"]["net_pnl"] == pytest.approx(
        123.6
    )
    assert get(client, "SPY", "spread-zzz").status_code == 404


def test_an_unreadable_spreads_book_is_a_503_not_a_missing_spread(client) -> None:
    assert get(client, "SPY", "spread-p1").status_code == 503


def test_the_position_page_needs_the_owner(client) -> None:
    assert client.get(f"/portfolio/positions/AAPL/{SLUG}").status_code in (401, 403)


# --- headlines -----------------------------------------------------------------------------


def _items():
    return [
        {"title": "Older", "url": "https://x/1", "published_at": datetime(2026, 10, 14, tzinfo=UTC), "source": "A", "sentiment": 0.1},
        {"title": "Newest", "url": "https://x/2", "published_at": datetime(2026, 10, 15, tzinfo=UTC), "source": "B", "sentiment": -0.4},
        {"title": "", "url": None, "published_at": None, "source": None, "sentiment": None},
        {"title": "Undated", "url": None, "published_at": None, "source": None, "sentiment": None},
    ]  # fmt: skip


def test_headlines_come_newest_first_without_blank_titles(client, monkeypatch) -> None:
    import src.research.ingest.news as news

    monkeypatch.setattr(news, "recent_news", lambda symbol, limit=25: _items())
    body = client.get("/research/aapl/headlines", headers=OWNER).json()
    assert body["symbol"] == "AAPL"
    assert [i["title"] for i in body["items"]] == ["Newest", "Older", "Undated"]
    assert body["items"][0]["sentiment"] == -0.4 and body["items"][0]["source"] == "B"


def test_headlines_honour_the_limit_and_an_unreachable_source_is_an_empty_list(
    client, monkeypatch
) -> None:
    import src.research.ingest.news as news

    monkeypatch.setattr(news, "recent_news", lambda symbol, limit=25: _items())
    assert len(client.get("/research/AAPL/headlines?limit=1", headers=OWNER).json()["items"]) == 1
    monkeypatch.setattr(news, "recent_news", lambda symbol, limit=25: [])
    r = client.get("/research/AAPL/headlines", headers=OWNER)
    assert r.status_code == 200 and r.json()["items"] == []


def test_headlines_refuse_what_is_not_a_ticker(client) -> None:
    assert client.get("/research/not%20a%20ticker/headlines", headers=OWNER).status_code in (
        404,
        422,
    )
    assert client.get("/research/AAPL/headlines?limit=500", headers=OWNER).status_code == 422
