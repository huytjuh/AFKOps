from __future__ import annotations

from time import sleep

from afkops.bots.tft.client_launcher import TftClientLauncher
from afkops.bots.tft.matchmaking import TftMatchmaking
from afkops.core.config import BotConfig


class TftSession:
    """Runs the TFT launcher-to-matchmaking handoff."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.launcher = TftClientLauncher(config)
        self.matchmaking = TftMatchmaking(config)

    def run_launcher_then_matchmaking(self) -> bool:
        if not self.launcher.prepare_for_matchmaking():
            return False
        sleep(self.config.tft_launcher_to_matchmaking_delay_seconds)
        return self.matchmaking.run_matchmaking()
