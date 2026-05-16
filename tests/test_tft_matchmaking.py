from pathlib import Path
from types import SimpleNamespace

from afkops.bots.tft.matchmaking import TftMatchmaking
from afkops.core.config import BotConfig
from afkops.core.vision import Detection


def window(title: str):
    return SimpleNamespace(
        title=title,
        left=10,
        top=20,
        width=100,
        height=100,
        close=lambda: None,
    )


def config(tmp_path: Path) -> BotConfig:
    return BotConfig(
        name="tft",
        dry_run=False,
        tft_credentials_path=tmp_path / "credentials.local.toml",
        tft_matchmaking_step_wait_seconds=0,
        tft_matchmaking_scan_seconds=1,
        tft_matchmaking_scan_interval_seconds=0,
        tft_play_button_click_delay_min_seconds=0,
        tft_play_button_click_delay_max_seconds=0,
        tft_click_after_move_delay_min_seconds=0,
        tft_click_after_move_delay_max_seconds=0,
    )


def test_matchmaking_clicks_quickplay_find_match_and_accept(monkeypatch, tmp_path) -> None:
    matchmaking = TftMatchmaking(config(tmp_path))
    clicked = []
    labels_seen = []
    find_match_seen = {"count": 0}

    def detect(image):
        if not labels_seen:
            labels_seen.append({"client_ui_quickplay"})
            return [Detection("client_ui_quickplay", 0.9, 10, 20, 40, 20)]
        labels_seen.append({"client_ui_findmatch", "client_ui_accept"})
        if find_match_seen["count"] < 1:
            find_match_seen["count"] += 1
            return [Detection("client_ui_findmatch", 0.9, 20, 30, 40, 20)]
        return [Detection("client_ui_accept", 0.9, 30, 40, 40, 20)]

    matchmaking.vision = SimpleNamespace(detect=detect)

    monkeypatch.setattr(
        "afkops.bots.tft.matchmaking.gw.getAllWindows",
        lambda: [window("League of Legends")],
    )
    monkeypatch.setattr(
        "afkops.bots.tft.matchmaking.pyautogui.screenshot",
        lambda region: object(),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.matchmaking.pyautogui.moveTo",
        lambda x, y: clicked.append(("move", x, y)),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.matchmaking.pyautogui.click",
        lambda: clicked.append(("click",)),
    )

    assert matchmaking.run_matchmaking()
    assert clicked == [
        ("move", 40, 50),
        ("click",),
        ("move", 50, 60),
        ("click",),
        ("move", 60, 70),
        ("click",),
    ]
    assert any("client_ui_findmatch" in labels for labels in labels_seen)
    assert any("client_ui_accept" in labels for labels in labels_seen)


def test_matchmaking_ignores_browser_windows(monkeypatch, tmp_path) -> None:
    matchmaking = TftMatchmaking(config(tmp_path))

    monkeypatch.setattr(
        "afkops.bots.tft.matchmaking.gw.getAllWindows",
        lambda: [window("Teamfight Tactics Download | EU West - Google Chrome")],
    )

    assert matchmaking._find_matchmaking_window() is None


def test_matchmaking_refetches_league_window_between_queue_scans(monkeypatch, tmp_path) -> None:
    matchmaking = TftMatchmaking(config(tmp_path))
    clicked = []
    find_match_clicked = {"value": False}
    window_left = {"value": 10}

    def detect(image):
        if find_match_clicked["value"]:
            return [Detection("client_ui_accept", 0.9, 30, 40, 40, 20)]
        return [Detection("client_ui_findmatch", 0.9, 20, 30, 40, 20)]

    def windows():
        return [
            SimpleNamespace(
                title="League of Legends",
                left=window_left["value"],
                top=20,
                width=100,
                height=100,
                close=lambda: None,
            )
        ]

    def click():
        clicked.append(("click",))
        if not find_match_clicked["value"]:
            find_match_clicked["value"] = True
            window_left["value"] = 100

    matchmaking.vision = SimpleNamespace(detect=detect)

    monkeypatch.setattr("afkops.bots.tft.matchmaking.gw.getAllWindows", windows)
    monkeypatch.setattr(
        "afkops.bots.tft.matchmaking.pyautogui.screenshot",
        lambda region: object(),
    )
    monkeypatch.setattr(
        "afkops.bots.tft.matchmaking.pyautogui.moveTo",
        lambda x, y: clicked.append(("move", x, y)),
    )
    monkeypatch.setattr("afkops.bots.tft.matchmaking.pyautogui.click", click)

    assert matchmaking._queue_until_accepted()
    assert clicked == [
        ("move", 50, 60),
        ("click",),
        ("move", 150, 70),
        ("click",),
    ]
