from __future__ import annotations

from afkops.bots.tft.actions import TftAction, TftActionKind, wait
from afkops.core.vision import Detection


class TftRequeue:
    """Clicks play again after a match so matchmaking can restart."""

    def play_again(self, detections: list[Detection]) -> TftAction:
        by_label = {detection.label: detection for detection in detections}
        target = by_label.get("play_again_button") or by_label.get("play_button")
        if target:
            return TftAction(TftActionKind.PLAY_AGAIN, "Return to TFT matchmaking.", target)
        return wait("Waiting for postgame play again.")
