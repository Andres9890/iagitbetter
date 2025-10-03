"""
iagitbetter - Archiving any git repository to the Internet Archive
"""

__version__ = "1.0.7"
__version_v__ = f"v{__version__}"
__author__ = "Andres99"
__license__ = "GPL-3.0"

from .__main__ import main

# Import main components
from .iagitbetter import GitArchiver, check_for_updates, get_latest_pypi_version

__all__ = ["GitArchiver", "main", "get_latest_pypi_version", "check_for_updates", "__version__", "__version_v__"]
