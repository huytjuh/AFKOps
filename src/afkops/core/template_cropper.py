from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class CropBox:
    x: int
    y: int
    width: int
    height: int

    def validate_for(self, image: np.ndarray) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Crop width and height must be greater than zero.")
        if self.x < 0 or self.y < 0:
            raise ValueError("Crop x and y must be positive.")

        image_height, image_width = image.shape[:2]
        if self.x + self.width > image_width or self.y + self.height > image_height:
            raise ValueError(
                f"Crop box {self} is outside image bounds {image_width}x{image_height}."
            )


class TemplateCropper:
    def load_image(self, image_path: Path) -> np.ndarray:
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"Could not read screenshot: {image_path}")
        return image

    def crop(self, image: np.ndarray, box: CropBox) -> np.ndarray:
        box.validate_for(image)
        return image[box.y : box.y + box.height, box.x : box.x + box.width].copy()

    def save_template(self, crop: np.ndarray, output_dir: Path, label: str) -> Path:
        if not label:
            raise ValueError("Template label cannot be empty.")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{label}.png"
        if not cv2.imwrite(str(output_path), crop):
            raise OSError(f"Could not write template: {output_path}")
        return output_path

