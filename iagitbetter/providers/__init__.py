"""
Git provider implementations for various hosting platforms.

This module provides a unified interface for interacting with different
git hosting providers (GitHub, GitLab, Bitbucket, etc.).
"""

from __future__ import annotations

from typing import Type

from .base import BaseProvider
from .bitbucket import BitbucketProvider
from .gerrit import GerritProvider
from .gitea import GiteaProvider
from .gitee import GiteeProvider
from .github import GistProvider, GitHubProvider
from .gitlab import GitLabProvider
from .gogs import GogsProvider
from .launchpad import LaunchpadProvider
from .sourceforge import SourceForgeProvider

# Registry of all available providers
PROVIDERS: list[Type[BaseProvider]] = [
    GitHubProvider,
    GistProvider,
    GitLabProvider,
    BitbucketProvider,
    GiteaProvider,
    GiteeProvider,
    GogsProvider,
    SourceForgeProvider,
    GerritProvider,
    LaunchpadProvider,
]

# Map of provider names to classes
PROVIDER_BY_NAME: dict[str, Type[BaseProvider]] = {
    provider.name: provider for provider in PROVIDERS
}
# Add aliases for providers
PROVIDER_BY_NAME["codeberg"] = GiteaProvider  # Codeberg uses Gitea API


def get_provider_for_domain(
    domain: str,
    api_token: str | None = None,
    api_url: str | None = None,
    api_username: str | None = None,
    verbose: bool = True,
) -> BaseProvider | None:
    """
    Get the appropriate provider instance for a given domain.

    Args:
        domain: The domain name (e.g., "github.com", "gitlab.com")
        api_token: Optional API token for authentication
        api_url: Optional custom API URL
        api_username: Optional username (for Bitbucket basic auth)
        verbose: Whether to enable verbose output

    Returns:
        Provider instance or None if no matching provider is found
    """
    domain_lower = domain.lower()

    for provider_class in PROVIDERS:
        if provider_class.matches_domain(domain_lower):
            return provider_class(
                api_token=api_token,
                api_url=api_url,
                api_username=api_username,
                verbose=verbose,
            )

    return None


def get_provider_by_name(
    name: str,
    api_token: str | None = None,
    api_url: str | None = None,
    api_username: str | None = None,
    verbose: bool = True,
) -> BaseProvider | None:
    """
    Get a provider instance by its name.

    Args:
        name: The provider name (e.g., "github", "gitlab")
        api_token: Optional API token for authentication
        api_url: Optional custom API URL
        api_username: Optional username (for Bitbucket basic auth)
        verbose: Whether to enable verbose output

    Returns:
        Provider instance or None if no matching provider is found
    """
    provider_class = PROVIDER_BY_NAME.get(name.lower())
    if provider_class:
        return provider_class(
            api_token=api_token,
            api_url=api_url,
            api_username=api_username,
            verbose=verbose,
        )
    return None


def detect_git_site(domain: str, explicit_type: str | None = None) -> str:
    """
    Detect the git site type from domain or explicit type.

    Args:
        domain: The domain name
        explicit_type: Explicitly specified provider type

    Returns:
        The detected git site name
    """
    if explicit_type:
        return explicit_type.lower()

    domain_lower = domain.lower()

    # Check for gist first (more specific)
    if domain_lower == "gist.github.com":
        return "gist"

    # Special case for codeberg.org - should return "codeberg" not "gitea"
    if domain_lower == "codeberg.org":
        return "codeberg"

    # Check each provider's domains
    for provider_class in PROVIDERS:
        if provider_class.matches_domain(domain_lower):
            return provider_class.name

    # Fallback: use first part of domain or "git"
    if "." in domain:
        return domain.split(".")[0]
    return "git"


__all__ = [
    # Base class
    "BaseProvider",
    # Provider classes
    "GitHubProvider",
    "GistProvider",
    "GitLabProvider",
    "BitbucketProvider",
    "GiteaProvider",
    "GiteeProvider",
    "GogsProvider",
    "SourceForgeProvider",
    "GerritProvider",
    "LaunchpadProvider",
    # Registry
    "PROVIDERS",
    "PROVIDER_BY_NAME",
    # Helper functions
    "get_provider_for_domain",
    "get_provider_by_name",
    "detect_git_site",
]
