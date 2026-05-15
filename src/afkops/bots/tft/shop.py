from __future__ import annotations

from dataclasses import dataclass
import re

from afkops.core.vision import Detection


SHOP_SLOT_PREFIX = "champion_shop_slot_"
BUY_SLOT_PREFIX = "buy_shop_slot_"
PORTRAIT_PREFIXES = ("champion_", "shop_champion_")
TEXT_PREFIXES = ("shop_text_", "ocr_champion_")


def normalize_champion_id(value: str) -> str:
    normalized = value.lower().strip()
    normalized = re.sub(r"^champion_", "", normalized)
    normalized = re.sub(r"^shop_champion_", "", normalized)
    normalized = re.sub(r"^shop_text_", "", normalized)
    normalized = re.sub(r"^ocr_champion_", "", normalized)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


@dataclass(frozen=True)
class ShopSlotObservation:
    slot: Detection
    portrait_champion: str | None = None
    portrait_confidence: float = 0.0
    text_champion: str | None = None
    text_confidence: float = 0.0

    @property
    def slot_number(self) -> int:
        return int(self.slot.label.removeprefix(SHOP_SLOT_PREFIX))

    @property
    def champion(self) -> str | None:
        if self.portrait_champion and self.text_champion:
            if self.portrait_champion == self.text_champion:
                return self.portrait_champion
            return self.text_champion
        return self.portrait_champion or self.text_champion

    @property
    def confidence(self) -> float:
        if self.portrait_champion and self.text_champion:
            if self.portrait_champion == self.text_champion:
                return min(1.0, max(self.portrait_confidence, self.text_confidence) + 0.08)
            return self.text_confidence
        return max(self.portrait_confidence, self.text_confidence)


class TftShopRecognizer:
    def __init__(
        self,
        preferred_units: list[str] | None = None,
        buy_confidence: float = 0.78,
    ) -> None:
        self.preferred_units = {
            normalize_champion_id(unit)
            for unit in preferred_units or []
            if normalize_champion_id(unit)
        }
        self.buy_confidence = buy_confidence

    def recognize(self, detections: list[Detection]) -> list[ShopSlotObservation]:
        slots = sorted(
            [detection for detection in detections if detection.label.startswith(SHOP_SLOT_PREFIX)],
            key=lambda detection: detection.label,
        )
        observations: list[ShopSlotObservation] = []

        for slot in slots:
            portrait = self._best_detection_for_slot(detections, slot, PORTRAIT_PREFIXES)
            text = self._best_detection_for_slot(detections, slot, TEXT_PREFIXES)
            observations.append(
                ShopSlotObservation(
                    slot=slot,
                    portrait_champion=self._champion_from_detection(portrait),
                    portrait_confidence=portrait.confidence if portrait else 0.0,
                    text_champion=self._champion_from_detection(text),
                    text_confidence=text.confidence if text else 0.0,
                )
            )

        return observations

    def buy_detections(self, detections: list[Detection]) -> list[Detection]:
        buyable: list[Detection] = []
        for observation in self.recognize(detections):
            champion = observation.champion
            if champion is None:
                continue
            if observation.confidence < self.buy_confidence:
                continue
            if self.preferred_units and champion not in self.preferred_units:
                continue
            slot = observation.slot
            buyable.append(
                Detection(
                    label=f"{BUY_SLOT_PREFIX}{observation.slot_number}",
                    confidence=observation.confidence,
                    x=slot.x,
                    y=slot.y,
                    width=slot.width,
                    height=slot.height,
                )
            )
        return buyable

    def _best_detection_for_slot(
        self,
        detections: list[Detection],
        slot: Detection,
        prefixes: tuple[str, ...],
    ) -> Detection | None:
        candidates = [
            detection
            for detection in detections
            if detection is not slot
            and detection.label.startswith(prefixes)
            and self._is_inside_expanded_slot(detection, slot)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda detection: detection.confidence)

    def _is_inside_expanded_slot(self, detection: Detection, slot: Detection) -> bool:
        center_x, center_y = detection.center
        margin_x = max(12, round(slot.width * 0.25))
        margin_top = max(12, round(slot.height * 0.25))
        margin_bottom = max(24, round(slot.height * 0.75))
        return (
            slot.x - margin_x <= center_x <= slot.x + slot.width + margin_x
            and slot.y - margin_top <= center_y <= slot.y + slot.height + margin_bottom
        )

    def _champion_from_detection(self, detection: Detection | None) -> str | None:
        if detection is None:
            return None
        for prefix in PORTRAIT_PREFIXES + TEXT_PREFIXES:
            if detection.label.startswith(prefix):
                return normalize_champion_id(detection.label.removeprefix(prefix))
        return None
