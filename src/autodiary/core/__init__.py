"""
Core module for VTU Auto Diary Filler
Contains all business logic, API client, and data management.
"""

from autodiary.core.client import VTUApiClient
from autodiary.core.config import ConfigManager

__all__ = ["VTUApiClient", "ConfigManager"]
