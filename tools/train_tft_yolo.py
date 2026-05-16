from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a fast lightweight TFT YOLO model.")
    parser.add_argument("--data", type=Path, default=Path("configs/tft_yolo_dataset.yaml"))
    parser.add_argument("--base-model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--output-dir", type=Path, default=Path("models/tft"))
    parser.add_argument("--name", default="tft_fast_yolo")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise SystemExit("Install the optional 'detect' dependencies to train YOLO.") from error

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.base_model)
    result = model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        project=str(args.output_dir),
        name=args.name,
    )
    print(result)
    print(f"Copy best weights to: {args.output_dir / 'tft_fast_yolo.pt'}")


if __name__ == "__main__":
    main()
