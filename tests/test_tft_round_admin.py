from afkops.bots.tft.progression_monitor import TftProgressionMonitor
from afkops.bots.tft.round_admin import TftAugmentTier, TftRoundAdmin, TftRoundPlan, TftRoundType
from afkops.bots.tft.states import TftGameSubState
from afkops.core.vision import Detection


def detection(label: str) -> Detection:
    return Detection(label=label, confidence=1.0, x=0, y=0, width=10, height=10)


def test_round_plan_has_stage_one_and_stages_two_to_seven() -> None:
    plan = TftRoundPlan()

    assert len(plan.rounds) == 46
    assert plan.rounds[0].label == "1-1"
    assert plan.rounds[-1].label == "7-7"


def test_round_plan_assigns_expected_states() -> None:
    plan = TftRoundPlan()

    assert plan.rounds[0].expected_state is TftGameSubState.CAROUSEL
    assert plan.get("1-2").round_type is TftRoundType.PVE
    assert plan.get("2-1").round_type is TftRoundType.PVP
    assert plan.get("2-4").round_type is TftRoundType.CAROUSEL
    assert plan.get("2-7").round_type is TftRoundType.PVE


def test_round_plan_marks_augment_rounds() -> None:
    plan = TftRoundPlan()

    assert plan.get("2-1").augment_tier is TftAugmentTier.SILVER
    assert plan.get("3-2").augment_tier is TftAugmentTier.GOLD
    assert plan.get("4-2").augment_tier is TftAugmentTier.PRISMATIC
    assert plan.get("2-1").expected_state is TftGameSubState.AUGMENT


def test_round_admin_advances_in_order() -> None:
    admin = TftRoundAdmin()

    assert admin.current.label == "1-1"
    admin.advance()
    assert admin.current.label == "1-2"
    admin.advance()
    assert admin.current.label == "1-3"


def test_progression_monitor_syncs_from_round_template_label() -> None:
    monitor = TftProgressionMonitor()

    monitor.update([detection("round_3_2")])

    assert monitor.admin.current.label == "3-2"
    assert monitor.admin.current.augment_tier is TftAugmentTier.GOLD


def test_progression_monitor_syncs_from_ocr_round_label() -> None:
    monitor = TftProgressionMonitor()

    monitor.update([detection("ocr_round_4_2")])

    assert monitor.admin.current.label == "4-2"
    assert monitor.admin.current.augment_tier is TftAugmentTier.PRISMATIC
