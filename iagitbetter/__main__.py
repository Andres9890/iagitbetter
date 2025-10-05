#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# iagitbetter - Archiving any git repository to the Internet Archive

# Copyright (C) 2025 Andres99
# Based on iagitup Copyright (C) 2017-2018 Giovanni Damiola
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

__author__ = "Andres99"
__copyright__ = "Copyright 2025, Andres99"
__main_name__ = "iagitbetter"
__license__ = "GPLv3"
__status__ = "Production/Stable"
from . import __version_v__

__version__ = __version_v__

import argparse
import json
import sys
import urllib.request
from datetime import datetime

# Import from the iagitbetter module
try:
    from . import iagitbetter
except ImportError:
    import iagitbetter

PROGRAM_DESCRIPTION = """A tool for archiving any git repository to the Internet Archive
                       An improved version of iagitup with support for all git providers
                       The script downloads the git repository, creates a git bundle, uploads
                       all files preserving structure, and archives to archive.org

                       Supports archiving individual repositories or entire user/org profiles

                       Based on https://github.com/gdamdam/iagitup"""


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
                    f"Update available: {latest_version} (Upgrade with pip install --upgrade iagitbetter)"
                )
                print("   Run: pip install --upgrade iagitbetter")
                print()
    except Exception:
        # Silently ignore any errors in version checking
        pass


# Configure argparser
def build_argument_parser():
    """Create the argument parser used by the CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description=PROGRAM_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single repository archiving
  %(prog)s https://github.com/user/repo
  %(prog)s https://gitlab.com/user/repo
  %(prog)s https://bitbucket.org/user/repo
  %(prog)s --metadata="license:MIT,topic:python" https://github.com/user/repo
  %(prog)s --quiet https://github.com/user/repo
  %(prog)s --releases --all-releases https://github.com/user/repo
  %(prog)s --releases --latest-release https://github.com/user/repo
  %(prog)s --all-branches https://github.com/user/repo
  %(prog)s --branch develop https://github.com/user/repo
  %(prog)s --all-branches --releases --all-releases https://github.com/user/repo
  %(prog)s --no-repo-info https://github.com/user/repo

  # User/Organization profile archiving
  %(prog)s https://github.com/username
  %(prog)s https://gitlab.com/organization
  %(prog)s https://github.com/username --skip-forks --skip-archived
  %(prog)s https://github.com/username --max-repos 10
  %(prog)s https://github.com/username --skip-private --releases
  %(prog)s https://codeberg.org/username --all-branches

  # Self-hosted repositories
  %(prog)s --git-provider-type gitlab --api-url https://gitlab.example.com/api/v4 https://git.example.com/user/repo
  %(prog)s --git-provider-type gitea --api-token example https://git.example.com/user/repo
  %(prog)s --git-provider-type gitlab --api-token example --all-branches --releases https://gitlab.example.com/user/repo

  # Self-hosted profile archiving
  %(prog)s --git-provider-type gitlab --api-token TOKEN https://gitlab.example.com/username
  %(prog)s --git-provider-type gitea https://git.example.com/organization --skip-forks

Key improvements over iagitup:
  - Works with ALL git providers (not just GitHub)
  - Self-hosted git instance support (GitLab, Gitea, Forgejo, etc.)
  - Profile archiving - archive all repos from a user/org
  - Uploads complete file structure (not just bundle)
  - Preserves important directories (.github/, .gitlab/, .gitea/)
  - Clean naming: {owner} - {repo}
  - Adds originalrepo and gitsite metadata
  - Preserves directory structure
  - Uses archive date for identifier consistency
  - Records first commit date as repository date
  - Shows detailed upload progress like tubeup
  - Downloads releases from supported git providers
  - Supports archiving all branches of a repository
  - API token authentication for private repositories
  - Creates repository info JSON with all metadata
    """,
    )

    parser.add_argument(
        "giturl",
        type=str,
        help="Git repository URL or user/organization profile URL to archive",
    )
    parser.add_argument(
        "--metadata",
        "-m",
        default=None,
        type=str,
        required=False,
        help="custom metadata to add to the archive.org item (format: key1:value1,key2:value2)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress verbose output (only show errors and final results)",
    )
    parser.add_argument("--version", "-v", action="version", version=__version__)
    parser.add_argument(
        "--bundle-only",
        action="store_true",
        help="only upload git bundle, not all files (iagitup compatibility mode)",
    )
    parser.add_argument(
        "--no-update-check",
        action="store_true",
        help="Skip checking for updates on PyPI",
    )
    parser.add_argument(
        "--no-repo-info",
        action="store_true",
        help="Skip creating the repository info JSON file",
    )

    release_group = parser.add_argument_group(
        "release options", "Download releases from supported git providers"
    )
    release_group.add_argument(
        "--releases",
        action="store_true",
        help="Download releases from the repository (GitHub, GitLab, etc)",
    )
    release_group.add_argument(
        "--all-releases", action="store_true", help="Download all releases"
    )
    release_group.add_argument(
        "--latest-release",
        action="store_true",
        help="Download only the latest release (default when used)",
    )

    branch_group = parser.add_argument_group(
        "branch options", "Archive multiple branches"
    )
    branch_group.add_argument(
        "--all-branches",
        action="store_true",
        help="Clone and archive all branches of the repository",
    )
    branch_group.add_argument(
        "--branch",
        type=str,
        help="Clone and archive a specific branch of the repository",
    )

    profile_group = parser.add_argument_group(
        "profile archiving options", "Options for archiving user/org profiles"
    )
    profile_group.add_argument(
        "--skip-forks",
        action="store_true",
        help="Skip forked repositories when archiving profiles",
    )
    profile_group.add_argument(
        "--skip-archived",
        action="store_true",
        help="Skip archived repositories when archiving profiles",
    )
    profile_group.add_argument(
        "--skip-private",
        action="store_true",
        help="Skip private repositories when archiving profiles",
    )
    profile_group.add_argument(
        "--max-repos",
        type=int,
        help="Maximum number of repositories to archive from a profile",
    )

    selfhosted_group = parser.add_argument_group(
        "self-hosted instance options", "Options for self-hosted git instances"
    )
    selfhosted_group.add_argument(
        "--git-provider-type",
        type=str,
        choices=["github", "gitlab", "gitea", "bitbucket"],
        help="Specify the git provider type for self-hosted instances",
    )
    selfhosted_group.add_argument(
        "--api-url",
        type=str,
        help="Custom API URL for self-hosted instances (e.g., https://git.example.com/api/v1)",
    )
    selfhosted_group.add_argument(
        "--api-token",
        type=str,
        help="API token for authentication with private/self-hosted repositories",
    )
    selfhosted_group.add_argument(
        "--api-username",
        type=str,
        help="Username for Bitbucket App Passwords (used with --api-token for basic auth)",
    )

    return parser


def parse_args(argv=None):
    """Parse command line arguments.

    Exposed as a helper to make testing the CLI easier while avoiding side
    effects when the module is imported.
    """

    parser = build_argument_parser()
    return parser.parse_args(argv)


def archive_single_repository(archiver, url, args, verbose):
    """Archive a single repository"""
    try:
        # Extract repository information
        if verbose:
            print(f"Analyzing repository: {url}")
        archiver.extract_repo_info(url)
        if verbose:
            print(f"   Repository: {archiver.repo_data['full_name']}")
            print(f"   Git Provider: {archiver.repo_data['git_site']}")

            # Show what will be archived
            archive_components = []
            if args.bundle_only:
                archive_components.append("Git bundle only")
            else:
                archive_components.append("Repository files")
                if args.all_branches:
                    archive_components.append("All branches")
                elif args.branch:
                    archive_components.append(f"Branch: {args.branch}")
                else:
                    archive_components.append("Default branch")
                if args.releases:
                    if args.all_releases:
                        archive_components.append("All releases")
                    else:
                        archive_components.append("Latest release")
            if not args.no_repo_info:
                archive_components.append("Repository info file")
            print(f"   Will archive: {', '.join(archive_components)}")
            print()

        # Clone the repository
        if verbose:
            print(f"Downloading {url} repository...")
        repo_path = archiver.clone_repository(
            url, all_branches=args.all_branches, specific_branch=args.branch
        )

        # Download releases if requested (skip for bundle-only mode)
        if args.releases and not args.bundle_only:
            if verbose:
                print("Downloading releases...")
            archiver.download_releases(repo_path, all_releases=args.all_releases)

        # Upload to Internet Archive
        identifier, metadata = archiver.upload_to_ia(
            repo_path,
            custom_metadata=archiver.parse_custom_metadata(args.metadata),
            includes_releases=args.releases and not args.bundle_only,
            includes_all_branches=args.all_branches,
            specific_branch=args.branch,
            bundle_only=args.bundle_only,
            create_repo_info=not args.no_repo_info,
        )

        return identifier, metadata

    except Exception as e:
        print(f"   Error archiving repository: {e}")
        return None, None


def archive_profile(archiver, url, args, verbose):
    """Archive all repositories from a user/organization profile"""
    # Parse the profile URL to get the username
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]

    if len(path_parts) != 1:
        print(f"Error: Invalid profile URL: {url}")
        print(
            "Profile URLs should have only one path component (username/organization)"
        )
        return []

    username = path_parts[0]
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    # Set up archiver with domain info for API calls
    archiver.repo_data = {"domain": domain}
    if archiver.git_provider_type:
        archiver.repo_data["git_site"] = archiver.git_provider_type
    elif "github" in domain:
        archiver.repo_data["git_site"] = "github"
    elif "gitlab" in domain:
        archiver.repo_data["git_site"] = "gitlab"
    elif "codeberg" in domain:
        archiver.repo_data["git_site"] = "codeberg"
    elif "gitea" in domain:
        archiver.repo_data["git_site"] = "gitea"
    elif "bitbucket" in domain:
        archiver.repo_data["git_site"] = "bitbucket"
    else:
        archiver.repo_data["git_site"] = "git"

    if verbose:
        print("=" * 60)
        print(f"PROFILE ARCHIVING MODE")
        print("=" * 60)
        print(f"Username/Organization: {username}")
        print(f"Git Provider: {archiver.repo_data['git_site']}")
        print()

    # Fetch all repositories
    if verbose:
        print("Fetching repositories from profile...")
    repositories = archiver.fetch_user_repositories(username)

    if not repositories:
        print("No repositories found for this profile")
        return []

    # Apply filters
    original_count = len(repositories)
    filtered_repos = repositories

    if args.skip_forks:
        filtered_repos = [r for r in filtered_repos if not r.get("fork", False)]
        if verbose:
            print(
                f"   Filtered out {original_count - len(filtered_repos)} forked repositories"
            )

    if args.skip_archived:
        before_filter = len(filtered_repos)
        filtered_repos = [r for r in filtered_repos if not r.get("archived", False)]
        if verbose and before_filter != len(filtered_repos):
            print(
                f"   Filtered out {before_filter - len(filtered_repos)} archived repositories"
            )

    if args.skip_private:
        before_filter = len(filtered_repos)
        filtered_repos = [r for r in filtered_repos if not r.get("private", False)]
        if verbose and before_filter != len(filtered_repos):
            print(
                f"   Filtered out {before_filter - len(filtered_repos)} private repositories"
            )

    if args.max_repos and len(filtered_repos) > args.max_repos:
        filtered_repos = filtered_repos[: args.max_repos]
        if verbose:
            print(f"   Limiting to {args.max_repos} repositories")

    if verbose:
        print(f"\nWill archive {len(filtered_repos)} repositories")
        print()

    # Archive each repository
    results = []
    successful = 0
    failed = 0

    for i, repo in enumerate(filtered_repos, 1):
        repo_name = repo["full_name"]
        clone_url = repo["clone_url"]

        if verbose:
            print("=" * 60)
            print(f"Repository {i}/{len(filtered_repos)}: {repo_name}")
            print("=" * 60)

        # Create new archiver instance for each repo to avoid state conflicts
        repo_archiver = iagitbetter.GitArchiver(
            verbose=verbose,
            git_provider_type=archiver.git_provider_type,
            api_url=archiver.api_url,
            api_token=archiver.api_token,
            api_username=archiver.api_username,
        )

        identifier, metadata = archive_single_repository(
            repo_archiver, clone_url, args, verbose
        )

        if identifier:
            successful += 1
            results.append(
                {"repo": repo_name, "identifier": identifier, "success": True}
            )
            if verbose:
                print(f"  Successfully archived: {repo_name}")
                print(f"   URL: https://archive.org/details/{identifier}")
        else:
            failed += 1
            results.append({"repo": repo_name, "identifier": None, "success": False})
            if verbose:
                print(f"  Failed to archive: {repo_name}")

        # Cleanup after each repository
        repo_archiver.cleanup()

        if verbose:
            print()

    # Print summary
    print("\n" + "=" * 60)
    print("PROFILE ARCHIVING SUMMARY")
    print("=" * 60)
    print(f"Username/Organization: {username}")
    print(f"Total repositories found: {original_count}")
    print(f"Repositories archived: {len(filtered_repos)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    if args.skip_forks or args.skip_archived or args.skip_private or args.max_repos:
        print("\nFilters applied:")
        if args.skip_forks:
            print("  Skipped forks")
        if args.skip_archived:
            print("  Skipped archived repositories")
        if args.skip_private:
            print("  Skipped private repositories")
        if args.max_repos:
            print(f"  Limited to {args.max_repos} repositories")

    if successful > 0:
        print("\nSuccessfully archived repositories:")
        for result in results:
            if result["success"]:
                print(f"  {result['repo']}")
                print(f"    https://archive.org/details/{result['identifier']}")

    if failed > 0:
        print("\nFailed to archive:")
        for result in results:
            if not result["success"]:
                print(f"  {result['repo']}")

    print("=" * 60)

    return results


def main(argv=None):
    """Main entry point for iagitbetter"""

    args = parse_args(argv)

    # Validate argument combinations
    if args.all_releases and args.latest_release:
        print("Error: Cannot specify both --all-releases and --latest-release")
        sys.exit(1)

    if args.all_branches and args.branch:
        print("Error: Cannot specify both --all-branches and --branch")
        sys.exit(1)

    if args.releases and not args.all_releases and not args.latest_release:
        # Default to latest release when --releases is specified without other options
        args.latest_release = True

    # Create archiver instance with verbose setting and self-hosted parameters
    verbose = not args.quiet
    archiver = iagitbetter.GitArchiver(
        verbose=verbose,
        git_provider_type=(
            args.git_provider_type if hasattr(args, "git_provider_type") else None
        ),
        api_url=args.api_url if hasattr(args, "api_url") else None,
        api_token=args.api_token if hasattr(args, "api_token") else None,
        api_username=args.api_username if hasattr(args, "api_username") else None,
    )

    # Check IA credentials first
    archiver.check_ia_credentials()

    URL = args.giturl

    if verbose:
        print("=" * 60)
        print(f"{__main_name__} {__version__}")
        print("=" * 60)
        print()

        # Check for updates unless disabled
        if not args.no_update_check:
            check_for_updates(__version__, verbose=True)

    try:
        # Determine if this is a profile URL or repository URL
        if archiver.is_profile_url(URL):
            # Profile archiving mode
            results = archive_profile(archiver, URL, args, verbose)
        else:
            # Single repository archiving mode
            identifier, metadata = archive_single_repository(
                archiver, URL, args, verbose
            )

            # Output results
            if identifier:
                print("\nUpload finished, Item information:")
                print("=" * 60)
                print(f"Title: {metadata['title']}")
                print(f"Identifier: {identifier}")
                print(f"Git Provider: {metadata['gitsite']}")
                print(f"Original Repository: {metadata['originalrepo']}")

                # Show dates information
                if "first_commit_date" in archiver.repo_data:
                    print(
                        f"First Commit Date: {archiver.repo_data['first_commit_date'].strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                print(f"Archive Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # Show additional metadata if available
                if metadata.get("stars"):
                    print(f"Stars: {metadata['stars']}")
                if metadata.get("forks"):
                    print(f"Forks: {metadata['forks']}")
                if metadata.get("language"):
                    print(f"Primary Language: {metadata['language']}")
                if metadata.get("license"):
                    print(f"License: {metadata['license']}")
                if metadata.get("topics"):
                    print(f"Topics: {metadata['topics']}")

                # Show what was archived
                if args.bundle_only:
                    print("Archive mode: Bundle only")
                else:
                    if args.all_branches:
                        branch_count = archiver.repo_data.get("branch_count", 0)
                        branches = archiver.repo_data.get("branches", [])
                        default_branch = archiver.repo_data.get(
                            "default_branch", "main"
                        )
                        branches_dir = archiver.repo_data.get("branches_dir_name", "")
                        print(f"Branches: {branch_count} branches archived")
                        print(
                            f"   Default branch ({default_branch}): Files in root directory"
                        )
                        other_branches = [b for b in branches if b != default_branch]
                        if other_branches and branches_dir:
                            print(
                                f"   Other branches: {', '.join(other_branches)} (organized in {branches_dir}/)"
                            )
                    elif args.branch:
                        print(f"Branch: {args.branch} archived")
                    if args.releases:
                        release_count = archiver.repo_data.get("downloaded_releases", 0)
                        releases_dir = archiver.repo_data.get(
                            "releases_dir_name", "releases"
                        )
                        if args.all_releases:
                            print(
                                f"Releases: {release_count} releases archived in {releases_dir}/"
                            )
                        else:
                            print(
                                f"Releases: Latest release archived in {releases_dir}/"
                            )

                print("Archived repository URL:")
                print(f"    https://archive.org/details/{identifier}")
                print("Archived git bundle file:")
                bundle_name = (
                    f"{archiver.repo_data['owner']}-{archiver.repo_data['repo_name']}"
                )
                print(
                    f"    https://archive.org/download/{identifier}/{bundle_name}.bundle"
                )

                print("=" * 60)
                print("Archive complete")
                print()
            else:
                print("\nUpload failed. Please check the errors above")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Always cleanup
        archiver.cleanup()


if __name__ == "__main__":
    main()
