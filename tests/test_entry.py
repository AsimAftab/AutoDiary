import pytest

from autodiary.models.entry import DiaryEntry


def test_diary_entry_validation():
    # Valid entry
    data = {
        "description": "Worked on tests",
        "hours": 8,
        "learnings": "Learned pytest",
        "mood_slider": 5,
        "skill_ids": ["3", "44"],
    }
    entry = DiaryEntry(**data)
    assert entry.description == "Worked on tests"
    assert entry.hours == 8

    # Missing description
    invalid_data = data.copy()
    del invalid_data["description"]
    with pytest.raises(ValueError):
        DiaryEntry(**invalid_data)

    # Invalid hours
    invalid_data = data.copy()
    invalid_data["hours"] = 25
    with pytest.raises(ValueError):
        DiaryEntry(**invalid_data)

    # Boundary hours
    boundary_data = data.copy()
    boundary_data["hours"] = 24
    boundary_entry = DiaryEntry(**boundary_data)
    assert boundary_entry.hours == 24

    invalid_data = data.copy()
    invalid_data["hours"] = 0
    with pytest.raises(ValueError):
        DiaryEntry(**invalid_data)

    invalid_data = data.copy()
    invalid_data["hours"] = -1
    with pytest.raises(ValueError):
        DiaryEntry(**invalid_data)

    # Empty skill_ids
    invalid_data = data.copy()
    invalid_data["skill_ids"] = []
    with pytest.raises(ValueError):
        DiaryEntry(**invalid_data)

    # Invalid date format
    invalid_data = data.copy()
    invalid_data["date"] = "07-04-2026"
    with pytest.raises(ValueError, match="Date must be in YYYY-MM-DD format"):
        DiaryEntry(**invalid_data)
