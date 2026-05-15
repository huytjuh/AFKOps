from __future__ import annotations

from dataclasses import dataclass

from afkops.bots.tft.actions import TftAction
from afkops.bots.tft.board import BoardMatrix
from afkops.bots.tft.round_admin import TftRound
from afkops.bots.tft.states import TftState


@dataclass
class TftMemory:
    current_round: TftRound | None = None
    detected_state: TftState | None = None
    gold: int | None = None
    level: int | None = None
    health: int | None = None
    streak: int | None = None
    bench_slots: int | None = None
    board_matrix: BoardMatrix | None = None
    last_action: TftAction | None = None
    ticks_seen: int = 0

    def update_tick(self, round_info: TftRound, state: TftState) -> None:
        self.current_round = round_info
        self.detected_state = state
        self.ticks_seen += 1
