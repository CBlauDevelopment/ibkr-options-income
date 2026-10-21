"""Tests for _NoiseFilter — collapses the IBKR error-callback flood (see scan logs)."""

from __future__ import annotations

import logging

from src.common.logging import _NoiseFilter


def _record(name: str, msg: str, levelno: int = logging.ERROR) -> logging.LogRecord:
    return logging.LogRecord(
        name=name, level=levelno, pathname="x.py", lineno=1, msg=msg, args=(), exc_info=None
    )


def test_truncates_overly_long_messages():
    f = _NoiseFilter()
    rec = _record("ib_async.wrapper", "Error 354" + "&BEST/OPT/Top" * 100)
    assert f.filter(rec) is True
    assert len(rec.getMessage()) <= _NoiseFilter._MAX_LEN + 40
    assert "truncated" in rec.getMessage()


def test_suppresses_runs_of_near_identical_messages():
    f = _NoiseFilter()

    decisions = []
    for i in range(6):
        rec = _record(
            "ib_async.wrapper", f"Error 300, reqId 1792{i}: Can't find EId with tickerId:1792{i}"
        )
        decisions.append(f.filter(rec))

    # First _SUPPRESS_AFTER+1 pass through (identical 120-char prefix), rest suppressed.
    assert decisions[:3] == [True, True, True]
    assert all(d is False for d in decisions[3:])


def test_repeat_count_resets_on_distinct_message(caplog):
    f = _NoiseFilter()
    logger_name = "ib_async.wrapper"

    for i in range(5):
        f.filter(_record(logger_name, f"Error 300, reqId {i}: Can't find EId with tickerId:{i}"))

    with caplog.at_level(logging.ERROR, logger=logger_name):
        rec = _record(logger_name, "scan: processing SOFI")
        assert f.filter(rec) is True

    assert any("suppressed" in r.message for r in caplog.records)


def test_the_suppressed_summary_keeps_the_level_of_the_run_it_summarises(caplog):
    """A run of INFO lines cut off by an ERROR used to log "ERROR … (suppressed N …)": the
    summary took the interrupting record's level, so 12 harmless "ledger ingest: no-op" lines
    read as an error storm in the logs (approval.log carries 150+ phantom ledger ERRORs)."""
    f = _NoiseFilter()
    for _ in range(6):
        f.filter(_record("src.ledger.ingest", "ledger ingest (live ): no-op", logging.INFO))

    with caplog.at_level(logging.DEBUG, logger="src.ledger.ingest"):
        f.filter(_record("ib_async.wrapper", "Error 300, reqId 1: Can't find EId", logging.ERROR))

    summary = [r for r in caplog.records if "suppressed" in r.message]
    assert [(r.name, r.levelno) for r in summary] == [("src.ledger.ingest", logging.INFO)]


_CAP_322 = (
    "Error 322, reqId 1297: Error processing request.-'ReqAccountSummary(62)' : cause - "
    "Maximum number of account summary requests exceeded; desubscribe to previous request first"
)


def test_the_account_summary_cap_is_logged_as_info_not_error():
    """Every Gateway flap makes a second connection's auto-resubscribe hit IBKR's one-summary
    cap (Error 322): ~2,000 red lines in monitor.log/approval.log, though the connection that
    holds the subscription is unaffected. Kept (a real empty-summary failure must stay
    greppable) but not at ERROR."""
    f = _NoiseFilter()
    rec = _record("ib_async.wrapper", _CAP_322)
    assert f.filter(rec) is True
    assert (rec.levelno, rec.levelname) == (logging.INFO, "INFO")
    assert f.filter(rec) is True  # a second handler sees the same record: still INFO, once
    assert rec.getMessage() == _CAP_322


def test_only_the_account_summary_cap_is_demoted():
    f = _NoiseFilter()
    other = _record("ib_async.wrapper", "Error 322, reqId 9: Duplicate ticker ID")
    assert f.filter(other) is True and other.levelno == logging.ERROR
    elsewhere = _record("src.somewhere", _CAP_322)
    assert f.filter(elsewhere) is True and elsewhere.levelno == logging.ERROR


def test_suppresses_runs_that_alternate_option_right():
    """A chain probe fires 'Unknown contract' once per (strike, right) combo, alternating
    right='C'/'P' every other line. Since that token used to survive normalisation, it
    defeated the consecutive-repeat check and let a single symbol emit hundreds of
    un-suppressed lines (2026-08-27 incident)."""
    f = _NoiseFilter()

    decisions = []
    for i in range(6):
        strike = 485.0 + i * 2.5
        right = "C" if i % 2 == 0 else "P"
        # Since 2026-10-14 "Unknown contract" option probes are dropped outright; the right
        # normalisation still collapses other per-contract callbacks, e.g. Error 10091.
        rec = _record(
            "ib_async.wrapper",
            f"Error 10091, reqId {i}: Part of requested market data is not subscribed, "
            f"contract: Option(symbol='SMH', "
            f"lastTradeDateOrContractMonth='20261009', strike={strike}, right='{right}', "
            f"exchange='SMART')",
            levelno=logging.WARNING,
        )
        decisions.append(f.filter(rec))

    assert decisions[:3] == [True, True, True]
    assert all(d is False for d in decisions[3:])


def test_same_record_processed_by_multiple_handlers_is_idempotent():
    f = _NoiseFilter()
    rec = _record("ib_async.wrapper", "Error 300, reqId 1: Can't find EId with tickerId:1")
    first = f.filter(rec)
    second = f.filter(rec)
    assert first == second is True


def test_httpx_loggers_are_pinned_to_warning_even_at_debug(monkeypatch):
    """M8: httpx's INFO request line embeds the Flex token, so DEBUG must not unmute it."""
    import src.common.logging as lg
    from src.common.config import get_config

    saved = {n: logging.getLogger(n).level for n in ("httpx", "httpcore")}
    monkeypatch.setattr(lg, "_CONFIGURED", False)
    monkeypatch.setattr(get_config().logging, "level", "DEBUG")
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    try:
        lg.setup_logging()
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("httpcore").level == logging.WARNING
    finally:
        root.handlers[:] = handlers
        root.setLevel(level)
        for n, lv in saved.items():
            logging.getLogger(n).setLevel(lv)


def test_drops_option_strikes_ibkr_says_do_not_exist():
    # 2026-10-13: 2,301 of these lines in one session, interleaved wrapper/ib so the run
    # suppression never engaged. The contract cache already counts and remembers them.
    f = _NoiseFilter()
    err = _record(
        "ib_async.wrapper",
        "Error 200, reqId 5597: No security definition has been found for the request, "
        "contract: Option(symbol='VST', lastTradeDateOrContractMonth='20261030', strike=124.0, "
        "right='P', exchange='SMART', tradingClass='VST')",
    )
    unknown = _record(
        "ib_async.ib",
        "Unknown contract: Option(symbol='VST', lastTradeDateOrContractMonth='20261030', "
        "strike=124.0, right='P', exchange='SMART', tradingClass='VST')",
        logging.WARNING,
    )
    assert f.filter(err) is False
    assert f.filter(unknown) is False


def test_keeps_an_error_200_that_is_not_an_option_probe():
    f = _NoiseFilter()
    stock = _record(
        "ib_async.wrapper",
        "Error 200, reqId 9: No security definition has been found for the request, "
        "contract: Stock(symbol='XYZ', exchange='SMART', currency='USD')",
    )
    assert f.filter(stock) is True
    assert f.filter(_record("ib_async.ib", "Unknown contract: Stock(symbol='XYZ')")) is True
