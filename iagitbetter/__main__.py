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

__author__     = "Andres99"
__copyright__  = "Copyright 2025, Andres99"
__main_name__  = 'iagitbetter'
__license__    = 'GPLv3'
__status__     = "Production/Stable"
__version__    = "v1.0.3"

import os
import sys
import shutil
import argparse
import json
import urllib.request
from datetime import datetime

# Import from the iagitbetter module
try:
    from . import iagitbetter
except ImportError:
    import iagitbetter

PROGRAM_DESCRIPTION = '''A tool for archiving any git repository to the Internet Archive
                       An improved version of iagitup with support for all git providers
                       The script downloads the git repository, creates a git bundle, uploads
                       all files preserving structure, and archives to archive.org
                       Based on https://github.com/gdamdam/iagitup'''

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
        current_clean = current_version.lstrip('v')
        latest_version = get_latest_pypi_version("iagitbetter")
        
        if latest_version and latest_version != current_clean:
            # Simple version comparison (works for semantic versioning)
            current_parts = [int(x) for x in current_clean.split('.')]
            latest_parts = [int(x) for x in latest_version.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            
            if latest_parts > current_parts:
                print(f"Update available: {latest_version} (current is {current_version})")
                print(f"   Run: pip install --upgrade iagitbetter")
                print()
    except Exception:
        # Silently ignore any errors in version checking
        pass

# Configure argparser
parser = argparse.ArgumentParser(
    description=PROGRAM_DESCRIPTION,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  %(prog)s https://github.com/user/repo
  %(prog)s https://gitlab.com/user/repo
  %(prog)s https://bitbucket.org/user/repo
  %(prog)s --metadata="license:MIT,topic:python" https://github.com/user/repo
  %(prog)s --quiet https://github.com/user/repo
  %(prog)s --releases --all-releases https://github.com/user/repo
  %(prog)s --releases --latest-release https://github.com/user/repo
  %(prog)s --all-branches https://github.com/user/repo
  %(prog)s --all-branches --releases --all-releases https://github.com/user/repo

Key improvements over iagitup:
  - Works with ALL git providers (not just GitHub)
  - Uploads complete file structure (not just bundle)
  - Clean naming: {owner} - {repo}
  - Adds originalrepo and gitsite metadata
  - Preserves directory structure
  - Uses archive date for identifier consistency
  - Records first commit date as repository date
  - Shows detailed upload progress like tubeup
  - Downloads releases from supported git providers
  - Supports archiving all branches of a repository
  - Supports archiving specific branches only
    """
)

parser.add_argument('giturl', type=str, 
                   help='Git repository URL to archive (works with any git provider)')
parser.add_argument('--metadata', '-m', default=None, type=str, required=False, 
                   help="custom metadata to add to the archive.org item (format: key1:value1,key2:value2)")
parser.add_argument('--quiet', '-q', action='store_true',
                   help='Suppress verbose output (only show errors and final results)')
parser.add_argument('--version', '-v', action='version', version=__version__)
parser.add_argument('--bundle-only', action='store_true', 
                   help="only upload git bundle, not all files (iagitup compatibility mode)")
parser.add_argument('--no-update-check', action='store_true',
                   help='Skip checking for updates on PyPI')

release_group = parser.add_argument_group('release options', 'Download releases from supported git providers')
release_group.add_argument('--releases', action='store_true',
                          help='Download releases from the repository (GitHub, GitLab, etc)')
release_group.add_argument('--all-releases', action='store_true',
                          help='Download all releases')
release_group.add_argument('--latest-release', action='store_true',
                          help='Download only the latest release (default when used)')

branch_group = parser.add_argument_group('branch options', 'Archive multiple branches')
branch_group.add_argument('--all-branches', action='store_true',
                         help='Clone and archive all branches of the repository')

args = parser.parse_args()

def main():
    """Main entry point for iagitbetter"""
    
    # Validate argument combinations
    if args.all_releases and args.latest_release:
        print("Error: Cannot specify both --all-releases and --latest-release")
        sys.exit(1)
    
    if args.releases and not args.all_releases and not args.latest_release:
        # Default to latest release when --releases is specified without other options
        args.latest_release = True
    
    # Create archiver instance with verbose setting
    verbose = not args.quiet
    archiver = iagitbetter.GitArchiver(verbose=verbose)
    
    # Check IA credentials first
    archiver.check_ia_credentials()
    
    URL = args.giturl
    custom_metadata = args.metadata
    custom_meta_dict = None
    
    if verbose:
        print("=" * 60)
        print(f"{__main_name__} {__version__}")
        print("=" * 60)
        print()
        
        # Check for updates unless disabled
        if not args.no_update_check:
            check_for_updates(__version__, verbose=True)
    
    # Parse custom metadata if provided
    if custom_metadata is not None:
        custom_meta_dict = {}
        try:
            for meta in custom_metadata.split(','):
                if ':' in meta:
                    k, v = meta.split(':', 1)
                    custom_meta_dict[k.strip()] = v.strip()
        except Exception as e:
            print(f"Error parsing metadata: {e}")
            custom_meta_dict = None
    
    try:
        # Extract repository information
        if verbose:
            print(f"Analyzing repository: {URL}")
        archiver.extract_repo_info(URL)
        if verbose:
            print(f"   Repository: {archiver.repo_data['full_name']}")
            print(f"   Git Provider: {archiver.repo_data['git_site']}")
            
            # Show what will be archived
            archive_components = []
            archive_components.append("Repository files")
            if args.all_branches:
                archive_components.append("All branches")
            else:
                archive_components.append("Default branch")
            if args.releases:
                if args.all_releases:
                    archive_components.append("All releases")
                else:
                    archive_components.append("Latest release")
            print(f"   Will archive: {', '.join(archive_components)}")
            print()
        
        # Clone the repository
        if verbose:
            print(f"Downloading {URL} repository...")
        repo_path = archiver.clone_repository(URL, all_branches=args.all_branches)
        
        # Download releases if requested
        if args.releases:
            if verbose:
                print("Downloading releases...")
            archiver.download_releases(repo_path, all_releases=args.all_releases)
        
        # Upload to Internet Archive
        identifier, metadata = archiver.upload_to_ia(
            repo_path, 
            custom_metadata=custom_meta_dict,
            includes_releases=args.releases,
            includes_all_branches=args.all_branches
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
            if 'first_commit_date' in archiver.repo_data:
                print(f"First Commit Date: {archiver.repo_data['first_commit_date'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Archive Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Show additional metadata if available
            if metadata.get('stars'):
                print(f"Stars: {metadata['stars']}")
            if metadata.get('forks'):
                print(f"Forks: {metadata['forks']}")
            if metadata.get('language'):
                print(f"Primary Language: {metadata['language']}")
            if metadata.get('license'):
                print(f"License: {metadata['license']}")
            if metadata.get('topics'):
                print(f"Topics: {metadata['topics']}")
            
            # Show what was archived
            if args.all_branches:
                print(f"Branches: All branches archived")
            if args.releases:
                release_count = archiver.repo_data.get('downloaded_releases', 0)
                if args.all_releases:
                    print(f"Releases: {release_count} releases archived")
                else:
                    print(f"Releases: Latest release archived")
            
            print(f"Archived repository URL:")
            print(f"    https://archive.org/details/{identifier}")
            print(f"Archived git bundle file(s):")
            if args.all_branches:
                # Multiple bundles for all branches
                default_branch = archiver.repo_data.get('default_branch', 'main')
                branches = archiver.repo_data.get('branches', [])
                for branch in branches:
                    if branch == default_branch:
                        bundle_name = f"{archiver.repo_data['owner']}-{archiver.repo_data['repo_name']}"
                        print(f"    https://archive.org/download/{identifier}/{bundle_name}.bundle ({branch} - default)")
                    else:
                        bundle_name = f"{archiver.repo_data['owner']}-{archiver.repo_data['repo_name']}_{branch}"
                        print(f"    https://archive.org/download/{identifier}/{bundle_name}.bundle ({branch})")
            else:
                # Single bundle
                if args.branch:
                    bundle_name = f"{archiver.repo_data['owner']}-{archiver.repo_data['repo_name']}_{args.branch}"
                else:
                    bundle_name = f"{archiver.repo_data['owner']}-{archiver.repo_data['repo_name']}"
                print(f"    https://archive.org/download/{identifier}/{bundle_name}.bundle")
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
        sys.exit(1)
    finally:
        # Always cleanup
        archiver.cleanup()


if __name__ == '__main__':
    main()