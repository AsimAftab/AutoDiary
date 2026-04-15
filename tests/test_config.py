import pytest

from autodiary.core.config import ConfigManager
from autodiary.models.config import AppConfig


def test_app_config_validation():
    # Valid config
    valid_data = {
        "email": "user@example.com",
        "password_encrypted": "encrypted",
        "internship_id": 123,
        "internship_start_date": "2026-01-01",
    }
    config = AppConfig(**valid_data)
    assert config.email == "user@example.com"

    # Invalid email
    with pytest.raises(ValueError, match="Invalid email format"):
        AppConfig(**{**valid_data, "email": "invalid"})

    # Invalid internship_id
    with pytest.raises(ValueError):
        AppConfig(**{**valid_data, "internship_id": 0})

    # Invalid weekday
    with pytest.raises(ValueError, match="Invalid weekday"):
        AppConfig(**{**valid_data, "holiday_weekdays": ["Funday"]})


def test_config_manager_lifecycle(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path)

    # Load non-existent
    with pytest.raises(FileNotFoundError):
        manager.load()

    # Create default
    config = manager.load_or_create_default()
    assert config.email == ""
    assert config.internship_id == -1

    # Save and reload
    config.email = "test@example.com"
    config.password_encrypted = "secret"
    manager.save(config)

    new_manager = ConfigManager(config_path)
    loaded_config = new_manager.load()
    assert loaded_config.email == "test@example.com"


def test_config_manager_password(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path)
    config = manager.load_or_create_default()
    manager.save(config)

    manager.set_password("my-password")
    assert config.password_encrypted != "my-password"

    decrypted = manager.get_password()
    assert decrypted == "my-password"


def test_config_manager_clear_credentials(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path)
    config = manager.load_or_create_default()
    config.email = "test@example.com"
    config.internship_id = 123
    config.internship_title = "Data Analyst Internship"
    manager.save(config)
    manager.set_password("my-password")
    manager.save(manager.config)

    updated = manager.clear_credentials()

    assert updated.email == ""
    assert updated.password_encrypted == ""
    assert updated.internship_id == 123
    assert updated.internship_title == "Data Analyst Internship"

    reloaded = ConfigManager(config_path).load()
    assert reloaded.email == ""
    assert reloaded.password_encrypted == ""
    assert reloaded.internship_id == 123


def test_config_manager_is_configured(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path)
    config = manager.load_or_create_default()

    assert manager.is_configured is False

    config.email = "test@example.com"
    config.password_encrypted = "something"
    config.internship_id = 123
    config.internship_start_date = "2026-01-01"
    manager.save(config)

    assert manager.is_configured is True
