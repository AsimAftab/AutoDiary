import pytest

from autodiary.utils.validators import (
    sanitize_filename,
    validate_date_format,
    validate_email,
    validate_hours,
    validate_internship_id,
    validate_mood,
    validate_required_fields,
    validate_weekday,
)


@pytest.mark.parametrize(
    "email, expected",
    [
        ("test@example.com", True),
        ("user.name+tag@domain.co.uk", True),
        ("invalid-email", False),
        ("test@domain", False),
        ("@domain.com", False),
        ("", False),
        (None, False),
    ],
)
def test_validate_email(email, expected):
    assert validate_email(email) is expected


@pytest.mark.parametrize(
    "date_str, expected",
    [
        ("2026-04-07", True),
        ("2026-13-01", False),
        ("2026-04-32", False),
        ("07-04-2026", False),
        ("invalid", False),
        ("", False),
        (None, False),
    ],
)
def test_validate_date_format(date_str, expected):
    assert validate_date_format(date_str) is expected


@pytest.mark.parametrize(
    "internship_id, expected",
    [
        ("12345", True),
        ("1", True),
        ("0", False),
        ("-5", False),
        ("abc", False),
        ("", False),
        (None, False),
    ],
)
def test_validate_internship_id(internship_id, expected):
    assert validate_internship_id(internship_id) is expected


@pytest.mark.parametrize(
    "hours, expected",
    [
        ("1", True),
        ("8", True),
        ("24", True),
        ("0", False),
        ("25", False),
        ("abc", False),
        ("", False),
        (None, False),
    ],
)
def test_validate_hours(hours, expected):
    assert validate_hours(hours) is expected


@pytest.mark.parametrize(
    "mood, expected",
    [
        ("1", True),
        ("3", True),
        ("5", True),
        ("0", False),
        ("6", False),
        ("abc", False),
        ("", False),
        (None, False),
    ],
)
def test_validate_mood(mood, expected):
    assert validate_mood(mood) is expected


@pytest.mark.parametrize(
    "weekday, expected",
    [
        ("Monday", True),
        ("monday", True),
        ("  Friday  ", True),
        ("Funday", False),
        ("", False),
        (None, False),
    ],
)
def test_validate_weekday(weekday, expected):
    assert validate_weekday(weekday) is expected


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("my/file:name*.txt", "my_file_name_.txt"),
        ("simple.json", "simple.json"),
        ("  spaces  ", "spaces"),
        ("", ""),
    ],
)
def test_sanitize_filename(filename, expected):
    assert sanitize_filename(filename) == expected


@pytest.mark.parametrize(
    "data, required, expected_valid, expected_missing",
    [
        ({"name": "Test", "id": 1}, ["name", "id"], True, []),
        ({"name": "Test"}, ["name", "id"], False, ["id"]),
        ({"name": "Test", "id": ""}, ["name", "id"], True, []),
        ({"name": "Test", "id": 0}, ["name", "id"], True, []),
        ({"name": False}, ["name"], True, []),
        ({"name": None}, ["name"], False, ["name"]),
        ({}, ["name"], False, ["name"]),
    ],
)
def test_validate_required_fields(data, required, expected_valid, expected_missing):
    is_valid, missing = validate_required_fields(data, required)
    assert is_valid is expected_valid
    assert missing == expected_missing
