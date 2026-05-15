from __future__ import annotations

import argparse
from pathlib import Path
import sys

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from afkops.core.template_cropper import CropBox, TemplateCropper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crop a TFT template from a saved screenshot.")
    parser.add_argument("image", type=Path, help="Screenshot path, usually from data/screenshots/tft.")
    parser.add_argument("label", help="Template label, for example round_2_1 or find_match_button.")
    parser.add_argument("--x", type=int, help="Crop left coordinate.")
    parser.add_argument("--y", type=int, help="Crop top coordinate.")
    parser.add_argument("--width", type=int, help="Crop width.")
    parser.add_argument("--height", type=int, help="Crop height.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "assets" / "templates" / "tft",
        help="Template output directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cropper = TemplateCropper()
    image = cropper.load_image(args.image)

    if all(value is not None for value in [args.x, args.y, args.width, args.height]):
        box = CropBox(x=args.x, y=args.y, width=args.width, height=args.height)
    else:
        print("Select the template area, press Enter/Space to confirm, or C to cancel.")
        x, y, width, height = cv2.selectROI("Crop TFT template", image, showCrosshair=True)
        cv2.destroyWindow("Crop TFT template")
        box = CropBox(x=int(x), y=int(y), width=int(width), height=int(height))

    crop = cropper.crop(image, box)
    output_path = cropper.save_template(crop, args.output_dir, args.label)
    print(f"Saved template: {output_path}")


if __name__ == "__main__":
    main()

