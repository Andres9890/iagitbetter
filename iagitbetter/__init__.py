"""
iagitbetter - Archiving any git repository to the Internet Archive
"""

__version__ = "1.0.1"
__author__ = "Andres99"
__license__ = "GPL-3.0"

# Import main components
from .iagitbetter import GitArchiver, get_latest_pypi_version, check_for_updates
from .__main__ import main

__all__ = ['GitArchiver', 'main', 'get_latest_pypi_version', 'check_for_updates']