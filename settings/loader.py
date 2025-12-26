"""
Configuration loader - reads from config.json and merges with defaults
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from rich.console import Console
from rich.theme import Theme

# Rich console for colored output
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


def colored_error(message: str) -> None:
    """Display a rich formatted error"""
    console.print(f"[error]✖ Error:[/error] {message}")


def colored_info(message: str) -> None:
    """Display a rich formatted info message"""
    console.print(f"[info]ℹ Info:[/info] {message}")


def colored_success(message: str) -> None:
    """Display a rich formatted success message"""
    console.print(f"[success]✓ Success:[/success] {message}")


def expand_path(path_str: str) -> Path:
    """Expand ~ and environment variables in path"""
    return Path(os.path.expanduser(os.path.expandvars(path_str)))


def load_user_config(config_file: Path = None) -> Dict[str, Any]:
    """
    Load user configuration from config.json

    Args:
        config_file: Path to config.json (defaults to ~/.config/ignis/config.json)

    Returns:
        Dictionary with user configuration
    """
    if config_file is None:
        config_file = Path.home() / ".config" / "ignis" / "config.json"

    # Create default config if it doesn't exist
    if not config_file.exists():
        colored_info(
            f"No config.json found. Creating default at [value]{config_file}[/value]"
        )
        config_file.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "weather": {
                "api_key": "",
                "city_id": "643492",
                "cache_ttl": 600,
                "use_12h_format": False,
            },
            "ui": {
                "monitors": {
                    "primary": 0,
                    "bar": 0,
                    "osd": 0,
                    "launcher": 0,
                    "notifications": 0,
                    "recording_overlay": 0,
                    "window_switcher": 0,
                    "weather": 0,
                    "power_overlay": 0,
                    "system_menu": 0,
                    "integrated_center": 0,
                },
                "timeouts": {
                    "osd": 2000,
                    "volume_osd": 2000,
                    "media_osd": 5000,
                    "time_osd": 8000,
                    "workspace_osd": 1500,
                },
            },
            "recorder": {
                "audio_device": "default_output",
                "video_format": "mp4",
            },
            "battery": {
                "critical_threshold": 15,
                "warning_threshold": 30,
            },
            "paths": {
                "recordings_dir": "~/Videos/Captures",
                "screenshots_dir": "~/Pictures/Screenshots",
            },
            "animations": {
                "revealer_duration": 180,
                "revealer_type": "slide_down",
            },
        }

        with open(config_file, "w") as f:
            json.dump(default_config, f, indent=2)

        colored_success(f"Created default config at [value]{config_file}[/value]")
        return default_config

    # Load existing config
    try:
        with open(config_file) as f:
            user_config = json.load(f)
        colored_success(f"Loaded config from [value]{config_file}[/value]")
        return user_config
    except json.JSONDecodeError as e:
        colored_error(f"Failed to parse config.json: {e}")
        colored_warning("Using default configuration")
        return {}
    except Exception as e:
        colored_error(f"Failed to load config.json: {e}")
        colored_warning("Using default configuration")
        return {}


def merge_dicts(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value

    return result
