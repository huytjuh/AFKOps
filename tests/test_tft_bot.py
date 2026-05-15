import numpy as np

from afkops.bots.tft.bot import TftBot
from afkops.core.config import BotConfig
from afkops.core.screen import CapturedFrame


def test_tft_bot_starts_without_templates() -> None:
    bot = TftBot(BotConfig(name="tft"))
    bot.capture.grab_frame = lambda: CapturedFrame(
        image=np.zeros((100, 100, 3), dtype=np.uint8),
        origin_left=0,
        origin_top=0,
    )

    bot.run_once()
