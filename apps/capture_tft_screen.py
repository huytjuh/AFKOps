from __future__ import annotations

from datetime import datetime
import argparse
from pathlib import Path
import sys

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from afkops.core.screen import ScreenCapture


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a TFT screenshot.")
    parser.add_argument(
        "--window-title",
        default="League of Legends (TM) Client",
        help="Capture only a window whose title contains this text.",
    )
    parser.add_argument(
        "--full-screen",
        action="store_true",
        help="Capture the primary monitor instead of a named window.",
    )
    parser.add_argument(
        "--include-window-frame",
        action="store_true",
        help="Capture the full window rectangle instead of the client area.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = PROJECT_ROOT / "data" / "tft" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"tft_{timestamp}.png"

    capture = ScreenCapture()
    if args.full_screen:
        screenshot = capture.grab()
    elif args.include_window_frame:
        screenshot = capture.grab(capture.find_window_region(args.window_title, client_area=False))
    else:
        screenshot = capture.grab_window(args.window_title)
    cv2.imwrite(str(output_path), screenshot)
    print(f"Saved screenshot: {output_path}")


if __name__ == "__main__":
    main()
