"""
Base configuration classes
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from .loader import colored_warning, expand_path


@dataclass
class PathConfig:
    """File and directory paths"""

    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "ignis")
    data_dir: Path = field(
        default_factory=lambda: Path.home() / ".local" / "share" / "ignis"
    )
    config_dir: Path = field(default_factory=lambda: Path.home() / ".config" / "ignis")

    # User-configurable directories
    recordings_dir: Path = field(
        default_factory=lambda: Path.home() / "Videos" / "Captures"
    )
    screenshots_dir: Path = field(
        default_factory=lambda: Path.home() / "Pictures" / "Screenshots"
    )

    # Specific file paths (derived)
    weather_cache: Path = field(init=False)
    timer_queue: Path = field(init=False)
    emoji_file: Path = field(init=False)

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

    @classmethod
    def from_dict(cls, data: Dict) -> "PathConfig":
        """Create PathConfig from dictionary"""
        recordings_dir = expand_path(data.get("recordings_dir", "~/Videos/Captures"))
        screenshots_dir = expand_path(
            data.get("screenshots_dir", "~/Pictures/Screenshots")
        )

        return cls(recordings_dir=recordings_dir, screenshots_dir=screenshots_dir)


@dataclass
class WeatherConfig:
    """Weather widget configuration"""

    api_key: str = ""
    city_id: str = "643492"
    cache_ttl: int = 600  # seconds
    use_12h_format: bool = False
    icon_base_path: str = field(
        default_factory=lambda: os.path.expanduser(
            "~/.config/ignis/assets/icons/weather"
        )
    )

    def __post_init__(self):
        """Validate weather configuration"""
        # Check environment variables if not set
        if not self.api_key:
            self.api_key = os.getenv("OPEN_WEATHER_APIKEY", "")

        if not self.city_id or self.city_id == "643492":
            env_city = os.getenv("OPEN_WEATHER_CITY_ID", "")
            if env_city:
                self.city_id = env_city

        if not self.api_key:
            colored_warning(
                "Weather API key not set in config.json or OPEN_WEATHER_APIKEY. "
                "Weather widgets will not work."
            )

        # Verify icon directory exists
        icon_path = Path(self.icon_base_path)
        if not icon_path.exists():
            colored_warning(
                f"Weather icon directory not found: {self.icon_base_path}. "
                "Weather icons may not display correctly."
            )

    @classmethod
    def from_dict(cls, data: Dict) -> "WeatherConfig":
        """Create WeatherConfig from dictionary"""
        return cls(
            api_key=data.get("api_key", ""),
            city_id=data.get("city_id", "643492"),
            cache_ttl=data.get("cache_ttl", 600),
            use_12h_format=data.get("use_12h_format", False),
        )


@dataclass
class UIConfig:
    """UI and appearance settings"""

    # Monitor assignments
    primary_monitor: int = 0
    bar_monitor: int = 0
    osd_monitor: int = 0
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

    # Bar settings
    bar_remember_state: bool = True

    def __post_init__(self):
        """Validate monitor configuration"""
        from ignis import utils

        try:
            monitors = utils.get_monitors()
            monitor_count = len(monitors)

            monitor_settings = [
                ("primary_monitor", self.primary_monitor),
                ("bar_monitor", self.bar_monitor),
                ("osd_monitor", self.osd_monitor),
                ("notifications_monitor", self.notifications_monitor),
                ("recording_overlay_monitor", self.recording_overlay_monitor),
                ("window_switcher_monitor", self.window_switcher_monitor),
                ("weather_monitor", self.weather_monitor),
                ("power_overlay_monitor", self.power_overlay_monitor),
                ("system_menu_monitor", self.system_menu_monitor),
                ("integrated_center_monitor", self.integrated_center_monitor),
            ]

            for setting_name, monitor_id in monitor_settings:
                if monitor_id >= monitor_count or monitor_id < 0:
                    colored_warning(
                        f"{setting_name} is set to {monitor_id}, "
                        f"but only {monitor_count} monitor(s) detected. "
                        f"Falling back to monitor 0."
                    )
                    setattr(self, setting_name, 0)

        except Exception as e:
            colored_warning(
                f"Could not validate monitor configuration: {e}. "
                "All windows will default to primary monitor."
            )

    @classmethod
    def from_dict(cls, data: Dict) -> "UIConfig":
        """Create UIConfig from dictionary"""
        monitors = data.get("monitors", {})
        timeouts = data.get("timeouts", {})
        bar_settings = data.get("bar", {})

        return cls(
            primary_monitor=monitors.get("primary", 0),
            bar_monitor=monitors.get("bar", 0),
            osd_monitor=monitors.get("osd", 0),
            notifications_monitor=monitors.get("notifications", 0),
            recording_overlay_monitor=monitors.get("recording_overlay", 0),
            window_switcher_monitor=monitors.get("window_switcher", 0),
            weather_monitor=monitors.get("weather", 0),
            power_overlay_monitor=monitors.get("power_overlay", 0),
            system_menu_monitor=monitors.get("system_menu", 0),
            integrated_center_monitor=monitors.get("integrated_center", 0),
            osd_timeout=timeouts.get("osd", 2000),
            volume_osd_timeout=timeouts.get("volume_osd", 2000),
            media_osd_timeout=timeouts.get("media_osd", 5000),
            time_osd_timeout=timeouts.get("time_osd", 8000),
            workspace_osd_timeout=timeouts.get("workspace_osd", 1500),
            bar_remember_state=bar_settings.get("remember_state", True),
        )


@dataclass
class RecorderConfig:
    """Recording settings"""

    audio_device: str = "default_output"
    video_format: str = "mp4"

    @classmethod
    def from_dict(cls, data: Dict) -> "RecorderConfig":
        """Create RecorderConfig from dictionary"""
        return cls(
            audio_device=data.get("audio_device", "default_output"),
            video_format=data.get("video_format", "mp4"),
        )


@dataclass
class BatteryConfig:
    """Battery widget thresholds"""

    critical_threshold: int = 15
    warning_threshold: int = 30

    def __post_init__(self):
        """Validate battery thresholds"""
        if not 0 <= self.critical_threshold <= 100:
            colored_warning(
                f"critical_threshold ({self.critical_threshold}) "
                f"must be between 0-100. Using default 15."
            )
            self.critical_threshold = 15

        if not 0 <= self.warning_threshold <= 100:
            colored_warning(
                f"warning_threshold ({self.warning_threshold}) "
                f"must be between 0-100. Using default 30."
            )
            self.warning_threshold = 30

        if self.critical_threshold >= self.warning_threshold:
            colored_warning(
                f"critical_threshold ({self.critical_threshold}) "
                f"should be less than warning_threshold ({self.warning_threshold}). "
                f"Adjusting to defaults."
            )
            self.critical_threshold = 15
            self.warning_threshold = 30

    @classmethod
    def from_dict(cls, data: Dict) -> "BatteryConfig":
        """Create BatteryConfig from dictionary"""
        return cls(
            critical_threshold=data.get("critical_threshold", 15),
            warning_threshold=data.get("warning_threshold", 30),
        )


@dataclass
class AnimationConfig:
    """Animation settings"""

    revealer_duration: int = 180  # milliseconds
    revealer_type: str = (
        "slide_down"  # slide_down, slide_up, slide_left, slide_right, crossfade
    )

    def __post_init__(self):
        """Validate animation settings"""
        valid_types = [
            "slide_down",
            "slide_up",
            "slide_left",
            "slide_right",
            "crossfade",
            "none",
        ]

        if self.revealer_type not in valid_types:
            colored_warning(
                f"revealer_type '{self.revealer_type}' is invalid. "
                f"Must be one of: {', '.join(valid_types)}. Using 'slide_down'."
            )
            self.revealer_type = "slide_down"

        if self.revealer_duration < 0:
            colored_warning(
                f"revealer_duration ({self.revealer_duration}) must be >= 0. "
                f"Using default 180ms."
            )
            self.revealer_duration = 180

        if self.revealer_duration > 2000:
            colored_warning(
                f"revealer_duration ({self.revealer_duration}) is very high. "
                f"Recommended range: 100-500ms."
            )

    @classmethod
    def from_dict(cls, data: Dict) -> "AnimationConfig":
        """Create AnimationConfig from dictionary"""
        return cls(
            revealer_duration=data.get("revealer_duration", 180),
            revealer_type=data.get("revealer_type", "slide_down"),
        )
