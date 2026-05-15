from __future__ import annotations

from pathlib import Path
from time import sleep

from afkops.bots.tft.actions import TftActionKind
from afkops.bots.tft.board import BoardLayout, BoardMatrixBuilder
from afkops.bots.tft.memory import TftMemory
from afkops.bots.tft.progression_monitor import TftProgressionMonitor
from afkops.bots.tft.round_admin import TftRoundPlan
from afkops.bots.tft.shop import TftShopRecognizer
from afkops.bots.tft.states import TftGameSubState, TftStateResolver
from afkops.bots.tft.strategy import TftStrategy
from afkops.bots.tft.strategy_config import TftStrategyConfig
from afkops.core.config import BotConfig
from afkops.core.input import MouseController
from afkops.core.object_detection import ObjectDetectionModel
from afkops.core.safety import SafetyController
from afkops.core.screen import ScreenCapture
from afkops.core.vision import Detection, DetectionOverlayWriter, TemplateDetector


NON_SHOP_CHAMPION_TOKENS = {
    "animasquadprop",
    "darkstardamagetracker",
    "darkstar_fakeunit",
    "drxtracker",
    "enemy_",
    "ivernminion",
    "missfortune_traitclone",
    "primordiantracker",
    "pve_",
    "summon",
    "timebreakercore",
}


class TftBot:
    """TFT app bot that reads the screen and acts through a strategy."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.capture = ScreenCapture()
        self.detector = TemplateDetector(threshold=config.confidence_threshold)
        self.shop_model = ObjectDetectionModel(
            config.models_dir / "tft" / "shop_detector.pt",
            threshold=config.object_detection_threshold,
        )
        self.mouse = MouseController(dry_run=config.dry_run)
        self.templates_dir = config.assets_dir / "templates" / "tft"
        self.debug_dir = config.debug_dir / "tft"
        self.board_layout = BoardLayout.load(config.assets_dir / "layouts" / "tft" / "board_1600x1000.toml")
        self.board_matrix_builder = BoardMatrixBuilder()
        strategy_config = TftStrategyConfig.load(Path("configs/tft_strategy.local.toml"))
        self.strategy = TftStrategy(strategy_config)
        self.shop_recognizer = TftShopRecognizer(
            strategy_config.preferred_units,
            buy_confidence=strategy_config.shop_buy_confidence,
        )
        self.safety = SafetyController(
            click_cooldown_seconds=strategy_config.click_cooldown_seconds,
            max_clicks_per_minute=strategy_config.max_clicks_per_minute,
        )
        self.memory = TftMemory()
        self.state_resolver = TftStateResolver()
        self.progression = TftProgressionMonitor()
        self.overlay_writer = DetectionOverlayWriter()

    def run(self, tick_seconds: float = 1.0) -> None:
        print(f"Starting TFT bot app loop. dry_run={self.config.dry_run}")
        while True:
            self.run_once()
            sleep(tick_seconds)

    def run_once(self) -> None:
        frame = (
            self.capture.grab_window_frame(self.config.window_title)
            if self.config.window_title
            else self.capture.grab_frame()
        )
        screenshot = frame.image
        detections = self.find_targets(screenshot)
        self.progression.update(detections)
        state = self.state_resolver.resolve(
            detections,
            round_info=self.progression.admin.current,
            previous_state=self.memory.detected_state,
        )
        self.memory.update_tick(self.progression.admin.current, state)
        scaled_layout = self.board_layout.scaled(
            image_width=screenshot.shape[1],
            image_height=screenshot.shape[0],
        )
        if state.game is TftGameSubState.PLANNING:
            self.memory.board_matrix = self.board_matrix_builder.build_occupancy(
                scaled_layout,
                detections,
            )

        action = self.strategy.choose_next_action(state, detections, self.memory)
        target = action.detection
        board_points = [(slot.id, slot.x, slot.y) for slot in scaled_layout.slots]
        self.overlay_writer.save(
            screenshot,
            detections,
            self.debug_dir / "latest_detection.png",
            target,
            points=board_points,
        )
        self.memory.last_action = action

        if action.kind is TftActionKind.WAIT or target is None:
            print(f"No TFT target found. state={state.client.value}/{state.game.value if state.game else '-'}")
            return

        relative_x, relative_y = target.center
        screen_x, screen_y = frame.to_screen_position(target.center)
        print(
            f"state={state.client.value}/{state.game.value if state.game else '-'} "
            f"{self.progression.admin.status_line()} "
            f"action={action.kind.value} target={target.label} "
            f"relative=({relative_x}, {relative_y}) screen=({screen_x}, {screen_y}) "
            f"({target.confidence:.2%}) reason={action.reason}"
        )
        if self.memory.board_matrix and self.memory.board_matrix.assignments:
            print(f"board={self.memory.board_matrix.as_dict()}")
        elif self.memory.board_matrix and self.memory.board_matrix.occupied_slots:
            print(f"occupancy={self.memory.board_matrix.occupancy_dict()}")

        if not self.safety.can_click():
            print(f"[safety] skipped click for {target.label}; cooldown or click limit active")
            return

        self.mouse.click(screen_x, screen_y)
        self.safety.record_click()

    def find_targets(self, screenshot) -> list[Detection]:
        detections: list[Detection] = []
        for label, path in self.target_templates():
            if not Path(path).exists():
                continue
            detection = self.detector.find(screenshot, path, label)
            if detection:
                detections.append(detection)
        detections.extend(self.shop_model.detect(screenshot))
        detections.extend(self.shop_recognizer.buy_detections(detections))
        return detections

    def find_next_target(self, screenshot) -> Detection | None:
        detections = self.find_targets(screenshot)
        state = self.state_resolver.resolve(
            detections,
            round_info=self.progression.admin.current,
            previous_state=self.memory.detected_state,
        )
        self.memory.update_tick(self.progression.admin.current, state)
        return self.strategy.choose_next_action(state, detections, self.memory).detection

    def target_templates(self) -> list[tuple[str, Path]]:
        templates = [
            ("play_button", self.templates_dir / "play_button.png"),
            ("accept_button", self.templates_dir / "accept_button.png"),
            ("find_match_button", self.templates_dir / "find_match_button.png"),
            ("confirm_button", self.templates_dir / "confirm_button.png"),
            ("buy_xp_button", self.templates_dir / "buy_xp_button.png"),
            ("reroll_button", self.templates_dir / "reroll_button.png"),
            ("champion_shop_slot_1", self.templates_dir / "champion_shop_slot_1.png"),
            ("champion_shop_slot_2", self.templates_dir / "champion_shop_slot_2.png"),
            ("champion_shop_slot_3", self.templates_dir / "champion_shop_slot_3.png"),
            ("champion_shop_slot_4", self.templates_dir / "champion_shop_slot_4.png"),
            ("champion_shop_slot_5", self.templates_dir / "champion_shop_slot_5.png"),
            ("augment_choice_1", self.templates_dir / "augment_choice_1.png"),
            ("augment_choice_2", self.templates_dir / "augment_choice_2.png"),
            ("augment_choice_3", self.templates_dir / "augment_choice_3.png"),
            ("carousel_unit", self.templates_dir / "carousel_unit.png"),
            ("carousel_marker", self.templates_dir / "carousel_marker.png"),
            ("combat_marker", self.templates_dir / "combat_marker.png"),
            ("enemy_board_marker", self.templates_dir / "enemy_board_marker.png"),
            ("loot_orb", self.templates_dir / "loot_orb.png"),
            ("item_orb", self.templates_dir / "item_orb.png"),
        ]
        for round_info in TftRoundPlan().rounds:
            label = f"round_{round_info.stage}_{round_info.round}"
            templates.append((label, self.templates_dir / f"{label}.png"))
        champions_dir = self.templates_dir / "champions"
        if champions_dir.exists():
            for path in sorted(champions_dir.glob("*.png")):
                if any(token in path.stem.lower() for token in NON_SHOP_CHAMPION_TOKENS):
                    continue
                templates.append((f"champion_{path.stem}", path))
        return templates
