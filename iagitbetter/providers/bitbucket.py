"""
Bitbucket provider implementation.
Handles bitbucket.org repositories.
"""

import base64
from typing import Any

import requests

from .base import BaseProvider


class BitbucketProvider(BaseProvider):
    """Provider for Bitbucket repositories."""

    name = "bitbucket"
    domains = ["bitbucket.org", "bitbucket"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for Bitbucket API."""
        # App Passwords: requires username + app password via basic auth
        if self.api_username and self.api_token:
            token = base64.b64encode(
                f"{self.api_username}:{self.api_token}".encode("utf-8")
            ).decode("utf-8")
            return {"Authorization": f"Basic {token}"}
        # OAuth 2 access token: Bearer
        if self.api_token:
            return {"Authorization": f"Bearer {self.api_token}"}
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build Bitbucket API URL."""
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/repositories/{owner}/{repo_name}"
        return f"https://api.bitbucket.org/2.0/repositories/{owner}/{repo_name}"

    def parse_repo_response(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """Parse Bitbucket API response."""
        return {
            "description": api_data.get("description", ""),
            "created_at": api_data.get("created_on", ""),
            "updated_at": api_data.get("updated_on", ""),
            "language": api_data.get("language", ""),
            "private": api_data.get("is_private", False),
            "fork": api_data.get("parent") is not None,
            "size": api_data.get("size", 0),
            "has_wiki": api_data.get("has_wiki", False),
            "has_issues": api_data.get("has_issues", False),
            "clone_url": (
                api_data.get("links", {}).get("clone", [{}])[0].get("href", "")
            ),
            "homepage": api_data.get("website", ""),
            "scm": api_data.get("scm", "git"),
            "mainbranch": api_data.get("mainbranch", {}).get("name", "main"),
            "project": (
                api_data.get("project", {}).get("name", "")
                if api_data.get("project")
                else ""
            ),
            "owner_type": api_data.get("owner", {}).get("type", ""),
            "owner_display_name": api_data.get("owner", {}).get("display_name", ""),
            "avatar_url": (
                api_data.get("owner", {})
                .get("links", {})
                .get("avatar", {})
                .get("href", "")
                if api_data.get("owner")
                else ""
            ),
        }

    def fetch_user_repos(self, username: str, domain: str) -> list[dict[str, Any]]:
        """Fetch all repositories from Bitbucket user/workspace."""
        repos = []
        url = f"https://api.bitbucket.org/2.0/repositories/{username}"
        headers = self.get_auth_headers()

        while url:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                for repo in data.get("values", []):
                    clone_url = None
                    for link in repo.get("links", {}).get("clone", []):
                        if link.get("name") == "https":
                            clone_url = link.get("href")
                            break

                    repos.append(
                        {
                            "name": repo["name"],
                            "full_name": repo["full_name"],
                            "clone_url": clone_url or "",
                            "html_url": (
                                repo.get("links", {}).get("html", {}).get("href", "")
                            ),
                            "description": repo.get("description", ""),
                            "fork": repo.get("parent") is not None,
                            "archived": False,  # Bitbucket doesn't have archived status
                            "private": repo.get("is_private", False),
                        }
                    )

                # Get next page
                url = data.get("next")
            else:
                break

        return repos
