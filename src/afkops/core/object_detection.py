from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from afkops.core.vision import Detection


class ObjectDetectionModel:
    def __init__(self, model_path: Path, threshold: float = 0.45) -> None:
        self.model_path = model_path
        self.threshold = threshold
        self._model: Any | None = None

    @property
    def available(self) -> bool:
        return self.model_path.exists() and self._load_model() is not None

    def detect(self, image: np.ndarray) -> list[Detection]:
        model = self._load_model()
        if model is None:
            return []

        results = model.predict(image, verbose=False, conf=self.threshold)
        detections: list[Detection] = []
        for result in results:
            names = result.names
            for box in result.boxes:
                confidence = float(box.conf[0])
                if confidence < self.threshold:
                    continue

                class_id = int(box.cls[0])
                label = str(names[class_id])
                x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
                detections.append(
                    Detection(
                        label=label,
                        confidence=confidence,
                        x=x1,
                        y=y1,
                        width=max(1, x2 - x1),
                        height=max(1, y2 - y1),
                    )
                )
        return detections

    def _load_model(self) -> Any | None:
        if self._model is not None:
            return self._model
        if not self.model_path.exists():
            return None

        try:
            from ultralytics import YOLO
        except ImportError:
            return None

        self._model = YOLO(str(self.model_path))
        return self._model
