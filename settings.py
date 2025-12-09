import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PathConfig:
    """File and directory paths"""

    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "ignis")
    data_dir: Path = field(
        default_factory=lambda: Path.home() / ".local" / "share" / "ignis"
    )
    config_dir: Path = field(default_factory=lambda: Path.home() / ".config" / "ignis")

    # Specific file paths
    weather_cache: Path = field(init=False)
    timer_queue: Path = field(init=False)
    emoji_file: Path = field(init=False)

    # Output directories
    recordings_dir: Path = field(
        default_factory=lambda: Path.home() / "Videos" / "Captures"
    )
    screenshots_dir: Path = field(
        default_factory=lambda: Path.home() / "Pictures" / "Screenshots"
    )

    def __post_init__(self):
        """Set derived paths and ensure directories exist"""
        self.weather_cache = self.cache_dir / "weather_cache.json"
        self.timer_queue = self.data_dir / "timers" / "queue.json"
        self.emoji_file = self.config_dir / "assets" / "emoji" / "emoji"

        # Create directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "timers").mkdir(parents=True, exist_ok=True)

        # Initialize timer queue if it doesn't exist
        if not self.timer_queue.exists():
            self.timer_queue.write_text("[]")


@dataclass
class WeatherConfig:
    """Weather widget configuration"""

    api_key: str = field(default_factory=lambda: os.getenv("OPEN_WEATHER_APIKEY", ""))
    city_id: str = field(
        default_factory=lambda: os.getenv("OPEN_WEATHER_CITY_ID", "643492")
    )
    cache_ttl: int = 600  # seconds
    use_12h_format: bool = field(
        default_factory=lambda: os.getenv("IGNIS_WEATHER_12H", "").lower()
        in ("1", "true", "yes", "on")
    )
    icon_base_path: str = field(
        default_factory=lambda: os.path.expanduser(
            "~/.config/ignis/assets/icons/weather"
        )
    )


@dataclass
class UIConfig:
    """UI and appearance settings"""

    # OSD settings
    osd_timeout: int = 2000  # milliseconds
    volume_osd_timeout: int = 2000
    media_osd_timeout: int = 5000
    time_osd_timeout: int = 8000
    workspace_osd_timeout: int = 1500


@dataclass
class AppConfig:
    """Main application configuration"""

    paths: PathConfig = field(default_factory=PathConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    # Terminal and editor
    terminal: str = field(default_factory=lambda: os.getenv("TERMINAL", "foot"))
    editor: str = field(default_factory=lambda: os.getenv("EDITOR", "nvim"))
    file_opener: str = field(default_factory=lambda: os.getenv("FILE_OPENER", "vopen"))

    # Launher match color
    match_color: str = "#24837B"

    # Terminal command format for applications
    terminal_format: str = field(init=False)

    def __post_init__(self):
        self.terminal_format = f"{self.terminal} %command%"


# Global configuration instance
config = AppConfig()


# Convenience function
def get_config() -> AppConfig:
    """Get the global configuration instance"""
    return config
