from __future__ import annotations

from src.common.config import get_config
from src.spreads_ai.picker import ClaudePicker


def test_the_entrypoint_builds_a_claude_picker() -> None:
    from scripts.run_spreads import make_picker

    cfg = get_config()
    p = make_picker(cfg)
    assert isinstance(p, ClaudePicker)
    assert p.cli_command == cfg.claude.cli_command and p.workdir == cfg.spreads_ai_workdir()
