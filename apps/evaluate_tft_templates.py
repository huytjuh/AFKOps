from __future__ import annotations

import argparse
from pathlib import Path
import sys

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from afkops.core.vision import TemplateDetector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate TFT template confidence on one image.")
    parser.add_argument("image", type=Path, help="Screenshot or debug image to scan.")
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=PROJECT_ROOT / "assets" / "templates" / "tft",
        help="Directory containing .png templates.",
    )
    parser.add_argument("--threshold", type=float, default=0.0, help="Only print scores >= threshold.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {args.image}")

    detector = TemplateDetector()
    rows: list[tuple[str, float, tuple[int, int]]] = []
    for template_path in sorted(args.templates_dir.glob("*.png")):
        confidence, location, _, _ = detector.score(image, template_path)
        if confidence >= args.threshold:
            rows.append((template_path.stem, confidence, location))

    if not rows:
        print("No templates found or no scores met the threshold.")
        return

    for label, confidence, location in sorted(rows, key=lambda row: row[1], reverse=True):
        print(f"{label:<28} {confidence:.3f} at {location}")


if __name__ == "__main__":
    main()
