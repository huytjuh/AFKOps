from afkops.core.safety import SafetyController


def test_safety_blocks_immediate_second_click() -> None:
    safety = SafetyController(click_cooldown_seconds=10, max_clicks_per_minute=40)

    assert safety.can_click()
    safety.record_click()

    assert not safety.can_click()
