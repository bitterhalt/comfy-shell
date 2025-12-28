import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

try:
    from rich.console import Console

    console = Console(stderr=True)
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def log_error(msg: str):
    """Print error and exit"""
    if HAS_RICH:
        console.print(f"[bold red]✖ Error:[/bold red] {msg}")
    else:
        print(f"✖ Error: {msg}", file=sys.stderr)
    sys.exit(1)


def log_warning(msg: str):
    """Print warning"""
    if HAS_RICH:
        console.print(f"[bold yellow]⚠ Warning:[/bold yellow] {msg}")
    else:
        print(f"⚠ Warning: {msg}", file=sys.stderr)


def expand_path(path_str: str) -> Path:
    """Expand ~ and environment variables"""
    return Path(os.path.expanduser(os.path.expandvars(path_str)))


@dataclass
class PathConfig:
    """File and directory paths"""

    # Base directories
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "ignis")
    data_dir: Path = field(
        default_factory=lambda: Path.home() / ".local" / "share" / "ignis"
    )
    config_dir: Path = field(default_factory=lambda: Path.home() / ".config" / "ignis")

    # User-configurable directories
    recordings_dir: Path = Path.home() / "Videos" / "Captures"
    screenshots_dir: Path = Path.home() / "Pictures" / "Screenshots"

    # Derived paths
    weather_cache: Path = field(init=False)
    timer_queue: Path = field(init=False)

    def __post_init__(self):
        """Set derived paths and ensure directories exist"""
        self.weather_cache = self.cache_dir / "weather_cache.json"
        self.timer_queue = self.data_dir / "timers" / "queue.json"

        # Create directories
        for directory in [
            self.cache_dir,
            self.data_dir,
            self.config_dir,
            self.recordings_dir,
            self.screenshots_dir,
            self.data_dir / "timers",
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        # Initialize timer queue if needed
        if not self.timer_queue.exists():
            self.timer_queue.write_text("[]")

    @classmethod
    def from_dict(cls, data: Dict) -> "PathConfig":
        """Create from config dict"""
        return cls(
            recordings_dir=expand_path(data.get("recordings_dir", "~/Videos/Captures")),
            screenshots_dir=expand_path(
                data.get("screenshots_dir", "~/Pictures/Screenshots")
            ),
        )


@dataclass
class WeatherConfig:
    """Weather widget configuration"""

    api_key: str = ""
    city_id: str = "643492"
    cache_ttl: int = 600
    use_12h_format: bool = False
    icon_base_path: str = "~/.config/ignis/assets/icons/weather"

    def __post_init__(self):
        """Validate and resolve paths"""
        # Check environment variables as fallback
        if not self.api_key:
            self.api_key = os.getenv("OPEN_WEATHER_APIKEY", "")

        if not self.city_id or self.city_id == "643492":
            self.city_id = os.getenv("OPEN_WEATHER_CITY_ID", "643492")

        # Expand icon path
        self.icon_base_path = os.path.expanduser(self.icon_base_path)

    @classmethod
    def from_dict(cls, data: Dict) -> "WeatherConfig":
        """Create from config dict"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class MonitorConfig:
    """Monitor assignments"""

    primary: int = 0
    bar: int = 0
    osd: int = 0
    notifications: int = 0
    recording_overlay: int = 0
    window_switcher: int = 0
    weather: int = 0
    power_overlay: int = 0
    system_menu: int = 0
    integrated_center: int = 0

    @classmethod
    def from_dict(cls, data: Dict) -> "MonitorConfig":
        """Create from config dict"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class TimeoutConfig:
    """OSD timeout durations in milliseconds"""

    osd: int = 2000
    volume_osd: int = 2000
    media_osd: int = 5000
    time_osd: int = 8000
    workspace_osd: int = 1500

    @classmethod
    def from_dict(cls, data: Dict) -> "TimeoutConfig":
        """Create from config dict"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class BarConfig:
    """Bar settings"""

    remember_state: bool = True

    @classmethod
    def from_dict(cls, data: Dict) -> "BarConfig":
        """Create from config dict"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class NotificationConfig:
    """Notification settings"""

    max_history: int = 10
    popup_timeout: int = 5000

    @classmethod
    def from_dict(cls, data: Dict) -> "NotificationConfig":
        """Create from config dict"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class UIConfig:
    """UI and appearance settings"""

    monitors: MonitorConfig = field(default_factory=MonitorConfig)
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    bar: BarConfig = field(default_factory=BarConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)

    # Convenience properties for backward compatibility
    @property
    def primary_monitor(self) -> int:
        return self.monitors.primary

    @property
    def bar_monitor(self) -> int:
        return self.monitors.bar

    @property
    def osd_monitor(self) -> int:
        return self.monitors.osd

    @property
    def notifications_monitor(self) -> int:
        return self.monitors.notifications

    @property
    def recording_overlay_monitor(self) -> int:
        return self.monitors.recording_overlay

    @property
    def window_switcher_monitor(self) -> int:
        return self.monitors.window_switcher

    @property
    def weather_monitor(self) -> int:
        return self.monitors.weather

    @property
    def power_overlay_monitor(self) -> int:
        return self.monitors.power_overlay

    @property
    def system_menu_monitor(self) -> int:
        return self.monitors.system_menu

    @property
    def integrated_center_monitor(self) -> int:
        return self.monitors.integrated_center

    @property
    def osd_timeout(self) -> int:
        return self.timeouts.osd

    @property
    def volume_osd_timeout(self) -> int:
        return self.timeouts.volume_osd

    @property
    def media_osd_timeout(self) -> int:
        return self.timeouts.media_osd

    @property
    def time_osd_timeout(self) -> int:
        return self.timeouts.time_osd

    @property
    def workspace_osd_timeout(self) -> int:
        return self.timeouts.workspace_osd

    @property
    def bar_remember_state(self) -> bool:
        return self.bar.remember_state

    @property
    def max_notifications(self) -> int:
        return self.notifications.max_history

    @property
    def notification_popup_timeout(self) -> int:
        return self.notifications.popup_timeout

    @classmethod
    def from_dict(cls, data: Dict) -> "UIConfig":
        """Create from config dict"""
        return cls(
            monitors=MonitorConfig.from_dict(data.get("monitors", {})),
            timeouts=TimeoutConfig.from_dict(data.get("timeouts", {})),
            bar=BarConfig.from_dict(data.get("bar", {})),
            notifications=NotificationConfig.from_dict(data.get("notifications", {})),
        )


@dataclass
class RecorderConfig:
    """Recording settings"""

    audio_device: str = "default_output"
    video_format: str = "mp4"

    @classmethod
    def from_dict(cls, data: Dict) -> "RecorderConfig":
        """Create from config dict"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class BatteryConfig:
    """Battery widget thresholds"""

    critical_threshold: int = 15
    warning_threshold: int = 30

    def __post_init__(self):
        """Validate thresholds"""
        if self.critical_threshold >= self.warning_threshold:
            log_warning(
                f"Battery critical_threshold ({self.critical_threshold}) "
                f"should be less than warning_threshold ({self.warning_threshold})"
            )

    @classmethod
    def from_dict(cls, data: Dict) -> "BatteryConfig":
        """Create from config dict"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class AnimationConfig:
    """Animation settings"""

    revealer_duration: int = 180
    revealer_type: str = "slide_down"

    def __post_init__(self):
        """Validate animation type"""
        valid_types = [
            "slide_down",
            "slide_up",
            "slide_left",
            "slide_right",
            "crossfade",
            "none",
        ]
        if self.revealer_type not in valid_types:
            log_warning(
                f"Invalid revealer_type '{self.revealer_type}'. "
                f"Must be one of: {', '.join(valid_types)}. Using 'slide_down'."
            )
            self.revealer_type = "slide_down"

    @classmethod
    def from_dict(cls, data: Dict) -> "AnimationConfig":
        """Create from config dict"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class AppConfig:
    """Main configuration"""

    paths: PathConfig = field(default_factory=PathConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    recorder: RecorderConfig = field(default_factory=RecorderConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)
    animations: AnimationConfig = field(default_factory=AnimationConfig)

    @classmethod
    def from_file(cls, config_file: Path = None) -> "AppConfig":
        """Load configuration from JSON file"""
        if config_file is None:
            config_file = Path.home() / ".config" / "ignis" / "config.json"

        if not config_file.exists():
            log_error(f"Config file not found: {config_file}")

        try:
            with open(config_file) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            log_error(f"Failed to parse {config_file}: {e}")
        except Exception as e:
            log_error(f"Failed to read {config_file}: {e}")

        return cls(
            paths=PathConfig.from_dict(data.get("paths", {})),
            weather=WeatherConfig.from_dict(data.get("weather", {})),
            ui=UIConfig.from_dict(data.get("ui", {})),
            recorder=RecorderConfig.from_dict(data.get("recorder", {})),
            battery=BatteryConfig.from_dict(data.get("battery", {})),
            animations=AnimationConfig.from_dict(data.get("animations", {})),
        )


config = AppConfig.from_file()
