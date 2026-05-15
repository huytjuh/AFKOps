from __future__ import annotations

import pyautogui


class MouseController:
    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def click(self, x: int, y: int) -> None:
        if self.dry_run:
            print(f"[dry-run] click at ({x}, {y})")
            return
        pyautogui.click(x=x, y=y)

