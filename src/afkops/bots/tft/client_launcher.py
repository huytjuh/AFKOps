from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import random
import subprocess
from time import monotonic, sleep
import tomllib

import pyautogui
import pygetwindow as gw
from pygetwindow import PyGetWindowException
import numpy as np
from PIL import Image

from afkops.bots.tft.yolo_vision import (
    LAUNCHER_LOGIN_LABELS,
    LAUNCHER_PLAY_LABELS,
    TftYoloVision,
)
from afkops.core.config import BotConfig

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional local OCR dependency.
    pytesseract = None


@dataclass(frozen=True)
class TftCredentials:
    username: str
    password: str

    @classmethod
    def load(cls, path: Path) -> TftCredentials | None:
        if not path.exists():
            return cls.from_environment()

        with path.open("rb") as handle:
            data = tomllib.load(handle)

        username = str(data.get("username", "")).strip()
        password = str(data.get("password", "")).strip()
        if not username or not password:
            return cls.from_environment()
        return cls(username=username, password=password)

    @classmethod
    def from_environment(cls) -> TftCredentials | None:
        username = os.getenv("TFT_USERNAME", "").strip()
        password = os.getenv("TFT_PASSWORD", "").strip()
        if not username or not password:
            return None
        return cls(username=username, password=password)


class TftClientLauncher:
    """Starts the local game client before TFT automation takes over."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.vision = TftYoloVision(config)

    def prepare_for_matchmaking(self, credentials: TftCredentials | None = None) -> bool:
        """Ensure the League/TFT client is open and logged in before matchmaking starts."""
        credentials = credentials or self.load_credentials()
        if not self._has_credentials(credentials):
            return False

        if self._has_existing_client() and not self._quit_existing_clients():
            return False

        if not self._is_login_window_open() and not self._launch_client():
            return False

        if self.config.dry_run:
            print(f"[dry-run] would enter Riot credentials for {credentials.username}")
            return True

        login_window = self._wait_for_window(self.config.riot_login_window_titles)
        if login_window is None:
            return self.is_tft_client_open()

        if not self._login(login_window, credentials):
            return False
        return self._click_play_when_detected()

    def start_tft_client(self, credentials: TftCredentials | None = None) -> bool:
        credentials = credentials or self.load_credentials()
        if credentials is not None:
            return self.prepare_for_matchmaking(credentials)
        if self._has_existing_client() and not self._quit_existing_clients():
            return False
        return self._launch_client()

    def is_tft_client_open(self) -> bool:
        return self._has_window(self.config.riot_client_window_titles) or self._has_process(
            self.config.riot_client_process_names
        )

    def _has_existing_client(self) -> bool:
        return (
            self._has_window(self.config.riot_client_window_titles)
            or self._has_window(self.config.riot_login_window_titles)
            or self._has_process(self.config.riot_client_process_names)
        )

    def load_credentials(self) -> TftCredentials | None:
        return TftCredentials.load(self.config.tft_credentials_path)

    def _has_credentials(self, credentials: TftCredentials | None) -> bool:
        return credentials is not None and bool(credentials.username and credentials.password)

    def _launch_client(self) -> bool:
        client_path = self.config.riot_client_path
        if client_path is None:
            return False

        path = Path(client_path)
        if not path.exists():
            return False

        if self.config.dry_run:
            print(f"[dry-run] launch TFT client: {path}")
            return True

        subprocess.Popen([str(path), *self.config.riot_client_args])
        return True

    def _quit_existing_clients(self) -> bool:
        if self.config.dry_run:
            print("[dry-run] quit existing Riot/League/TFT client instances")
            return True

        for window in self._find_windows(
            self.config.riot_client_window_titles + self.config.riot_login_window_titles
        ):
            try:
                window.close()
            except PyGetWindowException:
                continue

        sleep(1.0)
        for process_name in self.config.riot_client_process_names:
            image_name = process_name if process_name.lower().endswith(".exe") else f"{process_name}.exe"
            subprocess.run(
                ["taskkill", "/F", "/T", "/IM", image_name],
                capture_output=True,
                check=False,
                text=True,
            )

        return self._wait_for_clients_closed()

    def _wait_for_clients_closed(self) -> bool:
        deadline = monotonic() + self.config.riot_login_timeout_seconds
        while monotonic() < deadline:
            if not self._has_existing_client():
                return True
            sleep(1.0)
        return False

    def _login(self, login_window, credentials: TftCredentials) -> bool:
        if self.config.dry_run:
            print(f"[dry-run] login as {credentials.username}")
            return True

        if getattr(login_window, "isMinimized", False):
            login_window.restore()
        login_window.activate()
        login_form_found, username_position = self._wait_for_login_form(login_window)
        if not login_form_found:
            return False
        if username_position is not None:
            self._wait_before_click()
            self._move_then_click(username_position)
        pyautogui.write(credentials.username, interval=0.01)
        pyautogui.press("tab")
        pyautogui.write(credentials.password, interval=0.01)
        pyautogui.press("enter")
        return True

    def _wait_for_login_form(self, login_window) -> tuple[bool, tuple[int, int] | None]:
        sleep(self.config.riot_login_form_delay_seconds)
        deadline = monotonic() + self.config.riot_login_form_scan_seconds
        while monotonic() < deadline:
            current_window = self._find_window(self.config.riot_login_window_titles) or login_window
            detection = self._find_yolo_detection(current_window, LAUNCHER_LOGIN_LABELS)
            if detection is not None:
                label, position = detection
                if "username" in label:
                    return True, position
                return True, None
            if pytesseract is not None:
                text = self._read_window_text(current_window).lower()
                if any(keyword.lower() in text for keyword in self.config.riot_login_form_keywords):
                    return True, None
            sleep(self.config.riot_login_form_scan_interval_seconds)

        return False, None

    def _read_window_text(self, window) -> str:
        geometry = self._window_geometry(window)
        if geometry is None:
            return ""
        left, top, width, height = geometry
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        image = screenshot if isinstance(screenshot, Image.Image) else Image.fromarray(screenshot)
        return pytesseract.image_to_string(image)

    def _click_play_when_detected(self) -> bool:
        sleep(self.config.tft_play_button_min_wait_seconds)

        deadline = monotonic() + self.config.tft_play_button_scan_seconds
        while monotonic() < deadline:
            client_window = self._find_play_window()
            if client_window is None:
                sleep(self.config.tft_play_button_scan_interval_seconds)
                continue
            position = self._find_play_position(client_window)
            if position is not None:
                self._wait_before_click()
                self._move_then_click(position)
                return True
            sleep(self.config.tft_play_button_scan_interval_seconds)
        return False

    def _find_play_window(self):
        return self._find_window(
            self.config.riot_client_window_titles + self.config.riot_login_window_titles
        )

    def _find_play_position(self, window) -> tuple[int, int] | None:
        position = self._find_yolo_position(window, LAUNCHER_PLAY_LABELS)
        if position is not None:
            return position
        if pytesseract is None:
            return None
        return self._find_text_position(window, self.config.tft_play_button_text)

    def _find_yolo_position(self, window, labels: set[str]) -> tuple[int, int] | None:
        detection = self._find_yolo_detection(window, labels)
        if detection is None:
            return None
        return detection[1]

    def _find_yolo_detection(
        self, window, labels: set[str]
    ) -> tuple[str, tuple[int, int]] | None:
        geometry = self._window_geometry(window)
        if geometry is None:
            return None
        left, top, width, height = geometry
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        image = np.array(screenshot)
        detection = self.vision.first(image, labels)
        if detection is None:
            return None
        x, y = detection.center
        return detection.label, (left + x, top + y)

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

    def _find_text_position(self, window, text: str) -> tuple[int, int] | None:
        geometry = self._window_geometry(window)
        if geometry is None:
            return None
        left, top, width, height = geometry
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        image = screenshot if isinstance(screenshot, Image.Image) else Image.fromarray(screenshot)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        target = text.lower()

        for index, word in enumerate(data.get("text", [])):
            if word.strip().lower() != target:
                continue
            x = left + int(data["left"][index]) + int(data["width"][index]) // 2
            y = top + int(data["top"][index]) + int(data["height"][index]) // 2
            return x, y
        return None

    def _wait_until_ready(self) -> bool:
        deadline = monotonic() + self.config.riot_login_timeout_seconds
        while monotonic() < deadline:
            if self.is_tft_client_open():
                return True
            sleep(1.0)
        return False

    def _wait_for_window(self, titles: tuple[str, ...]):
        deadline = monotonic() + self.config.riot_login_timeout_seconds
        while monotonic() < deadline:
            window = self._find_window(titles)
            if window is not None:
                return window
            sleep(1.0)
        return None

    def _is_login_window_open(self) -> bool:
        return self._has_window(self.config.riot_login_window_titles)

    def _has_window(self, titles: tuple[str, ...]) -> bool:
        return self._find_window(titles) is not None

    def _find_window(self, titles: tuple[str, ...]):
        windows = self._find_windows(titles)
        if not windows:
            return None
        return windows[0]

    def _find_windows(self, titles: tuple[str, ...]) -> list:
        lowered_titles = tuple(title.lower() for title in titles)
        matches = []
        for window in gw.getAllWindows():
            try:
                title = getattr(window, "title", "")
                if not title or getattr(window, "width", 0) <= 0 or getattr(window, "height", 0) <= 0:
                    continue
                if self._matches_window_title(title, lowered_titles):
                    matches.append(window)
            except PyGetWindowException:
                continue
        return matches

    @staticmethod
    def _window_geometry(window) -> tuple[int, int, int, int] | None:
        try:
            left = max(0, int(getattr(window, "left", 0)))
            top = max(0, int(getattr(window, "top", 0)))
            width = max(1, int(getattr(window, "width", 1)))
            height = max(1, int(getattr(window, "height", 1)))
        except PyGetWindowException:
            return None
        return left, top, width, height

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

    def _has_process(self, process_names: tuple[str, ...]) -> bool:
        if not process_names:
            return False
        try:
            result = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True,
                check=False,
                text=True,
            )
        except OSError:
            return False

        processes = result.stdout.lower()
        return any(process_name.lower() in processes for process_name in process_names)
