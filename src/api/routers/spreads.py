"""GET /spreads/positions — read-only, through src/api/spreads_db.py (never src.spreads)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Query

from src.api.deps import OwnerUser
from src.api.models.common import as_utc, as_utc_opt
from src.api.models.spreads import SpreadPositionOut, SpreadPositionsResponse
from src.api.spreads_db import read_spread_rows, spreads_read_session
from src.common.config import get_config

router = APIRouter(prefix="/spreads", tags=["spreads"])


@router.get("/positions", response_model=SpreadPositionsResponse)
def spread_positions(
    user: OwnerUser,  # noqa: ARG001
    status: Literal["open", "closed", "all"] = "open",
    mode: Literal["paper", "shadow", "baseline"] = "paper",
    limit: int = Query(50, ge=1, le=500),
) -> SpreadPositionsResponse:
    now = datetime.now(UTC)
    underlying = get_config().spreads.underlying
    with spreads_read_session() as s:
        if s is None:
            return SpreadPositionsResponse(
                as_of=now, available=False, underlying=underlying, mode=mode
            )
        rows = read_spread_rows(s, mode=mode, status=status, limit=limit)
    positions = [
        SpreadPositionOut(
            as_of=now,
            **{
                **r,
                "opened_at": as_utc(r["opened_at"])
                if isinstance(r["opened_at"], datetime)
                else r["opened_at"],
                "closed_at": as_utc_opt(r["closed_at"])
                if isinstance(r["closed_at"], datetime)
                else r["closed_at"],
                "realized_pnl_usd": r["realized_pnl_usd"] if r["status"] == "closed" else None,
            },
        )
        for r in rows
    ]
    return SpreadPositionsResponse(
        as_of=now, available=True, underlying=underlying, mode=mode, positions=positions
    )
