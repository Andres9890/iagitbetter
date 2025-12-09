"""
GitLab provider implementation.
Handles gitlab.com and self-hosted GitLab instances.
"""

from typing import Any

import requests

from .base import BaseProvider


class GitLabProvider(BaseProvider):
    """Provider for GitLab repositories."""

    name = "gitlab"
    domains = ["gitlab.com", "gitlab"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for GitLab API."""
        if self.api_token:
            return {"PRIVATE-TOKEN": self.api_token}
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build GitLab API URL."""
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/projects/{owner}%2F{repo_name}"
        return f"https://{domain}/api/v4/projects/{owner}%2F{repo_name}"

    def parse_repo_response(
        self, api_data: dict[str, Any], domain: str = "gitlab.com"
    ) -> dict[str, Any]:
        """Parse GitLab API response."""
        # Handle GitLab avatar URL - prefer project-level, then namespace
        avatar_url = ""
        if api_data.get("avatar_url"):
            avatar_url = api_data["avatar_url"]
        elif api_data.get("namespace", {}).get("avatar_url"):
            avatar_url = api_data["namespace"]["avatar_url"]

        # Handle relative URLs by prefixing with instance URL
        if avatar_url and not avatar_url.startswith(("http://", "https://")):
            instance_url = f"https://{domain}"
            avatar_url = (
                f"{instance_url}{avatar_url}"
                if avatar_url.startswith("/")
                else f"{instance_url}/{avatar_url}"
            )

        return {
            "description": api_data.get("description", ""),
            "created_at": api_data.get("created_at", ""),
            "updated_at": api_data.get("updated_at", ""),
            "pushed_at": api_data.get("last_activity_at", ""),
            "stars": api_data.get("star_count", 0),
            "forks": api_data.get("forks_count", 0),
            "topics": api_data.get("topics", []),
            "default_branch": api_data.get("default_branch", "main"),
            "archived": api_data.get("archived", False),
            "private": api_data.get("visibility", "public") != "public",
            "fork": api_data.get("forked_from_project") is not None,
            "open_issues": api_data.get("open_issues_count", 0),
            "has_wiki": api_data.get("wiki_enabled", False),
            "has_pages": api_data.get("pages_enabled", False),
            "has_issues": api_data.get("issues_enabled", False),
            "clone_url": api_data.get("http_url_to_repo", ""),
            "ssh_url": api_data.get("ssh_url_to_repo", ""),
            "web_url": api_data.get("web_url", ""),
            "namespace": api_data.get("namespace", {}).get("name", ""),
            "path_with_namespace": api_data.get("path_with_namespace", ""),
            "visibility": api_data.get("visibility", "public"),
            "merge_requests_enabled": api_data.get("merge_requests_enabled", False),
            "ci_enabled": api_data.get("builds_enabled", False),
            "shared_runners_enabled": api_data.get("shared_runners_enabled", False),
            "avatar_url": avatar_url,
            "project_id": (
                str(api_data.get("id", "")) if api_data.get("id") is not None else ""
            ),
        }

    def fetch_user_repos(self, username: str, domain: str) -> list[dict[str, Any]]:
        """Fetch all repositories from GitLab user/org."""
        repos = []
        page = 1
        per_page = 100
        headers = self.get_auth_headers()

        base_url = self.api_url if self.api_url else f"https://{domain}/api/v4"

        # Get user info to find user ID
        user_url = f"{base_url}/users?username={username}"
        response = requests.get(user_url, headers=headers, timeout=10)

        if response.status_code != 200 or not response.json():
            self._log(f"   Could not find GitLab user: {username}")
            return []

        user_id = response.json()[0]["id"]

        # Fetch user's projects
        while True:
            url = f"{base_url}/users/{user_id}/projects?per_page={per_page}&page={page}&order_by=updated_at"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                page_repos = response.json()
                if not page_repos:
                    break

                for repo in page_repos:
                    repos.append(
                        {
                            "name": repo["name"],
                            "full_name": repo["path_with_namespace"],
                            "clone_url": repo["http_url_to_repo"],
                            "html_url": repo["web_url"],
                            "description": repo.get("description", ""),
                            "fork": repo.get("forked_from_project") is not None,
                            "archived": repo.get("archived", False),
                            "private": repo.get("visibility") != "public",
                        }
                    )

                if len(page_repos) < per_page:
                    break
                page += 1
            else:
                break

        return repos

    def fetch_releases(
        self,
        owner: str,
        repo_name: str,
        domain: str,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch releases from GitLab API."""
        releases = []
        if not project_id:
            return releases

        page = 1
        per_page = 100
        headers = self.get_auth_headers()

        while True:
            url = f"https://{domain}/api/v4/projects/{project_id}/releases?per_page={per_page}&page={page}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                break

            api_releases = response.json()
            if not api_releases:
                break

            for release in api_releases:
                tag_name = release.get("tag_name")
                release_data = {
                    "tag_name": tag_name,
                    "name": release.get("name", tag_name),
                    "description": release.get("description", ""),
                    "released_at": release.get("released_at"),
                    "zipball_url": f"https://{domain}/{owner}/{repo_name}/-/archive/{tag_name}/{repo_name}-{tag_name}.zip",
                    "tarball_url": f"https://{domain}/{owner}/{repo_name}/-/archive/{tag_name}/{repo_name}-{tag_name}.tar.gz",
                    "assets": [],
                }

                for link in release.get("assets", {}).get("links", []):
                    release_data["assets"].append(
                        {
                            "name": link.get("name"),
                            "download_url": link.get("url"),
                            "link_type": link.get("link_type"),
                        }
                    )

                releases.append(release_data)

            if len(api_releases) < per_page:
                break
            page += 1

        return releases
