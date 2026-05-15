from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic


@dataclass
class SafetyController:
    click_cooldown_seconds: float = 0.75
    max_clicks_per_minute: int = 40
    _last_click_at: float = 0.0
    _click_timestamps: list[float] = field(default_factory=list)

    def can_click(self) -> bool:
        now = monotonic()
        if now - self._last_click_at < self.click_cooldown_seconds:
            return False

        cutoff = now - 60.0
        self._click_timestamps = [
            timestamp for timestamp in self._click_timestamps if timestamp >= cutoff
        ]
        return len(self._click_timestamps) < self.max_clicks_per_minute

    def record_click(self) -> None:
        now = monotonic()
        self._last_click_at = now
        self._click_timestamps.append(now)

