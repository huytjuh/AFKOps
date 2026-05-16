from afkops.bots.tft.session import TftSession
from afkops.core.config import BotConfig


def test_session_waits_between_launcher_and_matchmaking(monkeypatch) -> None:
    config = BotConfig(name="tft", tft_launcher_to_matchmaking_delay_seconds=60)
    session = TftSession(config)
    calls = []

    session.launcher.prepare_for_matchmaking = lambda: calls.append("launcher") or True
    session.matchmaking.run_matchmaking = lambda: calls.append("matchmaking") or True
    monkeypatch.setattr("afkops.bots.tft.session.sleep", lambda seconds: calls.append(("sleep", seconds)))

    assert session.run_launcher_then_matchmaking()
    assert calls == ["launcher", ("sleep", 60), "matchmaking"]
