"""Read-only access to data/spreads.db for the web API (web overhaul Part 1, Task 8).

The spreads fence forbids src/api from importing src.spreads, so this module opens the file
itself with SQLite mode=ro and reads it with plain SQL. It yields None when the file does not
exist yet or cannot be opened (or is not a SQLite database), so a route answers
`available: false` instead of a 500.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Date, DateTime, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.common.config import get_config

log = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None

_COLUMNS = (
    "spread_id, mode, side, expiry, short_strike, long_strike, width, contracts_opened, "
    "contracts, entry_credit, entry_commission, opened_at, status, exit_debit, "
    "exit_commission, exit_reason, closed_at, realized_pnl_usd"
)


def _resolve_path() -> str:
    """Filesystem path of data/spreads.db. Patched in tests."""
    url = get_config().spreads_db_url_abs()
    return url[len("sqlite:///") :] if url.startswith("sqlite:///") else url


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def spreads_read_session() -> Iterator[Session | None]:
    global _engine, _SessionLocal
    path = _resolve_path()
    if not Path(path).exists():
        yield None
        return
    s: Session | None = None
    try:
        if _engine is None:
            _engine = create_engine(
                f"sqlite:///file:{path}?mode=ro&uri=true",
                future=True,
                connect_args={"timeout": 5},
            )
            _SessionLocal = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
        assert _SessionLocal is not None
        s = _SessionLocal()
        # Reads the schema page: `SELECT 1` never touches the file, so a file that is not a
        # SQLite database would pass it and then read as an empty book.
        s.execute(text("SELECT count(*) FROM sqlite_master"))
    except Exception as exc:  # noqa: BLE001 - a /spreads route degrades, never 500s
        log.debug("api spreads_db: cannot open %s: %s", path, exc)
        if s is not None:
            s.close()
        yield None
        return
    try:
        yield s
    finally:
        s.close()


def try_read_spread_rows(
    session: Session, *, mode: str, status: str, limit: int
) -> list[dict[str, Any]] | None:
    """spread_positions rows as dicts, newest first, or None when the read failed (a missing
    table on an old file). `status` is open|closed|all; "open" includes "expiring" (still
    held, settling today)."""
    where = "mode = :mode"
    if status == "open":
        where += " AND status IN ('open', 'expiring')"
    elif status == "closed":
        where += " AND status = 'closed'"
    # Typed, so SQLite's stored strings come back as date/datetime (naive UTC, as written).
    sql = text(
        f"SELECT {_COLUMNS} FROM spread_positions WHERE {where} ORDER BY opened_at DESC LIMIT :limit"
    ).columns(expiry=Date, opened_at=DateTime, closed_at=DateTime)
    try:
        result = session.execute(sql, {"mode": mode, "limit": limit})
    except Exception as exc:  # noqa: BLE001 - the caller decides what unreadable means
        log.debug("api spreads_db: read failed: %s", exc)
        return None
    return [dict(r._mapping) for r in result]


def read_spread_rows(
    session: Session, *, mode: str, status: str, limit: int
) -> list[dict[str, Any]]:
    """`try_read_spread_rows`, with a failed read (a missing table on an old file) as empty."""
    rows = try_read_spread_rows(session, mode=mode, status=status, limit=limit)
    return rows if rows is not None else []
