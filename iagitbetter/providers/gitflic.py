"""
GitFlic provider implementation.
Handles gitflic.ru and self-hosted GitFlic instances.
"""

from typing import Any

import requests

from .base import BaseProvider


class GitFlicProvider(BaseProvider):
    """Provider for GitFlic repositories."""

    name = "gitflic"
    domains = ["gitflic.ru"]

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for GitFlic API."""
        if self.api_token:
            return {"Authorization": f"token {self.api_token}"}
        return {}

    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build GitFlic API URL."""
        if self.api_url:
            return f"{self.api_url.rstrip('/')}/project/{owner}/{repo_name}"
        return f"https://api.gitflic.ru/project/{owner}/{repo_name}"

    def parse_repo_response(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """Parse GitFlic API response."""
        return {
            "description": api_data.get("description") or "",
            "created_at": "",
            "updated_at": "",
            "pushed_at": "",
            "language": api_data.get("language") or "",
            "stars": 0,
            "forks": 0,
            "watchers": 0,
            "subscribers": 0,
            "open_issues": 0,
            "homepage": api_data.get("siteUrl") or "",
            "topics": api_data.get("topics", []),
            "license": "",
            "default_branch": api_data.get("defaultBranch", "master"),
            "has_wiki": False,
            "has_pages": False,
            "has_projects": False,
            "has_issues": False,
            "archived": False,
            "disabled": False,
            "private": api_data.get("private", False),
            "fork": bool(api_data.get("forkedFromId")),
            "size": 0,
            "network_count": 0,
            "clone_url": api_data.get("httpTransportUrl", ""),
            "ssh_url": api_data.get("sshTransportUrl", ""),
            "svn_url": "",
            "mirror_url": api_data.get("mirrorUrl", ""),
            "visibility": "private" if api_data.get("private") else "public",
            "avatar_url": "",
        }

    def fetch_user_repos(self, username: str, domain: str) -> list[dict[str, Any]]:
        """Fetch all repositories from GitFlic user/organization."""
        repos = []
        page = 0
        size = 100
        headers = self.get_auth_headers()

        base_url = self.api_url if self.api_url else "https://api.gitflic.ru"

        while True:
            url = f"{base_url.rstrip('/')}/user/{username}/projects?size={size}&page={page}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                embedded = data.get("_embedded", {})
                project_list = embedded.get("projectList", [])

                if not project_list:
                    break

                for repo in project_list:
                    repos.append(
                        {
                            "name": repo.get("alias", ""),
                            "full_name": f"{repo.get('ownerAlias', username)}/{repo.get('alias', '')}",
                            "clone_url": repo.get("httpTransportUrl", ""),
                            "html_url": f"https://{domain}/{repo.get('ownerAlias', username)}/{repo.get('alias', '')}",
                            "description": repo.get("description", ""),
                            "fork": bool(repo.get("forkedFromId")),
                            "archived": False,
                            "private": repo.get("private", False),
                        }
                    )

                page_info = data.get("page", {})
                total_pages = page_info.get("totalPages", 1)

                if page + 1 >= total_pages:
                    break
                page += 1
            else:
                self._log(
                    f"   Error fetching GitFlic repos (status {response.status_code})"
                )
                break

        return repos

    def fetch_releases(
        self, owner: str, repo_name: str, domain: str
    ) -> list[dict[str, Any]]:
        """Fetch releases from GitFlic API."""
        releases = []
        page = 0
        size = 100
        headers = self.get_auth_headers()

        base_url = self.api_url if self.api_url else "https://api.gitflic.ru"

        while True:
            url = f"{base_url.rstrip('/')}/project/{owner}/{repo_name}/release?size={size}&page={page}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                break

            data = response.json()
            embedded = data.get("_embedded", {})
            api_releases = embedded.get("releaseTagModelList", [])

            if not api_releases:
                break

            for release in api_releases:
                release_data = {
                    "id": release.get("id"),
                    "tag_name": release.get("tagName"),
                    "name": release.get("title", release.get("tagName")),
                    "body": release.get("description", ""),
                    "draft": False,
                    "prerelease": release.get("preRelease", False),
                    "published_at": release.get("createdAt"),
                    "zipball_url": "",
                    "tarball_url": "",
                    "assets": [],
                }

                for asset in release.get("attachmentFiles", []):
                    release_data["assets"].append(
                        {
                            "name": asset.get("name"),
                            "download_url": asset.get("link"),
                            "size": asset.get("size"),
                            "content_type": "",
                        }
                    )

                releases.append(release_data)

            page_info = data.get("page", {})
            total_pages = page_info.get("totalPages", 1)

            if page + 1 >= total_pages:
                break
            page += 1

        return releases
