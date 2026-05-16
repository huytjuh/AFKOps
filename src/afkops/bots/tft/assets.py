from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from afkops.bots.tft.round_admin import TftRoundPlan


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


@dataclass(frozen=True)
class TftAssetPaths:
    root: Path

    @property
    def league_client(self) -> Path:
        return self.root / "tft" / "league_client"

    @property
    def ui(self) -> Path:
        return self.root / "tft" / "teamfight_tactics_ui"

    @property
    def game_assets(self) -> Path:
        return self.root / "tft" / "game_assets"

    @property
    def champions(self) -> Path:
        return self.game_assets / "champions"

    @property
    def board_layout(self) -> Path:
        return self.ui / "board_1600x1000.toml"

    def target_templates(self) -> list[tuple[str, Path]]:
        templates = [
            *self._league_client_templates(),
            *self._tft_ui_templates(),
            *self._round_templates(),
            *self._champion_templates(),
        ]
        return [(label, path) for label, path in templates if path.exists()]

    def _league_client_templates(self) -> list[tuple[str, Path]]:
        return [
            (label, self.league_client / f"{label}.png")
            for label in (
                "play_button",
                "accept_button",
                "find_match_button",
                "confirm_button",
                "play_again_button",
            )
        ]

    def _tft_ui_templates(self) -> list[tuple[str, Path]]:
        labels = [
            "buy_xp_button",
            "reroll_button",
            "champion_shop_slot_1",
            "champion_shop_slot_2",
            "champion_shop_slot_3",
            "champion_shop_slot_4",
            "champion_shop_slot_5",
            "augment_choice_1",
            "augment_choice_2",
            "augment_choice_3",
            "carousel_unit",
            "carousel_marker",
            "combat_marker",
            "enemy_board_marker",
            "loot_orb",
            "item_orb",
        ]
        return [(label, self.ui / f"{label}.png") for label in labels]

    def _round_templates(self) -> list[tuple[str, Path]]:
        return [
            (
                f"round_{round_info.stage}_{round_info.round}",
                self.ui / f"round_{round_info.stage}_{round_info.round}.png",
            )
            for round_info in TftRoundPlan().rounds
        ]

    def _champion_templates(self) -> list[tuple[str, Path]]:
        if not self.champions.exists():
            return []
        return [
            (f"champion_{path.stem}", path)
            for path in sorted(self.champions.glob("*.png"))
            if not any(token in path.stem.lower() for token in NON_SHOP_CHAMPION_TOKENS)
        ]
