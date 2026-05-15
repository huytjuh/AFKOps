from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class BotConfig(BaseModel):
    name: str
    dry_run: bool = True
    confidence_threshold: float = 0.82
    object_detection_threshold: float = 0.45
    window_title: str | None = None
    assets_dir: Path = Field(default=Path("assets"))
    screenshots_dir: Path = Field(default=Path("data/screenshots"))
    debug_dir: Path = Field(default=Path("data/debug"))
    models_dir: Path = Field(default=Path("models"))
