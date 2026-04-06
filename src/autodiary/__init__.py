"""
VTU Auto Diary Filler
A user-friendly console application for uploading internship diary entries to VTU portal.
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("autodiary")
    _meta = importlib.metadata.metadata("autodiary")
    __author__ = _meta.get("Author", "VTU Auto Diary Team")
    __description__ = _meta.get(
        "Summary", "VTU Internship Diary Auto Filler - User Friendly Console Application"
    )
except importlib.metadata.PackageNotFoundError:
    __version__ = "1.0.0"
    __author__ = "VTU Auto Diary Team"
    __description__ = "VTU Internship Diary Auto Filler - User Friendly Console Application"

__all__ = ["__version__", "__author__", "__description__"]
