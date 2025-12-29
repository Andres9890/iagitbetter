"""
Gerrit provider implementation.
Handles Gerrit code review instances.
"""

import base64
from typing import Any

from .base import BaseProvider


class GerritProvider(BaseProvider):
    """Provider for Gerrit repositories."""

    name = "gerrit"
    domains = ["gerrit"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for Gerrit API."""
        if self.api_username and self.api_token:
            credentials = f"{self.api_username}:{self.api_token}"
            token = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            return {"Authorization": f"Basic {token}"}
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build Gerrit API URL."""
        project_path = f"{owner}%2F{repo_name}"

        # Determine if authenticated (need /a/ prefix)
        is_authenticated = bool(self.api_username and self.api_token)
        auth_prefix = "/a" if is_authenticated else ""

        if self.api_url:
            base = self.api_url.rstrip("/")
            return f"{base}{auth_prefix}/projects/{project_path}"
        return f"https://{domain}{auth_prefix}/projects/{project_path}"

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
