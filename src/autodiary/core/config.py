"""
Configuration management for VTU Auto Diary Filler.
Handles loading, saving, and validating application configuration.
"""

import json
import logging
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from autodiary.models.config import AppConfig
from autodiary.utils.crypto import CryptoManager

LOGGER = logging.getLogger("autodiary")


class ConfigManager:
    """Manager for application configuration."""

    def __init__(self, config_path: Path):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config_dir = config_path.parent
        self.crypto = CryptoManager(self.config_dir)
        self._config: AppConfig | None = None

    def load(self) -> AppConfig:
        """
        Load configuration from file.

        Returns:
            Loaded configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle legacy config format (from old settings.json + .env)
        if "credentials" not in data and "email" not in data:
            # Try to migrate from old format
            data = self._migrate_old_config(data)

        try:
            self._config = AppConfig(**data)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}") from e

        return self._config

    def save(self, config: AppConfig) -> None:
        """
        Save configuration to file atomically.

        Args:
            config: Configuration to save
        """
        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        config_dict = config.model_dump()

        # Atomic write: temp file → flush → fsync → replace
        fd, tmp_path = tempfile.mkstemp(dir=self.config_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            Path(tmp_path).replace(self.config_path)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise

        self._config = config

    def load_or_create_default(self) -> AppConfig:
        """
        Load existing config or create default.

        Returns:
            Configuration (existing or default)
        """
        if self.config_path.exists():
            return self.load()

        # Return default config (will need setup)
        return self._get_default_config()

    def _get_default_config(self) -> AppConfig:
        """Get default configuration."""
        return AppConfig(
            email="",
            password_encrypted="",
            internship_id=-1,  # Default placeholder ID, will be set during setup
            internship_start_date=str(date.today()),
            internship_end_date="today",
            internship_title="",
            company_name="",
        )

    def _migrate_old_config(self, old_data: dict[str, Any]) -> dict[str, Any]:
        """
        Migrate from old configuration format.

        Args:
            old_data: Old configuration data

        Returns:
            New configuration format
        """
        # This would handle migration from settings.json + .env format
        # For now, return minimal config
        return {
            "email": "",
            "password_encrypted": "",
            "api_base_url": "https://vtuapi.internyet.in",
            "internship_id": -1,
            "internship_start_date": str(date.today()),
            "internship_end_date": "today",
            "internship_title": "",
            "company_name": "",
            "holiday_weekdays": [],
            "holiday_dates": [],
            "timeout_seconds": 30,
            "request_delay_min": 0.8,
            "request_delay_max": 1.5,
            "max_retries": 3,
            "auto_skip_existing": True,
        }

    def get_password(self) -> str:
        """
        Get decrypted password.

        Returns:
            Decrypted password

        Raises:
            ValueError: If password decryption fails or config not loaded
        """
        if not self.config.password_encrypted:
            return ""

        try:
            return self.crypto.decrypt(self.config.password_encrypted)
        except Exception as e:
            raise ValueError(f"Failed to decrypt password: {e}") from e

    def set_password(self, password: str) -> None:
        """
        Encrypt and set password.

        Args:
            password: Plain text password
        """
        self.config.password_encrypted = self.crypto.encrypt(password)

    def clear_credentials(self) -> AppConfig:
        """
        Clear saved login credentials while preserving other configuration.

        Returns:
            Updated configuration
        """
        config = self.config
        config.email = ""
        config.password_encrypted = ""
        self.save(config)
        return config

    def get_api_config(self) -> dict[str, Any]:
        """
        Get API configuration for client.

        Returns:
            API configuration dictionary
        """
        return {
            "base_url": self.config.api_base_url,
            "timeout": self.config.timeout_seconds,
            "request_delay_min": self.config.request_delay_min,
            "request_delay_max": self.config.request_delay_max,
            "max_retries": self.config.max_retries,
        }

    def get_internship_config(self) -> dict[str, Any]:
        """
        Get internship configuration.

        Returns:
            Internship configuration dictionary
        """
        return {
            "id": self.config.internship_id,
            "start_date": self.config.internship_start_date,
            "end_date": self.config.internship_end_date,
            "title": self.config.internship_title,
            "company": self.config.company_name,
        }

    def get_holiday_config(self) -> dict[str, Any]:
        """
        Get holiday configuration.

        Returns:
            Holiday configuration dictionary
        """
        return {
            "weekdays": self.config.holiday_weekdays,
            "dates": self.config.holiday_dates,
        }

    def get_credentials(self) -> dict[str, str]:
        """
        Get user credentials.

        Returns:
            Credentials dictionary with email and decrypted password
        """
        return {
            "email": self.config.email,
            "password": self.get_password(),
        }

    def update_field(self, field: str, value: Any) -> None:
        """
        Update a single configuration field.

        Args:
            field: Field name to update
            value: New value

        Raises:
            ValueError: If config not loaded or field doesn't exist
        """
        # Special handling for password (maps to password_encrypted)
        if field == "password":
            self.set_password(value)
            return

        if not hasattr(self.config, field):
            raise ValueError(f"Unknown configuration field: {field}")

        setattr(self.config, field, value)

    def backup(self) -> Path:
        """
        Create backup of current configuration.

        Returns:
            Path to backup file
        """
        if not self.config_path.exists():
            raise FileNotFoundError("No configuration to backup")

        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        backup_path = self.config_path.with_suffix(f".backup.{timestamp}.json")
        backup_path.write_text(self.config_path.read_text(encoding="utf-8"), encoding="utf-8")
        return backup_path

    def list_backups(self) -> list[Path]:
        """List available backup files, newest first."""
        pattern = self.config_path.stem + ".backup.*.json"
        backups = sorted(self.config_dir.glob(pattern), reverse=True)
        return backups

    def restore(self, backup_path: Path) -> AppConfig:
        """
        Restore configuration from a backup file.

        Args:
            backup_path: Path to backup file

        Returns:
            Restored configuration
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        backup_path.replace(self.config_path)
        self._config = None  # Force reload
        return self.load()

    def reset_to_default(self) -> AppConfig:
        """
        Reset configuration to defaults.

        Returns:
            New default configuration
        """
        self._config = self._get_default_config()
        self.save(self._config)
        return self._config

    @property
    def is_configured(self) -> bool:
        """Check if configuration is complete."""
        try:
            if self._config is None:
                self.load()
            return bool(
                self._config.email
                and self._config.password_encrypted
                and self._config.internship_id > 0
                and self._config.internship_start_date
            )
        except (FileNotFoundError, ValueError) as e:
            LOGGER.warning("Configuration is missing or invalid: %s", e)
            return False

    @property
    def config(self) -> AppConfig:
        """Get current configuration (loads if necessary)."""
        if self._config is None:
            self.load()
        return self._config
