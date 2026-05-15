from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from afkops.core.vision import Detection


class TftActionKind(str, Enum):
    WAIT = "wait"
    CLICK_TARGET = "click_target"
    QUEUE_MATCH = "queue_match"
    ACCEPT_MATCH = "accept_match"
    PICK_AUGMENT = "pick_augment"
    PICK_CAROUSEL_UNIT = "pick_carousel_unit"
    BUY_UNIT = "buy_unit"
    BUY_XP = "buy_xp"
    REROLL = "reroll"
    COLLECT_LOOT = "collect_loot"


@dataclass(frozen=True)
class TftAction:
    kind: TftActionKind
    reason: str
    detection: Detection | None = None

    @property
    def is_click(self) -> bool:
        return self.detection is not None


def wait(reason: str) -> TftAction:
    return TftAction(kind=TftActionKind.WAIT, reason=reason)
