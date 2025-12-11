"""
Launchpad provider implementation.
Handles launchpad.net repositories.
"""

from typing import Any

from .base import BaseProvider


class LaunchpadProvider(BaseProvider):
    """Provider for Launchpad repositories."""

    name = "launchpad"
    domains = ["launchpad.net", "launchpad"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for Launchpad API."""
        if self.api_token:
            self._log(
                "Warning: Launchpad requires OAuth 1.0 authentication which is not "
                "supported. The provided api_token will be ignored. Only public API "
                "access is available."
            )
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build Launchpad API URL."""
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/{owner}/{repo_name}"
        return f"https://api.launchpad.net/1.0/{owner}/{repo_name}"

    def parse_repo_response(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """Parse Launchpad API response."""
        return {
            "description": api_data.get("description", ""),
            "created_at": api_data.get("date_created", ""),
            "updated_at": api_data.get("date_last_modified", ""),
            "html_url": api_data.get("web_link", ""),
            "default_branch": "master",
        }
