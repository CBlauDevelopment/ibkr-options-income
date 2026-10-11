"""Claude picks the daily credit spread (docs/superpowers/specs/2026-10-12-spreads-claude-picker-design.md).

Enrichment only. It gathers context, prompts ``claude -p`` through src.claude.cli and returns a
menu letter. It never imports src.spreads or the trading path, and it writes nothing:
src/spreads/service.py validates the letter, re-gates the spread and records everything.
"""
