from __future__ import annotations

from afkops.bots.tft.actions import TftAction, TftActionKind, wait
from afkops.bots.tft.memory import TftMemory
from afkops.bots.tft.round_admin import TftRoundType
from afkops.bots.tft.states import TftGameSubState, TftState
from afkops.bots.tft.strategy_config import TftStrategyConfig
from afkops.core.vision import Detection


class TftStrategy:
    """State-aware TFT strategy.

    League client behavior stays simple: queue and accept matches. Once the game client is
    detected, each sub-state gets its own priorities so richer play logic can grow there.
    """

    def __init__(self, config: TftStrategyConfig | None = None) -> None:
        self.config = config or TftStrategyConfig()

    def choose_next_action(
        self, state: TftState, detections: list[Detection], memory: TftMemory
    ) -> TftAction:
        round_info = memory.current_round

        if state.game is None:
            return wait("No game sub-state detected.")

        if state.game is TftGameSubState.AUGMENT or (round_info and round_info.has_augment):
            return self._pick_augment(detections)

        if state.game is TftGameSubState.CAROUSEL or (
            round_info
            and round_info.round_type in {TftRoundType.PORTAL_SELECT, TftRoundType.CAROUSEL}
        ):
            return self._carousel_action(detections)

        if state.game is TftGameSubState.COMBAT:
            return wait("Combat detected; waiting for next planning window.")

        if round_info and round_info.round_type is TftRoundType.PVE:
            return self._pve_action(detections, memory)

        if round_info and round_info.round_type is TftRoundType.PVP:
            return self._pvp_action(detections, memory)

        if state.game in {TftGameSubState.PVE, TftGameSubState.PVP, TftGameSubState.PLANNING}:
            return self._planning_action(detections, memory)

        return wait(f"No action for {state.game.value}.")

    def _pick_augment(self, detections: list[Detection]) -> TftAction:
        labels = [f"augment_choice_{slot}" for slot in self.config.augment_pick_order]
        target = self._first_detected(labels, detections)
        if target:
            return TftAction(TftActionKind.PICK_AUGMENT, "Pick configured augment slot.", target)
        return wait("Waiting for augment choices.")

    def _carousel_action(self, detections: list[Detection]) -> TftAction:
        target = self._first_detected(["carousel_unit"], detections)
        if target:
            return TftAction(TftActionKind.PICK_CAROUSEL_UNIT, "Pick carousel unit.", target)
        return wait("Waiting for carousel target.")

    def _pve_action(self, detections: list[Detection], memory: TftMemory) -> TftAction:
        target = self._first_detected(["loot_orb", "item_orb"], detections)
        if target:
            return TftAction(TftActionKind.COLLECT_LOOT, "Collect PvE loot.", target)

        planning_action = self._planning_action(detections, memory, allow_reroll=False)
        if planning_action.kind is not TftActionKind.WAIT:
            return planning_action

        return wait("PvE round; waiting for loot or shop action.")

    def _pvp_action(self, detections: list[Detection], memory: TftMemory) -> TftAction:
        planning_action = self._planning_action(detections, memory)
        if planning_action.kind is not TftActionKind.WAIT:
            return planning_action

        return wait("PvP round; no planning target visible, likely combat.")

    def _planning_action(
        self,
        detections: list[Detection],
        memory: TftMemory,
        allow_reroll: bool = True,
    ) -> TftAction:
        shop_labels = [f"buy_shop_slot_{slot}" for slot in self.config.shop_buy_order]
        target = self._first_detected(shop_labels, detections)
        if target:
            if self._bench_is_full(memory):
                return wait("Preferred shop unit detected, but bench occupancy is full.")
            return TftAction(TftActionKind.BUY_UNIT, "Buy preferred champion from shop.", target)

        labels = ["buy_xp_button"]
        if allow_reroll:
            labels.append("reroll_button")

        target = self._first_detected(labels, detections)
        if target and target.label == "buy_xp_button":
            return TftAction(TftActionKind.BUY_XP, "Buy XP when no shop target is available.", target)
        if target and target.label == "reroll_button":
            return TftAction(TftActionKind.REROLL, "Reroll when no shop target is available.", target)

        return wait("No planning action available.")

    def _bench_is_full(self, memory: TftMemory) -> bool:
        if memory.board_matrix is None:
            return False
        bench_slots = [slot_id for slot_id in memory.board_matrix.slot_ids if slot_id.startswith("bench_")]
        if not bench_slots:
            return False
        return all(memory.board_matrix.is_occupied(slot_id) for slot_id in bench_slots)

    def _first_detected(
        self, priority: list[str], detections: list[Detection]
    ) -> Detection | None:
        by_label = {detection.label: detection for detection in detections}
        for label in priority:
            if label in by_label:
                return by_label[label]
        return None
