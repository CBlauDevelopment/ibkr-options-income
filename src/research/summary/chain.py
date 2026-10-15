"""``claude_cli_then_ollama`` summary backend: claude -p, then the local model.

Falls back on every claude failure except a timeout (``cli.should_fall_back``). The provider's
self-reported ``Summary.model`` names whichever model wrote the summary.
"""

from __future__ import annotations

import logging

from src.claude.cli import should_fall_back
from src.research.summary.claude_cli import ClaudeCliSummaryProvider
from src.research.summary.context import ResearchContext
from src.research.summary.ollama import OllamaSummaryProvider
from src.research.summary.protocol import Summary

log = logging.getLogger(__name__)


class ClaudeCliThenOllamaSummaryProvider:
    def __init__(self) -> None:
        self._cli = ClaudeCliSummaryProvider()
        self._ollama = OllamaSummaryProvider()

    def generate(self, context: ResearchContext) -> Summary | None:
        summary, error = self._cli.generate_with_error(context)
        if summary is None and should_fall_back(error):
            log.warning("summary: claude unavailable (%s) — using ollama", error)
            return self._ollama.generate(context)
        return summary
