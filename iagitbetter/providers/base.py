"""
Base provider class for git hosting services.
All provider implementations should inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Base class for all git provider implementations."""

    # Provider name (e.g., "github", "gitlab")
    name: str = ""
    # List of domains this provider handles
    domains: list[str] = []

    def __init__(
        self,
        api_token: str | None = None,
        api_url: str | None = None,
        api_username: str | None = None,
        verbose: bool = True,
    ):
        self.api_token = api_token
        self.api_url = api_url
        self.api_username = api_username
        self.verbose = verbose

    @classmethod
    def matches_domain(cls, domain: str) -> bool:
        """Check if this provider handles the given domain."""
        domain_lower = domain.lower()
        return any(d in domain_lower for d in cls.domains)

    def get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests."""
        return {}

    @abstractmethod
    def build_api_url(self, owner: str, repo_name: str, domain: str) -> str:
        """Build the API URL for fetching repository metadata."""
        pass

    @abstractmethod
    def parse_repo_response(self, api_data: dict[str, Any]) -> dict[str, Any]:
        """Parse repository API response into standardized format."""
        pass

    def fetch_user_repos(self, username: str, domain: str) -> list[dict[str, Any]]:
        """
        Fetch all repositories for a user/organization.
        Returns empty list if not implemented.
        """
        return []

    def fetch_releases(
        self, owner: str, repo_name: str, domain: str
    ) -> list[dict[str, Any]]:
        """
        Fetch releases for a repository.
        Returns empty list if not implemented.
        """
        return []

    def _log(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
