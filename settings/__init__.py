"""
Settings module - Loads configuration from config.json
"""

from dataclasses import dataclass, field
from pathlib import Path

from .base import (
    AnimationConfig,
    BatteryConfig,
    PathConfig,
    RecorderConfig,
    UIConfig,
    WeatherConfig,
)
from .loader import colored_info, load_user_config


@dataclass
class AppConfig:
    paths: PathConfig = field(default_factory=PathConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    recorder: RecorderConfig = field(default_factory=RecorderConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)
    animations: AnimationConfig = field(default_factory=AnimationConfig)

    @classmethod
    def from_user_config(cls, config_file: Path = None) -> "AppConfig":
        """Create AppConfig from user's config.json"""
        user_config = load_user_config(config_file)

        return cls(
            paths=PathConfig.from_dict(user_config.get("paths", {})),
            weather=WeatherConfig.from_dict(user_config.get("weather", {})),
            ui=UIConfig.from_dict(user_config.get("ui", {})),
            recorder=RecorderConfig.from_dict(user_config.get("recorder", {})),
            battery=BatteryConfig.from_dict(user_config.get("battery", {})),
            animations=AnimationConfig.from_dict(user_config.get("animations", {})),
        )


# Load global configuration
config = AppConfig.from_user_config()

colored_info("Configuration loaded successfully")


__all__ = [
    "config",
    "AppConfig",
    "PathConfig",
    "WeatherConfig",
    "UIConfig",
    "RecorderConfig",
    "BatteryConfig",
    "AnimationConfig",
]
