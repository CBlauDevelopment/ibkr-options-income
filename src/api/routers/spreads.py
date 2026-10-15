"""GET /spreads/positions — read-only, through src/api/spreads_db.py (never src.spreads)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Query

from src.api.deps import OwnerUser
from src.api.models.spreads import SpreadPositionsResponse
from src.api.spread_inputs import spread_position_out
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
    positions = [spread_position_out(r, now) for r in rows]
    return SpreadPositionsResponse(
        as_of=now, available=True, underlying=underlying, mode=mode, positions=positions
    )
