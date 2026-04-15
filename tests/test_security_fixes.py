"""
Tests for security fixes S1–S3.
"""

import logging
import sys
from unittest.mock import patch

import pytest

from autodiary.core.client import VTUApiClient
from autodiary.core.config import ConfigManager
from autodiary.utils.crypto import CryptoManager

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


# ── S1: Encryption key file permission check ─────────────────────────────────


class TestS1KeyPermissions:
    def test_key_loads_successfully(self, tmp_path):
        """Key should load without error on any platform."""
        crypto = CryptoManager(tmp_path)
        # First call creates the key, second loads it
        key1 = crypto._get_or_create_key()
        crypto._key = None  # Reset to force reload
        key2 = crypto._get_or_create_key()
        assert key1 == key2

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions not enforced on Windows")
    def test_warns_on_insecure_permissions_unix(self, tmp_path, caplog):
        """On Unix, should log warning if key file is world-readable."""
        crypto = CryptoManager(tmp_path)
        crypto._get_or_create_key()

        # Make key file world-readable
        crypto.key_file.chmod(0o644)

        # Reset and reload
        crypto._key = None
        with caplog.at_level(logging.WARNING, logger="autodiary"):
            crypto._get_or_create_key()

        assert any("insecure permissions" in msg for msg in caplog.messages)

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions not enforced on Windows")
    def test_no_warning_on_secure_permissions_unix(self, tmp_path, caplog):
        """On Unix, should not warn if key file has 600 permissions."""
        crypto = CryptoManager(tmp_path)
        crypto._get_or_create_key()

        # Ensure key file has correct permissions
        crypto.key_file.chmod(0o600)

        crypto._key = None
        with caplog.at_level(logging.WARNING, logger="autodiary"):
            crypto._get_or_create_key()

        assert not any("insecure permissions" in msg for msg in caplog.messages)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_debug_log_on_windows(self, tmp_path, caplog):
        """On Windows, should log debug message about skipping POSIX check."""
        crypto = CryptoManager(tmp_path)
        crypto._get_or_create_key()

        crypto._key = None
        with caplog.at_level(logging.DEBUG, logger="autodiary"):
            crypto._get_or_create_key()

        assert any("Skipping POSIX permission check" in msg for msg in caplog.messages)


# ── S2: Honest User-Agent headers ────────────────────────────────────────────


class TestS2HonestHeaders:
    def test_user_agent_starts_with_autodiary(self, client):
        """User-Agent header should identify as AutoDiary, not a browser."""
        assert client.headers["User-Agent"].startswith("AutoDiary/")

    def test_no_browser_spoofing_headers(self, client):
        """Headers should not contain sec-ch-ua browser fingerprint headers."""
        assert "sec-ch-ua" not in client.headers
        assert "sec-ch-ua-mobile" not in client.headers
        assert "sec-ch-ua-platform" not in client.headers

    def test_user_agent_contains_version(self, client):
        """User-Agent should contain the package version."""
        from autodiary import __version__

        assert client.headers["User-Agent"] == f"AutoDiary/{__version__}"

    def test_required_api_headers_preserved(self, client):
        """Essential API headers (Accept, Content-Type, Origin, Referer) should remain."""
        assert "Accept" in client.headers
        assert "Content-Type" in client.headers
        assert "Origin" in client.headers
        assert "Referer" in client.headers


# ── S3: Input trimming on credentials ────────────────────────────────────────


class TestS3InputTrimming:
    def test_email_validator_rejects_whitespace_only(self):
        """validate_email should reject whitespace-only input."""
        from autodiary.utils.validators import validate_email

        assert validate_email("  ") is False
        # Validator doesn't strip — the config_menu strips before passing to validator
        assert validate_email(" test@example.com ") is False
        assert validate_email("test@example.com") is True

    def test_strip_applied_in_edit_credentials(self, mock_config_manager):
        """edit_credentials should strip whitespace from email before saving."""
        from autodiary.cli.config_menu import ConfigMenu

        menu = ConfigMenu(mock_config_manager)

        with (
            patch("autodiary.cli.config_menu.questionary") as mock_q,
            patch("autodiary.cli.config_menu.print_success"),
        ):
            # Simulate email with leading/trailing whitespace
            mock_q.text.return_value.ask.return_value = "  new@example.com  "
            mock_q.password.return_value.ask.return_value = ""
            mock_q.confirm.return_value.ask.return_value = False

            menu.edit_credentials()

            config = mock_config_manager.config
            assert config.email == "new@example.com"

    def test_strip_applied_in_edit_internship(self, mock_config_manager):
        """edit_internship_settings should strip whitespace from title and company."""
        from autodiary.cli.config_menu import ConfigMenu

        menu = ConfigMenu(mock_config_manager)

        with (
            patch("autodiary.cli.config_menu.questionary") as mock_q,
            patch("autodiary.cli.config_menu.print_header"),
            patch("autodiary.cli.config_menu.print_success"),
        ):
            # Return values for sequential .text() calls:
            # internship_id, start_date, end_date, title, company
            text_returns = ["", "", "", "  My Title  ", "  My Company  "]
            mock_q.text.return_value.ask.side_effect = text_returns

            menu.edit_internship_settings()

            config = mock_config_manager.config
            assert config.internship_title == "My Title"
            assert config.company_name == "My Company"
