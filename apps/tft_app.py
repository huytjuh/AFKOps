from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from afkops.bots.tft.bot import TftBot
from afkops.core.config import BotConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the TFT bot app.")
    parser.add_argument("--ticks", type=int, help="Run a fixed number of bot ticks, then exit.")
    parser.add_argument("--tick-seconds", type=float, default=1.0, help="Seconds between ticks.")
    parser.add_argument(
        "--window-title",
        default="League of Legends (TM) Client",
        help="Capture only a window whose title contains this text.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = BotConfig(
        name="tft",
        dry_run=True,
        window_title=args.window_title,
        assets_dir=PROJECT_ROOT / "assets",
        screenshots_dir=PROJECT_ROOT / "data" / "tft" / "screenshots",
        debug_dir=PROJECT_ROOT / "data" / "tft" / "debug",
        models_dir=PROJECT_ROOT / "models",
    )
    bot = TftBot(config)
    if args.ticks is None:
        bot.run(tick_seconds=args.tick_seconds)
        return

    print(f"Running TFT bot for {args.ticks} tick(s). dry_run={config.dry_run}")
    for _ in range(args.ticks):
        bot.run_once()


if __name__ == "__main__":
    main()
