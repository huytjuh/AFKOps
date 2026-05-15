from types import SimpleNamespace

import pytest

from afkops.core import screen
from afkops.core.screen import CapturedFrame, ScreenCapture


def test_find_window_region_by_title(monkeypatch) -> None:
    fake_window = SimpleNamespace(
        title="League of Legends (TM) Client",
        left=100,
        top=200,
        width=1280,
        height=720,
        isMinimized=False,
    )
    monkeypatch.setattr(screen.gw, "getWindowsWithTitle", lambda title: [fake_window])

    region = ScreenCapture().find_window_region("League of Legends (TM) Client")

    assert region.left == 100
    assert region.top == 200
    assert region.width == 1280
    assert region.height == 720


def test_captured_frame_converts_relative_to_screen_position() -> None:
    frame = CapturedFrame(image=None, origin_left=100, origin_top=200)

    assert frame.to_screen_position((25, 30)) == (125, 230)


def test_find_window_region_raises_when_window_missing(monkeypatch) -> None:
    monkeypatch.setattr(screen.gw, "getWindowsWithTitle", lambda title: [])
    monkeypatch.setattr(screen.gw, "getAllWindows", lambda: [])

    with pytest.raises(RuntimeError, match="Window not found"):
        ScreenCapture().find_window_region("League of Legends (TM) Client")
