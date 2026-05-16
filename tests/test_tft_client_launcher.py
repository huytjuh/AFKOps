from pathlib import Path
from types import SimpleNamespace

from afkops.bots.tft.client_launcher import TftClientLauncher, TftCredentials
from afkops.core.config import BotConfig
from afkops.core.vision import Detection


def window(title: str):
    return SimpleNamespace(
        title=title,
        left=10,
        top=20,
        width=100,
        height=100,
        isMinimized=False,
        activate=lambda: None,
        restore=lambda: None,
        close=lambda: None,
    )


def config(tmp_path: Path, dry_run: bool = False) -> BotConfig:
    client_path = tmp_path / "RiotClientServices.exe"
    client_path.write_text("", encoding="utf-8")
    return BotConfig(
        name="tft",
        dry_run=dry_run,
        riot_client_path=client_path,
        riot_login_timeout_seconds=0.01,
        riot_login_startup_delay_seconds=0,
        riot_login_form_delay_seconds=0,
        riot_login_form_scan_seconds=0,
        riot_login_form_scan_interval_seconds=0,
        tft_play_button_min_wait_seconds=0,
        tft_play_button_scan_seconds=0,
        tft_play_button_scan_interval_seconds=0,
        tft_play_button_click_delay_min_seconds=0,
        tft_play_button_click_delay_max_seconds=0,
        tft_click_after_move_delay_min_seconds=0,
        tft_click_after_move_delay_max_seconds=0,
        tft_credentials_path=tmp_path / "credentials.local.toml",
    )


def test_launcher_skips_launch_when_tft_client_is_open(monkeypatch, tmp_path) -> None:
    launcher = TftClientLauncher(config(tmp_path, dry_run=True))
    popen_calls = []

    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.gw.getAllWindows",
        lambda: [window("League of Legends (TM) Client")],
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.subprocess.Popen",
        lambda args: popen_calls.append(args),
    )

    assert launcher.prepare_for_matchmaking(TftCredentials("user", "pass"))
    assert popen_calls == []


def test_launcher_ignores_browser_windows_that_mention_league(monkeypatch, tmp_path) -> None:
    launcher = TftClientLauncher(config(tmp_path))

    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.gw.getAllWindows",
        lambda: [window("V25.09 | League of Legends Wiki - Google Chrome")],
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout="", returncode=0),
    )

    assert not launcher.is_tft_client_open()


def test_launcher_opens_client_and_logs_in(monkeypatch, tmp_path) -> None:
    launcher_config = config(tmp_path)
    launcher_config.riot_login_form_scan_seconds = 1
    launcher_config.tft_play_button_scan_seconds = 1
    launcher = TftClientLauncher(launcher_config)
    calls = []
    window_calls = {"count": 0}

    def windows():
        window_calls["count"] += 1
        if window_calls["count"] < 4:
            return []
        if window_calls["count"] < 6:
            return [window("Riot Client")]
        return [window("League of Legends (TM) Client")]

    def first_detection(image, labels):
        if "login_ui_username_field" in labels:
            return Detection(
                label="login_ui_username_field",
                confidence=0.9,
                x=10,
                y=20,
                width=40,
                height=20,
            )
        if "play_ui_play_button" in labels:
            return Detection(
                label="play_ui_play_button",
                confidence=0.9,
                x=20,
                y=30,
                width=40,
                height=20,
            )
        return None

    launcher.vision = SimpleNamespace(first=first_detection)

    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.gw.getAllWindows",
        windows,
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.subprocess.Popen",
        lambda args: calls.append(("popen", args)),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout="", returncode=0),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.write",
        lambda text, interval=0: calls.append(("write", text)),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.press",
        lambda key: calls.append(("press", key)),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.screenshot",
        lambda region: object(),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.moveTo",
        lambda x, y: calls.append(("move", x, y)),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.click",
        lambda: calls.append(("click",)),
    )

    assert launcher.prepare_for_matchmaking(TftCredentials("user", "pass"))
    assert ("popen", [str(launcher.config.riot_client_path), *launcher.config.riot_client_args]) in calls
    assert ("write", "user") in calls
    assert ("press", "tab") in calls
    assert ("write", "pass") in calls
    assert ("press", "enter") in calls


def test_launcher_rejects_missing_credentials(tmp_path) -> None:
    launcher = TftClientLauncher(config(tmp_path))

    assert not launcher.prepare_for_matchmaking(TftCredentials("", "pass"))


def test_launcher_loads_credentials_from_local_file(tmp_path) -> None:
    credentials_path = tmp_path / "credentials.local.toml"
    credentials_path.write_text('username = "user"\npassword = "pass"\n', encoding="utf-8")
    launcher = TftClientLauncher(
        BotConfig(name="tft", tft_credentials_path=credentials_path)
    )

    credentials = launcher.load_credentials()

    assert credentials == TftCredentials("user", "pass")


def test_launcher_detects_login_form_text(monkeypatch, tmp_path) -> None:
    launcher_config = config(tmp_path)
    launcher_config.riot_login_form_scan_seconds = 1
    launcher = TftClientLauncher(launcher_config)
    launcher.vision = SimpleNamespace(first=lambda image, labels: None)
    fake_ocr = SimpleNamespace(image_to_string=lambda image: "USERNAME\nPASSWORD")

    monkeypatch.setattr("afkops.bots.tft.client_launcher.pytesseract", fake_ocr)
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.screenshot",
        lambda region: object(),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.Image.fromarray",
        lambda image: image,
    )

    assert launcher._wait_for_login_form(window("Riot Client")) == (True, None)


def test_launcher_clicks_play_text_when_detected(monkeypatch, tmp_path) -> None:
    launcher_config = config(tmp_path)
    launcher_config.tft_play_button_scan_seconds = 1
    launcher = TftClientLauncher(launcher_config)
    launcher.vision = SimpleNamespace(first=lambda image, labels: None)
    clicked = []
    fake_ocr = SimpleNamespace(
        Output=SimpleNamespace(DICT="dict"),
        image_to_data=lambda image, output_type: {
            "text": ["Home", "Play"],
            "left": [1, 40],
            "top": [1, 30],
            "width": [10, 20],
            "height": [10, 10],
        },
    )

    monkeypatch.setattr("afkops.bots.tft.client_launcher.pytesseract", fake_ocr)
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.gw.getAllWindows",
        lambda: [window("League of Legends (TM) Client")],
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.screenshot",
        lambda region: object(),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.Image.fromarray",
        lambda image: image,
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.moveTo",
        lambda x, y: clicked.append(("move", x, y)),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.click",
        lambda: clicked.append(("click",)),
    )

    assert launcher._click_play_when_detected()
    assert clicked == [("move", 60, 55), ("click",)]


def test_launcher_clicks_yolo_play_detection_before_ocr(monkeypatch, tmp_path) -> None:
    launcher_config = config(tmp_path)
    launcher_config.tft_play_button_scan_seconds = 1
    launcher = TftClientLauncher(launcher_config)
    clicked = []
    launcher.vision = SimpleNamespace(
        first=lambda image, labels: Detection(
            label="play_txt_play",
            confidence=0.91,
            x=20,
            y=30,
            width=40,
            height=20,
        )
    )

    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.gw.getAllWindows",
        lambda: [window("League of Legends (TM) Client")],
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.screenshot",
        lambda region: object(),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.moveTo",
        lambda x, y: clicked.append(("move", x, y)),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.pyautogui.click",
        lambda: clicked.append(("click",)),
    )

    assert launcher._click_play_when_detected()
    assert clicked == [("move", 50, 60), ("click",)]


def test_launcher_rejects_missing_client_path(monkeypatch, tmp_path) -> None:
    launcher = TftClientLauncher(
        BotConfig(
            name="tft",
            riot_client_path=tmp_path / "missing.exe",
            riot_login_timeout_seconds=0.01,
            tft_credentials_path=tmp_path / "missing_credentials.local.toml",
        )
    )
    monkeypatch.setattr("afkops.bots.tft.client_launcher.gw.getAllWindows", lambda: [])
    monkeypatch.setattr(
        "afkops.bots.tft.client_launcher.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout="", returncode=0),
    )

    assert not launcher.start_tft_client()
