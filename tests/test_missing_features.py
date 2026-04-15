"""
Tests for missing features F1–F6.
"""

from unittest.mock import MagicMock, patch

import pytest

from autodiary.core.client import VTUApiClient
from autodiary.core.config import ConfigManager
from autodiary.models.api import ApiResponse, PaginatedData
from autodiary.models.config import AppConfig

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_config_manager(tmp_path):
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path)
    config = manager.load_or_create_default()
    config.email = "test@example.com"
    config.internship_id = 123
    config.internship_start_date = "2026-01-05"
    manager.save(config)
    manager.set_password("password")
    return manager


@pytest.fixture
def client(mock_config_manager):
    with patch("time.sleep", return_value=None):
        yield VTUApiClient(mock_config_manager)


# ── F1: Resume interrupted uploads ──────────────────────────────────────────


class TestF1ResumeUploads:
    def test_save_and_load_progress(self, tmp_path):
        """Should save and load upload progress."""
        from autodiary.cli.upload_menu import UploadMenu

        with patch("autodiary.cli.upload_menu.UPLOAD_PROGRESS_FILE", tmp_path / "progress.json"):
            UploadMenu._save_upload_progress({"2026-04-07", "2026-04-08"})
            result = UploadMenu._load_upload_progress()
            assert result == {"2026-04-07", "2026-04-08"}

    def test_load_progress_empty_when_no_file(self, tmp_path):
        """Should return empty set when no progress file exists."""
        from autodiary.cli.upload_menu import UploadMenu

        with patch("autodiary.cli.upload_menu.UPLOAD_PROGRESS_FILE", tmp_path / "nonexistent.json"):
            result = UploadMenu._load_upload_progress()
            assert result == set()

    def test_clear_progress(self, tmp_path):
        """Should remove progress file."""
        from autodiary.cli.upload_menu import UploadMenu

        progress_file = tmp_path / "progress.json"
        progress_file.write_text("{}")

        with patch("autodiary.cli.upload_menu.UPLOAD_PROGRESS_FILE", progress_file):
            UploadMenu._clear_upload_progress()
            assert not progress_file.exists()

    def test_load_progress_handles_corrupt_file(self, tmp_path):
        """Should return empty set for corrupt progress file."""
        from autodiary.cli.upload_menu import UploadMenu

        progress_file = tmp_path / "progress.json"
        progress_file.write_text("not valid json")

        with patch("autodiary.cli.upload_menu.UPLOAD_PROGRESS_FILE", progress_file):
            result = UploadMenu._load_upload_progress()
            assert result == set()


# ── F2: Entry de-duplication ────────────────────────────────────────────────


class TestF2Deduplication:
    def test_no_duplicates(self):
        """Should not warn when no duplicates exist."""
        from autodiary.cli.upload_menu import UploadMenu

        entries = [
            {"date": "2026-04-07", "description": "A"},
            {"date": "2026-04-08", "description": "B"},
        ]
        # Should not raise or print warning
        UploadMenu._warn_duplicates(entries)

    def test_detects_duplicates(self):
        """Should detect duplicate entries with same date+description."""
        from autodiary.cli.upload_menu import UploadMenu

        entries = [
            {"date": "2026-04-07", "description": "Same work"},
            {"date": "2026-04-07", "description": "Same work"},
            {"date": "2026-04-08", "description": "Different"},
        ]
        with patch("autodiary.cli.upload_menu.print_warning") as mock_warn:
            UploadMenu._warn_duplicates(entries)
            mock_warn.assert_called_once()
            assert "1 duplicate" in mock_warn.call_args[0][0]

    def test_no_false_positive_same_date_different_desc(self):
        """Same date but different description should not be flagged."""
        from autodiary.cli.upload_menu import UploadMenu

        entries = [
            {"date": "2026-04-07", "description": "Morning work"},
            {"date": "2026-04-07", "description": "Afternoon work"},
        ]
        with patch("autodiary.cli.upload_menu.print_warning") as mock_warn:
            UploadMenu._warn_duplicates(entries)
            mock_warn.assert_not_called()


# ── F3: Internship date cross-validation ────────────────────────────────────


class TestF3DateValidation:
    def test_valid_date_range(self):
        """Should accept valid start < end dates."""
        config = AppConfig(
            email="test@example.com",
            password_encrypted="x",
            internship_id=1,
            internship_start_date="2026-01-01",
            internship_end_date="2026-06-30",
        )
        assert config.internship_start_date == "2026-01-01"

    def test_start_after_end_raises(self):
        """Should reject start date after end date."""
        with pytest.raises(ValueError, match="cannot be after end date"):
            AppConfig(
                email="test@example.com",
                password_encrypted="x",
                internship_id=1,
                internship_start_date="2026-07-01",
                internship_end_date="2026-06-30",
            )

    def test_invalid_start_date_format_raises(self):
        """Should reject invalid start date format."""
        with pytest.raises(ValueError, match="internship_start_date"):
            AppConfig(
                email="test@example.com",
                password_encrypted="x",
                internship_id=1,
                internship_start_date="01-01-2026",
                internship_end_date="2026-06-30",
            )

    def test_invalid_end_date_format_raises(self):
        """Should reject invalid end date format."""
        with pytest.raises(ValueError, match="internship_end_date"):
            AppConfig(
                email="test@example.com",
                password_encrypted="x",
                internship_id=1,
                internship_start_date="2026-01-01",
                internship_end_date="30-06-2026",
            )

    def test_end_date_today_is_valid(self):
        """Should accept 'today' as end date."""
        config = AppConfig(
            email="test@example.com",
            password_encrypted="x",
            internship_id=1,
            internship_start_date="2026-01-01",
            internship_end_date="today",
        )
        assert config.internship_end_date == "today"

    def test_same_start_and_end_is_valid(self):
        """Should accept same start and end date."""
        config = AppConfig(
            email="test@example.com",
            password_encrypted="x",
            internship_id=1,
            internship_start_date="2026-01-01",
            internship_end_date="2026-01-01",
        )
        assert config.internship_start_date == "2026-01-01"


# ── F4: API response schema validation ──────────────────────────────────────


class TestF4ApiSchemas:
    def test_api_response_success(self):
        """ApiResponse should parse successful response."""
        resp = ApiResponse(success=True, message="ok", data={"key": "value"})
        assert resp.success is True
        assert resp.data == {"key": "value"}

    def test_api_response_defaults(self):
        """ApiResponse should have sensible defaults."""
        resp = ApiResponse()
        assert resp.success is False
        assert resp.message == ""
        assert resp.data is None

    def test_paginated_data_parsing(self):
        """PaginatedData should parse paginated response."""
        data = PaginatedData(
            data=[{"date": "2026-04-07"}],
            next_page_url="http://example.com/next",
        )
        assert len(data.data) == 1
        assert data.next_page_url == "http://example.com/next"

    def test_paginated_data_no_next(self):
        """PaginatedData should handle missing next_page_url."""
        data = PaginatedData(data=[{"date": "2026-04-07"}])
        assert data.next_page_url is None

    def test_client_uses_api_response_in_pagination(self, client):
        """Client pagination should use ApiResponse and PaginatedData models."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b'{"success": true}'
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "data": [{"date": "2026-04-07"}],
                "next_page_url": None,
            },
        }

        client._authenticated = True
        with patch.object(client.session, "get", return_value=mock_response):
            items = client._paginate_diary_list()
            assert len(items) == 1


# ── F5: Connection pooling / retry adapter ──────────────────────────────────


class TestF5RetryAdapter:
    def test_session_has_https_adapter(self, client):
        """Session should have an HTTPAdapter mounted for https."""
        adapter = client.session.get_adapter("https://example.com")
        assert adapter is not None

    def test_session_has_http_adapter(self, client):
        """Session should have an HTTPAdapter mounted for http."""
        adapter = client.session.get_adapter("http://example.com")
        assert adapter is not None

    def test_create_session_returns_session(self):
        """_create_session should return a requests.Session."""
        import requests

        session = VTUApiClient._create_session()
        assert isinstance(session, requests.Session)


# ── F6: Config backup and restore ───────────────────────────────────────────


class TestF6BackupRestore:
    def test_backup_creates_file(self, mock_config_manager):
        """backup() should create a backup file."""
        backup_path = mock_config_manager.backup()
        assert backup_path.exists()
        assert ".backup." in backup_path.name

    def test_list_backups(self, mock_config_manager):
        """list_backups() should return backup files."""
        mock_config_manager.backup()
        backups = mock_config_manager.list_backups()
        assert len(backups) >= 1

    def test_restore_from_backup(self, mock_config_manager):
        """restore() should restore config from backup file."""
        # Change config
        config = mock_config_manager.config
        config.company_name = "Original Corp"
        mock_config_manager.save(config)

        # Create backup
        backup_path = mock_config_manager.backup()

        # Change config again
        config.company_name = "Changed Corp"
        mock_config_manager.save(config)
        assert mock_config_manager.config.company_name == "Changed Corp"

        # Restore from backup
        mock_config_manager.restore(backup_path)
        assert mock_config_manager.config.company_name == "Original Corp"

    def test_restore_nonexistent_raises(self, mock_config_manager, tmp_path):
        """restore() should raise for nonexistent backup."""
        with pytest.raises(FileNotFoundError):
            mock_config_manager.restore(tmp_path / "nonexistent.json")

    def test_backup_no_config_raises(self, tmp_path):
        """backup() should raise when no config exists."""
        manager = ConfigManager(tmp_path / "nonexistent.json")
        with pytest.raises(FileNotFoundError):
            manager.backup()
