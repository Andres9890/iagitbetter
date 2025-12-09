"""
Gerrit provider implementation.
Handles Gerrit code review instances.
"""

from typing import Any

from .base import BaseProvider


class GerritProvider(BaseProvider):
    """Provider for Gerrit repositories."""

    name = "gerrit"
    domains = ["gerrit"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for Gerrit API."""
        if self.api_token:
            return {"Authorization": f"Bearer {self.api_token}"}
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build Gerrit API URL."""
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/projects/{owner}%2F{repo_name}"
        return f"https://{domain}/projects/{owner}%2F{repo_name}"

    def parse_repo_response(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """Parse Gerrit REST API response."""
        return {
            "description": api_data.get("description", ""),
            "html_url": (
                api_data.get("web_links", [{}])[0].get("url", "")
                if api_data.get("web_links")
                else ""
            ),
            "default_branch": api_data.get("branches", {}).get("HEAD", "master"),
        }
