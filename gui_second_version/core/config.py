"""Configuration management system for FLASH-TV GUI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Dict

from .exceptions import ConfigurationError


class Environment(StrEnum):
    """Application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass
class AppConfig:
    """Main application configuration."""

    # Environment settings
    environment: Environment = Environment.PRODUCTION
    debug: bool = False

    # Paths
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    state_file: Path = field(default_factory=lambda: Path("flash_setup_state.json"))
    backup_dir: Path = field(default_factory=lambda: Path("backups"))

    # Timeouts and intervals
    sudo_timeout_seconds: int = 300
    auto_save_interval_ms: int = 30000
    process_monitor_interval_ms: int = 1000
    status_update_interval_ms: int = 5000
    network_timeout_seconds: int = 10
    wifi_scan_timeout_seconds: int = 10
    wifi_connect_timeout_seconds: int = 30

    # UI settings
    min_window_width: int = 1200
    min_window_height: int = 700
    default_margin: int = 8
    default_padding: int = 6
    section_spacing: int = 4
    content_spacing: int = 3
    border_radius: int = 3

    # Button heights
    action_button_height: int = 40
    standard_button_height: int = 30

    # UI Colors
    success_color: str = "#4CAF50"  # Green
    error_color: str = "#F44336"  # Red
    warning_color: str = "#FF9800"  # Orange
    info_color: str = "#2196F3"  # Blue
    pending_color: str = "#9E9E9E"  # Grey
    primary_color: str = "#1976D2"  # Dark Blue
    secondary_color: str = "#757575"  # Grey

    # Background colors
    error_bg: str = "#FFEBEE"  # Light Red
    success_bg: str = "#E8F5E8"  # Light Green
    warning_bg: str = "#FFF3E0"  # Light Orange
    info_bg: str = "#E3F2FD"  # Light Blue

    # Process settings
    max_output_lines: int = 1000
    process_cleanup_interval_seconds: int = 60

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S"
    max_log_size_mb: int = 10
    log_backup_count: int = 5

    @classmethod
    def from_file(cls, config_path: Path) -> AppConfig:
        """Load configuration from JSON file."""
        try:
            with open(config_path, "r") as f:
                data = json.load(f)

            for key, value in data.items():
                if key.endswith("_dir") or key.endswith("_file"):
                    data[key] = Path(value)

            if "environment" in data:
                data["environment"] = Environment(data["environment"])

            return cls(**data)

        except FileNotFoundError:
            raise ConfigurationError(
                f"Configuration file not found: {config_path}",
                recovery_action="Create a configuration file or use default settings",
            )
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in configuration file: {e}",
                recovery_action="Fix the JSON syntax in the configuration file",
            )
        except (TypeError, ValueError) as e:
            raise ConfigurationError(
                f"Invalid configuration values: {e}",
                recovery_action="Check configuration file for correct data types",
            )

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load configuration from environment variables."""
        config_data = {}

        env_mappings = {
            "FLASH_ENV": ("environment", lambda x: Environment(x)),
            "FLASH_DEBUG": ("debug", lambda x: x.lower() == "true"),
            "FLASH_LOG_DIR": ("log_dir", Path),
            "FLASH_STATE_FILE": ("state_file", Path),
            "FLASH_SUDO_TIMEOUT": ("sudo_timeout_seconds", int),
            "FLASH_AUTO_SAVE_INTERVAL": ("auto_save_interval_ms", int),
            "FLASH_LOG_LEVEL": ("log_level", str),
            "FLASH_MIN_WIDTH": ("min_window_width", int),
            "FLASH_MIN_HEIGHT": ("min_window_height", int),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    config_data[config_key] = converter(value)
                except (ValueError, TypeError) as e:
                    raise ConfigurationError(
                        f"Invalid value for {env_var}: {value} ({e})",
                        config_key=config_key,
                    )

        return cls(**config_data)

    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to JSON file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                data[key] = str(value)
            elif isinstance(value, Environment):
                data[key] = value.value
            else:
                data[key] = value

        try:
            with open(config_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise ConfigurationError(
                f"Failed to save configuration file: {e}",
                recovery_action="Check file permissions and disk space",
            )

    def get_user_data_path(self, username: str) -> Path:
        """Get user-specific data path."""
        return Path(f"/home/{username}/data")

    def get_python_env_path(self, username: str) -> Path:
        """Get Python virtual environment path."""
        return Path(f"/home/{username}/py38/bin/python")

    def get_model_paths(self, username: str) -> Dict[str, Path]:
        """Get model file paths for a user."""
        return {
            "insightface": Path(
                f"/home/{username}/insightface/models/buffalo_l/det_10g.onnx"
            ),
            "adaface": Path(
                f"/home/{username}/Desktop/FLASH_TV_v3/AdaFace/pretrained/adaface_ir101_webface12m.ckpt"
            ),
            "gaze_model1": Path(f"/home/{username}/gaze_models/model1.pth"),
            "gaze_model2": Path(f"/home/{username}/gaze_models/model2.pth"),
        }


class ConfigManager:
    """Singleton configuration manager."""

    _instance: ConfigManager | None = None
    _config: AppConfig | None = None

    def __new__(cls) -> ConfigManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> AppConfig:
        """Load configuration from various sources with fallback chain: file -> env -> defaults."""
        config_file = Path("config.json")
        if config_file.exists():
            try:
                return AppConfig.from_file(config_file)
            except ConfigurationError:
                pass

        try:
            return AppConfig.from_env()
        except ConfigurationError:
            pass

        return AppConfig()

    def reload_config(self) -> None:
        """Reload configuration from sources."""
        self._config = self._load_config()

    def save_config(self, config_path: Path | None = None) -> None:
        """Save current configuration to file."""
        if config_path is None:
            config_path = Path("config.json")

        if self._config:
            self._config.save_to_file(config_path)


# Global configuration instance
def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return ConfigManager().config
