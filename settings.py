import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.theme import Theme

# ═══════════════════════════════════════════════════════════════
# Rich Console Setup for Colored Output
# ═══════════════════════════════════════════════════════════════

rich_theme = Theme(
    {
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold cyan",
        "success": "bold green",
        "value": "bold magenta",
    }
)

console = Console(stderr=True, theme=rich_theme)


def colored_warning(message: str) -> None:
    """Display a rich formatted warning"""
    console.print(f"[warning]⚠ Warning:[/warning] {message}")
    warnings.warn(message, UserWarning, stacklevel=3)


def colored_error(message: str) -> None:
    """Display a rich formatted error"""
    console.print(f"[error]✖ Error:[/error] {message}")


def colored_info(message: str) -> None:
    """Display a rich formatted info message"""
    console.print(f"[info]ℹ Info:[/info] {message}")


def colored_success(message: str) -> None:
    """Display a rich formatted success message"""
    console.print(f"[success]✓ Success:[/success] {message}")


# ═══════════════════════════════════════════════════════════════
# Configuration Classes
# ═══════════════════════════════════════════════════════════════


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
        self.weather_cache = self.cache_dir / "weather_cache. json"
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

    def __post_init__(self):
        """Validate weather configuration"""
        if not self.api_key:
            colored_warning(
                "Weather API key not set. Set [value]OPEN_WEATHER_APIKEY[/value] "
                "environment variable.  Weather widgets will not work properly."
            )

        # Verify icon directory exists
        icon_path = Path(self.icon_base_path)
        if not icon_path.exists():
            colored_warning(
                f"Weather icon directory not found: [value]{self.icon_base_path}[/value]. "
                f"Weather icons may not display correctly."
            )


@dataclass
class UIConfig:
    """UI and appearance settings"""

    # ═══════════════════════════════════════════════════════════════
    # MONITOR CONFIGURATION - Edit these to control window placement
    # ═══════════════════════════════════════════════════════════════

    # Primary monitor (0 = first monitor, 1 = second, etc.)
    primary_monitor: int = 0
    bar_monitor: int = 0
    osd_monitor: int = 0
    launcher_monitor: int = 0
    notifications_monitor: int = 0
    recording_overlay_monitor: int = 0
    window_switcher_monitor: int = 0
    weather_monitor: int = 0
    power_overlay_monitor: int = 0
    system_menu_monitor: int = 0
    integrated_center_monitor: int = 0

    # OSD timeouts (milliseconds)
    osd_timeout: int = 2000
    volume_osd_timeout: int = 2000
    media_osd_timeout: int = 5000
    time_osd_timeout: int = 8000
    workspace_osd_timeout: int = 1500

    def __post_init__(self):
        """Validate monitor configuration"""
        from ignis import utils

        try:
            monitors = utils.get_monitors()
            monitor_count = len(monitors)

            # List of all monitor settings to validate
            monitor_settings = [
                ("primary_monitor", self.primary_monitor),
                ("bar_monitor", self.bar_monitor),
                ("osd_monitor", self.osd_monitor),
                ("launcher_monitor", self.launcher_monitor),
                ("notifications_monitor", self.notifications_monitor),
                ("recording_overlay_monitor", self.recording_overlay_monitor),
                ("window_switcher_monitor", self.window_switcher_monitor),
                ("weather_monitor", self.weather_monitor),
                ("power_overlay_monitor", self.power_overlay_monitor),
                ("system_menu_monitor", self.system_menu_monitor),
                ("integrated_center_monitor", self.integrated_center_monitor),
            ]

            # Validate each monitor setting
            for setting_name, monitor_id in monitor_settings:
                if monitor_id >= monitor_count or monitor_id < 0:
                    colored_warning(
                        f"[value]{setting_name}[/value] is set to [error]{monitor_id}[/error], "
                        f"but only [success]{monitor_count}[/success] monitor(s) detected. "
                        f"Falling back to monitor 0."
                    )
                    setattr(self, setting_name, 0)

        except Exception as e:
            colored_error(
                f"Could not validate monitor configuration: {e}. "
                "All windows will default to primary monitor."
            )


@dataclass
class RecorderConfig:
    """Recording settings"""

    output_dir: Path = field(
        default_factory=lambda: Path.home() / "Videos" / "Captures"
    )
    audio_device: str = "default_output"
    video_format: str = "mp4"

    def __post_init__(self):
        """Ensure recording directory exists"""
        self.output_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class BatteryConfig:
    """Battery widget thresholds"""

    critical_threshold: int = 15  # percentage
    warning_threshold: int = 30  # percentage

    def __post_init__(self):
        """Validate battery thresholds"""
        if not 0 <= self.critical_threshold <= 100:
            colored_warning(
                f"[value]critical_threshold[/value] ([error]{self.critical_threshold}[/error]) "
                f"must be between 0-100. Using default value [success]15[/success]."
            )
            self.critical_threshold = 15

        if not 0 <= self.warning_threshold <= 100:
            colored_warning(
                f"[value]warning_threshold[/value] ([error]{self.warning_threshold}[/error]) "
                f"must be between 0-100. Using default value [success]30[/success]."
            )
            self.warning_threshold = 30

        if self.critical_threshold >= self.warning_threshold:
            colored_warning(
                f"[value]critical_threshold[/value] ([error]{self.critical_threshold}[/error]) "
                f"should be less than [value]warning_threshold[/value] "
                f"([error]{self.warning_threshold}[/error]). Adjusting values."
            )
            self.critical_threshold = 15
            self.warning_threshold = 30


@dataclass
class AppConfig:
    """Main application configuration"""

    paths: PathConfig = field(default_factory=PathConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    recorder: RecorderConfig = field(default_factory=RecorderConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)


# Global configuration instance
config = AppConfig()


# Convenience function
def get_config() -> AppConfig:
    """Get the global configuration instance"""
    return config
