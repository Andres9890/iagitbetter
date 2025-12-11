"""
SourceForge provider implementation.
Handles sourceforge.net repositories.
"""

from typing import Any

from .base import BaseProvider


class SourceForgeProvider(BaseProvider):
    """Provider for SourceForge repositories."""

    name = "sourceforge"
    domains = ["sourceforge.net", "sourceforge"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for SourceForge API."""
        if self.api_token:
            self._log(
                "Warning: SourceForge requires OAuth 1.0a authentication which is not "
                "supported. The provided api_token will be ignored. Only public API "
                "access is available."
            )
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build SourceForge API URL."""
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/rest/p/{owner}/{repo_name}"
        return f"https://sourceforge.net/rest/p/{owner}/{repo_name}"

    def parse_repo_response(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """Parse SourceForge Allura API response."""
        return {
            "description": api_data.get("description", ""),
            "html_url": api_data.get("url", ""),
            "default_branch": "master",
        }
