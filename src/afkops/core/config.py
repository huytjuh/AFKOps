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
    tft_yolo_model_path: Path = Field(default=Path("models/tft/tft_fast_yolo.pt"))
    tft_yolo_base_model: str = "yolo11n.pt"
    tft_yolo_threshold: float = 0.03
    tft_yolo_image_size: int = 960
    riot_client_path: Path | None = None
    riot_client_args: tuple[str, ...] = (
        "--launch-product=teamfighttactics",
        "--launch-patchline=live",
    )
    riot_client_process_names: tuple[str, ...] = (
        "LeagueClient",
        "LeagueClientUx",
        "LeagueClientUxRender",
        "League of Legends",
        "RiotClientServices",
        "RiotClientUx",
        "RiotClientUxRender",
    )
    riot_client_window_titles: tuple[str, ...] = (
        "League of Legends (TM) Client",
        "League of Legends",
    )
    riot_login_window_titles: tuple[str, ...] = (
        "Riot Client",
        "Riot Sign In",
        "Sign in",
    )
    riot_login_timeout_seconds: float = 30.0
    riot_login_startup_delay_seconds: float = 5.0
    riot_login_form_delay_seconds: float = 5.0
    riot_login_form_scan_seconds: float = 180.0
    riot_login_form_scan_interval_seconds: float = 2.0
    riot_login_form_keywords: tuple[str, ...] = ("username", "password")
    tft_play_button_min_wait_seconds: float = 5.0
    tft_play_button_scan_seconds: float = 120.0
    tft_play_button_scan_interval_seconds: float = 2.0
    tft_play_button_click_delay_min_seconds: float = 0.5
    tft_play_button_click_delay_max_seconds: float = 1.0
    tft_click_after_move_delay_min_seconds: float = 0.15
    tft_click_after_move_delay_max_seconds: float = 0.35
    tft_play_button_text: str = "play"
    tft_matchmaking_step_wait_seconds: float = 2.0
    tft_matchmaking_scan_seconds: float = 120.0
    tft_matchmaking_scan_interval_seconds: float = 2.0
    tft_launcher_to_matchmaking_delay_seconds: float = 60.0
    tft_credentials_path: Path = Field(default=Path("configs/tft_credentials.local.toml"))
    strategy_config_path: Path = Field(default=Path("configs/tft_strategy.local.toml"))
