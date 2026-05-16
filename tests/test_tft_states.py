from afkops.bots.tft.round_admin import TftRoundPlan
from afkops.bots.tft.matchmaking import TftMatchmaking
from afkops.bots.tft.requeue import TftRequeue
from afkops.bots.tft.states import TftClientState, TftGameSubState, TftStateResolver
from afkops.core.vision import Detection


def detection(label: str) -> Detection:
    return Detection(label=label, confidence=1.0, x=0, y=0, width=10, height=10)


def test_resolves_league_client_state() -> None:
    state = TftStateResolver().resolve([detection("find_match_button")])

    assert state.client is TftClientState.LEAGUE_CLIENT
    assert state.game is None


def test_resolves_game_planning_sub_state() -> None:
    state = TftStateResolver().resolve([detection("champion_shop_slot_1")])

    assert state.client is TftClientState.GAME_CLIENT
    assert state.game is TftGameSubState.PLANNING


def test_combat_marker_beats_visible_shop_slot() -> None:
    state = TftStateResolver().resolve(
        [detection("champion_shop_slot_1"), detection("combat_marker")]
    )

    assert state.client is TftClientState.GAME_CLIENT
    assert state.game is TftGameSubState.COMBAT


def test_state_falls_back_to_expected_round_state() -> None:
    state = TftStateResolver().resolve([], round_info=TftRoundPlan().get("2-4"))

    assert state.client is TftClientState.GAME_CLIENT
    assert state.game is TftGameSubState.CAROUSEL


def test_resolves_league_postgame_state() -> None:
    state = TftStateResolver().resolve([detection("play_again_button")])

    assert state.client is TftClientState.LEAGUE_CLIENT
    assert state.game is TftGameSubState.POSTGAME


def test_league_client_uses_matchmaking_priority() -> None:
    detections = [detection("play_button"), detection("find_match_button")]

    action = TftMatchmaking().start_matchmaking(detections)

    assert action.detection is not None
    assert action.detection.label == "find_match_button"


def test_postgame_clicks_play_again() -> None:
    action = TftRequeue().play_again([detection("play_again_button")])

    assert action.detection is not None
    assert action.detection.label == "play_again_button"
