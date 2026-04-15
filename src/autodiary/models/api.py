"""
Pydantic models for VTU API responses.
"""

from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """Base API response structure."""

    success: bool = False
    message: str = ""
    data: Any = None


class DiaryItem(BaseModel):
    """Single diary entry from API."""

    date: str | None = None
    description: str = ""
    hours: int | None = None
    mood_slider: int | None = None
    skill_ids: list[str] = Field(default_factory=list)


class PaginatedData(BaseModel):
    """Paginated response data."""

    data: list[dict[str, Any]] = Field(default_factory=list)
    next_page_url: str | None = None
