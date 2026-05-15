import cv2
import numpy as np
import pytest

from afkops.core.template_cropper import CropBox, TemplateCropper


def test_template_cropper_saves_named_crop(tmp_path) -> None:
    image = np.zeros((40, 60, 3), dtype=np.uint8)
    image[10:20, 15:30] = (255, 255, 255)

    cropper = TemplateCropper()
    crop = cropper.crop(image, CropBox(x=15, y=10, width=15, height=10))
    output_path = cropper.save_template(crop, tmp_path, "round_2_1")

    saved = cv2.imread(str(output_path))
    assert saved is not None
    assert saved.shape[:2] == (10, 15)


def test_template_cropper_rejects_out_of_bounds_crop() -> None:
    image = np.zeros((40, 60, 3), dtype=np.uint8)

    with pytest.raises(ValueError):
        TemplateCropper().crop(image, CropBox(x=50, y=30, width=20, height=20))
