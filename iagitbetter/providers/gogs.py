"""
Gogs provider implementation.
Handles Gogs instances including Notabug.org.
"""

from typing import Any

import requests

from .base import BaseProvider


class GogsProvider(BaseProvider):
    """Provider for Gogs repositories (including Notabug.org)."""

    name = "gogs"
    domains = ["gogs", "notabug.org"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for Gogs API."""
        if self.api_token:
            return {"Authorization": f"token {self.api_token}"}
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build Gogs API URL."""
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/repos/{owner}/{repo_name}"
        return f"https://{domain}/api/v1/repos/{owner}/{repo_name}"

    def parse_repo_response(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """Parse Gogs API response."""
        return {
            "description": api_data.get("description", ""),
            "created_at": api_data.get("created_at", ""),
            "updated_at": api_data.get("updated_at", ""),
            "stars": api_data.get("stars_count", 0),
            "forks": api_data.get("forks_count", 0),
            "watchers": api_data.get("watchers_count", 0),
            "open_issues": api_data.get("open_issues_count", 0),
            "homepage": api_data.get("website", ""),
            "default_branch": api_data.get("default_branch", "master"),
            "private": api_data.get("private", False),
            "fork": api_data.get("fork", False),
            "size": api_data.get("size", 0),
            "clone_url": api_data.get("clone_url", ""),
            "ssh_url": api_data.get("ssh_url", ""),
            "html_url": api_data.get("html_url", ""),
            "avatar_url": (
                api_data.get("owner", {}).get("avatar_url", "")
                if api_data.get("owner")
                else ""
            ),
        }

    def fetch_user_repos(self, username: str, domain: str) -> list[dict[str, Any]]:
        """Fetch all repositories from Gogs/Notabug user."""
        repos = []
        page = 1
        per_page = 50
        headers = self.get_auth_headers()

        base_url = self.api_url if self.api_url else f"https://{domain}/api/v1"

        while True:
            url = f"{base_url}/users/{username}/repos?limit={per_page}&page={page}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                page_repos = response.json()
                if not page_repos:
                    break

                for repo in page_repos:
                    repos.append(
                        {
                            "name": repo["name"],
                            "full_name": repo["full_name"],
                            "clone_url": repo["clone_url"],
                            "html_url": repo["html_url"],
                            "description": repo.get("description", ""),
                            "fork": repo.get("fork", False),
                            "archived": False,
                            "private": repo.get("private", False),
                        }
                    )

                if len(page_repos) < per_page:
                    break
                page += 1
            else:
                self._log(
                    f"   Error fetching Gogs repos (status {response.status_code})"
                )
                break

        return repos

    def fetch_releases(
        self, owner: str, repo_name: str, domain: str
    ) -> list[dict[str, Any]]:
        """Fetch releases from Gogs/Notabug API."""
        releases = []
        page = 1
        per_page = 50
        headers = self.get_auth_headers()

        while True:
            url = f"https://{domain}/api/v1/repos/{owner}/{repo_name}/releases?per_page={per_page}&page={page}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                break

            api_releases = response.json()
            if not api_releases:
                break

            for release in api_releases:
                release_data = {
                    "id": release.get("id"),
                    "tag_name": release.get("tag_name"),
                    "name": release.get("name", release.get("tag_name")),
                    "body": release.get("body", ""),
                    "draft": release.get("draft", False),
                    "prerelease": release.get("prerelease", False),
                    "published_at": release.get("created_at"),
                    "zipball_url": release.get("zipball_url"),
                    "tarball_url": release.get("tarball_url"),
                    "assets": [],
                }

                for asset in release.get("assets", []):
                    release_data["assets"].append(
                        {
                            "name": asset.get("name"),
                            "download_url": asset.get("browser_download_url"),
                            "size": asset.get("size"),
                        }
                    )

                releases.append(release_data)

            if len(api_releases) < per_page:
                break
            page += 1

        return releases
