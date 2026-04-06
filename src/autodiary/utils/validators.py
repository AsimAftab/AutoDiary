"""
Validation utilities for input and configuration.
"""

import re
from datetime import datetime
from pathlib import Path


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_date_format(date_str: str) -> bool:
    """
    Validate date format (YYYY-MM-DD).

    Args:
        date_str: Date string to validate

    Returns:
        True if valid, False otherwise
    """
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_first_run(config_path: Path) -> bool:
    """
    Check if this is the first time running the application.

    Args:
        config_path: Path to configuration file

    Returns:
        True if first run (no config exists), False otherwise
    """
    return not config_path.exists()


def validate_internship_id(internship_id: str) -> bool:
    """
    Validate internship ID format.

    Args:
        internship_id: Internship ID string

    Returns:
        True if valid, False otherwise
    """
    try:
        id_int = int(internship_id)
        return id_int > 0
    except (ValueError, TypeError):
        return False


def validate_hours(hours: str) -> bool:
    """
    Validate hours worked.

    Args:
        hours: Hours string

    Returns:
        True if valid (1-24), False otherwise
    """
    try:
        hours_int = int(hours)
        return 1 <= hours_int <= 24
    except (ValueError, TypeError):
        return False


def validate_mood(mood: str) -> bool:
    """
    Validate mood slider value.

    Args:
        mood: Mood value string

    Returns:
        True if valid (1-5), False otherwise
    """
    try:
        mood_int = int(mood)
        return 1 <= mood_int <= 5
    except (ValueError, TypeError):
        return False


def validate_weekday(weekday: str) -> bool:
    """
    Validate weekday name.

    Args:
        weekday: Weekday name

    Returns:
        True if valid weekday name, False otherwise
    """
    if not weekday:
        return False
    valid_days = {day.lower() for day in get_valid_weekdays()}
    return weekday.lower().strip() in valid_days


def get_valid_weekdays() -> list:
    """Get list of valid weekday names."""
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    if not filename:
        return ""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename.strip()


def validate_json_file(file_path: Path) -> bool:
    """
    Validate if a file is valid JSON.

    Args:
        file_path: Path to JSON file

    Returns:
        True if valid JSON, False otherwise
    """
    if not file_path.exists():
        return False

    try:
        import json

        with open(file_path, encoding="utf-8") as f:
            json.load(f)
        return True
    except (OSError, json.JSONDecodeError):
        return False


def validate_required_fields(data: dict, required_fields: list) -> tuple[bool, list]:
    """
    Validate that all required fields are present in data.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, missing_fields)
    """
    missing = [field for field in required_fields if field not in data or data[field] is None]
    return len(missing) == 0, missing
