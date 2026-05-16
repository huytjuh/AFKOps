from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from afkops.core.vision import Detection


class TftClientState(str, Enum):
    LEAGUE_CLIENT = "league_client"
    GAME_CLIENT = "game_client"


class TftGameSubState(str, Enum):
    LOADING = "loading"
    CAROUSEL = "carousel"
    PVE = "pve"
    PVP = "pvp"
    PLANNING = "planning"
    COMBAT = "combat"
    AUGMENT = "augment"
    GAME_OVER = "game_over"
    POSTGAME = "postgame"


@dataclass(frozen=True)
class TftState:
    client: TftClientState
    game: TftGameSubState | None = None


class TftStateResolver:
    """Infers whether TFT is in the League client or game client."""

    league_client_labels = {
        "play_button",
        "find_match_button",
        "accept_button",
        "confirm_button",
    }
    postgame_labels = {"play_again_button"}
    augment_labels = {"augment_choice_1", "augment_choice_2", "augment_choice_3"}
    carousel_labels = {"carousel_unit", "carousel_marker"}
    planning_labels = {
        "buy_xp_button",
        "reroll_button",
        "champion_shop_slot_1",
        "champion_shop_slot_2",
        "champion_shop_slot_3",
        "champion_shop_slot_4",
        "champion_shop_slot_5",
        "buy_shop_slot_1",
        "buy_shop_slot_2",
        "buy_shop_slot_3",
        "buy_shop_slot_4",
        "buy_shop_slot_5",
    }
    combat_labels = {"combat_marker", "enemy_board_marker"}

    def resolve(
        self,
        detections: list[Detection],
        round_info: Any | None = None,
        previous_state: TftState | None = None,
    ) -> TftState:
        labels = {detection.label for detection in detections}
        if labels & self.postgame_labels:
            return TftState(client=TftClientState.LEAGUE_CLIENT, game=TftGameSubState.POSTGAME)

        game_labels = (
            self.augment_labels
            | self.carousel_labels
            | self.planning_labels
            | self.combat_labels
        )

        if labels & self.league_client_labels and not labels & game_labels:
            return TftState(client=TftClientState.LEAGUE_CLIENT)

        if labels & self.augment_labels:
            return TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.AUGMENT)

        if labels & self.carousel_labels:
            return TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.CAROUSEL)

        if labels & self.combat_labels:
            return TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.COMBAT)

        if labels & self.planning_labels:
            return TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.PLANNING)

        expected_state = getattr(round_info, "expected_state", None)
        if expected_state is not None:
            return TftState(client=TftClientState.GAME_CLIENT, game=expected_state)

        if previous_state and previous_state.client is TftClientState.GAME_CLIENT:
            return previous_state

        return TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.COMBAT)
