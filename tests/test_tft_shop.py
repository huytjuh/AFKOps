from afkops.bots.tft.shop import TftShopRecognizer, normalize_champion_id
from afkops.core.vision import Detection


def detection(label: str, x: int, y: int, confidence: float = 1.0) -> Detection:
    return Detection(label=label, confidence=confidence, x=x, y=y, width=80, height=40)


def test_normalizes_champion_names() -> None:
    assert normalize_champion_id("TFT17 Miss Fortune") == "tft17_miss_fortune"
    assert normalize_champion_id("shop_text_tft17_aatrox") == "tft17_aatrox"


def test_shop_recognizer_uses_portrait_detection_inside_slot() -> None:
    recognizer = TftShopRecognizer(preferred_units=["tft17_aatrox"])

    buy_detections = recognizer.buy_detections(
        [
            detection("champion_shop_slot_1", 100, 700),
            detection("champion_tft17_aatrox", 112, 708, confidence=0.86),
        ]
    )

    assert [detection.label for detection in buy_detections] == ["buy_shop_slot_1"]
    assert buy_detections[0].confidence == 0.86


def test_shop_recognizer_uses_text_detection_below_portrait() -> None:
    recognizer = TftShopRecognizer(preferred_units=["tft17_aatrox"])

    buy_detections = recognizer.buy_detections(
        [
            detection("champion_shop_slot_1", 100, 700),
            detection("shop_text_tft17_aatrox", 112, 742, confidence=0.91),
        ]
    )

    assert [detection.label for detection in buy_detections] == ["buy_shop_slot_1"]


def test_shop_recognizer_requires_preferred_unit_when_configured() -> None:
    recognizer = TftShopRecognizer(preferred_units=["tft17_teemo"])

    buy_detections = recognizer.buy_detections(
        [
            detection("champion_shop_slot_1", 100, 700),
            detection("champion_tft17_aatrox", 112, 708, confidence=0.86),
        ]
    )

    assert buy_detections == []


def test_shop_recognizer_requires_buy_confidence() -> None:
    recognizer = TftShopRecognizer(preferred_units=["tft17_aatrox"], buy_confidence=0.9)

    buy_detections = recognizer.buy_detections(
        [
            detection("champion_shop_slot_1", 100, 700),
            detection("champion_tft17_aatrox", 112, 708, confidence=0.86),
        ]
    )

    assert buy_detections == []


def test_shop_recognizer_boosts_agreeing_portrait_and_text() -> None:
    recognizer = TftShopRecognizer(preferred_units=["tft17_aatrox"])

    buy_detections = recognizer.buy_detections(
        [
            detection("champion_shop_slot_1", 100, 700),
            detection("champion_tft17_aatrox", 112, 708, confidence=0.86),
            detection("shop_text_tft17_aatrox", 112, 742, confidence=0.91),
        ]
    )

    assert buy_detections[0].confidence == 0.99
