from __future__ import annotations

from afkops.bots.tft.actions import TftAction, wait
from afkops.bots.tft.memory import TftMemory
from afkops.bots.tft.states import TftGameSubState, TftState
from afkops.bots.tft.strategy import TftStrategy
from afkops.core.vision import Detection


class TftGameplay:
    """Plays the active TFT match according to the configured strategy."""

    def __init__(self, strategy: TftStrategy) -> None:
        self.strategy = strategy

    def play_game(self, state: TftState, detections: list[Detection], memory: TftMemory) -> TftAction:
        if state.game is None:
            return wait("No game sub-state detected.")
        if state.game is TftGameSubState.POSTGAME:
            return wait("Postgame is handled by the requeue module.")
        return self.strategy.choose_next_action(state, detections, memory)
