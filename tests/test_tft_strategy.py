from afkops.bots.tft.actions import TftActionKind
from afkops.bots.tft.board import BoardMatrix
from afkops.bots.tft.memory import TftMemory
from afkops.bots.tft.round_admin import TftRoundPlan
from afkops.bots.tft.states import TftClientState, TftGameSubState, TftState
from afkops.bots.tft.strategy import TftStrategy
from afkops.bots.tft.strategy_config import TftStrategyConfig
from afkops.core.vision import Detection


def detection(label: str) -> Detection:
    return Detection(label=label, confidence=1.0, x=0, y=0, width=10, height=10)


def memory_for_round(label: str) -> TftMemory:
    memory = TftMemory()
    memory.current_round = TftRoundPlan().get(label)
    return memory


def test_strategy_returns_action_object_for_augment_choice() -> None:
    strategy = TftStrategy(TftStrategyConfig(augment_pick_order=[2, 1, 3]))
    state = TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.AUGMENT)

    action = strategy.choose_next_action(
        state,
        [detection("augment_choice_1"), detection("augment_choice_2")],
        TftMemory(),
    )

    assert action.kind is TftActionKind.PICK_AUGMENT
    assert action.detection is not None
    assert action.detection.label == "augment_choice_2"


def test_strategy_prioritizes_augment_round_from_progression() -> None:
    state = TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.PVP)

    action = TftStrategy().choose_next_action(
        state,
        [detection("augment_choice_1"), detection("champion_shop_slot_1")],
        memory_for_round("2-1"),
    )

    assert action.kind is TftActionKind.PICK_AUGMENT
    assert action.detection is not None
    assert action.detection.label == "augment_choice_1"


def test_strategy_picks_carousel_target_on_carousel_round() -> None:
    state = TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.PVP)

    action = TftStrategy().choose_next_action(
        state,
        [detection("carousel_unit"), detection("champion_shop_slot_1")],
        memory_for_round("2-4"),
    )

    assert action.kind is TftActionKind.PICK_CAROUSEL_UNIT


def test_strategy_collects_loot_on_pve_round() -> None:
    state = TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.PVE)

    action = TftStrategy().choose_next_action(
        state,
        [detection("loot_orb"), detection("champion_shop_slot_1")],
        memory_for_round("2-7"),
    )

    assert action.kind is TftActionKind.COLLECT_LOOT


def test_strategy_buys_unit_during_pvp_planning_window() -> None:
    state = TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.PLANNING)

    action = TftStrategy().choose_next_action(
        state,
        [detection("buy_shop_slot_1")],
        memory_for_round("2-2"),
    )

    assert action.kind is TftActionKind.BUY_UNIT


def test_strategy_does_not_buy_plain_visible_shop_slot() -> None:
    state = TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.PLANNING)

    action = TftStrategy().choose_next_action(
        state,
        [detection("champion_shop_slot_1")],
        memory_for_round("2-2"),
    )

    assert action.kind is TftActionKind.WAIT


def test_strategy_does_not_buy_when_bench_is_full() -> None:
    state = TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.PLANNING)
    memory = memory_for_round("2-2")
    bench_slots = [f"bench_{slot}" for slot in range(1, 10)]
    memory.board_matrix = BoardMatrix(
        slot_ids=bench_slots,
        occupied_slots=set(bench_slots),
    )

    action = TftStrategy().choose_next_action(
        state,
        [detection("buy_shop_slot_1")],
        memory,
    )

    assert action.kind is TftActionKind.WAIT


def test_strategy_waits_when_no_target_is_available() -> None:
    state = TftState(client=TftClientState.GAME_CLIENT, game=TftGameSubState.PVP)

    action = TftStrategy().choose_next_action(state, [], TftMemory())

    assert action.kind is TftActionKind.WAIT
