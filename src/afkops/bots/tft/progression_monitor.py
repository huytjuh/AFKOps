from __future__ import annotations

import re

from afkops.bots.tft.round_admin import TftRoundAdmin, TftRoundPlan
from afkops.core.vision import Detection


class TftProgressionMonitor:
    """Keeps stage/round admin synced with screen observations.

    The first implementation supports template labels like `round_2_1` or `stage_2_round_1`.
    Later this can be fed by OCR from the round label area.
    """

    round_patterns = [
        re.compile(r"^round_(?P<stage>[1-7])_(?P<round>[1-7])$"),
        re.compile(r"^ocr_round_(?P<stage>[1-7])_(?P<round>[1-7])$"),
        re.compile(r"^round_text_(?P<stage>[1-7])_(?P<round>[1-7])$"),
        re.compile(r"^stage_(?P<stage>[1-7])_round_(?P<round>[1-7])$"),
    ]

    def __init__(self, admin: TftRoundAdmin | None = None) -> None:
        self.admin = admin or TftRoundAdmin()

    def update(self, detections: list[Detection]) -> None:
        observed_label = self._observed_round_label(detections)
        if observed_label is None:
            return
        self.admin.sync_to_label(observed_label)

    def _observed_round_label(self, detections: list[Detection]) -> str | None:
        valid_labels = set(TftRoundPlan().rounds_by_label)
        for detection in sorted(detections, key=lambda detection: detection.confidence, reverse=True):
            for pattern in self.round_patterns:
                match = pattern.match(detection.label)
                if not match:
                    continue
                label = f"{match.group('stage')}-{match.group('round')}"
                if label in valid_labels:
                    return label
        return None
