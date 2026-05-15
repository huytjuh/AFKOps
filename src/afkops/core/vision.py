from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


class TemplateDetector:
    def __init__(self, threshold: float = 0.82) -> None:
        self.threshold = threshold

    def find(self, image: np.ndarray, template_path: Path, label: str) -> Detection | None:
        confidence, max_location, width, height = self.score(image, template_path)
        if confidence < self.threshold:
            return None

        return Detection(
            label=label,
            confidence=float(confidence),
            x=max_location[0],
            y=max_location[1],
            width=width,
            height=height,
        )

    def score(self, image: np.ndarray, template_path: Path) -> tuple[float, tuple[int, int], int, int]:
        template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if template is None:
            raise FileNotFoundError(f"Template not found: {template_path}")

        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        _, confidence, _, max_location = cv2.minMaxLoc(result)
        height, width = template.shape[:2]
        return float(confidence), max_location, width, height


class DetectionOverlayWriter:
    def save(
        self,
        image: np.ndarray,
        detections: list[Detection],
        output_path: Path,
        selected: Detection | None = None,
        points: list[tuple[str, int, int]] | None = None,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        overlay = image.copy()

        for detection in detections:
            color = (0, 255, 0) if detection == selected else (255, 180, 0)
            top_left = (detection.x, detection.y)
            bottom_right = (detection.x + detection.width, detection.y + detection.height)
            cv2.rectangle(overlay, top_left, bottom_right, color, 2)
            cv2.circle(overlay, detection.center, 4, color, -1)

            text = f"{detection.label} {detection.confidence:.2f}"
            text_origin = (detection.x, max(16, detection.y - 6))
            cv2.putText(
                overlay,
                text,
                text_origin,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )

        for label, x, y in points or []:
            color = (255, 0, 255)
            cv2.circle(overlay, (x, y), 5, color, -1)
            cv2.putText(
                overlay,
                label,
                (x + 6, y - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
                cv2.LINE_AA,
            )

        cv2.imwrite(str(output_path), overlay)
