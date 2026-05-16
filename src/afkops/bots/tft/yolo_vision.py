from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from afkops.core.config import BotConfig
from afkops.core.object_detection import ObjectDetectionModel
from afkops.core.vision import Detection


LAUNCHER_PLAY_LABELS = {
    "play_ui_play_button",
    "play_text_play",
    "play_txt_play",
    "ui_play_button",
    "text_play",
    "play_button",
}

LAUNCHER_LOGIN_LABELS = {
    "login_ui_username_field",
    "login_ui_password_field",
    "login_txt_username",
    "login_txt_password",
    "ui_username_field",
    "ui_password_field",
    "text_username",
    "text_password",
}

MATCHMAKING_LABELS = {
    "client_ui_find_match_button",
    "client_ui_findmatch",
    "client_ui_accept_button",
    "client_ui_accept",
    "client_ui_confirm_button",
    "client_ui_login_button",
    "client_ui_quickplay",
    "client_txt_quickplay",
    "client_txt_findmatch",
    "client_txt_accept",
    "ui_find_match_button",
    "ui_accept_button",
    "ui_confirm_button",
    "find_match_button",
    "accept_button",
    "confirm_button",
}

GAMEPLAY_UI_LABELS = {
    "ingame_ui_buy_xp_button",
    "ingame_ui_reroll_button",
    "ingame_ui_augment_choice",
    "ingame_ui_carousel_unit",
    "ingame_ui_loot_orb",
    "ingame_ui_item_orb",
    "ui_buy_xp_button",
    "ui_reroll_button",
    "ui_augment_choice",
    "ui_carousel_unit",
    "ui_loot_orb",
    "ui_item_orb",
}

TEXT_LABEL_PREFIXES = (
    "text_",
    "shop_text_",
    "ocr_",
    "login_text_",
    "play_text_",
    "login_txt_",
    "play_txt_",
    "client_txt_",
)
CHAMPION_LABEL_PREFIXES = ("champion_", "shop_champion_", "ingame_champion_")


@dataclass(frozen=True)
class TftYoloTaxonomy:
    """Shared lightweight YOLO labels for TFT launcher and gameplay."""

    launcher_ui: tuple[str, ...] = tuple(sorted(LAUNCHER_PLAY_LABELS))
    matchmaking_ui: tuple[str, ...] = tuple(sorted(MATCHMAKING_LABELS))
    gameplay_ui: tuple[str, ...] = tuple(sorted(GAMEPLAY_UI_LABELS))
    text_prefixes: tuple[str, ...] = TEXT_LABEL_PREFIXES
    champion_prefixes: tuple[str, ...] = CHAMPION_LABEL_PREFIXES

    def is_launcher_play(self, label: str) -> bool:
        return label in LAUNCHER_PLAY_LABELS

    def is_champion(self, label: str) -> bool:
        return label.startswith(CHAMPION_LABEL_PREFIXES)

    def is_text(self, label: str) -> bool:
        return label.startswith(TEXT_LABEL_PREFIXES)


class TftYoloVision:
    """Fast shared TFT object detector backed by a lightweight Ultralytics YOLO model."""

    def __init__(self, config: BotConfig) -> None:
        self.model = ObjectDetectionModel(
            config.tft_yolo_model_path,
            threshold=config.tft_yolo_threshold,
            image_size=config.tft_yolo_image_size,
        )
        self.taxonomy = TftYoloTaxonomy()

    @property
    def available(self) -> bool:
        return self.model.available

    def detect(self, image: np.ndarray) -> list[Detection]:
        return self.model.detect(image)

    def first(self, image: np.ndarray, labels: set[str]) -> Detection | None:
        detections = [
            detection
            for detection in self.detect(image)
            if detection.label in labels
        ]
        if not detections:
            return None
        return max(detections, key=lambda detection: detection.confidence)

    @staticmethod
    def default_model_path(models_dir: Path) -> Path:
        return models_dir / "tft" / "tft_fast_yolo.pt"
