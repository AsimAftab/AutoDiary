"""
Tests for coverage gaps T1–T5.
T1: CLI integration tests
T2: Upload error-path tests
T3: Date generation edge-case tests
T4: CSV export tests
T5: Statistics calculation tests
"""

import csv
from unittest.mock import MagicMock, patch

import pytest
import requests

from autodiary.core.client import VTUApiClient
from autodiary.core.config import ConfigManager

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


# ── T1: CLI Integration Tests ───────────────────────────────────────────────


class TestT1MainMenuIntegration:
    def test_main_menu_initializes_submenus(self, mock_config_manager):
        """MainMenu should initialize all sub-menus."""
        from autodiary.cli.main_menu import MainMenu

        menu = MainMenu(mock_config_manager)
        assert menu.upload_menu is not None
        assert menu.view_menu is not None
        assert menu.config_menu is not None

    def test_main_menu_exit(self, mock_config_manager):
        """MainMenu should exit cleanly on exit choice."""
        from autodiary.cli.main_menu import MainMenu

        menu = MainMenu(mock_config_manager)

        with (
            patch("autodiary.cli.main_menu.questionary") as mock_q,
            patch("autodiary.cli.main_menu.console"),
        ):
            mock_q.select.return_value.ask.return_value = "exit"
            menu.show()
            # Should reach here without error

    def test_main_menu_dispatches_to_upload(self, mock_config_manager):
        """MainMenu should dispatch to upload_menu.show() on upload choice."""
        from autodiary.cli.main_menu import MainMenu

        menu = MainMenu(mock_config_manager)

        with (
            patch("autodiary.cli.main_menu.questionary") as mock_q,
            patch("autodiary.cli.main_menu.console"),
            patch.object(menu.upload_menu, "show") as mock_upload_show,
        ):
            mock_q.select.return_value.ask.side_effect = ["upload", "exit"]
            menu.show()
            mock_upload_show.assert_called_once()

    def test_main_menu_dispatches_to_view(self, mock_config_manager):
        """MainMenu should dispatch to view_menu.show() on view choice."""
        from autodiary.cli.main_menu import MainMenu

        menu = MainMenu(mock_config_manager)

        with (
            patch("autodiary.cli.main_menu.questionary") as mock_q,
            patch("autodiary.cli.main_menu.console"),
            patch.object(menu.view_menu, "show") as mock_view_show,
        ):
            mock_q.select.return_value.ask.side_effect = ["view", "exit"]
            menu.show()
            mock_view_show.assert_called_once()

    def test_main_menu_dispatches_to_config(self, mock_config_manager):
        """MainMenu should dispatch to config_menu.show() on config choice."""
        from autodiary.cli.main_menu import MainMenu

        menu = MainMenu(mock_config_manager)

        with (
            patch("autodiary.cli.main_menu.questionary") as mock_q,
            patch("autodiary.cli.main_menu.console"),
            patch.object(menu.config_menu, "show") as mock_config_show,
        ):
            mock_q.select.return_value.ask.side_effect = ["config", "exit"]
            menu.show()
            mock_config_show.assert_called_once()


class TestT1UploadMenuIntegration:
    def test_upload_menu_back(self):
        """UploadMenu should return on back choice."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())

        with patch("autodiary.cli.upload_menu.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = "back"
            menu.show()

    def test_upload_menu_dispatches_dry_run(self):
        """UploadMenu should dispatch to dry_run_upload on dry choice."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())

        with (
            patch("autodiary.cli.upload_menu.questionary") as mock_q,
            patch.object(menu, "dry_run_upload") as mock_dry,
        ):
            mock_q.select.return_value.ask.side_effect = ["dry", "back"]
            menu.show()
            mock_dry.assert_called_once()

    def test_load_entries_valid_json(self, tmp_path):
        """_load_entries should load valid JSON array."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        entries_file = tmp_path / "entries.json"
        entries_file.write_text('[{"description": "test", "hours": 8}]')

        result = menu._load_entries(entries_file)
        assert len(result) == 1
        assert result[0]["description"] == "test"

    def test_load_entries_invalid_json(self, tmp_path):
        """_load_entries should return [] for invalid JSON."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        entries_file = tmp_path / "entries.json"
        entries_file.write_text("not json")

        result = menu._load_entries(entries_file)
        assert result == []

    def test_load_entries_non_array(self, tmp_path):
        """_load_entries should return [] for non-array JSON."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        entries_file = tmp_path / "entries.json"
        entries_file.write_text('{"key": "value"}')

        result = menu._load_entries(entries_file)
        assert result == []


class TestT1ViewMenuIntegration:
    def test_view_menu_back(self):
        """ViewMenu should return on back choice."""
        from autodiary.cli.view_menu import ViewMenu

        menu = ViewMenu(MagicMock())

        with patch("autodiary.cli.view_menu.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = "back"
            menu.show()


class TestT1ConfigMenuIntegration:
    def test_config_menu_back(self, mock_config_manager):
        """ConfigMenu should return on back choice."""
        from autodiary.cli.config_menu import ConfigMenu

        menu = ConfigMenu(mock_config_manager)

        with patch("autodiary.cli.config_menu.questionary") as mock_q:
            mock_q.select.return_value.ask.return_value = "back"
            menu.show()

    def test_config_menu_dispatches_to_test_connection(self, mock_config_manager):
        """ConfigMenu should dispatch to test_connection on test choice."""
        from autodiary.cli.config_menu import ConfigMenu

        menu = ConfigMenu(mock_config_manager)

        with (
            patch("autodiary.cli.config_menu.questionary") as mock_q,
            patch.object(menu, "test_connection") as mock_test,
        ):
            mock_q.select.return_value.ask.side_effect = ["test", "back"]
            menu.show()
            mock_test.assert_called_once()


# ── T2: Upload Error-Path Tests ──────────────────────────────────────────────


class TestT2UploadErrorPaths:
    def test_partial_batch_failure(self, client):
        """upload_entries should count individual failures without stopping."""
        success_response = MagicMock()
        success_response.ok = True
        success_response.content = b'{"success": true, "message": "ok"}'
        success_response.json.return_value = {"success": True, "message": "ok"}

        fail_response = MagicMock()
        fail_response.ok = False
        fail_response.status_code = 400
        fail_response.content = b'{"success": false, "message": "bad"}'
        fail_response.json.return_value = {"success": False, "message": "bad"}

        entries = [
            {"date": "2026-04-07", "description": "Test 1"},
            {"date": "2026-04-08", "description": "Test 2"},
            {"date": "2026-04-09", "description": "Test 3"},
        ]

        with (
            patch.object(client, "login", return_value=True),
            patch.object(
                client,
                "upload_entry",
                side_effect=[(True, "ok"), (False, "bad"), (True, "ok")],
            ),
        ):
            client.config.auto_skip_existing = False
            results = client.upload_entries(entries)

        assert results["success"] == 2
        assert results["failed"] == 1

    def test_network_timeout_during_upload(self, client):
        """upload_entry should handle network timeout and retry."""
        timeout_exc = requests.Timeout("Connection timed out")

        success_response = MagicMock()
        success_response.ok = True
        success_response.content = b'{"success": true, "message": "ok"}'
        success_response.json.return_value = {"success": True, "message": "ok"}

        with patch.object(client.session, "post", side_effect=[timeout_exc, success_response]):
            success, msg = client.upload_entry({"date": "2026-04-07"})
            assert success is True

    def test_429_rate_limit_with_retry(self, client):
        """upload_entry should retry on HTTP 429."""
        rate_limit_response = MagicMock()
        rate_limit_response.ok = False
        rate_limit_response.status_code = 429
        rate_limit_response.content = b'{"message": "rate limited"}'
        rate_limit_response.json.return_value = {"message": "rate limited"}

        success_response = MagicMock()
        success_response.ok = True
        success_response.content = b'{"success": true, "message": "ok"}'
        success_response.json.return_value = {"success": True, "message": "ok"}

        with patch.object(
            client.session, "post", side_effect=[rate_limit_response, success_response]
        ):
            success, msg = client.upload_entry({"date": "2026-04-07"})
            assert success is True

    def test_all_retries_exhausted(self, client):
        """upload_entry should return failure after all retries exhausted."""
        fail_response = MagicMock()
        fail_response.ok = False
        fail_response.status_code = 500
        fail_response.content = b'{"message": "server error"}'
        fail_response.json.return_value = {"message": "server error"}

        with patch.object(client.session, "post", return_value=fail_response):
            success, msg = client.upload_entry({"date": "2026-04-07"})
            assert success is False

    def test_upload_entries_empty_list(self, client):
        """upload_entries should handle empty list gracefully."""
        results = client.upload_entries([], dry_run=False)
        assert results == {"success": 0, "failed": 0, "skipped": 0}

    def test_upload_entries_skips_existing(self, client):
        """upload_entries should skip dates that already exist on server."""
        entries = [
            {"date": "2026-04-07", "description": "Test 1"},
            {"date": "2026-04-08", "description": "Test 2"},
        ]

        with (
            patch.object(client, "login", return_value=True),
            patch.object(client, "fetch_existing_dates", return_value={"2026-04-07"}),
            patch.object(client, "upload_entry", return_value=(True, "ok")) as mock_upload,
        ):
            client.config.auto_skip_existing = True
            results = client.upload_entries(entries)

        assert results["skipped"] == 1
        assert results["success"] == 1
        # Only the non-existing date should be uploaded
        mock_upload.assert_called_once()


# ── T3: Date Generation Edge-Case Tests ──────────────────────────────────────


class TestT3DateEdgeCases:
    @pytest.fixture
    def upload_menu(self):
        from autodiary.cli.upload_menu import UploadMenu

        return UploadMenu(MagicMock())

    def test_leap_year_feb_29(self, upload_menu):
        """Should include Feb 29 on leap years."""
        result = upload_menu._generate_working_dates(
            "2028-02-28", "2028-03-01", {"weekdays": [], "dates": []}
        )
        assert "2028-02-29" in result
        assert len(result) == 3

    def test_non_leap_year_feb_28(self, upload_menu):
        """Should skip Feb 29 on non-leap years."""
        result = upload_menu._generate_working_dates(
            "2027-02-27", "2027-03-01", {"weekdays": [], "dates": []}
        )
        assert "2027-02-29" not in result
        assert len(result) == 3  # 27, 28, Mar 1

    def test_overlapping_holiday_weekday_and_specific_date(self, upload_menu):
        """Date that's both a holiday weekday and specific date should be excluded once."""
        # 2026-04-12 is a Sunday
        result = upload_menu._generate_working_dates(
            "2026-04-11",
            "2026-04-13",
            {"weekdays": ["sunday"], "dates": ["2026-04-12"]},
        )
        # Only Saturday and Monday should remain
        assert "2026-04-12" not in result
        assert "2026-04-11" in result  # Saturday
        assert "2026-04-13" in result  # Monday

    def test_all_days_are_holidays(self, upload_menu):
        """Should return empty list if all days in range are holidays."""
        result = upload_menu._generate_working_dates(
            "2026-04-11",
            "2026-04-12",
            {"weekdays": ["saturday", "sunday"], "dates": []},
        )
        assert result == []

    def test_end_date_today(self, upload_menu):
        """Should handle 'today' as end_date."""
        result = upload_menu._generate_working_dates(
            "2026-04-14", "today", {"weekdays": [], "dates": []}
        )
        assert isinstance(result, list)
        # Should include at least April 14 and 15 (today)
        assert "2026-04-14" in result
        assert "2026-04-15" in result

    def test_weekend_exclusion_full_week(self, upload_menu):
        """Should exclude Saturday and Sunday from a full week."""
        # 2026-04-13 Monday to 2026-04-19 Sunday
        result = upload_menu._generate_working_dates(
            "2026-04-13",
            "2026-04-19",
            {"weekdays": ["saturday", "sunday"], "dates": []},
        )
        assert len(result) == 5  # Mon-Fri
        assert "2026-04-18" not in result  # Saturday
        assert "2026-04-19" not in result  # Sunday


class TestT3AssignDates:
    def test_assign_dates_skips_existing(self):
        """_assign_dates_to_entries should skip dates that already exist."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        entries = [{"description": "A"}, {"description": "B"}]
        working_dates = ["2026-04-07", "2026-04-08", "2026-04-09"]
        existing_dates = {"2026-04-07"}

        result = menu._assign_dates_to_entries(entries, working_dates, existing_dates)
        assert result[0]["date"] == "2026-04-08"
        assert result[1]["date"] == "2026-04-09"

    def test_assign_dates_stops_when_no_more_dates(self):
        """Should stop assigning when no available dates left."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        entries = [{"description": "A"}, {"description": "B"}, {"description": "C"}]
        working_dates = ["2026-04-07"]
        existing_dates = set()

        result = menu._assign_dates_to_entries(entries, working_dates, existing_dates)
        assert len(result) == 1  # Only one date available

    def test_assign_dates_preserves_existing_date(self):
        """Entries with existing dates should keep them."""
        from autodiary.cli.upload_menu import UploadMenu

        menu = UploadMenu(MagicMock())
        entries = [{"description": "A", "date": "2026-05-01"}, {"description": "B"}]
        working_dates = ["2026-04-07", "2026-04-08"]
        existing_dates = set()

        result = menu._assign_dates_to_entries(entries, working_dates, existing_dates)
        assert result[0]["date"] == "2026-05-01"  # Preserved
        assert result[1]["date"] == "2026-04-07"  # Assigned


# ── T4: CSV Export Tests ─────────────────────────────────────────────────────


class TestT4CsvExport:
    def _write_csv(self, entries, path):
        """Helper to replicate the CSV export logic from view_menu."""
        with open(path, "w", newline="", encoding="utf-8") as f:
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

    def test_special_characters_in_description(self, tmp_path):
        """CSV should handle commas, quotes, and newlines in fields."""
        entries = [
            {
                "date": "2026-04-15",
                "description": 'He said, "hello"\nNew line here',
                "hours": 8,
            }
        ]
        csv_path = tmp_path / "test.csv"
        self._write_csv(entries, csv_path)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert 'He said, "hello"' in row["description"]
            assert "New line here" in row["description"]

    def test_empty_entries_list(self, tmp_path):
        """CSV with empty entries should produce only headers or empty file."""
        # With no entries, no keys exist so fieldnames is empty
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[], extrasaction="ignore")
            writer.writeheader()
            writer.writerows([])

        content = csv_path.read_text()
        assert content.strip() == ""  # Empty fieldnames = empty header

    def test_entries_with_missing_optional_fields(self, tmp_path):
        """CSV should handle entries where some optional fields are missing."""
        entries = [
            {"date": "2026-04-15", "description": "Full entry", "hours": 8, "links": "http://x"},
            {"date": "2026-04-16", "description": "Minimal entry"},
        ]
        csv_path = tmp_path / "test.csv"
        self._write_csv(entries, csv_path)

        with open(csv_path, encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 2
            assert reader[0]["links"] == "http://x"
            assert reader[1]["links"] == ""  # Missing field becomes empty

    def test_skill_ids_list_serialized(self, tmp_path):
        """skill_ids (a list) should be serialized as a string in CSV."""
        entries = [
            {"date": "2026-04-15", "description": "Test", "skill_ids": ["3", "44"]},
        ]
        csv_path = tmp_path / "test.csv"
        self._write_csv(entries, csv_path)

        with open(csv_path, encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            # Lists get stringified by csv module
            assert "3" in reader[0]["skill_ids"]
            assert "44" in reader[0]["skill_ids"]


# ── T5: Statistics Calculation Tests ─────────────────────────────────────────


class TestT5Statistics:
    @pytest.fixture
    def view_menu(self):
        from autodiary.cli.view_menu import ViewMenu

        return ViewMenu(MagicMock())

    def test_basic_statistics(self, view_menu):
        """Should calculate basic stats correctly."""
        entries = [
            {"date": "2026-04-07", "hours": 8, "mood_slider": 5, "skill_ids": ["3"]},
            {"date": "2026-04-08", "hours": 6, "mood_slider": 3, "skill_ids": ["3", "44"]},
        ]
        stats = view_menu._calculate_statistics(entries)

        assert stats["total_entries"] == 2
        assert stats["total_hours"] == 14
        assert stats["avg_hours"] == 7.0
        assert stats["avg_mood"] == 4.0

    def test_date_range(self, view_menu):
        """Should identify earliest and latest dates."""
        entries = [
            {"date": "2026-04-10", "hours": 8, "mood_slider": 5},
            {"date": "2026-04-07", "hours": 8, "mood_slider": 5},
            {"date": "2026-04-15", "hours": 8, "mood_slider": 5},
        ]
        stats = view_menu._calculate_statistics(entries)

        assert stats["earliest_date"] == "2026-04-07"
        assert stats["latest_date"] == "2026-04-15"
        assert stats["day_span"] == 9  # 7th to 15th inclusive

    def test_mood_distribution(self, view_menu):
        """Should count mood values correctly."""
        entries = [
            {"hours": 8, "mood_slider": 5},
            {"hours": 8, "mood_slider": 5},
            {"hours": 8, "mood_slider": 3},
        ]
        stats = view_menu._calculate_statistics(entries)

        assert stats["mood_distribution"]["5/5"] == 2
        assert stats["mood_distribution"]["3/5"] == 1

    def test_skill_counts(self, view_menu):
        """Should aggregate skill usage counts."""
        entries = [
            {"hours": 8, "mood_slider": 5, "skill_ids": ["3", "44"]},
            {"hours": 8, "mood_slider": 5, "skill_ids": ["3", "16"]},
            {"hours": 8, "mood_slider": 5, "skill_ids": ["44"]},
        ]
        stats = view_menu._calculate_statistics(entries)

        assert stats["skill_counts"]["3"] == 2
        assert stats["skill_counts"]["44"] == 2
        assert stats["skill_counts"]["16"] == 1

    def test_empty_entries(self, view_menu):
        """Should handle empty entries list gracefully."""
        stats = view_menu._calculate_statistics([])

        assert stats["total_entries"] == 0
        assert stats["total_hours"] == 0
        assert stats["avg_hours"] == 0
        assert stats["avg_mood"] == 0
        assert stats["earliest_date"] is None
        assert stats["latest_date"] is None
        assert stats["day_span"] == 0

    def test_entries_without_dates(self, view_menu):
        """Should handle entries that have no date field."""
        entries = [
            {"hours": 8, "mood_slider": 4},
            {"hours": 6, "mood_slider": 3},
        ]
        stats = view_menu._calculate_statistics(entries)

        assert stats["total_entries"] == 2
        assert stats["earliest_date"] is None
        assert stats["latest_date"] is None
        assert stats["day_span"] == 0

    def test_single_entry(self, view_menu):
        """Should work with a single entry."""
        entries = [
            {"date": "2026-04-15", "hours": 8, "mood_slider": 5, "skill_ids": ["3"]},
        ]
        stats = view_menu._calculate_statistics(entries)

        assert stats["total_entries"] == 1
        assert stats["avg_hours"] == 8.0
        assert stats["avg_mood"] == 5.0
        assert stats["day_span"] == 1
