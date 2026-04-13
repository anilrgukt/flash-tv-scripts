"""
FLASH-TV Configuration Loader

Loads configuration from YAML file with environment variable substitution.
Provides a singleton config object for use throughout the application.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import re
from typing import Any


from config.install_defaults_loader import load_install_defaults_module


yaml = importlib.import_module("yaml")


install_defaults_module = load_install_defaults_module()
DEFAULT_HOME_ASSISTANT_IMAGE = str(
    getattr(install_defaults_module, "HOME_ASSISTANT_IMAGE")
)
DEFAULT_CONFIG_ENV_FALLBACKS = {
    "HOME_ASSISTANT_IMAGE": DEFAULT_HOME_ASSISTANT_IMAGE,
    "DEFAULT_SMART_PLUG_SWITCH_ENTITY_ID": str(
        getattr(install_defaults_module, "DEFAULT_SMART_PLUG_SWITCH_ENTITY_ID")
    ),
    "DEFAULT_SMART_PLUG_POWER_SENSOR_ENTITY_ID": str(
        getattr(install_defaults_module, "DEFAULT_SMART_PLUG_POWER_SENSOR_ENTITY_ID")
    ),
    "BACKUP_USB_VENDOR": str(getattr(install_defaults_module, "BACKUP_USB_VENDOR")),
}


class ConfigurationError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""

    pass


class FlashConfig:
    """
    FLASH-TV configuration container.

    Loads configuration from YAML file and substitutes environment variables.
    Provides attribute-style access to configuration values.
    """

    _instance: FlashConfig | None = None
    _config: dict[str, Any] = {}
    _loaded: bool = False

    def __new__(cls) -> FlashConfig:
        """Singleton pattern - only one config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: str | Path | None = None) -> None:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file. If None, searches default locations.

        Raises:
            ConfigurationError: If config file not found or invalid.
        """
        if config_path is None:
            config_path = self._find_config_file()

        config_path = Path(config_path)

        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        if config_path.is_dir():
            raise ConfigurationError(
                f"Configuration path is a directory, not a file: {config_path}"
            )

        try:
            with open(config_path, "r") as f:
                raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file: {e}")

        # Substitute environment variables
        self._config = self._substitute_env_vars(raw_config)
        self._loaded = True

    def _find_config_file(self) -> Path:
        """Find configuration file in default locations."""
        search_paths = []
        env_config_path = os.environ.get("FLASH_CONFIG_PATH")
        if env_config_path:
            search_paths.append(Path(env_config_path))

        search_paths.extend([
            # Docker volume mount location
            Path("/config/flash_config.yaml"),
            # Relative to script
            Path(__file__).parent / "flash_config.yaml",
            # Home directory
            Path.home() / "flash-tv-scripts" / "config" / "flash_config.yaml",
        ])

        for path in search_paths:
            if path.exists():
                return path

        raise ConfigurationError(
            f"Configuration file not found. Searched: {[str(p) for p in search_paths]}"
        )

    def _substitute_env_vars(self, obj: Any) -> Any:
        """
        Recursively substitute ${VAR} patterns with environment variables.

        Args:
            obj: Configuration object (dict, list, or scalar).

        Returns:
            Object with environment variables substituted.
        """
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_string(obj)
        else:
            return obj

    def _substitute_string(self, s: str) -> str:
        """
        Substitute ${VAR} patterns in a string.

        Args:
            s: String potentially containing ${VAR} patterns.

        Returns:
            String with environment variables substituted.
        """
        pattern = r"\$\{([^}]+)\}"

        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            value = os.environ.get(var_name, "")
            if not value:
                if var_name in DEFAULT_CONFIG_ENV_FALLBACKS:
                    value = DEFAULT_CONFIG_ENV_FALLBACKS[var_name]
                elif var_name == "FLASH_USERNAME":
                    value = os.environ.get("USER", os.environ.get("USERNAME", ""))
                elif var_name == "PARTICIPANT_ID":
                    value = os.environ.get("FAMILY_ID", "UNKNOWN")
                elif var_name == "DEVICE_ID":
                    # Try to extract from username
                    username = os.environ.get(
                        "FLASH_USERNAME", os.environ.get("USER", "")
                    )
                    if username and len(username) >= 3:
                        value = username[-3:]
            return value

        return re.sub(pattern, replace, s)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path like "pipeline.standby_timeout_seconds"
            default: Default value if key not found.

        Returns:
            Configuration value or default.

        Example:
            config.get("camera.resolution.width")  # Returns 1920
            config.get("pipeline.num_identities")  # Returns 4
        """
        if not self._loaded:
            self.load()

        keys = key_path.split(".")
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to top-level config sections."""
        if name.startswith("_"):
            raise AttributeError(name)

        if not self._loaded:
            self.load()

        if name in self._config:
            return self._config[name]

        raise AttributeError(f"Configuration has no section '{name}'")

    @property
    def participant_id(self) -> str:
        """Get full participant ID (participant_id + device_id)."""
        return self.get("identity.full_id", "UNKNOWN")

    @property
    def data_dir(self) -> Path:
        """Get participant data directory path."""
        return Path(self.get("paths.data_dir", "/tmp/flash_data"))

    @property
    def faces_dir(self) -> Path:
        """Get faces gallery directory path."""
        return Path(self.get("paths.faces_dir", "/tmp/flash_faces"))

    @property
    def username(self) -> str:
        """Get system username."""
        return self.get("identity.username", "flashsys")

    def validate(self) -> list[str]:
        """
        Validate configuration for required values and paths.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors = []

        # Check required identity fields (including fallback/placeholder values)
        _pid = self.get("identity.participant_id")
        if _pid in ("", "UNKNOWN", None) or "${" in str(_pid):
            errors.append("identity.participant_id is not set")

        _did = self.get("identity.device_id")
        if _did in ("", "000", None) or "${" in str(_did):
            errors.append("identity.device_id is not set")

        _user = self.get("identity.username")
        if _user in ("", "flashsys", None) or "${" in str(_user):
            errors.append("identity.username is not set")

        # Check paths contain no unresolved variables
        paths_section = self.get("paths", {})
        for key, value in self._flatten_dict(paths_section).items():
            if isinstance(value, str) and "${" in value:
                errors.append(f"paths.{key} contains unresolved variable: {value}")

        return errors

    def _flatten_dict(
        self, d: dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> dict[str, Any]:
        """Flatten nested dictionary for validation."""
        items: list[tuple[str, Any]] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def to_dict(self) -> dict[str, Any]:
        """Return full configuration as dictionary."""
        if not self._loaded:
            self.load()
        return self._config.copy()

    def reload(self, config_path: str | Path | None = None) -> None:
        """Force reload configuration from file."""
        self._loaded = False
        self._config = {}
        self.load(config_path)


# Global singleton instance
_config: FlashConfig | None = None


def get_config() -> FlashConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = FlashConfig()
    return _config


def load_config(config_path: str | Path | None = None) -> FlashConfig:
    """Load configuration and return the global instance."""
    config = get_config()
    config.load(config_path)
    return config
