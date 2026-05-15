from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from afkops.bots.tft.states import TftGameSubState


class TftRoundType(str, Enum):
    PORTAL_SELECT = "portal_select"
    CAROUSEL = "carousel"
    PVE = "pve"
    PVP = "pvp"


class TftAugmentTier(str, Enum):
    SILVER = "silver"
    GOLD = "gold"
    PRISMATIC = "prismatic"


@dataclass(frozen=True)
class TftRound:
    stage: int
    round: int
    round_type: TftRoundType
    expected_state: TftGameSubState
    augment_tier: TftAugmentTier | None = None
    description: str = ""

    @property
    def label(self) -> str:
        return f"{self.stage}-{self.round}"

    @property
    def has_augment(self) -> bool:
        return self.augment_tier is not None


class TftRoundPlan:
    """Canonical TFT stage order used by the bot's round monitor.

    Stage 1 is a special opener. Stages 2-7 follow the standard 7-round cycle:
    PvP, PvP, PvP, carousel, PvP, PvP, PvE.
    """

    first_standard_stage = 2
    final_stage = 7
    rounds_per_standard_stage = 7
    augment_rounds = {
        (2, 1): TftAugmentTier.SILVER,
        (3, 2): TftAugmentTier.GOLD,
        (4, 2): TftAugmentTier.PRISMATIC,
    }

    def __init__(self) -> None:
        self.rounds = self._build_rounds()
        self.rounds_by_label = {round_info.label: round_info for round_info in self.rounds}

    def first(self) -> TftRound:
        return self.rounds[0]

    def get(self, label: str) -> TftRound | None:
        return self.rounds_by_label.get(label)

    def next_after(self, current: TftRound) -> TftRound | None:
        index = self.rounds.index(current)
        next_index = index + 1
        if next_index >= len(self.rounds):
            return None
        return self.rounds[next_index]

    def _build_rounds(self) -> list[TftRound]:
        rounds = self._stage_one_rounds()
        for stage in range(self.first_standard_stage, self.final_stage + 1):
            for round_number in range(1, self.rounds_per_standard_stage + 1):
                round_type = self._standard_round_type(round_number)
                rounds.append(self._round(stage, round_number, round_type))
        return rounds

    def _stage_one_rounds(self) -> list[TftRound]:
        return [
            self._round(
                1,
                1,
                TftRoundType.PORTAL_SELECT,
                description="Portal select / shared carousel opener.",
            ),
            self._round(1, 2, TftRoundType.PVE, description="Minion PvE round."),
            self._round(1, 3, TftRoundType.PVE, description="Minion PvE round."),
            self._round(1, 4, TftRoundType.PVE, description="Minion PvE round."),
        ]

    def _round(
        self,
        stage: int,
        round_number: int,
        round_type: TftRoundType,
        description: str = "",
    ) -> TftRound:
        augment_tier = self.augment_rounds.get((stage, round_number))
        return TftRound(
            stage=stage,
            round=round_number,
            round_type=round_type,
            expected_state=self._expected_state(round_type, augment_tier),
            augment_tier=augment_tier,
            description=description or self._description(round_type),
        )

    def _standard_round_type(self, round_number: int) -> TftRoundType:
        if round_number == 4:
            return TftRoundType.CAROUSEL
        if round_number == 7:
            return TftRoundType.PVE
        return TftRoundType.PVP

    def _expected_state(
        self, round_type: TftRoundType, augment_tier: TftAugmentTier | None
    ) -> TftGameSubState:
        if augment_tier:
            return TftGameSubState.AUGMENT
        if round_type in {TftRoundType.PORTAL_SELECT, TftRoundType.CAROUSEL}:
            return TftGameSubState.CAROUSEL
        if round_type is TftRoundType.PVE:
            return TftGameSubState.PVE
        return TftGameSubState.PVP

    def _description(self, round_type: TftRoundType) -> str:
        descriptions = {
            TftRoundType.PORTAL_SELECT: "Pick opener unit/item from shared carousel.",
            TftRoundType.CAROUSEL: "Shared draft item select.",
            TftRoundType.PVE: "Fight AI monsters for loot.",
            TftRoundType.PVP: "Fight another player's board.",
        }
        return descriptions[round_type]


class TftRoundAdmin:
    """Tracks the stage/round timeline separately from visual state detection."""

    def __init__(self, plan: TftRoundPlan | None = None) -> None:
        self.plan = plan or TftRoundPlan()
        self.current = self.plan.first()

    def reset(self) -> None:
        self.current = self.plan.first()

    def advance(self) -> TftRound | None:
        next_round = self.plan.next_after(self.current)
        if next_round is None:
            return None
        self.current = next_round
        return self.current

    def sync_to_label(self, label: str) -> TftRound | None:
        round_info = self.plan.get(label)
        if round_info is None:
            return None
        self.current = round_info
        return self.current

    def status_line(self) -> str:
        augment = f" augment={self.current.augment_tier.value}" if self.current.augment_tier else ""
        return (
            f"round={self.current.label} type={self.current.round_type.value}"
            f"{augment} expected={self.current.expected_state.value}"
        )
