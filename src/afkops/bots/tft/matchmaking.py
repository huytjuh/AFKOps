from __future__ import annotations

import random
from collections.abc import Iterable
from time import monotonic, sleep

import numpy as np
import pyautogui
import pygetwindow as gw
from pygetwindow import PyGetWindowException

from afkops.bots.tft.actions import TftAction, TftActionKind, wait
from afkops.bots.tft.yolo_vision import TftYoloVision
from afkops.core.config import BotConfig
from afkops.core.vision import Detection


QUICKPLAY_LABELS = {
    "client_ui_quickplay",
    "client_txt_quickplay",
}

FIND_MATCH_LABELS = {
    "client_ui_findmatch",
    "client_txt_findmatch",
    "client_ui_find_match_button",
    "ui_find_match_button",
    "find_match_button",
}

ACCEPT_LABELS = {
    "client_ui_accept",
    "client_txt_accept",
    "client_ui_accept_button",
    "ui_accept_button",
    "accept_button",
}


class TftMatchmaking:
    """Starts matchmaking and accepts ready checks from the client UI."""

    def __init__(self, config: BotConfig | None = None) -> None:
        self.config = config or BotConfig(name="tft")
        self.vision = TftYoloVision(self.config)

    def run_matchmaking(self) -> bool:
        """Click Quickplay, Find Match, and Accept in the League matchmaking client."""
        if not self._wait_and_click(QUICKPLAY_LABELS, "Quickplay"):
            return False
        return self._queue_until_accepted()

    def start_matchmaking(self, detections: list[Detection]) -> TftAction:
        actions = [
            ("client_ui_accept", TftActionKind.ACCEPT_MATCH, "Accept ready check."),
            ("client_txt_accept", TftActionKind.ACCEPT_MATCH, "Accept ready check."),
            ("accept_button", TftActionKind.ACCEPT_MATCH, "Accept ready check."),
            ("client_ui_findmatch", TftActionKind.QUEUE_MATCH, "Queue for TFT match."),
            ("client_txt_findmatch", TftActionKind.QUEUE_MATCH, "Queue for TFT match."),
            ("confirm_button", TftActionKind.CLICK_TARGET, "Confirm client prompt."),
            ("find_match_button", TftActionKind.QUEUE_MATCH, "Queue for TFT match."),
            ("client_ui_quickplay", TftActionKind.CLICK_TARGET, "Open Quickplay."),
            ("client_txt_quickplay", TftActionKind.CLICK_TARGET, "Open Quickplay."),
            ("play_button", TftActionKind.CLICK_TARGET, "Open play flow."),
        ]
        return self._first_action(actions, detections) or wait("Waiting in League client.")

    def _first_action(
        self,
        actions: list[tuple[str, TftActionKind, str]],
        detections: list[Detection],
    ) -> TftAction | None:
        by_label = {detection.label: detection for detection in detections}
        for label, kind, reason in actions:
            if label in by_label:
                return TftAction(kind, reason, by_label[label])
        return None

    def _wait_and_click(self, labels: set[str], name: str) -> bool:
        sleep(self.config.tft_matchmaking_step_wait_seconds)
        deadline = monotonic() + self.config.tft_matchmaking_scan_seconds
        while monotonic() < deadline:
            window = self._find_matchmaking_window()
            if window is None:
                sleep(self.config.tft_matchmaking_scan_interval_seconds)
                continue
            position = self._find_yolo_position(window, labels)
            if position is not None:
                self._wait_before_click()
                self._move_then_click(position)
                return True
            sleep(self.config.tft_matchmaking_scan_interval_seconds)
        print(f"TFTMatchmaking failed to detect {name}.")
        return False

    def _queue_until_accepted(self) -> bool:
        sleep(self.config.tft_matchmaking_step_wait_seconds)
        deadline = monotonic() + self.config.tft_matchmaking_scan_seconds
        find_match_clicked = False
        while monotonic() < deadline:
            window = self._find_matchmaking_window()
            if window is None:
                sleep(self.config.tft_matchmaking_scan_interval_seconds)
                continue

            detections = self._detect_labels(window, ACCEPT_LABELS | FIND_MATCH_LABELS)
            self._print_scan_summary(window, detections)

            accept_position = self._best_position(detections, ACCEPT_LABELS)
            if accept_position is not None:
                self._wait_before_click()
                self._move_then_click(accept_position)
                return True

            find_match_position = self._best_position(detections, FIND_MATCH_LABELS)
            if find_match_position is not None and not find_match_clicked:
                self._wait_before_click()
                self._move_then_click(find_match_position)
                find_match_clicked = True

            sleep(self.config.tft_matchmaking_scan_interval_seconds)

        print("TFTMatchmaking failed to detect Accept.")
        return False

    def _find_yolo_position(self, window, labels: set[str]) -> tuple[int, int] | None:
        return self._best_position(self._detect_labels(window, labels), labels)

    def _detect_labels(self, window, labels: set[str]) -> list[tuple[Detection, tuple[int, int]]]:
        geometry = self._window_geometry(window)
        if geometry is None:
            return []
        left, top, width, height = geometry
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        image = np.array(screenshot)
        detections = [
            detection
            for detection in self.vision.detect(image)
            if detection.label in labels
        ]
        return [
            (detection, (left + detection.center[0], top + detection.center[1]))
            for detection in detections
        ]

    @staticmethod
    def _best_position(
        detections: Iterable[tuple[Detection, tuple[int, int]]],
        labels: set[str],
    ) -> tuple[int, int] | None:
        candidates = [
            (detection, position)
            for detection, position in detections
            if detection.label in labels
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda candidate: candidate[0].confidence)[1]

    def _find_matchmaking_window(self):
        titles = self.config.riot_client_window_titles + self.config.riot_login_window_titles
        lowered_titles = tuple(title.lower() for title in titles)
        matches = []
        for window in gw.getAllWindows():
            try:
                title = getattr(window, "title", "")
                geometry = self._window_geometry(window)
                if not title or geometry is None:
                    continue
                if self._matches_window_title(title, lowered_titles):
                    matches.append((self._window_score(title, geometry), window))
            except PyGetWindowException:
                continue
        if not matches:
            return None
        return max(matches, key=lambda match: match[0])[1]

    @staticmethod
    def _window_geometry(window) -> tuple[int, int, int, int] | None:
        try:
            left = int(getattr(window, "left", 0))
            top = int(getattr(window, "top", 0))
            width = int(getattr(window, "width", 0))
            height = int(getattr(window, "height", 0))
        except PyGetWindowException:
            return None
        if width <= 0 or height <= 0 or left < -10000 or top < -10000:
            return None
        left = max(0, left)
        top = max(0, top)
        return left, top, width, height

    @staticmethod
    def _window_score(title: str, geometry: tuple[int, int, int, int]) -> tuple[int, int]:
        lowered = title.lower()
        _, _, width, height = geometry
        exact_league = int(lowered.strip() == "league of legends")
        exact_riot = int(lowered.strip() == "riot client")
        return exact_league + exact_riot, width * height

    def _wait_before_click(self) -> None:
        min_seconds = self.config.tft_play_button_click_delay_min_seconds
        max_seconds = self.config.tft_play_button_click_delay_max_seconds
        if max_seconds < min_seconds:
            max_seconds = min_seconds
        sleep(random.uniform(min_seconds, max_seconds))

    def _move_then_click(self, position: tuple[int, int]) -> None:
        pyautogui.moveTo(*position)
        min_seconds = self.config.tft_click_after_move_delay_min_seconds
        max_seconds = self.config.tft_click_after_move_delay_max_seconds
        if max_seconds < min_seconds:
            max_seconds = min_seconds
        sleep(random.uniform(min_seconds, max_seconds))
        pyautogui.click()

    def _matches_window_title(self, title: str, lowered_titles: tuple[str, ...]) -> bool:
        lowered = title.lower()
        if self._looks_like_browser_window(lowered):
            return False
        return any(candidate in lowered for candidate in lowered_titles)

    @staticmethod
    def _looks_like_browser_window(title: str) -> bool:
        browser_markers = (
            " - google chrome",
            " - microsoft edge",
            " - mozilla firefox",
            " - brave",
            " - opera",
            " - comet",
        )
        return any(marker in title for marker in browser_markers)

    @staticmethod
    def _print_scan_summary(window, detections: list[tuple[Detection, tuple[int, int]]]) -> None:
        title = getattr(window, "title", "")
        if not detections:
            print(f"TFTMatchmaking scan window={title!r} detections=[]")
            return
        summary = [
            f"{detection.label}:{detection.confidence:.2f}@{position}"
            for detection, position in sorted(
                detections,
                key=lambda item: item[0].confidence,
                reverse=True,
            )
        ]
        print(f"TFTMatchmaking scan window={title!r} detections={summary}")
