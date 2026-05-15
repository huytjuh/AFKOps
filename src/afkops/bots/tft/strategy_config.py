from __future__ import annotations

from pathlib import Path
import tomllib

from pydantic import BaseModel, Field


class TftStrategyConfig(BaseModel):
    preferred_units: list[str] = Field(default_factory=list)
    preferred_items: list[str] = Field(default_factory=list)
    augment_pick_order: list[int] = Field(default_factory=lambda: [1, 2, 3])
    shop_buy_order: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    shop_buy_confidence: float = 0.78
    click_cooldown_seconds: float = 0.75
    max_clicks_per_minute: int = 40

    @classmethod
    def load(cls, path: Path) -> "TftStrategyConfig":
        if not path.exists():
            return cls()

        with path.open("rb") as file:
            return cls.model_validate(tomllib.load(file))
