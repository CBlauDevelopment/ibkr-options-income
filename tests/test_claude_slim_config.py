"""Config for the slim headless call (2026-10-15 token-weight work): the workdir that keeps the
repo's CLAUDE.md out of every `claude -p` call, the per-call-kind model, and the two reuse /
info-alert switches. See STATUS.md "Headless call weight"."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.common.config import ROOT, ClaudeCfg, get_config

_EXAMPLE = Path(__file__).resolve().parents[1] / "config" / "examples" / "settings.yaml"


def test_defaults_are_the_cheap_safe_ones() -> None:
    c = ClaudeCfg()
    assert c.slim_context is True
    assert c.review_info_alerts is False
    assert c.review_reuse_minutes == 120
    # every call kind follows `claude.model` (Sonnet): the 2026-10-15 audit found Haiku understated
    # risk in 8 of 8 scan reviews, so no kind is routed to a cheaper model by default
    assert c.review_model == c.roll_model == c.eod_model == ""


def test_model_for_falls_back_to_the_shared_model() -> None:
    c = ClaudeCfg(model="sonnet-x", review_model="haiku-x")
    assert c.model_for("review") == "haiku-x"
    assert ClaudeCfg(model="sonnet-x", review_model="").model_for("review") == "sonnet-x"
    assert c.model_for("roll") == "sonnet-x"  # roll_model left empty
    assert c.model_for("eod") == "sonnet-x"


def test_default_workdir_is_outside_the_repo_and_expanded() -> None:
    wd = get_config().claude_workdir()
    assert wd.is_absolute() and "~" not in str(wd)
    assert wd != ROOT and ROOT not in wd.parents  # claude walks up from cwd looking for CLAUDE.md


@pytest.mark.parametrize("bad", ["relative/dir", "", str(ROOT), str(ROOT / "scratch")])
def test_workdir_must_be_absolute_and_outside_the_repo(bad: str) -> None:
    with pytest.raises(ValidationError):
        ClaudeCfg(workdir=bad)


def test_tilde_workdir_is_accepted() -> None:
    assert ClaudeCfg(workdir="~/.cache/somewhere").workdir == "~/.cache/somewhere"


def test_negative_reuse_window_is_refused() -> None:
    with pytest.raises(ValidationError):
        ClaudeCfg(review_reuse_minutes=-1)


def test_code_defaults_match_the_shipped_yaml() -> None:
    """A private config missing these keys must behave exactly like the template."""
    shipped = yaml.safe_load(_EXAMPLE.read_text())["claude"]
    d = ClaudeCfg()
    for key in (
        "slim_context",
        "workdir",
        "review_model",
        "roll_model",
        "eod_model",
        "review_info_alerts",
        "review_reuse_minutes",
    ):
        assert getattr(d, key) == shipped[key], key
