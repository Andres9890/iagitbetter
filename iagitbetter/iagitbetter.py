#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iagitbetter - Archive any git repository to the Internet Archive
Improved version with support for all git providers and full file preservation
"""

from . import __version__

__author__ = "Andres99"
__license__ = "GPL-3.0"

import argparse
import base64
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime
from urllib.parse import urlparse

import git
import internetarchive
import requests
from internetarchive.config import parse_config_file
from markdown2 import markdown_path


def get_latest_pypi_version(package_name="iagitbetter"):
    """
    Request PyPI for the latest version
    Returns the version string, or None if it cannot be determined
    """
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.load(response)
            return data["info"]["version"]
    except Exception:
        return None


def check_for_updates(current_version, verbose=True):
    """
    Check if a newer version is available on PyPI
    """
    if not verbose:
        return  # Skip version check in quiet mode

    try:
        # Remove 'v' prefix if present for comparison
        current_clean = current_version.lstrip("v")
        latest_version = get_latest_pypi_version("iagitbetter")

        if latest_version and latest_version != current_clean:
            # Simple version comparison (works for semantic versioning)
            current_parts = [int(x) for x in current_clean.split(".")]
            latest_parts = [int(x) for x in latest_version.split(".")]

            # Pad shorter version with zeros
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))

            if latest_parts > current_parts:
                print(
                    f"Update available: {latest_version} (current is v{current_version})"
                )
                print("   upgrade with: pip install --upgrade iagitbetter")
                print()
    except Exception:
        # Silently ignore any errors in version checking
        pass


class GitArchiver:
    def __init__(
        self,
        verbose=True,
        ia_config_path=None,
        git_provider_type=None,
        api_url=None,
        api_token=None,
        api_username=None,  # <-- added for Bitbucket App Passwords
    ):
        self.temp_dir = None
        self.repo_data = {}
        self.verbose = verbose
        self.ia_config_path = ia_config_path
        self.git_provider_type = git_provider_type  # e.g., 'github', 'gitlab', 'gitea'
        self.api_url = api_url  # Custom API URL for self-hosted instances
        self.api_token = api_token  # API token for authentication
        self.api_username = api_username  # <-- store username for Bitbucket Basic auth

    def is_profile_url(self, url):
        """Determine if URL is a profile/organization page or a specific repository"""
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]

        # Profile URLs typically have only 1 path component (username/org)
        # Repository URLs have 2 or more (username/repo, or username/group/repo)
        return len(path_parts) == 1

    def fetch_user_repositories(self, username):
        """Fetch all repositories for a given user/organization"""
        domain = self.repo_data.get("domain", "")
        site = (self.git_provider_type or self.repo_data.get("git_site") or "").lower()

        repositories = []

        try:
            if site == "github" or domain == "github.com":
                repositories = self._fetch_github_user_repos(username)
            elif site == "gitlab" or domain == "gitlab.com":
                repositories = self._fetch_gitlab_user_repos(username)
            elif (
                site in ["gitea", "codeberg"]
                or "gitea" in domain
                or domain == "codeberg.org"
            ):
                repositories = self._fetch_gitea_user_repos(username)
            elif site == "bitbucket" or domain == "bitbucket.org":
                repositories = self._fetch_bitbucket_user_repos(username)
            elif site == "gitee" or domain == "gitee.com":
                repositories = self._fetch_gitee_user_repos(username)
            elif site == "gogs" or domain == "notabug.org":
                repositories = self._fetch_gogs_user_repos(username)
            else:
                if self.verbose:
                    print(f"   Profile archiving not supported for {site or domain}")
                return []

            if self.verbose:
                print(f"   Found {len(repositories)} repositories for {username}")

            return repositories

        except Exception as e:
            if self.verbose:
                print(f"   Error fetching repositories: {e}")
            return []

    def _fetch_github_user_repos(self, username):
        """Fetch all repositories from GitHub user/org (supports org repos)"""
        repos = []
        page = 1
        per_page = 100

        # Detect whether the name is a User or an Organization
        who_url = f"https://api.github.com/users/{username}"
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"

        entity_type = "User"
        try:
            who_resp = requests.get(who_url, headers=headers, timeout=10)
            if who_resp.status_code == 200:
                entity_type = who_resp.json().get("type", "User")
        except Exception:
            pass

        # Choose the correct listing endpoint
        # Users: /users/{username}/repos
        # Orgs:  /orgs/{org}/repos
        base_list_path = (
            f"https://api.github.com/orgs/{username}/repos"
            if entity_type == "Organization"
            else f"https://api.github.com/users/{username}/repos"
        )

        while True:
            url = f"{base_list_path}?per_page={per_page}&page={page}&sort=updated"
            list_headers = {}
            if self.api_token:
                list_headers["Authorization"] = f"token {self.api_token}"

            response = requests.get(url, headers=list_headers, timeout=10)
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
                if self.verbose:
                    print(
                        f"   Error fetching GitHub repos (status {response.status_code})"
                    )
                break

        return repos

    def _fetch_gitlab_user_repos(self, username):
        """Fetch all repositories from GitLab user/org"""
        repos = []
        page = 1
        per_page = 100

        # First, try to get user ID
        base_url = (
            self.api_url
            if self.api_url
            else f"https://{self.repo_data.get('domain', 'gitlab.com')}/api/v4"
        )
        headers = {}
        if self.api_token:
            headers["PRIVATE-TOKEN"] = self.api_token

        # Get user info to find user ID
        user_url = f"{base_url}/users?username={username}"
        response = requests.get(user_url, headers=headers, timeout=10)

        if response.status_code != 200 or not response.json():
            if self.verbose:
                print(f"   Could not find GitLab user: {username}")
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

    def _fetch_gitea_user_repos(self, username):
        """Fetch all repositories from Gitea/Forgejo/Codeberg user/org"""
        repos = []
        page = 1
        per_page = 50

        base_url = (
            self.api_url
            if self.api_url
            else f"https://{self.repo_data.get('domain', 'gitea.com')}/api/v1"
        )
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"

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
                            "archived": repo.get("archived", False),
                            "private": repo.get("private", False),
                        }
                    )

                if len(page_repos) < per_page:
                    break
                page += 1
            else:
                break

        return repos

    def _bitbucket_auth_headers(self):
        """Build Bitbucket auth headers supporting App Passwords (Basic) or OAuth (Bearer)."""
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

    def _fetch_bitbucket_user_repos(self, username):
        """Fetch all repositories from Bitbucket user/workspace"""
        repos = []
        url = f"https://api.bitbucket.org/2.0/repositories/{username}"

        headers = self._bitbucket_auth_headers()

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
                            "html_url": repo.get("links", {})
                            .get("html", {})
                            .get("href", ""),
                            "description": repo.get("description", ""),
                            "fork": repo.get("parent") is not None,
                            "archived": False,  # Bitbucket doesn't have archived status in API
                            "private": repo.get("is_private", False),
                        }
                    )

                # Get next page
                url = data.get("next")
            else:
                break

        return repos

    def _fetch_gitee_user_repos(self, username):
        """Fetch all repositories from Gitee user"""
        repos = []
        page = 1
        per_page = 100

        base_url = "https://gitee.com/api/v5"
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"

        while True:
            url = f"{base_url}/users/{username}/repos?per_page={per_page}&page={page}&sort=updated"
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
                if self.verbose:
                    print(
                        f"   Error fetching Gitee repos (status {response.status_code})"
                    )
                break

        return repos

    def _fetch_gogs_user_repos(self, username):
        """Fetch all repositories from Gogs/Notabug user"""
        repos = []
        page = 1
        per_page = 50

        base_url = (
            self.api_url
            if self.api_url
            else f"https://{self.repo_data.get('domain', 'notabug.org')}/api/v1"
        )
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"

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
                if self.verbose:
                    print(
                        f"   Error fetching Gogs repos (status {response.status_code})"
                    )
                break

        return repos

    def extract_repo_info(self, repo_url):
        """Extract repository information from any git URL"""
        # Parse the URL
        parsed = urlparse(repo_url)
        domain = parsed.netloc.lower()

        # Remove www. prefix if present
        if domain.startswith("www."):
            domain = domain[4:]

        # Detect git provider type
        if not self.git_provider_type:
            # Auto-detect based on domain
            if domain == "gist.github.com":
                git_site = "gist"
            elif "github" in domain:
                git_site = "github"
            elif "gitlab" in domain:
                git_site = "gitlab"
            elif "bitbucket" in domain:
                git_site = "bitbucket"
            elif "codeberg" in domain:
                git_site = "codeberg"
            elif "gitea" in domain:
                git_site = "gitea"
            elif "gitee" in domain or domain == "gitee.com":
                git_site = "gitee"
            elif "gogs" in domain or domain == "notabug.org":
                git_site = "gogs"
            elif "sourceforge" in domain:
                git_site = "sourceforge"
            elif "launchpad" in domain:
                git_site = "launchpad"
            elif "gerrit" in domain:
                git_site = "gerrit"
            else:
                # For unknown/self-hosted, use domain name or 'git'
                git_site = domain.split(".")[0] if "." in domain else "git"
        else:
            git_site = self.git_provider_type

        # Extract path components
        path_parts = parsed.path.strip("/").split("/")

        # Handle different URL formats
        if git_site == "gist":
            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo_name = path_parts[1].removesuffix(".git")
            elif len(path_parts) == 1:
                owner = "unknown"
                repo_name = path_parts[0].removesuffix(".git")
            else:
                owner = "unknown"
                repo_name = "repository"
        elif len(path_parts) >= 2:
            owner = path_parts[0]
            repo_name = path_parts[1].removesuffix(".git")
        else:
            # Fallback for unusual URLs
            owner = "unknown"
            repo_name = (
                path_parts[0].replace(".git", "") if path_parts else "repository"
            )

        self.repo_data = {
            "url": repo_url,
            "domain": domain,
            "git_site": git_site,
            "owner": owner,
            "repo_name": repo_name,
            "full_name": f"{owner}/{repo_name}",
            "releases": [],
            "downloaded_releases": 0,
        }

        # Try to fetch additional metadata from API if available
        self._fetch_api_metadata()

        return self.repo_data

    def _build_api_url(self):
        """Build API URL for self-hosted or public instances"""
        owner = self.repo_data.get("owner", "")
        repo_name = self.repo_data.get("repo_name", "")
        domain = self.repo_data.get("domain", "")
        site = (self.git_provider_type or self.repo_data.get("git_site") or "").lower()

        # If custom API URL is provided, treat it as the base API URL for that provider
        if self.api_url:
            base = self.api_url.rstrip("/")
            if site == "gist":
                return f"{base}/gists/{repo_name}"
            elif site == "github":
                return f"{base}/repos/{owner}/{repo_name}"
            elif site == "gitlab":
                # GitLab projects use URL-encoded path
                return f"{base}/projects/{owner}%2F{repo_name}"
            elif site in ("gitea", "codeberg", "gogs") or "gitea" in domain:
                return f"{base}/repos/{owner}/{repo_name}"
            elif site == "bitbucket":
                return f"{base}/repositories/{owner}/{repo_name}"
            elif site == "gitee":
                return f"{base}/repos/{owner}/{repo_name}"
            elif site == "sourceforge":
                return f"{base}/rest/p/{owner}/{repo_name}"
            elif site == "gerrit":
                return f"{base}/projects/{owner}%2F{repo_name}"
            elif site == "launchpad":
                return f"{base}/{owner}/{repo_name}"
            # Fallback: assume Gitea/Forgejo shape
            return f"{base}/repos/{owner}/{repo_name}"

        # No custom api_url: use known public endpoints
        if site == "gist" or domain == "gist.github.com":
            return f"https://api.github.com/gists/{repo_name}"
        elif site == "github" or domain == "github.com":
            return f"https://api.github.com/repos/{owner}/{repo_name}"
        elif site == "gitlab" or domain == "gitlab.com":
            return f"https://gitlab.com/api/v4/projects/{owner}%2F{repo_name}"
        elif site == "bitbucket" or domain == "bitbucket.org":
            return f"https://api.bitbucket.org/2.0/repositories/{owner}/{repo_name}"
        elif site == "gitee" or domain == "gitee.com":
            return f"https://gitee.com/api/v5/repos/{owner}/{repo_name}"
        elif site == "gogs" or domain == "notabug.org":
            return f"https://{domain}/api/v1/repos/{owner}/{repo_name}"
        elif site == "sourceforge" or domain == "sourceforge.net":
            return f"https://sourceforge.net/rest/p/{owner}/{repo_name}"
        elif site == "gerrit":
            return f"https://{domain}/projects/{owner}%2F{repo_name}"
        elif site == "launchpad" or "launchpad" in domain:
            return f"https://api.launchpad.net/1.0/{owner}/{repo_name}"
        elif (
            site in ["codeberg", "gitea"]
            or "gitea" in domain
            or domain == "codeberg.org"
        ):
            return f"https://{domain}/api/v1/repos/{owner}/{repo_name}"
        return f"https://{domain}/api/v1/repos/{owner}/{repo_name}"

    def _fetch_api_metadata(self):
        """Try to fetch metadata from various git provider APIs"""
        try:
            api_url = self._build_api_url()

            # Prepare headers for authentication
            headers = {}
            site = (
                self.git_provider_type or self.repo_data.get("git_site") or ""
            ).lower()
            if self.api_token:
                if site == "gist":
                    headers["Authorization"] = f"token {self.api_token}"
                elif site == "github":
                    headers["Authorization"] = f"token {self.api_token}"
                elif site == "gitlab":
                    headers["PRIVATE-TOKEN"] = self.api_token
                elif site == "bitbucket":
                    headers.update(self._bitbucket_auth_headers())
                elif site == "gitee":
                    headers["Authorization"] = f"token {self.api_token}"
                elif site == "gogs":
                    headers["Authorization"] = f"token {self.api_token}"
                elif site == "sourceforge":
                    headers["Authorization"] = f"Bearer {self.api_token}"
                elif site == "gerrit":
                    headers["Authorization"] = f"Bearer {self.api_token}"
                elif site == "launchpad":
                    headers["Authorization"] = f"Bearer {self.api_token}"
                else:
                    # Gitea/Forgejo generally accept 'token', some accept Bearer too
                    headers["Authorization"] = f"token {self.api_token}"

            if self.verbose:
                print("   Fetching metadata from API...")

            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                api_data = response.json()
                self._parse_api_response(api_data)
            elif response.status_code == 404:
                if self.verbose:
                    print(
                        "   Note: Repository not found via API (may be private or API not available)"
                    )
            elif response.status_code == 401:
                if self.verbose:
                    print(
                        "   Note: API authentication required. Use --api-token for private repositories"
                    )
            else:
                if self.verbose:
                    print(
                        f"   Note: Could not fetch API metadata (status {response.status_code})"
                    )
        except Exception as e:
            if self.verbose:
                print(f"   Note: Could not fetch API metadata: {e}")

    def _parse_api_response(self, api_data):
        """Parse API response based on the git provider"""
        site = (self.git_provider_type or self.repo_data.get("git_site") or "").lower()

        if site == "gist":
            self._parse_gist_response(api_data)
        elif site == "gitee":
            self._parse_gitee_response(api_data)
        elif site == "gogs":
            self._parse_gogs_response(api_data)
        elif site == "sourceforge":
            self._parse_sourceforge_response(api_data)
        elif site == "gerrit":
            self._parse_gerrit_response(api_data)
        elif site == "launchpad":
            self._parse_launchpad_response(api_data)
        # Detect provider type from response structure if not already known
        elif "stargazers_count" in api_data and "clone_url" in api_data:
            # GitHub-like API
            self._parse_github_response(api_data)
        elif "star_count" in api_data and "path_with_namespace" in api_data:
            # GitLab-like API
            self._parse_gitlab_response(api_data)
        elif "scm" in api_data and api_data.get("scm") in ["git", "hg"]:
            # Bitbucket API
            self._parse_bitbucket_response(api_data)
        elif "stars_count" in api_data:
            # Gitea/Forgejo/Gogs API
            self._parse_gitea_response(api_data)
        else:
            # Try to extract common fields
            self._parse_generic_response(api_data)

    def _parse_github_response(self, api_data):
        """Parse GitHub API response"""
        self.repo_data.update(
            {
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
        )

    def _parse_gist_response(self, api_data):
        """Parse GitHub Gist API response"""
        description = api_data.get("description", "")

        files = api_data.get("files", {})
        file_list = list(files.keys()) if files else []

        languages = set()
        for file_info in files.values():
            if file_info.get("language"):
                languages.add(file_info.get("language"))
        primary_language = ", ".join(sorted(languages)) if languages else ""

        self.repo_data.update(
            {
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
        )

    def _parse_gitlab_response(self, api_data):
        """Parse GitLab API response"""
        # Handle GitLab avatar URL - prefer project-level, then namespace, handle relative URLs
        avatar_url = ""

        # Try project-level avatar first
        if api_data.get("avatar_url"):
            avatar_url = api_data["avatar_url"]
        # Fall back to namespace avatar for group-owned projects
        elif api_data.get("namespace", {}).get("avatar_url"):
            avatar_url = api_data["namespace"]["avatar_url"]

        # Handle relative URLs by prefixing with instance URL
        if avatar_url and not avatar_url.startswith(("http://", "https://")):
            instance_url = f"https://{self.repo_data['domain']}"
            avatar_url = (
                f"{instance_url}{avatar_url}"
                if avatar_url.startswith("/")
                else f"{instance_url}/{avatar_url}"
            )

        self.repo_data.update(
            {
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
                    str(api_data.get("id", ""))
                    if api_data.get("id") is not None
                    else ""
                ),
            }
        )

    def _parse_bitbucket_response(self, api_data):
        """Parse Bitbucket API response"""
        self.repo_data.update(
            {
                "description": api_data.get("description", ""),
                "created_at": api_data.get("created_on", ""),
                "updated_at": api_data.get("updated_on", ""),
                "language": api_data.get("language", ""),
                "private": api_data.get("is_private", False),
                "fork": api_data.get("parent") is not None,
                "size": api_data.get("size", 0),
                "has_wiki": api_data.get("has_wiki", False),
                "has_issues": api_data.get("has_issues", False),
                "clone_url": api_data.get("links", {})
                .get("clone", [{}])[0]
                .get("href", ""),
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
        )

    def _parse_gitea_response(self, api_data):
        """Parse Gitea/Forgejo API response"""
        self.repo_data.update(
            {
                "description": api_data.get("description", ""),
                "created_at": api_data.get("created_at", ""),
                "updated_at": api_data.get("updated_at", ""),
                "language": api_data.get("language", ""),
                "stars": api_data.get("stars_count", 0),
                "forks": api_data.get("forks_count", 0),
                "watchers": api_data.get("watchers_count", 0),
                "open_issues": api_data.get("open_issues_count", 0),
                "homepage": api_data.get("website", ""),
                "default_branch": api_data.get("default_branch", "main"),
                "archived": api_data.get("archived", False),
                "private": api_data.get("private", False),
                "fork": api_data.get("fork", False),
                "size": api_data.get("size", 0),
                "has_wiki": api_data.get("has_wiki", False),
                "has_issues": api_data.get("has_issues", False),
                "has_projects": api_data.get("has_projects", False),
                "has_pull_requests": api_data.get("has_pull_requests", False),
                "clone_url": api_data.get("clone_url", ""),
                "ssh_url": api_data.get("ssh_url", ""),
                "html_url": api_data.get("html_url", ""),
                "mirror": api_data.get("mirror", False),
                "template": api_data.get("template", False),
                "empty": api_data.get("empty", False),
                "permissions": api_data.get("permissions", {}),
                "internal_tracker": api_data.get("internal_tracker", {}),
                "external_tracker": api_data.get("external_tracker", {}),
                "external_wiki": api_data.get("external_wiki", {}),
                "avatar_url": (
                    api_data.get("owner", {}).get("avatar_url", "")
                    if api_data.get("owner")
                    else ""
                ),
            }
        )

    def _parse_generic_response(self, api_data):
        """Parse generic API response for unknown providers"""
        # Extract common fields that might exist
        self.repo_data.update(
            {
                "description": api_data.get("description", ""),
                "default_branch": api_data.get(
                    "default_branch", api_data.get("main_branch", "main")
                ),
                "private": api_data.get("private", api_data.get("is_private", False)),
                "fork": api_data.get("fork", api_data.get("is_fork", False)),
                "archived": api_data.get("archived", False),
            }
        )

    def get_license_url(self, license_name):
        """
        Get the standard URL for a given license name.
        Returns None if the license is not recognized or doesn't have a standard URL.

        This mapping includes Creative Commons licenses and common open source licenses.
        """
        if not license_name:
            return None

        # Normalize license name for comparison (lowercase, remove extra spaces)
        license_lower = license_name.lower().strip()

        # Creative Commons license mappings
        # These map to the deed URLs which are the canonical license URLs
        cc_licenses = {
            # CC0 (Public Domain)
            "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
            "cc0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
            "cc0 1.0 universal": "https://creativecommons.org/publicdomain/zero/1.0/",
            "cc0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
            # CC BY 4.0
            "cc by 4.0": "https://creativecommons.org/licenses/by/4.0/",
            "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
            "creative commons attribution 4.0": "https://creativecommons.org/licenses/by/4.0/",
            "attribution 4.0 international": "https://creativecommons.org/licenses/by/4.0/",
            # CC BY-SA 4.0
            "cc by-sa 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
            "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
            "creative commons attribution-sharealike 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution-sharealike 4.0 international": "https://creativecommons.org/licenses/by-sa/4.0/",
            # CC BY-ND 4.0
            "cc by-nd 4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
            "cc-by-nd-4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
            "creative commons attribution-noderivatives 4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
            "attribution-noderivatives 4.0 international": "https://creativecommons.org/licenses/by-nd/4.0/",
            # CC BY-NC 4.0
            "cc by-nc 4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
            "cc-by-nc-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
            "creative commons attribution-noncommercial 4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
            "attribution-noncommercial 4.0 international": "https://creativecommons.org/licenses/by-nc/4.0/",
            # CC BY-NC-SA 4.0
            "cc by-nc-sa 4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "cc-by-nc-sa-4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "creative commons attribution-noncommercial-sharealike 4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "attribution-noncommercial-sharealike 4.0 international": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            # CC BY-NC-ND 4.0
            "cc by-nc-nd 4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
            "cc-by-nc-nd-4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
            "creative commons attribution-noncommercial-noderivatives 4.0": (
                "https://creativecommons.org/licenses/by-nc-nd/4.0/"
            ),
            "attribution-noncommercial-noderivatives 4.0 international": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        }

        # Open source license mappings
        # These map to opensource.org or the official license URLs
        open_source_licenses = {
            # MIT
            "mit": "https://opensource.org/license/mit",
            "mit license": "https://opensource.org/license/mit",
            # Apache 2.0
            "apache-2.0": "https://opensource.org/license/apache-2-0",
            "apache 2.0": "https://opensource.org/license/apache-2-0",
            "apache license 2.0": "https://opensource.org/license/apache-2-0",
            "apache license, version 2.0": "https://opensource.org/license/apache-2-0",
            # GPL
            "gpl-3.0": "https://www.gnu.org/licenses/gpl-3.0.en.html",
            "gpl-3.0-or-later": "https://www.gnu.org/licenses/gpl-3.0.en.html",
            "gnu gpl v3": "https://www.gnu.org/licenses/gpl-3.0.en.html",
            "gnu general public license v3.0": "https://www.gnu.org/licenses/gpl-3.0.en.html",
            "gpl-2.0": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html",
            "gpl-2.0-or-later": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html",
            "gnu gpl v2": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html",
            "gnu general public license v2.0": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html",
            # LGPL
            "lgpl-3.0": "https://www.gnu.org/licenses/lgpl-3.0.en.html",
            "lgpl-3.0-or-later": "https://www.gnu.org/licenses/lgpl-3.0.en.html",
            "gnu lgpl v3": "https://www.gnu.org/licenses/lgpl-3.0.en.html",
            "gnu lesser general public license v3.0": "https://www.gnu.org/licenses/lgpl-3.0.en.html",
            "lgpl-2.1": "https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html",
            "lgpl-2.1-or-later": "https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html",
            # AGPL
            "agpl-3.0": "https://www.gnu.org/licenses/agpl-3.0.en.html",
            "agpl-3.0-or-later": "https://www.gnu.org/licenses/agpl-3.0.en.html",
            "gnu agpl v3": "https://www.gnu.org/licenses/agpl-3.0.en.html",
            "gnu affero general public license v3.0": "https://www.gnu.org/licenses/agpl-3.0.en.html",
            # BSD
            "bsd-3-clause": "https://opensource.org/license/bsd-3-clause",
            "bsd 3-clause": "https://opensource.org/license/bsd-3-clause",
            'bsd 3-clause "new" or "revised" license': "https://opensource.org/license/bsd-3-clause",
            "bsd-2-clause": "https://opensource.org/license/bsd-2-clause",
            "bsd 2-clause": "https://opensource.org/license/bsd-2-clause",
            'bsd 2-clause "simplified" license': "https://opensource.org/license/bsd-2-clause",
            # Mozilla Public License
            "mpl-2.0": "https://opensource.org/license/mpl-2-0",
            "mozilla public license 2.0": "https://opensource.org/license/mpl-2-0",
            # ISC
            "isc": "https://opensource.org/license/isc-license-txt",
            "isc license": "https://opensource.org/license/isc-license-txt",
            # Unlicense (Public Domain)
            "unlicense": "https://unlicense.org/",
            "the unlicense": "https://unlicense.org/",
            # Additional SPDX aliases and licenses
            "afl-3.0": "https://opensource.org/license/afl-3-0",
            "artistic-2.0": "https://opensource.org/license/artistic-2-0",
            "bsl-1.0": "https://opensource.org/license/bsl-1-0",
            "bsd-3-clause-clear": "https://opensource.org/license/bsd-3-clause-clear",
            "bsd-4-clause": "https://spdx.org/licenses/BSD-4-Clause.html",
            "0bsd": "https://opensource.org/license/0bsd",
            "wtfpl": "https://www.wtfpl.net/",
            "ecl-2.0": "https://opensource.org/license/ecl-2-0",
            "epl-1.0": "https://opensource.org/license/epl-1-0",
            "epl-2.0": "https://opensource.org/license/epl-2-0",
            "eupl-1.1": "https://opensource.org/license/eupl-1-1",
            "lppl-1.3c": "https://opensource.org/license/lppl",
            "ms-pl": "https://opensource.org/license/ms-pl-html",
            "osl-3.0": "https://opensource.org/license/osl-3-0-php",
            "postgresql": "https://opensource.org/license/postgresql",
            "ofl-1.1": "https://opensource.org/license/ofl-1-1",
            "ncsa": "https://opensource.org/license/uoi-ncsa-php",
            "zlib": "https://opensource.org/license/zlib",
        }

        # Check CC licenses first
        if license_lower in cc_licenses:
            return cc_licenses[license_lower]

        # Check open source licenses
        if license_lower in open_source_licenses:
            return open_source_licenses[license_lower]

        # No matching license URL found
        return None

    def _parse_gitee_response(self, api_data):
        """Parse Gitee API response"""
        self.repo_data.update(
            {
                "description": api_data.get("description", ""),
                "created_at": api_data.get("created_at", ""),
                "updated_at": api_data.get("updated_at", ""),
                "pushed_at": api_data.get("pushed_at", ""),
                "language": api_data.get("language", ""),
                "stars": api_data.get("stargazers_count", 0),
                "forks": api_data.get("forks_count", 0),
                "watchers": api_data.get("watchers_count", 0),
                "open_issues": api_data.get("open_issues_count", 0),
                "homepage": api_data.get("homepage", ""),
                "license": (
                    api_data.get("license", {}).get("name", "")
                    if api_data.get("license")
                    else ""
                ),
                "default_branch": api_data.get("default_branch", "master"),
                "has_wiki": api_data.get("has_wiki", False),
                "has_issues": api_data.get("has_issues", False),
                "archived": False,
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
        )

    def _parse_gogs_response(self, api_data):
        """Parse Gogs API response"""
        self.repo_data.update(
            {
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
        )

    def _parse_sourceforge_response(self, api_data):
        """Parse SourceForge Allura API response"""
        self.repo_data.update(
            {
                "description": api_data.get("description", ""),
                "html_url": api_data.get("url", ""),
                "default_branch": "master",
            }
        )

    def _parse_gerrit_response(self, api_data):
        """Parse Gerrit REST API response"""
        self.repo_data.update(
            {
                "description": api_data.get("description", ""),
                "html_url": (
                    api_data.get("web_links", [{}])[0].get("url", "")
                    if api_data.get("web_links")
                    else ""
                ),
                "default_branch": api_data.get("branches", {}).get("HEAD", "master"),
            }
        )

    def _parse_launchpad_response(self, api_data):
        """Parse Launchpad API response"""
        self.repo_data.update(
            {
                "description": api_data.get("description", ""),
                "created_at": api_data.get("date_created", ""),
                "updated_at": api_data.get("date_last_modified", ""),
                "html_url": api_data.get("web_link", ""),
                "default_branch": "master",
            }
        )

    def download_avatar(self, repo_path):
        """Download user avatar if available and save with username as filename"""
        avatar_url = self.repo_data.get("avatar_url", "")
        if not avatar_url:
            if self.verbose:
                print("   No avatar URL available for this user")
            return None

        try:
            if self.verbose:
                print(f"   Downloading user avatar from {self.repo_data['git_site']}")

            # Get the image
            response = requests.get(avatar_url, stream=True, timeout=10)
            response.raise_for_status()

            # Determine file extension from Content-Type or URL
            content_type = response.headers.get("content-type", "").lower()
            if "jpeg" in content_type or "jpg" in content_type:
                ext = ".jpg"
            elif "png" in content_type:
                ext = ".png"
            elif "gif" in content_type:
                ext = ".gif"
            elif "webp" in content_type:
                ext = ".webp"
            else:
                # Try to guess from URL
                if avatar_url.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".gif", ".webp")
                ):
                    ext = "." + avatar_url.split(".")[-1].lower()
                else:
                    ext = ".jpg"  # Default fallback

            # Save with username as filename
            username = self.repo_data["owner"]
            avatar_filename = f"{username}{ext}"
            avatar_path = os.path.join(repo_path, avatar_filename)

            with open(avatar_path, "wb") as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)

            if self.verbose:
                print(f"   Avatar saved as: {avatar_filename}")

            return avatar_filename

        except Exception as e:
            if self.verbose:
                print(f"   Could not download avatar: {e}")
            return None

    def create_repo_info_file(self, repo_path):
        """Create a file with all repository information"""
        info_filename = f"{self.repo_data['repo_name']}.info.json"
        info_path = os.path.join(repo_path, info_filename)

        # Prepare repo info
        repo_info = {}
        for key, value in self.repo_data.items():
            if isinstance(value, datetime):
                repo_info[key] = value.strftime("%Y-%m-%d %H:%M:%S")
            elif (
                isinstance(value, (list, dict, str, int, float, bool)) or value is None
            ):
                # Limit releases in file to latest 5
                if key == "releases" and isinstance(value, list) and len(value) > 5:
                    repo_info[key] = value[:5]
                else:
                    repo_info[key] = value
            else:
                repo_info[key] = str(value)

        # Add archive metadata
        repo_info["archived_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        repo_info["archiver_version"] = __version__

        # Write to file
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(repo_info, f, indent=2, ensure_ascii=False)

        if self.verbose:
            print(f"   Created repository info file: {info_filename}")

        return info_path

    def _fetch_github_releases(self, owner, repo_name):
        """Fetch releases from GitHub API"""
        releases = []
        page = 1
        per_page = 100

        while True:
            url = f"https://api.github.com/repos/{owner}/{repo_name}/releases?per_page={per_page}&page={page}"
            headers = {}
            if self.api_token and (self.repo_data.get("git_site") == "github"):
                headers["Authorization"] = f"token {self.api_token}"

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

    def _fetch_gitlab_releases(self, domain, owner, repo_name):
        """Fetch releases from GitLab API"""
        releases = []
        project_id = self.repo_data.get("project_id")
        if not project_id:
            return releases

        page = 1
        per_page = 100

        while True:
            url = f"https://{domain}/api/v4/projects/{project_id}/releases?per_page={per_page}&page={page}"
            headers = {}
            if self.api_token:
                headers["PRIVATE-TOKEN"] = self.api_token

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

    def _fetch_gitea_releases(self, domain, owner, repo_name):
        """Fetch releases from Gitea/Forgejo/Codeberg API"""
        releases = []
        page = 1
        per_page = 50

        while True:
            url = f"https://{domain}/api/v1/repos/{owner}/{repo_name}/releases?per_page={per_page}&page={page}"
            headers = {}
            if self.api_token:
                headers["Authorization"] = f"token {self.api_token}"

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
                        }
                    )

                releases.append(release_data)

            if len(api_releases) < per_page:
                break
            page += 1

        return releases

    def _fetch_gitee_releases(self, owner, repo_name):
        """Fetch releases from Gitee API"""
        releases = []
        page = 1
        per_page = 100

        while True:
            url = f"https://gitee.com/api/v5/repos/{owner}/{repo_name}/releases?per_page={per_page}&page={page}"
            headers = {}
            if self.api_token:
                headers["Authorization"] = f"token {self.api_token}"

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
                    "prerelease": release.get("prerelease", False),
                    "created_at": release.get("created_at"),
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

    def _fetch_gogs_releases(self, domain, owner, repo_name):
        """Fetch releases from Gogs/Notabug API"""
        releases = []
        page = 1
        per_page = 50

        while True:
            url = f"https://{domain}/api/v1/repos/{owner}/{repo_name}/releases?per_page={per_page}&page={page}"
            headers = {}
            if self.api_token:
                headers["Authorization"] = f"token {self.api_token}"

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

    def fetch_releases(self):
        """Fetch releases from the git provider API with pagination support"""
        domain = self.repo_data["domain"]
        owner = self.repo_data["owner"]
        repo_name = self.repo_data["repo_name"]

        releases = []

        try:
            if domain == "github.com" or self.repo_data["git_site"] == "github":
                releases = self._fetch_github_releases(owner, repo_name)
            elif domain == "gitlab.com" or self.repo_data["git_site"] == "gitlab":
                releases = self._fetch_gitlab_releases(domain, owner, repo_name)
            elif domain in ["codeberg.org", "gitea.com"] or self.repo_data[
                "git_site"
            ] in ["codeberg", "gitea"]:
                releases = self._fetch_gitea_releases(domain, owner, repo_name)
            elif domain == "gitee.com" or self.repo_data["git_site"] == "gitee":
                releases = self._fetch_gitee_releases(owner, repo_name)
            elif self.repo_data["git_site"] == "gogs" or domain == "notabug.org":
                releases = self._fetch_gogs_releases(domain, owner, repo_name)

            self.repo_data["releases"] = releases
            if self.verbose and releases:
                print(f"   Found {len(releases)} releases")
            elif self.verbose:
                print("   No releases found for this repository")

        except Exception as e:
            if self.verbose:
                print(f"   Could not fetch releases: {e}")

        return self.repo_data.get("releases", [])

    def fetch_gist_comments(self):
        """Fetch comments from a GitHub Gist"""
        gist_id = self.repo_data.get("repo_name")
        comments = []

        try:
            if self.repo_data.get("git_site") != "gist":
                return comments

            if not gist_id:
                if self.verbose:
                    print("   No gist ID available for comment fetching")
                return comments

            url = f"https://api.github.com/gists/{gist_id}/comments"
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.api_token:
                headers["Authorization"] = f"token {self.api_token}"

            if self.verbose:
                print("   Fetching comments from gist...")

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

                if self.verbose:
                    if len(comments) > 0:
                        print(f"   Fetched {len(comments)} comment(s)")
                    else:
                        print("   No comments found for this gist")
            elif response.status_code == 404:
                if self.verbose:
                    print("   Gist not found or comments not accessible")
            elif response.status_code == 403:
                if self.verbose:
                    print(
                        "   Access denied - API token may be required for private gists"
                    )
            else:
                if self.verbose:
                    print(
                        f"   Could not fetch comments (status {response.status_code})"
                    )

        except Exception as e:
            if self.verbose:
                print(f"   Could not fetch comments: {e}")

        return comments

    def save_gist_comments(self, repo_path):
        """Save gist comments to a JSON file"""
        try:
            if self.repo_data.get("git_site") != "gist":
                return None

            comments = self.fetch_gist_comments()

            if not comments:
                return None

            gist_id = self.repo_data.get("repo_name")
            comments_filename = f"{gist_id}.comments.json"
            comments_path = os.path.join(repo_path, comments_filename)

            with open(comments_path, "w", encoding="utf-8") as f:
                json.dump(comments, f, indent=2, ensure_ascii=False)

            if self.verbose:
                print(f"   Saved {len(comments)} comment(s) to: {comments_filename}")

            return comments_path

        except Exception as e:
            if self.verbose:
                print(f"   Could not save gist comments: {e}")
            return None

    def download_releases(self, repo_path, all_releases=False):
        """Download releases to the repository directory"""
        if not self.repo_data.get("releases"):
            # Fetch releases if not already done
            self.fetch_releases()

        releases = self.repo_data.get("releases", [])
        if not releases:
            if self.verbose:
                print("   No releases available to download")
            return

        # Determine which releases to download
        if all_releases:
            releases_to_download = releases
        else:
            # Download only the latest release (regardless of prerelease)
            # Filter out drafts only
            non_draft_releases = [r for r in releases if not r.get("draft", False)]
            releases_to_download = [non_draft_releases[0]] if non_draft_releases else []

        if not releases_to_download:
            if self.verbose:
                print("   No suitable releases found to download")
            return

        releases_dir_name = (
            f"{self.repo_data['owner']}-{self.repo_data['repo_name']}_releases"
        )
        releases_dir = os.path.join(repo_path, releases_dir_name)
        os.makedirs(releases_dir, exist_ok=True)

        downloaded_count = 0

        for release in releases_to_download:
            tag_name = release.get("tag_name", "unknown")
            release_name = release.get("name", tag_name)

            if self.verbose:
                print(f"   Downloading release: {release_name} ({tag_name})")

            # Create directory for this release
            release_dir = os.path.join(releases_dir, tag_name)
            os.makedirs(release_dir, exist_ok=True)

            # Create release info file
            release_info = {
                "tag_name": tag_name,
                "name": release_name,
                "published_at": release.get("published_at", release.get("released_at")),
                "description": release.get("body", release.get("description", "")),
                "prerelease": release.get("prerelease", False),
                "draft": release.get("draft", False),
            }

            with open(os.path.join(release_dir, f"{tag_name}.info.json"), "w") as f:
                json.dump(release_info, f, indent=2)

            # Download source archives
            if release.get("zipball_url"):
                try:
                    self._download_file(
                        release["zipball_url"],
                        os.path.join(release_dir, f"{tag_name}.source.zip"),
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"     Could not download source zip: {e}")

            if release.get("tarball_url"):
                try:
                    self._download_file(
                        release["tarball_url"],
                        os.path.join(release_dir, f"{tag_name}.source.tar.gz"),
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"     Could not download source tarball: {e}")

            # Download release assets
            for asset in release.get("assets", []):
                asset_name = asset.get("name", "unknown_asset")
                download_url = asset.get("download_url")

                if download_url:
                    try:
                        self._download_file(
                            download_url, os.path.join(release_dir, asset_name)
                        )
                        if self.verbose:
                            print(f"     Downloaded asset: {asset_name}")
                    except Exception as e:
                        if self.verbose:
                            print(f"     Could not download asset {asset_name}: {e}")

            downloaded_count += 1

        self.repo_data["downloaded_releases"] = downloaded_count
        self.repo_data["releases_dir_name"] = releases_dir_name
        if self.verbose:
            print(
                f"   Successfully downloaded {downloaded_count} release(s) to {releases_dir_name}/"
            )

    def _download_file(self, url, filepath):
        """Download a file from a URL to a local path"""
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    def _sanitize_branch_name(self, branch_name):
        """Sanitize branch name for use as directory name"""
        # Remove forward slashes and other problematic characters
        sanitized = branch_name.replace("/", "-").replace("\\", "-")
        # Remove other potentially problematic characters
        sanitized = re.sub(r'[<>:"|?*]', "-", sanitized)
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")
        return sanitized

    def clone_repository(self, repo_url, all_branches=False, specific_branch=None):
        """Clone the git repository to a temporary directory."""
        if self.verbose:
            if all_branches:
                branch_info = "all branches"
            elif specific_branch:
                branch_info = f"branch: {specific_branch}"
            else:
                branch_info = "default branch"
            print(f"Cloning repository from {repo_url} ({branch_info})...")

        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="iagitbetter_")
        repo_path = os.path.join(self.temp_dir, self.repo_data["repo_name"])

        try:
            # Clone the repository
            if specific_branch:
                # Clone specific branch only
                repo = git.Repo.clone_from(
                    repo_url, repo_path, branch=specific_branch, single_branch=True
                )
                self.repo_data["specific_branch"] = specific_branch
            else:
                # Clone all branches (default behavior)
                repo = git.Repo.clone_from(repo_url, repo_path)

            # Ensure the repository path exists even when using lightweight test doubles
            os.makedirs(repo_path, exist_ok=True)

            # Get the first commit date and last commit date
            try:
                # Get all commits and find the first one (oldest)
                commits = list(repo.iter_commits(all=True))
                if commits:
                    first_commit = commits[
                        -1
                    ]  # Last in the list is the first chronologically
                    last_commit = commits[
                        0
                    ]  # First in the list is the last chronologically

                    self.repo_data["first_commit_date"] = datetime.fromtimestamp(
                        first_commit.committed_date
                    )
                    self.repo_data["last_commit_date"] = datetime.fromtimestamp(
                        last_commit.committed_date
                    )
                    self.repo_data["total_commits"] = len(commits)

                    if self.verbose:
                        print(
                            f"   First commit date: {self.repo_data['first_commit_date']}"
                        )
                        print(
                            f"   Last commit date: {self.repo_data['last_commit_date']}"
                        )
                        print(f"   Total commits: {self.repo_data['total_commits']}")
                else:
                    # Fallback if no commits found
                    current_time = datetime.now()
                    self.repo_data["first_commit_date"] = current_time
                    self.repo_data["last_commit_date"] = current_time
                    self.repo_data["total_commits"] = 0
            except Exception as e:
                if self.verbose:
                    print(f"   Could not get commit information: {e}")
                current_time = datetime.now()
                self.repo_data["first_commit_date"] = current_time
                self.repo_data["last_commit_date"] = current_time
                self.repo_data["total_commits"] = 0

            # Get default branch
            if specific_branch:
                default_branch = specific_branch
            else:
                default_branch = (
                    repo.active_branch.name if repo.active_branch else "main"
                )
            self.repo_data["default_branch"] = default_branch

            if all_branches and not specific_branch:
                # Create separate directories for each branch
                self._create_branch_directories(repo, repo_path)
            else:
                # Store branch information for single branch
                if specific_branch:
                    self.repo_data["branches"] = [specific_branch]
                else:
                    self.repo_data["branches"] = [default_branch]
                self.repo_data["branch_count"] = 1

            # Download avatar after successful clone
            self.download_avatar(repo_path)

            return repo_path
        except Exception as e:
            print(f"Error cloning repository: {e}")
            self.cleanup()
            sys.exit(1)

    def _create_branch_directories(self, repo, repo_path):
        """Create separate directories for each branch (except default branch)"""
        try:
            # Fetch all remote branches
            for remote in repo.remotes:
                remote.fetch()

            # Get all remote branches
            remote_branches = []
            for remote_ref in repo.remote().refs:
                if remote_ref.name != "origin/HEAD":
                    branch_name = remote_ref.name.replace("origin/", "")
                    remote_branches.append(branch_name)

            if not remote_branches:
                remote_branches = [self.repo_data["default_branch"]]

            # Store branch information
            self.repo_data["branches"] = remote_branches
            self.repo_data["branch_count"] = len(remote_branches)

            if self.verbose:
                print(
                    f"   Found {len(remote_branches)} branches: {', '.join(remote_branches)}"
                )
                print(
                    f"   Default branch ({self.repo_data['default_branch']}) files will be in root directory"
                )
                print("   Other branches will be organized in branches directory")

            # Create branches directory for non-default branches: {repo_name}-{owner}_branches
            branches_dir_name = (
                f"{self.repo_data['owner']}-{self.repo_data['repo_name']}_branches"
            )
            branches_dir = os.path.join(repo_path, branches_dir_name)

            # Only create if there are other branches
            other_branches = [
                b for b in remote_branches if b != self.repo_data["default_branch"]
            ]
            if other_branches:
                os.makedirs(branches_dir, exist_ok=True)
                self.repo_data["branches_dir_name"] = branches_dir_name

                if self.verbose:
                    print(f"   Creating branches directory: {branches_dir_name}/")

            # For non-default branches, create separate directories inside branches folder
            for branch_name in other_branches:
                if self.verbose:
                    print(f"   Creating directory for branch: {branch_name}")

                # Sanitize branch name for directory
                sanitized_name = self._sanitize_branch_name(branch_name)
                branch_dir = os.path.join(branches_dir, sanitized_name)
                os.makedirs(branch_dir, exist_ok=True)

                # Checkout the branch
                try:
                    if branch_name not in [b.name for b in repo.heads]:
                        repo.create_head(branch_name, f"origin/{branch_name}")
                    repo.heads[branch_name].checkout()

                    # Copy all files to branch directory (excluding .git and special directories)
                    for item in os.listdir(repo_path):
                        if (
                            item == ".git"
                            or item == branches_dir_name
                            or item.endswith("_releases")
                            or item.endswith(".info.json")
                        ):
                            continue

                        src_path = os.path.join(repo_path, item)
                        dst_path = os.path.join(branch_dir, item)

                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path, symlinks=True)
                        else:
                            shutil.copy2(src_path, dst_path)

                except Exception as e:
                    if self.verbose:
                        print(
                            f"     Warning: Could not process branch {branch_name}: {e}"
                        )

            # Checkout default branch to keep files in root
            try:
                repo.heads[self.repo_data["default_branch"]].checkout()
                if self.verbose:
                    print(
                        f"   Checked out default branch: {self.repo_data['default_branch']}"
                    )
            except Exception as e:
                if self.verbose:
                    print(f"   Warning: Could not checkout default branch: {e}")

        except Exception as e:
            if self.verbose:
                print(f"   Warning: Could not create all branch directories: {e}")
            # Fallback to single branch
            self.repo_data["branches"] = [self.repo_data["default_branch"]]
            self.repo_data["branch_count"] = 1

    def create_git_bundle(self, repo_path):
        """Create a git bundle of the repository."""
        if self.verbose:
            print("Creating git bundle...")

        bundle_name = f"{self.repo_data['owner']}-{self.repo_data['repo_name']}.bundle"
        bundle_path = os.path.join(repo_path, bundle_name)

        try:
            # Change to repo directory
            original_dir = os.getcwd()
            os.chdir(repo_path)

            # Create bundle with all branches and tags
            subprocess.check_call(["git", "bundle", "create", bundle_path, "--all"])

            os.chdir(original_dir)
            if self.verbose:
                print(f"   Bundle created: {bundle_name}")
            return bundle_path
        except Exception as e:
            print(f"Error creating bundle: {e}")
            return None

    def _should_skip_directory(self, root):
        """Check if directory should be skipped during file collection"""
        dir_name = os.path.basename(root)
        if dir_name == ".git":
            return True
        if os.sep + ".git" + os.sep in root or root.endswith(os.sep + ".git"):
            return True
        return False

    def _validate_file(
        self,
        file_path,
        relative_path,
        skipped_corrupted_files,
        skipped_unreadable_files,
        skipped_empty_files,
    ):
        """Validate file for upload, return True if valid, False otherwise"""
        if not os.path.exists(file_path):
            skipped_corrupted_files.append((relative_path, "File does not exist"))
            return False

        if os.path.islink(file_path):
            if not os.path.exists(os.path.realpath(file_path)):
                skipped_corrupted_files.append((relative_path, "Broken symbolic link"))
                return False

        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                skipped_empty_files.append(relative_path)
                return False

            with open(file_path, "rb") as f:
                try:
                    f.read(1024)
                except (IOError, OSError) as e:
                    skipped_unreadable_files.append((relative_path, str(e)))
                    return False

        except OSError as e:
            skipped_corrupted_files.append((relative_path, f"OS error: {str(e)}"))
            return False
        except PermissionError as e:
            skipped_unreadable_files.append(
                (relative_path, f"Permission denied: {str(e)}")
            )
            return False
        except Exception as e:
            skipped_corrupted_files.append(
                (relative_path, f"Unexpected error: {str(e)}")
            )
            return False

        return True

    def _get_upload_name(self, relative_path, renamed_svg_files, renamed_bmp_files):
        """Get upload name for file with necessary renaming for IA compatibility"""
        if relative_path.lower().endswith(".svg"):
            renamed_svg_files.append(relative_path)
            return relative_path + ".xml"
        elif relative_path.lower().endswith(".bmp"):
            renamed_bmp_files.append(relative_path)
            return relative_path + ".bin"
        else:
            return relative_path

    def _print_skipped_files_summary(
        self,
        skipped_empty_files,
        skipped_corrupted_files,
        skipped_unreadable_files,
        renamed_svg_files,
        renamed_bmp_files,
        total_files,
    ):
        """Print summary of skipped and renamed files"""
        if not self.verbose:
            return

        total_skipped = (
            len(skipped_empty_files)
            + len(skipped_corrupted_files)
            + len(skipped_unreadable_files)
        )

        if total_skipped > 0:
            print("\n   File filtering summary:")
            print(f"   Total files found: {total_files + total_skipped}")
            print(f"   Files to upload: {total_files}")
            print(f"   Files skipped: {total_skipped}")

        if skipped_empty_files:
            print(f"\n   Skipping {len(skipped_empty_files)} empty file(s) (0 bytes):")
            for empty_file in skipped_empty_files[:5]:
                print(f"     - {empty_file}")
            if len(skipped_empty_files) > 5:
                print(f"     ... and {len(skipped_empty_files) - 5} more")

        if skipped_corrupted_files:
            print(
                f"\n   Skipping {len(skipped_corrupted_files)} corrupted/problematic file(s):"
            )
            for corrupted_file, reason in skipped_corrupted_files[:5]:
                print(f"     - {corrupted_file}: {reason}")
            if len(skipped_corrupted_files) > 5:
                print(f"     ... and {len(skipped_corrupted_files) - 5} more")

        if skipped_unreadable_files:
            print(f"\n   Skipping {len(skipped_unreadable_files)} unreadable file(s):")
            for unreadable_file, reason in skipped_unreadable_files[:5]:
                print(f"     - {unreadable_file}: {reason}")
            if len(skipped_unreadable_files) > 5:
                print(f"     ... and {len(skipped_unreadable_files) - 5} more")

        if renamed_svg_files:
            print(
                f"\n   Renaming {len(renamed_svg_files)} SVG file(s) to .svg.xml for IA compatibility:"
            )
            for svg_file in renamed_svg_files[:5]:
                print(f"     - {svg_file} → {svg_file}.xml")
            if len(renamed_svg_files) > 5:
                print(f"     ... and {len(renamed_svg_files) - 5} more")

        if renamed_bmp_files:
            print(
                f"\n   Renaming {len(renamed_bmp_files)} BMP file(s) to .bmp.bin for IA compatibility:"
            )
            for bmp_file in renamed_bmp_files[:5]:
                print(f"     - {bmp_file} → {bmp_file}.bin")
            if len(renamed_bmp_files) > 5:
                print(f"     ... and {len(renamed_bmp_files) - 5} more")

    def get_all_files(self, repo_path):
        """Get all files in the repository, preserving directory structure and filtering corrupted files."""
        files_to_upload = {}
        skipped_empty_files = []
        skipped_corrupted_files = []
        skipped_unreadable_files = []
        renamed_svg_files = []
        renamed_bmp_files = []

        for root, dirs, files in os.walk(repo_path):
            if self._should_skip_directory(root):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path).replace(
                    os.sep, "/"
                )

                if not self._validate_file(
                    file_path,
                    relative_path,
                    skipped_corrupted_files,
                    skipped_unreadable_files,
                    skipped_empty_files,
                ):
                    continue

                upload_name = self._get_upload_name(
                    relative_path, renamed_svg_files, renamed_bmp_files
                )
                files_to_upload[upload_name] = file_path

        # Print summary
        self._print_skipped_files_summary(
            skipped_empty_files,
            skipped_corrupted_files,
            skipped_unreadable_files,
            renamed_svg_files,
            renamed_bmp_files,
            len(files_to_upload),
        )

        # Store skip statistics
        total_skipped = (
            len(skipped_empty_files)
            + len(skipped_corrupted_files)
            + len(skipped_unreadable_files)
        )
        self.repo_data["skipped_files"] = {
            "empty": len(skipped_empty_files),
            "corrupted": len(skipped_corrupted_files),
            "unreadable": len(skipped_unreadable_files),
            "total": total_skipped,
        }

        return files_to_upload

    def get_description_from_readme(self, repo_path):
        """Get HTML description from README.md, or README.rst, or README.txt"""
        # Try README.md
        readme_md_paths = [
            os.path.join(repo_path, "README.md"),
            os.path.join(repo_path, "readme.md"),
            os.path.join(repo_path, "Readme.md"),
            os.path.join(repo_path, "README.MD"),
        ]

        for path in readme_md_paths:
            if os.path.exists(path):
                try:
                    # Use markdown2 to convert to HTML
                    description = markdown_path(path)
                    return description
                except Exception as e:
                    if self.verbose:
                        print(f"Could not parse README.md: {e}")

        # Try README.rst
        readme_rst_paths = [
            os.path.join(repo_path, "README.rst"),
            os.path.join(repo_path, "readme.rst"),
            os.path.join(repo_path, "Readme.rst"),
            os.path.join(repo_path, "README.RST"),
        ]

        for path in readme_rst_paths:
            if os.path.exists(path):
                try:
                    # Import docutils for RST parsing
                    from docutils.core import publish_parts

                    with open(path, "r", encoding="utf-8") as f:
                        rst_content = f.read()

                    # Convert RST to HTML
                    parts = publish_parts(
                        rst_content,
                        writer_name="html",
                        settings_overrides={
                            "initial_header_level": 1,
                            "report_level": 5,  # Suppress warnings
                            "halt_level": 5,
                        },
                    )
                    # Return only the body content without the full HTML structure
                    description = parts["body"]
                    return description
                except ImportError:
                    if self.verbose:
                        print("   docutils not available, cannot parse README.rst")
                except Exception as e:
                    if self.verbose:
                        print(f"   Could not parse README.rst: {e}")

        # Fallback to README.txt
        txt_paths = [
            os.path.join(repo_path, "README.txt"),
            os.path.join(repo_path, "readme.txt"),
            os.path.join(repo_path, "README"),
            os.path.join(repo_path, "readme"),
        ]

        for path in txt_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        description = f.readlines()
                        description = " ".join(description)
                        # Convert to basic HTML
                        description = f"<pre>{description}</pre>"
                        return description
                except Exception:
                    pass

        return "This repository doesn't have a README file"

    def _generate_upload_identifier(self, archive_date):
        """Generate identifier for Internet Archive upload"""
        return f"{self.repo_data['owner']}-{self.repo_data['repo_name']}-{archive_date.strftime('%Y%m%d%H%M%S')}"

    def _generate_item_name(self):
        """Generate item name for Internet Archive upload"""
        return f"{self.repo_data['owner']} - {self.repo_data['repo_name']}"

    def _build_archive_details(
        self, bundle_only, includes_all_branches, specific_branch, includes_releases
    ):
        """Build list of archive details for description"""
        archive_details = []
        if bundle_only:
            archive_details.append("Git bundle only")
        else:
            archive_details.append("Repository files")

            if includes_all_branches:
                branch_count = self.repo_data.get("branch_count", 0)
                archive_details.append(f"All {branch_count} branches")
            elif specific_branch:
                archive_details.append(f"Branch: {specific_branch}")
            else:
                archive_details.append("Default branch")

            if includes_releases:
                release_count = self.repo_data.get("downloaded_releases", 0)
                if release_count > 0:
                    archive_details.append(f"{release_count} release(s) with assets")

        return archive_details

    def _build_description_footer(
        self, identifier, bundle_filename, repo_date, archive_date
    ):
        """Build the footer section for repository description"""
        return f"""<br/><hr/>
        <p><strong>Repository Information:</strong></p>
        <ul>
            <li>Original Repository: <a href="{self.repo_data['url']}">{self.repo_data['url']}</a></li>
            <li>Git Provider: {self.repo_data['git_site'].title()}</li>
            <li>Owner: {self.repo_data['owner']}</li>
            <li>Repository Name: {self.repo_data['repo_name']}</li>
            <li>First Commit: {repo_date.strftime('%Y-%m-%d %H:%M:%S')}</li>
            <li>Last Commit: {self.repo_data.get('last_commit_date', archive_date).strftime('%Y-%m-%d %H:%M:%S')}</li>
            <li>Total Commits: {self.repo_data.get('total_commits', 'Unknown')}</li>
            <li>Archived: {archive_date.strftime('%Y-%m-%d %H:%M:%S')}</li>
        </ul>
        <p>To restore the repository, download the bundle:</p>
        <pre><code>wget https://archive.org/download/{identifier}/{bundle_filename}</code></pre>
        <p>And then run:</p>
        <pre><code>git clone {bundle_filename}</code></pre>
        """

    def _build_full_description(
        self, repo_path, identifier, bundle_filename, repo_date, archive_date
    ):
        """Build the full description for Internet Archive upload"""
        readme_description = self.get_description_from_readme(repo_path)
        description_footer = self._build_description_footer(
            identifier, bundle_filename, repo_date, archive_date
        )

        if self.repo_data.get("description"):
            return f"<br/>{self.repo_data['description']}<br/><br/>{readme_description}{description_footer}"
        else:
            return f"{readme_description}{description_footer}"

    def _build_subject_tags(
        self, bundle_only, includes_releases, includes_all_branches, specific_branch
    ):
        """Build subject tags for Internet Archive metadata"""
        subject_tags = [
            "git",
            "code",
            "software",
            self.repo_data["git_site"],
            "repository",
            "repo",
            self.repo_data["owner"],
            self.repo_data["repo_name"],
        ]

        if bundle_only:
            subject_tags.append("bundle-only")
        else:
            if includes_releases:
                subject_tags.append("releases")
            if includes_all_branches:
                subject_tags.append("branches")
            elif specific_branch:
                subject_tags.extend(["branch", specific_branch])

        if self.repo_data.get("language"):
            subject_tags.append(self.repo_data["language"].lower())

        if self.repo_data.get("topics"):
            subject_tags.extend(self.repo_data["topics"])

        return subject_tags

    def _build_base_metadata(
        self, item_name, description, repo_date, subject_tags, identifier
    ):
        """Build base metadata dictionary for Internet Archive"""
        from urllib.parse import urlparse

        parsed_url = urlparse(self.repo_data["url"])
        repo_owner_url = (
            f"{parsed_url.scheme}://{parsed_url.netloc}/{self.repo_data['owner']}"
        )

        metadata = {
            "title": item_name,
            "mediatype": "software",
            "collection": "opensource_media",
            "description": description,
            "creator": self.repo_data["owner"],
            "date": repo_date.strftime("%Y-%m-%d"),
            "year": str(repo_date.year),
            "subject": ";".join(subject_tags),
            "repourl": self.repo_data["url"],
            "repoowner": repo_owner_url,
            "gitsite": self.repo_data["git_site"],
            "language": self.repo_data.get("language", "Unknown"),
            "identifier": identifier,
            "scanner": f"iagitbetter Git Repository Mirroring Application {__version__}",
            "totalcommits": str(self.repo_data.get("total_commits", 0)),
        }

        license_url = self.get_license_url(self.repo_data.get("license", ""))
        if license_url:
            metadata["licenseurl"] = license_url

        return metadata

    def _add_branch_metadata(self, metadata, includes_all_branches, specific_branch):
        """Add branch-related metadata"""
        if includes_all_branches:
            metadata["allbranches"] = "true"
            metadata["branchcount"] = str(self.repo_data.get("branch_count", 0))
            if self.repo_data.get("branches"):
                metadata["branchlist"] = ";".join(self.repo_data["branches"])
        elif specific_branch:
            metadata["specificbranch"] = specific_branch

    def _add_optional_metadata(
        self, metadata, bundle_only, includes_releases, custom_metadata
    ):
        """Add optional metadata fields"""
        if bundle_only:
            metadata["bundleonly"] = "true"

        if includes_releases:
            metadata["includesreleases"] = "true"
            metadata["releasecount"] = str(self.repo_data.get("downloaded_releases", 0))

        if self.repo_data.get("stars") is not None:
            metadata["stars"] = str(self.repo_data["stars"])
        if self.repo_data.get("forks") is not None:
            metadata["forks"] = str(self.repo_data["forks"])
        if self.repo_data.get("license"):
            metadata["license"] = self.repo_data["license"]
        if self.repo_data.get("homepage"):
            metadata["homepage"] = self.repo_data["homepage"]
        if self.repo_data.get("default_branch"):
            metadata["defaultbranch"] = self.repo_data["default_branch"]
        if self.repo_data.get("archived"):
            metadata["repoarchived"] = str(self.repo_data["archived"])
        if self.repo_data.get("fork"):
            metadata["isfork"] = str(self.repo_data["fork"])
        if self.repo_data.get("private"):
            metadata["repoprivate"] = "true"

        if custom_metadata:
            metadata.update(custom_metadata)

    def _print_upload_info(
        self, identifier, item_name, repo_date, archive_date, archive_details, metadata
    ):
        """Print upload information to console"""
        if not self.verbose:
            return

        print("\nUploading to Internet Archive")
        print(f"   Identifier: {identifier}")
        print(f"   Title: {item_name}")
        print(f"   Repository Date: {repo_date.strftime('%Y-%m-%d')} (first commit)")
        print(f"   Archive Date: {archive_date.strftime('%Y-%m-%d')} (today)")
        print(f"   Contents: {', '.join(archive_details)}")

        if metadata.get("stars"):
            print(f"   Stars: {metadata['stars']}")
        if metadata.get("forks"):
            print(f"   Forks: {metadata['forks']}")
        if metadata.get("language"):
            print(f"   Primary Language: {metadata['language']}")
        if metadata.get("license"):
            print(f"   License: {metadata['license']}")
            if metadata.get("licenseurl"):
                print(f"   License URL: {metadata['licenseurl']}")

    def _prepare_base_files(self, repo_path, create_repo_info):
        """Prepare base files (bundle, info, avatar) for upload"""
        files_to_upload = {}

        bundle_path = self.create_git_bundle(repo_path)
        bundle_filename = os.path.basename(bundle_path) if bundle_path else None

        info_path = None
        info_filename = None
        if create_repo_info:
            info_path = self.create_repo_info_file(repo_path)
            info_filename = os.path.basename(info_path) if info_path else None

        if bundle_path and os.path.exists(bundle_path):
            files_to_upload[bundle_filename] = bundle_path

        if info_path and os.path.exists(info_path):
            files_to_upload[info_filename] = info_path

        username = self.repo_data["owner"]
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            avatar_filename = f"{username}{ext}"
            avatar_path = os.path.join(repo_path, avatar_filename)
            if os.path.exists(avatar_path):
                files_to_upload[avatar_filename] = avatar_path
                break

        return files_to_upload, bundle_filename

    def _add_repository_files(
        self, repo_path, files_to_upload, bundle_only, includes_releases
    ):
        """Add repository files to upload dictionary"""
        if not bundle_only:
            if self.verbose:
                print("Collecting all repository files...")
            repo_files = self.get_all_files(repo_path)
            files_to_upload.update(repo_files)
        else:
            if includes_releases and self.repo_data.get("releases_dir_name"):
                releases_dir_name = self.repo_data["releases_dir_name"]
                releases_path = os.path.join(repo_path, releases_dir_name)
                if os.path.exists(releases_path):
                    if self.verbose:
                        print(
                            f"Including releases directory in bundle-only upload: {releases_dir_name}/"
                        )
                    for root, dirs, files in os.walk(releases_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path, repo_path)
                            relative_path = relative_path.replace(os.sep, "/")
                            files_to_upload[relative_path] = file_path

    def _print_upload_components(
        self,
        files_to_upload,
        bundle_only,
        bundle_filename,
        info_filename,
        includes_all_branches,
        includes_releases,
        username,
    ):
        """Print information about upload components"""
        if not self.verbose:
            return

        if bundle_only:
            print("Uploading git bundle to Internet Archive")
            if includes_releases:
                print("   (including releases directory)")
        else:
            print(f"Uploading {len(files_to_upload)} files to Internet Archive")
        print(
            "This may take some time depending on repository size and connection speed"
        )

        components = []
        if bundle_filename:
            components.append("Git bundle")
        if info_filename:
            components.append("Repository info file")

        avatar_included = any(
            f.startswith(username)
            and f.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
            for f in files_to_upload.keys()
        )
        if avatar_included:
            components.append("User avatar")

        if not bundle_only:
            if includes_all_branches:
                branches_dir = self.repo_data.get("branches_dir_name")
                if branches_dir:
                    branch_files = [
                        f for f in files_to_upload.keys() if f.startswith(branches_dir)
                    ]
                    if branch_files:
                        non_default_count = len(
                            [
                                b
                                for b in self.repo_data.get("branches", [])
                                if b != self.repo_data.get("default_branch")
                            ]
                        )
                        components.append(
                            f"Branches directory ({non_default_count} branches in {branches_dir}/)"
                        )
            if includes_releases and self.repo_data.get("releases_dir_name"):
                release_files = [
                    f
                    for f in files_to_upload.keys()
                    if f.startswith(self.repo_data["releases_dir_name"])
                ]
                if release_files:
                    components.append(
                        f"Releases directory ({len(release_files)} files)"
                    )
            components.append("Repository files")
        else:
            if includes_releases and self.repo_data.get("releases_dir_name"):
                release_files = [
                    f
                    for f in files_to_upload.keys()
                    if f.startswith(self.repo_data["releases_dir_name"])
                ]
                if release_files:
                    components.append(
                        f"Releases directory ({len(release_files)} files)"
                    )

        print(f"   Components: {', '.join(components)}")

    def _get_ia_credentials(self):
        """Get Internet Archive credentials from config file"""
        access_key = None
        secret_key = None

        try:
            parsed_ia_config = parse_config_file(self.ia_config_path)[2]["s3"]
            access_key = parsed_ia_config.get("access")
            secret_key = parsed_ia_config.get("secret")
        except Exception as e:
            if self.verbose:
                print(
                    f"Note: Using default IA credentials (could not parse config: {e})"
                )

        return access_key, secret_key

    def upload_to_ia(
        self,
        repo_path,
        custom_metadata=None,
        includes_releases=False,
        includes_all_branches=False,
        specific_branch=None,
        bundle_only=False,
        create_repo_info=True,
    ):
        """Upload the repository to the Internet Archive"""
        # Generate timestamps
        archive_date = datetime.now()
        repo_date = self.repo_data.get("first_commit_date", archive_date)

        # Generate identifier and names
        identifier = self._generate_upload_identifier(archive_date)
        item_name = self._generate_item_name()
        bundle_filename = (
            f"{self.repo_data['owner']}-{self.repo_data['repo_name']}.bundle"
        )

        # Build archive details and description
        archive_details = self._build_archive_details(
            bundle_only, includes_all_branches, specific_branch, includes_releases
        )
        description = self._build_full_description(
            repo_path, identifier, bundle_filename, repo_date, archive_date
        )

        # Build metadata
        subject_tags = self._build_subject_tags(
            bundle_only, includes_releases, includes_all_branches, specific_branch
        )
        metadata = self._build_base_metadata(
            item_name, description, repo_date, subject_tags, identifier
        )
        self._add_branch_metadata(metadata, includes_all_branches, specific_branch)
        self._add_optional_metadata(
            metadata, bundle_only, includes_releases, custom_metadata
        )

        # Print upload information
        self._print_upload_info(
            identifier, item_name, repo_date, archive_date, archive_details, metadata
        )

        try:
            # Check if item already exists
            item = internetarchive.get_item(identifier)
            if item.exists:
                if self.verbose:
                    print(
                        "\nThis repository version already exists on the Internet Archive"
                    )
                    print(f"URL: https://archive.org/details/{identifier}")
                return identifier, metadata

            # Prepare files for upload
            files_to_upload, bundle_filename = self._prepare_base_files(
                repo_path, create_repo_info
            )
            info_filename = next(
                (k for k in files_to_upload.keys() if k.endswith("_info.json")), None
            )

            # Add repository files
            self._add_repository_files(
                repo_path, files_to_upload, bundle_only, includes_releases
            )

            # Print upload components
            username = self.repo_data["owner"]
            self._print_upload_components(
                files_to_upload,
                bundle_only,
                bundle_filename,
                info_filename,
                includes_all_branches,
                includes_releases,
                username,
            )

            # Get credentials and upload
            access_key, secret_key = self._get_ia_credentials()
            upload_kwargs = {
                "metadata": metadata,
                "retries": 9001,
                "request_kwargs": dict(timeout=(9001, 9001)),
                "verbose": self.verbose,
                "delete": False,
            }
            if access_key and secret_key:
                upload_kwargs["access_key"] = access_key
                upload_kwargs["secret_key"] = secret_key

            info_files = {
                k: v for k, v in files_to_upload.items() if k.endswith(".info.json")
            }
            other_files = {
                k: v for k, v in files_to_upload.items() if not k.endswith(".info.json")
            }

            if info_files:
                item.upload(info_files, **upload_kwargs)

            if other_files:
                item.upload(other_files, **upload_kwargs)

            if self.verbose:
                print("\nUpload completed successfully!")
                print(f"   Archive URL: https://archive.org/details/{identifier}")
                if bundle_filename:
                    print(
                        f"   Bundle download: https://archive.org/download/{identifier}/{bundle_filename}"
                    )

            return identifier, metadata

        except Exception as e:
            print(f"Error uploading to Internet Archive: {e}")
            return None, None

    def handle_remove_readonly(self, func, path, exc):
        """Error handler for Windows readonly files"""
        if os.path.exists(path):
            # Change the file to be writable and try again
            os.chmod(path, stat.S_IWRITE)
            func(path)

    def cleanup(self):
        """Clean up temporary files with Windows compatibility."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            if self.verbose:
                print("Cleaning up temporary files...")
            try:
                # On Windows, we need to handle read only files in .git directory
                if os.name == "nt":
                    shutil.rmtree(self.temp_dir, onerror=self.handle_remove_readonly)
                else:
                    shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not completely clean up temporary files: {e}")
                print(f"You may need to manually delete: {self.temp_dir}")

    def check_ia_credentials(self):
        """Check if Internet Archive credentials are configured."""
        ia_config_paths = [
            os.path.expanduser("~/.ia"),
            os.path.expanduser("~/.config/ia.ini"),
            os.path.expanduser("~/.config/internetarchive/ia.ini"),
        ]

        if not any(os.path.exists(path) for path in ia_config_paths):
            print("\nInternet Archive credentials not found")
            print("Run: ia configure")

            try:
                result = subprocess.call(["ia", "configure"])
                if result != 0:
                    sys.exit(1)
            except Exception as e:
                print(f"Error configuring Internet Archive account: {e}")
                sys.exit(1)

    def parse_custom_metadata(self, metadata_string):
        """Parse custom metadata from command line format."""
        if not metadata_string:
            return None

        custom_meta = {}
        for item in metadata_string.split(","):
            if ":" in item:
                key, value = item.split(":", 1)
                custom_meta[key.strip()] = value.strip()

        return custom_meta

    def run(
        self,
        repo_url,
        custom_metadata_string=None,
        verbose=True,
        check_updates=True,
        all_branches=False,
        specific_branch=None,
        releases=False,
        all_releases=False,
        bundle_only=False,
        create_repo_info=True,
    ):
        """Main execution flow."""
        self.verbose = verbose

        # Check for updates if enabled
        if check_updates and verbose:
            check_for_updates(__version__, verbose=True)

        # Check IA credentials
        self.check_ia_credentials()

        # Parse custom metadata
        custom_metadata = self.parse_custom_metadata(custom_metadata_string)

        # Extract repository information
        if self.verbose:
            print(f"\n:: Analyzing repository: {repo_url}")
        self.extract_repo_info(repo_url)
        if self.verbose:
            print(f"   Repository: {self.repo_data['full_name']}")
            print(f"   Git Provider: {self.repo_data['git_site']}")

        # Clone repository
        repo_path = self.clone_repository(
            repo_url, all_branches=all_branches, specific_branch=specific_branch
        )

        if self.repo_data.get("git_site") == "gist":
            self.save_gist_comments(repo_path)

        # Download releases if requested
        if releases:
            self.download_releases(repo_path, all_releases=all_releases)

        # Upload to Internet Archive
        identifier, metadata = self.upload_to_ia(
            repo_path,
            custom_metadata,
            includes_releases=releases,
            includes_all_branches=all_branches,
            specific_branch=specific_branch,
            bundle_only=bundle_only,
            create_repo_info=create_repo_info,
        )

        # Cleanup
        self.cleanup()

        return identifier, metadata


def main():
    parser = argparse.ArgumentParser(
        description="iagitbetter - Archive any git repository to the Internet Archive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://github.com/user/repo
  %(prog)s https://gitlab.com/user/repo
  %(prog)s https://bitbucket.org/user/repo
  %(prog)s --metadata="license:MIT,topic:python" https://github.com/user/repo
  %(prog)s --quiet https://github.com/user/repo
  %(prog)s --releases --all-releases https://github.com/user/repo
  %(prog)s --all-branches https://github.com/user/repo
  %(prog)s --branch develop https://github.com/user/repo
  %(prog)s --bundle-only https://github.com/user/repo
  %(prog)s --no-repo-info https://github.com/user/repo

  # Self-hosted instances
  %(prog)s --git-provider-type gitlab --api-url https://gitlab.company.com/api/v4 https://gitlab.company.com/user/repo
  %(prog)s --git-provider-type gitea --api-token TOKEN https://git.company.com/user/repo
        """,
    )

    parser.add_argument("repo_url", help="Git repository URL to archive")
    parser.add_argument(
        "--metadata", "-m", help="Custom metadata in format: key1:value1,key2:value2"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress verbose output"
    )
    parser.add_argument(
        "--no-update-check",
        action="store_true",
        help="Skip checking for updates on PyPI",
    )
    parser.add_argument(
        "--bundle-only",
        action="store_true",
        help="Only uploads the git bundle, not all files",
    )
    parser.add_argument(
        "--no-repo-info",
        action="store_true",
        help="Skip creating the repository info JSON file",
    )
    parser.add_argument(
        "--releases", action="store_true", help="Download releases from the repository"
    )
    parser.add_argument(
        "--all-releases",
        action="store_true",
        help="Download all releases (default: latest only)",
    )
    parser.add_argument(
        "--all-branches", action="store_true", help="Clone and archive all branches"
    )
    parser.add_argument(
        "--branch", type=str, help="Clone and archive a specific branch"
    )
    parser.add_argument(
        "--git-provider-type",
        type=str,
        choices=[
            "github",
            "gitlab",
            "gitea",
            "bitbucket",
            "gitee",
            "gogs",
            "sourceforge",
            "gerrit",
            "launchpad",
        ],
        help="Specify the git provider type for self-hosted instances",
    )
    parser.add_argument(
        "--api-url", type=str, help="Custom API URL for self-hosted instances"
    )
    parser.add_argument(
        "--api-token",
        type=str,
        help="API token for authentication with private/self-hosted repositories",
    )
    parser.add_argument(
        "--api-username",
        type=str,
        help="Username for Bitbucket App Passwords (used with --api-token for basic auth)",
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    # Validate argument combinations
    if args.all_branches and args.branch:
        print("Error: Cannot specify both --all-branches and --branch")
        sys.exit(1)

    # Create archiver instance and run
    archiver = GitArchiver(
        verbose=not args.quiet,
        git_provider_type=args.git_provider_type,
        api_url=args.api_url,
        api_token=args.api_token,
        api_username=args.api_username,  # <-- pass through for Bitbucket basic auth
    )
    try:
        identifier, metadata = archiver.run(
            args.repo_url,
            args.metadata,
            verbose=not args.quiet,
            check_updates=not args.no_update_check,
            all_branches=args.all_branches,
            specific_branch=args.branch,
            releases=args.releases,
            all_releases=args.all_releases,
            bundle_only=args.bundle_only,
            create_repo_info=not args.no_repo_info,
        )
        if identifier:
            print("\n" + "=" * 60)
            print("Archive complete")
            print("=" * 60)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        archiver.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        archiver.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
