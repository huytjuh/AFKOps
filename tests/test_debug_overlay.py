import cv2
import numpy as np

from afkops.core.vision import Detection, DetectionOverlayWriter


def test_overlay_writer_saves_debug_image(tmp_path) -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    detection = Detection(label="find_match_button", confidence=0.9, x=10, y=10, width=20, height=20)
    output_path = tmp_path / "latest_detection.png"

    DetectionOverlayWriter().save(image, [detection], output_path, selected=detection)

    assert output_path.exists()
    assert cv2.imread(str(output_path)) is not None
