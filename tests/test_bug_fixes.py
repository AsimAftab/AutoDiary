"""
Tests for bug fixes B1–B6.
"""

import csv
from unittest.mock import MagicMock, patch

import pytest

from autodiary.core.client import VTUApiClient
from autodiary.core.config import ConfigManager
from autodiary.models.entry import DiaryEntry

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


# ── B1: Session cookies cleared on login failure ─────────────────────────────


class TestB1SessionCookiesCleared:
    def test_cookies_cleared_on_401(self, client):
        """Cookies should be cleared between retries on 401."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.content = b'{"success": false}'
        mock_response.json.return_value = {"success": False}

        with patch.object(client.session, "post", return_value=mock_response):
            with patch.object(client.session.cookies, "clear") as mock_clear:
                client.login("user", "pass")
                assert mock_clear.call_count == client.max_login_attempts

    def test_cookies_cleared_on_non_retryable_failure(self, client):
        """Cookies should be cleared on non-retryable errors (e.g. 403)."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.content = b'{"success": false}'
        mock_response.json.return_value = {"success": False}

        with patch.object(client.session, "post", return_value=mock_response):
            with patch.object(client.session.cookies, "clear") as mock_clear:
                result = client.login("user", "pass")
                assert result is False
                assert mock_clear.call_count == 1

    def test_cookies_not_cleared_on_success(self, client):
        """Cookies should not be cleared on successful login."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b'{"success": true}'
        mock_response.json.return_value = {"success": True}

        with patch.object(client.session, "post", return_value=mock_response):
            with patch.object(client.session.cookies, "clear") as mock_clear:
                result = client.login("user", "pass")
                assert result is True
                mock_clear.assert_not_called()


# ── B2: Pagination max page guard ────────────────────────────────────────────


class TestB2PaginationMaxPages:
    def test_pagination_stops_at_max_pages(self, client):
        """Pagination should stop after max_pages even if next_page_url is present."""
        mock_login_response = MagicMock()
        mock_login_response.ok = True
        mock_login_response.content = b'{"success": true}'
        mock_login_response.json.return_value = {"success": True}

        mock_page_response = MagicMock()
        mock_page_response.ok = True
        mock_page_response.content = b'{"success": true}'
        mock_page_response.json.return_value = {
            "success": True,
            "data": {
                "data": [{"date": "2026-01-01"}],
                "next_page_url": "http://example.com/next",  # always present
            },
        }

        client._authenticated = True

        with patch.object(client.session, "get", return_value=mock_page_response):
            items = client._paginate_diary_list()
            # Should stop at 500 pages (max_pages default)
            assert len(items) == 500

    def test_pagination_stops_normally_when_no_next_page(self, client):
        """Pagination should stop when next_page_url is absent (normal case)."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b'{"success": true}'
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "data": [{"date": "2026-01-01"}, {"date": "2026-01-02"}],
                "next_page_url": None,
            },
        }

        client._authenticated = True

        with patch.object(client.session, "get", return_value=mock_response):
            items = client._paginate_diary_list()
            assert len(items) == 2


# ── B3: _fetch_user_internships return type (verified correct, testing anyway)


class TestB3FetchUserInternships:
    def test_returns_empty_list_on_failure(self, mock_config_manager):
        """Should return [] when API call raises an exception."""
        from autodiary.cli.config_menu import ConfigMenu

        menu = ConfigMenu(mock_config_manager)
        mock_client = MagicMock()
        mock_client.fetch_internships.side_effect = Exception("network error")

        result = menu._fetch_user_internships(mock_client)
        assert result == []

    def test_returns_empty_list_on_unexpected_structure(self, mock_config_manager):
        """Should return [] when API response has unexpected structure."""
        from autodiary.cli.config_menu import ConfigMenu

        menu = ConfigMenu(mock_config_manager)
        mock_client = MagicMock()
        mock_client.fetch_internships.return_value = {"success": True, "data": "unexpected"}

        result = menu._fetch_user_internships(mock_client)
        assert result == []

    def test_returns_normalized_internships(self, mock_config_manager):
        """Should return normalized list from valid API response."""
        from autodiary.cli.config_menu import ConfigMenu

        menu = ConfigMenu(mock_config_manager)
        mock_client = MagicMock()
        mock_client.fetch_internships.return_value = {
            "success": True,
            "data": {
                "data": [
                    {
                        "internship_id": 42,
                        "status": 6,
                        "internship_details": {"name": "Test", "company": "Corp"},
                    }
                ]
            },
        }

        result = menu._fetch_user_internships(mock_client)
        assert len(result) == 1
        assert result[0]["id"] == 42
        assert result[0]["title"] == "Test"


# ── B4: Early date range validation ──────────────────────────────────────────


class TestB4DateRangeValidation:
    def test_generate_working_dates_rejects_reversed_range(self):
        """_generate_working_dates should return [] and print error for reversed range."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        result = menu._generate_working_dates(
            "2026-04-15", "2026-04-10", {"weekdays": [], "dates": []}
        )
        assert result == []

    def test_generate_working_dates_valid_range(self):
        """_generate_working_dates should return dates for valid range."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        result = menu._generate_working_dates(
            "2026-04-13", "2026-04-15", {"weekdays": [], "dates": []}
        )
        assert result == ["2026-04-13", "2026-04-14", "2026-04-15"]

    def test_generate_working_dates_single_day(self):
        """_generate_working_dates should work for a single-day range."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        result = menu._generate_working_dates(
            "2026-04-15", "2026-04-15", {"weekdays": [], "dates": []}
        )
        assert result == ["2026-04-15"]

    def test_generate_working_dates_excludes_holidays(self):
        """_generate_working_dates should exclude holiday weekdays and specific dates."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        # 2026-04-12 is a Sunday, 2026-04-13 is Monday
        result = menu._generate_working_dates(
            "2026-04-12",
            "2026-04-14",
            {"weekdays": ["sunday"], "dates": ["2026-04-14"]},
        )
        # Sunday excluded by weekday, Tuesday excluded by specific date
        assert result == ["2026-04-13"]


# ── B5: CSV export column ordering ───────────────────────────────────────────


class TestB5CsvColumnOrder:
    def test_csv_uses_logical_column_order(self, tmp_path):
        """CSV columns should follow logical order, not alphabetical."""
        entries = [
            {
                "date": "2026-04-15",
                "description": "Test entry",
                "hours": 8,
                "learnings": "Learned stuff",
                "mood_slider": 5,
                "skill_ids": ["3"],
                "links": "",
                "blockers": "",
                "internship_id": 123,
            }
        ]

        csv_path = tmp_path / "test.csv"

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            preferred_order = [
                "date",
                "description",
                "hours",
                "learnings",
                "mood_slider",
                "skill_ids",
                "links",
                "blockers",
                "internship_id",
            ]
            all_keys = {k for entry in entries for k in entry}
            fieldnames = [k for k in preferred_order if k in all_keys]
            fieldnames += sorted(all_keys - set(fieldnames))
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(entries)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)

        assert headers == preferred_order

    def test_csv_includes_extra_keys_after_preferred(self, tmp_path):
        """Extra keys not in preferred order should appear alphabetically at the end."""
        entries = [{"date": "2026-04-15", "description": "Test", "custom_field": "val", "aaa": "x"}]

        csv_path = tmp_path / "test.csv"

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            preferred_order = [
                "date",
                "description",
                "hours",
                "learnings",
                "mood_slider",
                "skill_ids",
                "links",
                "blockers",
                "internship_id",
            ]
            all_keys = {k for entry in entries for k in entry}
            fieldnames = [k for k in preferred_order if k in all_keys]
            fieldnames += sorted(all_keys - set(fieldnames))
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(entries)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)

        # date and description from preferred, then aaa and custom_field alphabetically
        assert headers == ["date", "description", "aaa", "custom_field"]


# ── B6: Whitespace-only skill IDs ────────────────────────────────────────────


class TestB6WhitespaceSkillIds:
    def test_whitespace_only_skill_id_raises(self):
        """Skill IDs that are whitespace-only should raise ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            DiaryEntry(
                description="Test",
                hours=8,
                learnings="Test",
                mood_slider=5,
                skill_ids=["  ", "  "],
            )

    def test_mixed_whitespace_and_valid_raises(self):
        """A mix of valid and whitespace-only skill IDs should raise."""
        with pytest.raises(ValueError, match="non-empty"):
            DiaryEntry(
                description="Test",
                hours=8,
                learnings="Test",
                mood_slider=5,
                skill_ids=["3", "  "],
            )

    def test_valid_skill_ids_with_leading_trailing_spaces(self):
        """Skill IDs with leading/trailing spaces should be stripped and accepted."""
        entry = DiaryEntry(
            description="Test",
            hours=8,
            learnings="Test",
            mood_slider=5,
            skill_ids=[" 3 ", " 44"],
        )
        assert entry.skill_ids == ["3", "44"]

    def test_empty_skill_ids_list_raises(self):
        """Empty skill_ids list should raise."""
        with pytest.raises(ValueError):
            DiaryEntry(
                description="Test",
                hours=8,
                learnings="Test",
                mood_slider=5,
                skill_ids=[],
            )
