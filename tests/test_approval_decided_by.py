"""approvals.decided_by - who decided each approval (web overhaul Part 2, Task 2).

A record for the console, never an input: written where an approval is decided, read by the
API, and by nothing on the trading path.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from src.common.schemas import Strategy
from src.storage.models import ApprovalRow
from tests.test_roll_pipeline import _cand as _roll_cand

ROOT = Path(__file__).resolve().parents[1]


def _pending(db, candidate_id: str = "c1") -> int:
    with db() as s:
        row = ApprovalRow(
            candidate_id=candidate_id,
            status="pending",
            chat_id="9",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        s.add(row)
        s.flush()
        return row.id


def _decided_by(db, approval_id: int) -> str | None:
    with db() as s:
        return s.get(ApprovalRow, approval_id).decided_by


def test_a_tap_in_telegram_is_recorded_as_telegram(db) -> None:
    from src.notify.approval_service import _process_button

    approve, reject = _pending(db, "a"), _pending(db, "b")
    _process_button(approve, "approve")
    _process_button(reject, "reject")
    assert _decided_by(db, approve) == "telegram"
    assert _decided_by(db, reject) == "telegram"


def test_the_drain_names_the_web(db) -> None:
    # The drain's handler calls this indirection with (approval_id, action) exactly as before;
    # only the indirection adds who decided.
    from src.notify.command_drain import _process_button as via_drain

    approval_id = _pending(db)
    found, _text, _short = via_drain(approval_id, "approve")
    assert found
    assert _decided_by(db, approval_id) == "web"


def test_a_second_decision_never_overwrites_the_first(db) -> None:
    from src.notify.approval_service import _process_button
    from src.notify.command_drain import _process_button as via_drain

    approval_id = _pending(db)
    _process_button(approval_id, "approve")
    _found, text, _short = via_drain(approval_id, "approve")
    assert text.startswith("Already")
    assert _decided_by(db, approval_id) == "telegram"


def test_an_auto_approved_roll_is_recorded_as_the_system(db) -> None:
    from src.execution.roll_pipeline import queue_roll_candidate

    approval_id = queue_roll_candidate(
        _roll_cand(), chat_id="9", ttl_minutes=120, auto_approve=True
    )
    assert approval_id is not None
    assert _decided_by(db, approval_id) == "system"


def test_a_roll_waiting_for_a_tap_has_no_decider_yet(db) -> None:
    from src.execution.roll_pipeline import queue_roll_candidate

    approval_id = queue_roll_candidate(_roll_cand(), chat_id="9", ttl_minutes=120)
    assert approval_id is not None
    assert _decided_by(db, approval_id) is None


async def test_the_entry_auto_queue_is_recorded_as_the_system(db, monkeypatch) -> None:
    import src.notify.sender as sender

    class _Bot:
        def __init__(self, token: str) -> None:
            self.token = token

        async def __aenter__(self) -> _Bot:
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        async def send_message(self, **_: object) -> None:
            return None

    monkeypatch.setattr(sender, "is_halted", lambda: False)
    monkeypatch.setattr(sender, "Bot", _Bot)
    monkeypatch.setattr(sender, "format_auto_trade_notification", lambda queued: "queued")
    cand = _roll_cand().model_copy(
        update={
            "candidate_id": "csp-aapl-195",
            "strategy": Strategy.CASH_SECURED_PUT,
            "roll_from": None,
        }
    )
    cfg = SimpleNamespace(approval=SimpleNamespace(ttl_minutes=60), is_live=False)

    assert await sender._auto_queue_candidates([cand], cfg, "token", "chat", None) is True
    with db() as s:
        row = s.query(ApprovalRow).filter_by(candidate_id="csp-aapl-195").one()
        assert (row.status, row.decided_by) == ("approved", "system")


def test_an_expiry_leaves_it_unset(db) -> None:
    from src.storage.approvals import expire_stale_approvals

    approval_id = _pending(db)
    expire_stale_approvals(force=True)
    with db() as s:
        row = s.get(ApprovalRow, approval_id)
        assert (row.status, row.decided_by) == ("expired", None)


def test_the_trading_path_never_reads_who_decided() -> None:
    """decided_by is a record for the console. The engine and the strategies never mention it;
    execution only writes it, once, where the roll pipeline auto-approves."""
    hits = []
    for pkg in ("engine", "strategies", "execution"):
        for path in sorted((ROOT / "src" / pkg).rglob("*.py")):
            for line in path.read_text().splitlines():
                if "decided_by" in line:
                    hits.append((path.relative_to(ROOT).as_posix(), line.strip()))
    assert hits == [
        ("src/execution/roll_pipeline.py", 'decided_by="system" if auto_approve else None,'),
    ]
