"""
GitHub provider implementation.
Handles both github.com and GitHub Gists.
"""

from typing import Any

import requests

from .base import BaseProvider


class GitHubProvider(BaseProvider):
    """Provider for GitHub repositories."""

    name = "github"
    domains = ["github.com"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for GitHub API."""
        if self.api_token:
            return {"Authorization": f"token {self.api_token}"}
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build GitHub API URL."""
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/repos/{owner}/{repo_name}"
        return f"https://api.github.com/repos/{owner}/{repo_name}"

    def parse_repo_response(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """Parse GitHub API response."""
        return {
            "description": api_data.get("description", ""),
            "created_at": api_data.get("created_at", ""),
            "updated_at": api_data.get("updated_at", ""),
            "pushed_at": api_data.get("pushed_at", ""),
            "language": api_data.get("language", ""),
            "stars": api_data.get("stargazers_count", 0),
            "forks": api_data.get("forks_count", 0),
            "watchers": api_data.get("watchers_count", 0),
            "subscribers": api_data.get("subscribers_count", 0),
            "open_issues": api_data.get("open_issues_count", 0),
            "homepage": api_data.get("homepage", ""),
            "topics": api_data.get("topics", []),
            "license": (
                api_data.get("license", {}).get("name", "")
                if api_data.get("license")
                else ""
            ),
            "default_branch": api_data.get("default_branch", "main"),
            "has_wiki": api_data.get("has_wiki", False),
            "has_pages": api_data.get("has_pages", False),
            "has_projects": api_data.get("has_projects", False),
            "has_issues": api_data.get("has_issues", False),
            "archived": api_data.get("archived", False),
            "disabled": api_data.get("disabled", False),
            "private": api_data.get("private", False),
            "fork": api_data.get("fork", False),
            "size": api_data.get("size", 0),
            "network_count": api_data.get("network_count", 0),
            "clone_url": api_data.get("clone_url", ""),
            "ssh_url": api_data.get("ssh_url", ""),
            "svn_url": api_data.get("svn_url", ""),
            "mirror_url": api_data.get("mirror_url", ""),
            "visibility": api_data.get("visibility", "public"),
            "avatar_url": (
                api_data.get("owner", {}).get("avatar_url", "")
                if api_data.get("owner")
                else ""
            ),
        }

    def fetch_user_repos(self, username: str, domain: str) -> list[dict[str, Any]]:
        """Fetch all repositories from GitHub user/org."""
        repos = []
        page = 1
        per_page = 100
        headers = self.get_auth_headers()

        # Detect whether the name is a User or an Organization
        who_url = f"https://api.github.com/users/{username}"
        entity_type = "User"
        try:
            who_resp = requests.get(who_url, headers=headers, timeout=10)
            if who_resp.status_code == 200:
                entity_type = who_resp.json().get("type", "User")
        except Exception:
            pass

        # Choose the correct listing endpoint
        base_list_path = (
            f"https://api.github.com/orgs/{username}/repos"
            if entity_type == "Organization"
            else f"https://api.github.com/users/{username}/repos"
        )

        while True:
            url = f"{base_list_path}?per_page={per_page}&page={page}&sort=updated"
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
                            "archived": repo.get("archived", False),
                            "private": repo.get("private", False),
                        }
                    )

                if len(page_repos) < per_page:
                    break
                page += 1
            else:
                self._log(
                    f"   Error fetching GitHub repos (status {response.status_code})"
                )
                break

        return repos

    def fetch_releases(
        self, owner: str, repo_name: str, domain: str
    ) -> list[dict[str, Any]]:
        """Fetch releases from GitHub API."""
        releases = []
        page = 1
        per_page = 100
        headers = self.get_auth_headers()

        while True:
            url = f"https://api.github.com/repos/{owner}/{repo_name}/releases?per_page={per_page}&page={page}"
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
                    "published_at": release.get("published_at"),
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
                            "content_type": asset.get("content_type"),
                        }
                    )

                releases.append(release_data)

            if len(api_releases) < per_page:
                break
            page += 1

        return releases


class GistProvider(BaseProvider):
    """Provider for GitHub Gists."""

    name = "gist"
    domains = ["gist.github.com"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for GitHub API."""
        if self.api_token:
            return {"Authorization": f"token {self.api_token}"}
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build Gist API URL."""
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/gists/{repo_name}"
        return f"https://api.github.com/gists/{repo_name}"

    def parse_repo_response(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """Parse GitHub Gist API response."""
        description = api_data.get("description", "")
        files = api_data.get("files", {})
        file_list = list(files.keys()) if files else []

        languages = set()
        for file_info in files.values():
            if file_info.get("language"):
                languages.add(file_info.get("language"))
        primary_language = ", ".join(sorted(languages)) if languages else ""

        return {
            "description": description,
            "created_at": api_data.get("created_at", ""),
            "updated_at": api_data.get("updated_at", ""),
            "pushed_at": api_data.get("updated_at", ""),
            "language": primary_language,
            "stars": 0,
            "forks": len(api_data.get("forks", [])) if api_data.get("forks") else 0,
            "watchers": 0,
            "subscribers": 0,
            "open_issues": 0,
            "homepage": "",
            "topics": [],
            "license": "",
            "default_branch": "master",
            "has_wiki": False,
            "has_pages": False,
            "has_projects": False,
            "has_issues": False,
            "archived": False,
            "disabled": False,
            "private": not api_data.get("public", True),
            "fork": False,
            "size": sum(f.get("size", 0) for f in files.values()) if files else 0,
            "network_count": 0,
            "clone_url": api_data.get("git_pull_url", ""),
            "ssh_url": api_data.get("git_push_url", ""),
            "html_url": api_data.get("html_url", ""),
            "visibility": "public" if api_data.get("public", True) else "private",
            "avatar_url": (
                api_data.get("owner", {}).get("avatar_url", "")
                if api_data.get("owner")
                else ""
            ),
            "gist_files": file_list,
            "gist_comments": api_data.get("comments", 0),
        }

    def fetch_comments(self, gist_id: str) -> list[dict[str, Any]]:
        """Fetch comments from a GitHub Gist."""
        comments = []
        headers = self.get_auth_headers()
        headers["Accept"] = "application/vnd.github.v3+json"

        try:
            url = f"https://api.github.com/gists/{gist_id}/comments"
            self._log("   Fetching comments from gist...")

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                api_comments = response.json()

                for comment in api_comments:
                    comment_data = {
                        "id": comment.get("id"),
                        "user": comment.get("user", {}).get("login", ""),
                        "body": comment.get("body", ""),
                        "created_at": comment.get("created_at", ""),
                        "updated_at": comment.get("updated_at", ""),
                        "author_association": comment.get("author_association", ""),
                    }
                    comments.append(comment_data)

                if len(comments) > 0:
                    self._log(f"   Fetched {len(comments)} comment(s)")
                else:
                    self._log("   No comments found for this gist")
            elif response.status_code == 404:
                self._log("   Gist not found or comments not accessible")
            elif response.status_code == 403:
                self._log(
                    "   Access denied - API token may be required for private gists"
                )
            else:
                self._log(
                    f"   Could not fetch comments (status {response.status_code})"
                )

        except Exception as e:
            self._log(f"   Could not fetch comments: {e}")

        return comments
