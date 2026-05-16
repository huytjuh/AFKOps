from __future__ import annotations

import argparse
from pathlib import Path

import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract periodic image frames from a video.")
    parser.add_argument("video", type=Path, help="Input video path.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/tft/yolo/images/train"),
        help="Directory where extracted PNG frames are written.",
    )
    parser.add_argument(
        "--every-seconds",
        type=float,
        default=2.0,
        help="Extract one frame every N seconds.",
    )
    parser.add_argument("--prefix", default="frame", help="Output filename prefix.")
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="First numeric suffix for generated filenames.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output frame files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.every_seconds <= 0:
        raise SystemExit("--every-seconds must be greater than 0.")
    if not args.video.exists():
        raise SystemExit(f"Video not found: {args.video}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise SystemExit(f"Could not open video: {args.video}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise SystemExit(f"Could not read FPS for video: {args.video}")

    frame_step = max(1, round(fps * args.every_seconds))
    frame_index = 0
    saved_count = 0
    output_index = args.start_index

    while True:
        ok, frame = capture.read()
        if not ok:
            break

        if frame_index % frame_step == 0:
            output_path = args.output_dir / f"{args.prefix}_{output_index:04d}.png"
            if output_path.exists() and not args.overwrite:
                print(f"Skipped existing frame: {output_path}")
            else:
                if not cv2.imwrite(str(output_path), frame):
                    raise SystemExit(f"Could not write frame: {output_path}")
                saved_count += 1
                print(f"Saved {output_path}")
            output_index += 1

        frame_index += 1

    capture.release()
    print(f"Extracted {saved_count} frame(s) from {args.video}")


if __name__ == "__main__":
    main()
