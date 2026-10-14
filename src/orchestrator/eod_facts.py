"""Deterministic facts for the EOD report (2026-10-14 rebuild).

The old report handed Claude a handful of totals and printed the scan watchlist as
"Tomorrow", so the narrative guessed at what happened ("likely reflects new or rolled
options") and the forward-looking line said nothing. Everything here is read from the
system of record — fills, the roll-policy decision log, the position snapshots, and the news
calendar — so the report states what happened and what is coming, and the narrative only
interprets it.

Read-only: nothing in this module writes. Every loader degrades to "no data" rather than
raising, so a missing table or a missing news.db never blocks the EOD send.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from src.common.market_hours import next_session, previous_session
from src.common.schemas import (
    CloseReason,
    EODDecision,
    EODTrade,
    EODWatch,
    OptionRight,
    PositionSnapshot,
    VerdictOutcome,
)
from src.notify.formatters import contract_label
from src.storage.db import session_scope
from src.storage.models import JournalRow, RollAlertRow
from src.storage.portfolio_snapshots import load_latest_portfolio_snapshot
from src.storage.positions import load_latest_position_snapshot

log = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

_CLOSE_REASON = {
    CloseReason.PROFIT_TAKE: "profit take",
    CloseReason.LOSS_EXIT: "loss exit",
    CloseReason.ROLL: "rolled",
    CloseReason.MANUAL: "closed outside the system",
    CloseReason.DEFENSIVE: "defensive close",
}

# How far ahead "expiring soon" and "earnings soon" look, in calendar days from the report date.
_EXPIRY_LOOKAHEAD_DAYS = 7
_EARNINGS_LOOKAHEAD_DAYS = 7


def _et_midnight_utc(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=_ET).astimezone(UTC)


def _naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


# ---------------------------------------------------------------------------
# Baseline — the previous session's close
# ---------------------------------------------------------------------------


@dataclass
class Baseline:
    """Where today's changes are measured from."""

    as_of: date
    unrealized: float
    nlv: float | None
    by_underlying: dict[str, float] = field(default_factory=dict)


def _by_underlying(positions: list[PositionSnapshot]) -> dict[str, float]:
    out: dict[str, float] = {}
    for p in positions:
        if p.unrealized_pnl is None:
            continue
        sym = p.underlying or p.symbol
        out[sym] = out.get(sym, 0.0) + p.unrealized_pnl
    return out


def load_baseline(today: date) -> Baseline | None:
    """The previous session's close, or the nearest record of it.

    Order of preference: the previous session's journal row (written at its EOD); otherwise
    whichever is more recent of the latest earlier journal row and the last intraday portfolio
    snapshot captured before today. The snapshot fallback is what keeps a missed EOD (a hung
    run, a Mac asleep through the report) from turning the next day's change into the whole
    unrealised figure. None only when nothing at all is on record.
    """
    prev = previous_session(today)
    journal: Baseline | None = None
    try:
        with session_scope() as s:
            row = (
                s.query(JournalRow)
                .filter(JournalRow.entry_date < today)
                .order_by(JournalRow.entry_date.desc())
                .first()
            )
            if row is not None:
                acct = ((row.payload or {}).get("eod_summary") or {}).get("account") or {}
                nlv = acct.get("net_liquidation")
                journal = Baseline(
                    as_of=row.entry_date,
                    unrealized=float(row.unrealized_pnl or 0.0),
                    nlv=float(nlv) if nlv is not None else None,
                )
    except Exception:
        log.exception("EOD: journal baseline lookup failed")

    if journal is not None and journal.as_of >= prev:
        stored = load_latest_position_snapshot(before=today)
        journal.by_underlying = _by_underlying(stored)
        return journal

    snap = load_latest_portfolio_snapshot(before=_et_midnight_utc(today))
    if snap is not None:
        snap_day = snap.captured_at.astimezone(_ET).date()
        if journal is None or snap_day > journal.as_of:
            return Baseline(
                as_of=snap_day,
                unrealized=sum(p.unrealized_pnl or 0.0 for p in snap.positions),
                nlv=snap.account.net_liquidation if snap.account is not None else None,
                by_underlying=_by_underlying(snap.positions),
            )
    if journal is not None:
        journal.by_underlying = _by_underlying(load_latest_position_snapshot(before=today))
    return journal


def movers(
    positions: list[PositionSnapshot], baseline: Baseline | None, n: int = 3
) -> dict[str, float]:
    """The *n* held underlyings whose unrealised P&L moved most since the baseline."""
    now = _by_underlying(positions)
    base = baseline.by_underlying if baseline is not None else {}
    change = {sym: v - base.get(sym, 0.0) for sym, v in now.items()}
    ranked = sorted(change.items(), key=lambda kv: abs(kv[1]), reverse=True)[:n]
    return {sym: v for sym, v in ranked if abs(v) >= 0.5}


# ---------------------------------------------------------------------------
# Today's activity
# ---------------------------------------------------------------------------


def _label(underlying: str, strike: float, right: OptionRight | str, expiry: date) -> str:
    return contract_label(underlying, strike, right, expiry).replace("$", "")


def todays_trades(today: date, since: date | None = None) -> list[EODTrade]:
    """Opens, closes and expiries on the option legs, from the fills (``build_legs``)."""
    from src.reporting.pnl import build_legs

    start = _naive_utc(_et_midnight_utc(today))
    end = _naive_utc(_et_midnight_utc(today + timedelta(days=1)))
    since = since or previous_session(today)
    try:
        # build_legs only uses ``with factory() as s``; session_scope yields a Session the same
        # way (and commits nothing — build_legs never writes).
        legs = build_legs(session_scope, since=today - timedelta(days=400))  # type: ignore[arg-type]
    except Exception:
        log.exception("EOD: build_legs failed — no trade list")
        return []

    out: list[EODTrade] = []
    for leg in sorted(legs, key=lambda x: x.opened_at):
        label = _label(leg.underlying, leg.strike, leg.right, leg.expiry)
        n = max(leg.contracts, 1)
        if start <= _naive_utc(leg.opened_at) < end:
            out.append(
                EODTrade(
                    action="opened",
                    label=label,
                    underlying=leg.underlying,
                    contracts=leg.contracts,
                    price=leg.credit / (n * 100),
                    reason=leg.strategy.value,
                )
            )
        closed = leg.closed_at is not None and start <= _naive_utc(leg.closed_at) < end
        if leg.outcome == VerdictOutcome.CLOSED_EARLY and closed:
            reason = _CLOSE_REASON.get(leg.close_reason) if leg.close_reason else None
            out.append(
                EODTrade(
                    action="rolled" if leg.close_reason == CloseReason.ROLL else "closed",
                    label=label,
                    underlying=leg.underlying,
                    contracts=leg.contracts,
                    price=leg.debit / (n * 100),
                    pnl=leg.net_pnl,
                    reason=reason,
                )
            )
        elif leg.outcome == VerdictOutcome.EXPIRED_WORTHLESS and since < leg.expiry <= today:
            out.append(
                EODTrade(
                    action="expired",
                    label=label,
                    underlying=leg.underlying,
                    contracts=leg.contracts,
                    pnl=leg.net_pnl,
                    reason="expired worthless",
                )
            )
    return out


def assignment_trades(assigned: list) -> list[EODTrade]:  # list[OpenShort]
    out: list[EODTrade] = []
    for sh in assigned:
        right = "C" if str(sh.right).upper().startswith("C") else "P"
        shares = int(round(abs(sh.contracts) * 100))
        verb = "called away" if right == "C" else "assigned"
        out.append(
            EODTrade(
                action="assigned",
                label=_label(sh.underlying, sh.strike, right, sh.expiry),
                underlying=sh.underlying,
                contracts=int(round(abs(sh.contracts))),
                price=sh.strike,
                reason=f"{shares} shares {verb} at ${sh.strike:g}",
            )
        )
    return out


def occ_label(symbol: str) -> str:
    """``"TQQQ  261016P00078000"`` → ``"TQQQ 78P Oct 16"``; anything else comes back tidied."""
    compact = "".join(symbol.split())
    if len(compact) > 15 and compact[-9] in "CP":
        try:
            underlying = compact[:-15]
            expiry = datetime.strptime(compact[-15:-9], "%y%m%d").date()
            strike = int(compact[-8:]) / 1000
            return _label(underlying, strike, compact[-9], expiry)
        except ValueError:
            pass
    return " ".join(symbol.split())


def todays_decisions(today: date) -> list[EODDecision]:
    """Roll-policy decisions sent today (one per position, the latest)."""
    start = _naive_utc(_et_midnight_utc(today))
    try:
        with session_scope() as s:
            rows = (
                s.query(RollAlertRow)
                .filter(RollAlertRow.trigger == "roll_decision", RollAlertRow.created_at >= start)
                .order_by(RollAlertRow.created_at)
                .all()
            )
            latest: dict[str, tuple[str, dict]] = {}
            for r in rows:
                latest[r.position_symbol] = (r.underlying, dict(r.payload or {}))
    except Exception:
        log.exception("EOD: roll decision lookup failed")
        return []
    out: list[EODDecision] = []
    for symbol, (_underlying, payload) in latest.items():
        d = payload.get("decision") or {}
        out.append(
            EODDecision(
                label=occ_label(symbol),
                action=str(d.get("action") or "?"),
                reason=str(d.get("reason") or ""),
                detail=d.get("detail"),
            )
        )
    return out


# ---------------------------------------------------------------------------
# What is coming
# ---------------------------------------------------------------------------


def watch_items(
    positions: list[PositionSnapshot], today: date, *, breach_delta: float
) -> list[EODWatch]:
    """Macro events next session, breached shorts, shorts expiring this week, earnings."""
    nxt = next_session(today)
    out: list[EODWatch] = []
    out += _macro(nxt)

    shorts = [
        p
        for p in positions
        if p.sec_type == "OPT"
        and p.position < 0
        and p.expiry is not None
        and p.strike is not None
        and p.right is not None
    ]
    horizon = today + timedelta(days=_EXPIRY_LOOKAHEAD_DAYS)
    for p in sorted(shorts, key=lambda x: (x.expiry, x.underlying or x.symbol)):
        assert p.expiry is not None and p.strike is not None and p.right is not None
        label = _label(p.underlying or p.symbol, p.strike, p.right, p.expiry)
        qty = int(abs(p.position))
        delta = abs(p.delta) if p.delta is not None else None
        dtxt = f" (Δ {delta:.2f})" if delta is not None else ""
        if delta is not None and delta >= breach_delta:
            when = f"expires {p.expiry:%a %d %b}"
            out.append(
                EODWatch(
                    kind="breach",
                    text=f"{label} ×{qty} in the money{dtxt}, {when} — roll / assign decision",
                )
            )
        elif p.expiry <= horizon:
            out.append(
                EODWatch(kind="expiring", text=f"{label} ×{qty} expires {p.expiry:%a}{dtxt}")
            )

    held = {p.underlying or p.symbol for p in positions}
    out += _earnings(held, nxt, today + timedelta(days=_EARNINGS_LOOKAHEAD_DAYS))
    return out


def _macro(day: date) -> list[EODWatch]:
    try:
        from src.news.store.queries import econ_events_between
        from src.news.store.readonly import read_only_session

        with read_only_session() as s:
            if s is None:
                return []
            events = econ_events_between(
                s, _et_midnight_utc(day), _et_midnight_utc(day + timedelta(days=1))
            )
    except Exception:
        log.exception("EOD: macro calendar lookup failed")
        return []
    by_time: dict[str, list[str]] = {}
    for e in events:
        if (e.impact or "").lower() != "high":
            continue
        t = f"{e.scheduled_at.astimezone(_ET):%H:%M} ET"
        name = e.title
        if e.forecast:
            name += f" (f'cast {e.forecast})"
        by_time.setdefault(t, []).append(name)
    return [
        EODWatch(kind="macro", text=f"{day:%a} {t}: {', '.join(names)}")
        for t, names in by_time.items()
    ]


def _earnings(held: set[str], start: date, end: date) -> list[EODWatch]:
    if not held:
        return []
    try:
        from src.news.store.queries import earnings_between
        from src.news.store.readonly import read_only_session

        with read_only_session() as s:
            if s is None:
                return []
            rows = earnings_between(s, start, end, symbols=held)
    except Exception:
        log.exception("EOD: earnings calendar lookup failed")
        return []
    out: list[EODWatch] = []
    for r in rows:
        timing = f" {r.timing}" if r.timing else ""
        out.append(
            EODWatch(kind="earnings", text=f"{r.symbol} earnings {r.report_date:%a %d %b}{timing}")
        )
    return out
