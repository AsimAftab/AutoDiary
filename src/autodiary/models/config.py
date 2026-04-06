"""
Configuration model and validation.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AppConfig(BaseModel):
    """Application configuration model."""

    # Credentials
    email: str = Field(..., description="VTU portal email")
    password_encrypted: str = Field(..., description="Encrypted password")

    # API Configuration
    api_base_url: str = Field("https://vtuapi.internyet.in", description="API base URL")
    internship_id: int = Field(-1, description="Internship ID")

    # Internship Details
    internship_start_date: str = Field(..., description="Internship start date (YYYY-MM-DD)")
    internship_end_date: str = Field(
        "today", description="Internship end date (YYYY-MM-DD or 'today')"
    )
    internship_title: str = Field("", description="Internship title")
    company_name: str = Field("", description="Company name")

    # Holiday Configuration
    holiday_weekdays: list[str] = Field(
        default_factory=list, description="Holiday weekdays (e.g., ['Sunday'])"
    )
    holiday_dates: list[str] = Field(
        default_factory=list, description="Specific holiday dates (YYYY-MM-DD)"
    )

    # Advanced Settings
    timeout_seconds: int = Field(30, ge=1, le=300, description="Request timeout")
    request_delay_min: float = Field(0.8, ge=0, description="Min request delay")
    request_delay_max: float = Field(1.5, ge=0, description="Max request delay")
    max_retries: int = Field(3, ge=1, description="Max upload retries")
    auto_skip_existing: bool = Field(True, description="Skip existing entries automatically")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not v:  # Allow empty for default config
            return v
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("Invalid email format")
        return v

    @field_validator("internship_id")
    @classmethod
    def validate_internship_id(cls, v: int) -> int:
        """Validate internship ID cleanly."""
        if v == 0:
            raise ValueError("Internship ID cannot be 0. Please update your configuration.")
        return v

    @field_validator("holiday_weekdays")
    @classmethod
    def validate_weekdays(cls, v: list[str]) -> list[str]:
        """Validate weekday names."""
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        result = []
        for day in v:
            day_lower = day.lower().strip()
            if day_lower not in valid_days:
                raise ValueError(f"Invalid weekday: {day}. Must be one of {valid_days}")
            result.append(day_lower)
        return result

    @field_validator("holiday_dates")
    @classmethod
    def validate_holiday_dates(cls, v: list[str]) -> list[str]:
        """Validate holiday date format."""
        from datetime import datetime

        result = []
        for date_str in v:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                result.append(date_str)
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD") from None
        return result

    @model_validator(mode="after")
    def validate_delays(self) -> "AppConfig":
        """Validate delay range."""
        if self.request_delay_min > self.request_delay_max:
            raise ValueError("Min delay cannot be greater than max delay")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password_encrypted": "gAAAAA...",
                "api_base_url": "https://vtuapi.internyet.in",
                "internship_id": 8530,
                "internship_start_date": "2026-01-05",
                "internship_end_date": "today",
                "internship_title": "Data Analyst Internship",
                "company_name": "Tech Company",
                "holiday_weekdays": ["sunday"],
                "holiday_dates": ["2026-01-26"],
                "timeout_seconds": 30,
                "request_delay_min": 0.8,
                "request_delay_max": 1.5,
                "max_retries": 3,
                "auto_skip_existing": True,
            }
        }
    )
