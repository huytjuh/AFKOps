from __future__ import annotations

from time import sleep

from afkops.bots.tft.actions import TftActionKind
from afkops.bots.tft.assets import TftAssetPaths
from afkops.bots.tft.board import BoardLayout, BoardMatrixBuilder
from afkops.bots.tft.client_launcher import TftClientLauncher, TftCredentials
from afkops.bots.tft.gameplay import TftGameplay
from afkops.bots.tft.matchmaking import TftMatchmaking
from afkops.bots.tft.memory import TftMemory
from afkops.bots.tft.requeue import TftRequeue
from afkops.bots.tft.progression_monitor import TftProgressionMonitor
from afkops.bots.tft.shop import TftShopRecognizer
from afkops.bots.tft.states import TftGameSubState, TftStateResolver
from afkops.bots.tft.strategy import TftStrategy
from afkops.bots.tft.strategy_config import TftStrategyConfig
from afkops.bots.tft.yolo_vision import TftYoloVision
from afkops.core.config import BotConfig
from afkops.core.input import MouseController
from afkops.core.safety import SafetyController
from afkops.core.screen import ScreenCapture
from afkops.core.vision import Detection, DetectionOverlayWriter, TemplateDetector


class TftBot:
    """Four-module TFT runner: launch, matchmaking, gameplay, requeue."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.capture = ScreenCapture()
        self.detector = TemplateDetector(threshold=config.confidence_threshold)
        self.yolo_vision = TftYoloVision(config)
        self.mouse = MouseController(dry_run=config.dry_run)
        self.assets = TftAssetPaths(config.assets_dir)
        self.debug_dir = (
            config.debug_dir
            if config.debug_dir.name == "debug" and config.debug_dir.parent.name == "tft"
            else config.debug_dir / "tft"
        )
        self.board_layout = BoardLayout.load(self.assets.board_layout)
        self.board_matrix_builder = BoardMatrixBuilder()
        strategy_config = TftStrategyConfig.load(config.strategy_config_path)
        self.strategy = TftStrategy(strategy_config)
        self.launcher = TftClientLauncher(config)
        self.matchmaking = TftMatchmaking(config)
        self.gameplay = TftGameplay(self.strategy)
        self.requeue = TftRequeue()
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

    def start_client(self, credentials: TftCredentials | None = None) -> bool:
        return self.launcher.start_tft_client(credentials)

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

        if state.game is TftGameSubState.POSTGAME:
            action = self.requeue.play_again(detections)
        elif state.game is None:
            action = self.matchmaking.start_matchmaking(detections)
        else:
            action = self.gameplay.play_game(state, detections, self.memory)
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
        for label, path in self.assets.target_templates():
            detection = self.detector.find(screenshot, path, label)
            if detection:
                detections.append(detection)
        detections.extend(self.yolo_vision.detect(screenshot))
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
        if state.game is None:
            return self.matchmaking.start_matchmaking(detections).detection
        if state.game is TftGameSubState.POSTGAME:
            return self.requeue.play_again(detections).detection
        return self.gameplay.play_game(state, detections, self.memory).detection
