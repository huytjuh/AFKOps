from __future__ import annotations

from enum import Enum

import typer

from afkops.bots.tft.bot import TftBot
from afkops.core.config import BotConfig

app = typer.Typer(help="Run AFKOps bots.")


class BotName(str, Enum):
    tft = "tft"
    hearthstone = "hearthstone"
    slay_the_spire = "slay-the-spire"
    twitch_viewer = "twitch-viewer"


@app.command()
def run(bot: BotName, dry_run: bool = True) -> None:
    """Run one bot. Dry-run is enabled by default while detectors are being trained."""
    config = BotConfig(name=bot.value, dry_run=dry_run)

    if bot is BotName.tft:
        TftBot(config).run_once()
        return

    typer.echo(f"{bot.value} is scaffolded but not implemented yet.")

