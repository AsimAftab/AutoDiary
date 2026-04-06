from unittest.mock import MagicMock, patch

import pytest

from autodiary.core.client import VTUApiClient
from autodiary.core.config import ConfigManager


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
    with patch("time.sleep", return_value=None):  # Skip delays in tests
        yield VTUApiClient(mock_config_manager)


def test_login_success(client):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.content = b'{"success": true}'
    mock_response.json.return_value = {"success": True}

    with patch.object(client.session, "post", return_value=mock_response) as mock_post:
        assert client.login("user", "pass") is True
        mock_post.assert_called_once()


def test_login_failure(client):
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.content = b'{"success": false, "message": "Invalid credentials"}'
    mock_response.json.return_value = {"success": False, "message": "Invalid credentials"}

    with patch.object(client.session, "post", return_value=mock_response) as mock_post:
        assert client.login("user", "pass") is False
        # 401 errors are retried up to max_login_attempts (default 3)
        assert mock_post.call_count == 3


def test_upload_entry_success(client):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.content = b'{"success": true, "message": "Created"}'
    mock_response.json.return_value = {"success": True, "message": "Created"}

    entry = {"date": "2026-04-07", "description": "Test"}
    with patch.object(client.session, "post", return_value=mock_response):
        success, message = client.upload_entry(entry)
        assert success is True
        assert message == "Created"


def test_upload_entries_dry_run(client):
    entries = [
        {"date": "2026-04-07", "description": "Test 1"},
        {"date": "2026-04-08", "description": "Test 2"},
    ]
    results = client.upload_entries(entries, dry_run=True)
    assert results["success"] == 2
    assert results["failed"] == 0
    assert results["skipped"] == 0


def test_upload_entries_raises_when_fetch_existing_dates_fails(client):
    entries = [{"date": "2026-04-07", "description": "Test"}]

    with (
        patch.object(client, "login", return_value=True),
        patch.object(client, "fetch_existing_dates", side_effect=ValueError("fetch failed")),
    ):
        with pytest.raises(ValueError, match="fetch failed"):
            client.upload_entries(entries)
