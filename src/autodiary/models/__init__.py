"""
Models module for VTU Auto Diary Filler
Contains data models and validation schemas.
"""

from autodiary.models.config import AppConfig
from autodiary.models.entry import DiaryEntry

__all__ = ["AppConfig", "DiaryEntry"]
