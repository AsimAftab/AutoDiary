"""
Diary entry model and validation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiaryEntry(BaseModel):
    """Diary entry model with validation."""

    description: str = Field(..., min_length=1, description="Work description")
    hours: int = Field(..., ge=1, le=24, description="Hours worked")
    links: str = Field(default="", description="Related links")
    blockers: str = Field(default="", description="Blockers encountered")
    learnings: str = Field(..., min_length=1, description="Key learnings")
    mood_slider: int = Field(..., ge=1, le=5, description="Mood rating (1-5)")
    skill_ids: list[str] = Field(..., min_length=1, description="Skill IDs")
    date: str | None = Field(None, description="Entry date (YYYY-MM-DD)")
    internship_id: int | None = Field(None, description="Internship ID override")

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str | None) -> str | None:
        """Validate date format."""
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format") from None
        return v

    @field_validator("skill_ids")
    @classmethod
    def validate_skill_ids(cls, v: list[str]) -> list[str]:
        """Validate skill IDs are non-empty strings."""
        if not all(isinstance(sid, str) for sid in v):
            raise ValueError("All skill IDs must be strings")
        stripped = [sid.strip() for sid in v]
        if not all(stripped):
            raise ValueError("All skill IDs must be non-empty strings")
        return stripped

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Worked on data analysis using Python and SQL",
                "hours": 8,
                "links": "https://github.com/project",
                "blockers": "None",
                "learnings": "Improved SQL query optimization",
                "mood_slider": 5,
                "skill_ids": ["44", "16", "20"],
                "date": "2026-01-15",
            }
        }
    )
