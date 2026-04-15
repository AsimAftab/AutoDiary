"""
Tests for code quality fixes CQ1–CQ4.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from autodiary.core.client import (
    BACKOFF_JITTER_RANGE,
    DEFAULT_MAX_LOGIN_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    INTERNSHIP_STATUS_ONGOING,
    MAX_PAGINATION_PAGES,
    RETRYABLE_STATUS_CODES,
    UPLOAD_JITTER_RANGE,
    VTUApiClient,
)
from autodiary.core.config import ConfigManager

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_config_manager(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path)
    config = manager.load_or_create_default()
    config.email = "test@example.com"
    config.internship_id = 123
    manager.save(config)
    manager.set_password("password")
    return manager


@pytest.fixture
def client(mock_config_manager):
    with patch("time.sleep", return_value=None):
        yield VTUApiClient(mock_config_manager)


# ── CQ1: Narrowed exception handlers ────────────────────────────────────────


class TestCQ1NarrowExceptions:
    def test_login_catches_request_exception_and_retries(self, client):
        """RequestException should be retried, not crash."""
        with patch.object(client.session, "post", side_effect=requests.ConnectionError("refused")):
            result = client.login("user", "pass")
            assert result is False

    def test_login_value_error_stops_immediately(self, client):
        """ValueError (e.g. bad JSON parse) should not retry."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b"not json"
        mock_response.json.side_effect = ValueError("bad json")

        with patch.object(client.session, "post", return_value=mock_response) as mock_post:
            result = client.login("user", "pass")
            assert result is False
            # Should stop after first attempt, not retry
            assert mock_post.call_count == 1

    def test_fetch_existing_dates_catches_request_exception(self, client):
        """Network errors in fetch_existing_dates should return empty set."""
        client._authenticated = True
        with patch.object(client.session, "get", side_effect=requests.Timeout("timeout")):
            result = client.fetch_existing_dates()
            assert result == set()

    def test_fetch_all_entries_catches_value_error(self, client):
        """ValueError from pagination should return empty list."""
        client._authenticated = True
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b'{"success": false}'
        mock_response.json.return_value = {"success": False}

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.fetch_all_entries()
            assert result == []


# ── CQ2: Named constants ────────────────────────────────────────────────────


class TestCQ2NamedConstants:
    def test_constants_have_expected_values(self):
        """Module-level constants should have sensible defaults."""
        assert DEFAULT_MAX_LOGIN_ATTEMPTS == 3
        assert DEFAULT_RETRY_DELAY == 2.0
        assert MAX_PAGINATION_PAGES == 500
        assert INTERNSHIP_STATUS_ONGOING == 6
        assert 401 in RETRYABLE_STATUS_CODES
        assert 429 in RETRYABLE_STATUS_CODES

    def test_jitter_ranges_are_valid(self):
        """Jitter range tuples should have min < max."""
        for name, r in [
            ("UPLOAD_JITTER_RANGE", UPLOAD_JITTER_RANGE),
            ("BACKOFF_JITTER_RANGE", BACKOFF_JITTER_RANGE),
        ]:
            assert r[0] < r[1], f"{name} min >= max"

    def test_internship_url_uses_constant(self, client):
        """Internship list URL should use INTERNSHIP_STATUS_ONGOING constant."""
        assert f"status={INTERNSHIP_STATUS_ONGOING}" in client.internship_list_url


# ── CQ3: Consolidated date validation ───────────────────────────────────────


class TestCQ3DateValidation:
    def test_upload_menu_uses_shared_validator(self):
        """upload_menu should import validate_date_format from validators."""
        from autodiary.cli import upload_menu

        assert hasattr(upload_menu, "validate_date_format")

    def test_view_menu_uses_shared_validator(self):
        """view_menu should import validate_date_format from validators."""
        from autodiary.cli import view_menu

        assert hasattr(view_menu, "validate_date_format")

    def test_upload_menu_has_no_private_validate_date(self):
        """upload_menu should not have its own _validate_date method."""
        from autodiary.cli.upload_menu import UploadMenu

        assert not hasattr(UploadMenu, "_validate_date")

    def test_view_menu_has_no_private_validate_date(self):
        """view_menu should not have its own _validate_date method."""
        from autodiary.cli.view_menu import ViewMenu

        assert not hasattr(ViewMenu, "_validate_date")


# ── CQ4: Config property-based access ───────────────────────────────────────


class TestCQ4ConfigProperty:
    def test_getters_use_config_property(self, mock_config_manager):
        """Getter methods should work without explicit load() call."""
        # Don't call load() — getters should use self.config property
        api = mock_config_manager.get_api_config()
        assert "base_url" in api
        assert "timeout" in api

    def test_get_credentials_uses_config_property(self, mock_config_manager):
        """get_credentials should work via config property."""
        creds = mock_config_manager.get_credentials()
        assert "email" in creds
        assert "password" in creds

    def test_get_holiday_config_uses_config_property(self, mock_config_manager):
        """get_holiday_config should work via config property."""
        holidays = mock_config_manager.get_holiday_config()
        assert "weekdays" in holidays
        assert "dates" in holidays

    def test_get_internship_config_uses_config_property(self, mock_config_manager):
        """get_internship_config should work via config property."""
        internship = mock_config_manager.get_internship_config()
        assert "id" in internship
        assert "start_date" in internship

    def test_set_password_uses_config_property(self, mock_config_manager):
        """set_password should work via config property without explicit load."""
        # Create fresh manager pointing to same file
        fresh_manager = ConfigManager(mock_config_manager.config_path)
        # This should not raise — config property handles loading
        fresh_manager.set_password("newpass")
        assert fresh_manager.config.password_encrypted != ""
