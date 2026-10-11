"""Daily credit-spread service entrypoint.

Usage:
    python -m scripts.run_spreads

Connects with clientId 30 (config/settings.yaml → ibkr.client_ids.spreads). Idles when
config/spreads.yaml → enabled is false; refuses to trade when LIVE_TRADING=true. With
spreads.ai.enabled, wires in the Claude picker (src/spreads_ai/) — the only place it is
imported, so src/spreads/ never depends on it. Runs until SIGINT/SIGTERM. Supervised by
scripts.start like the other daemons.
"""

import asyncio
import signal

from src.common.config import Config
from src.common.logging import setup_logging
from src.spreads.service import Picker, run


def make_picker(cfg: Config) -> Picker:
    from src.spreads_ai.picker import ClaudePicker

    return ClaudePicker.from_config(cfg)


async def _main() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await run(stop, picker_factory=make_picker)


def main() -> None:
    setup_logging()
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
