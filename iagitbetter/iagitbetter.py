#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iagitbetter - Archive any git repository to the Internet Archive
Improved version with support for all git providers and full file preservation
"""

__version__ = "1.0.5"
__author__ = "iagitbetter"
__license__ = "GPL-3.0"

import os
import sys
import shutil
import argparse
import json
import tempfile
import re
import subprocess
import stat
import urllib.request
import zipfile
import tarfile
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
import requests
import internetarchive
from internetarchive.config import parse_config_file
import git
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
                print(f"Update available: {latest_version} (current is v{current_version})")
                print(f"   upgrade with: pip install --upgrade iagitbetter")
                print()
    except Exception:
        # Silently ignore any errors in version checking
        pass

class GitArchiver:
    def __init__(self, verbose=True, ia_config_path=None, git_provider_type=None, api_url=None, api_token=None):
        self.temp_dir = None
        self.repo_data = {}
        self.verbose = verbose
        self.ia_config_path = ia_config_path
        self.git_provider_type = git_provider_type  # e.g., 'github', 'gitlab', 'gitea'
        self.api_url = api_url  # Custom API URL for self-hosted instances
        self.api_token = api_token  # API token for authentication
        
    def extract_repo_info(self, repo_url):
        """Extract repository information from any git URL"""
        # Parse the URL
        parsed = urlparse(repo_url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Detect git provider type
        if not self.git_provider_type:
            # Auto-detect based on domain
            if 'github' in domain:
                git_site = 'github'
            elif 'gitlab' in domain:
                git_site = 'gitlab'
            elif 'bitbucket' in domain:
                git_site = 'bitbucket'
            elif 'codeberg' in domain:
                git_site = 'codeberg'
            elif 'gitea' in domain:
                git_site = 'gitea'
            else:
                # For unknown/self-hosted, use domain name or 'git'
                git_site = domain.split('.')[0] if '.' in domain else 'git'
        else:
            git_site = self.git_provider_type
        
        # Extract path components
        path_parts = parsed.path.strip('/').split('/')
        
        # Handle different URL formats
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo_name = path_parts[1].replace('.git', '')
        else:
            # Fallback for unusual URLs
            owner = "unknown"
            repo_name = path_parts[0].replace('.git', '') if path_parts else "repository"
        
        self.repo_data = {
            'url': repo_url,
            'domain': domain,
            'git_site': git_site,
            'owner': owner,
            'repo_name': repo_name,
            'full_name': f"{owner}/{repo_name}",
            'releases': [],
            'downloaded_releases': 0
        }
        
        # Try to fetch additional metadata from API if available
        self._fetch_api_metadata()
        
        return self.repo_data
    
    def _build_api_url(self):
        """Build API URL for self-hosted or public instances"""
        domain = self.repo_data['domain']
        owner = self.repo_data['owner']
        repo_name = self.repo_data['repo_name']
        
        # If custom API URL is provided, use it
        if self.api_url:
            # Replace placeholders if present
            return self.api_url.rstrip('/') + f"/repos/{owner}/{repo_name}"
        
        # Otherwise, use standard endpoints based on detected provider
        git_site = self.repo_data['git_site']
        
        if git_site == 'github' or domain == 'github.com':
            return f"https://api.github.com/repos/{owner}/{repo_name}"
        elif git_site == 'gitlab' or domain == 'gitlab.com':
            return f"https://gitlab.com/api/v4/projects/{owner}%2F{repo_name}"
        elif git_site == 'bitbucket' or domain == 'bitbucket.org':
            return f"https://api.bitbucket.org/2.0/repositories/{owner}/{repo_name}"
        elif git_site in ['codeberg', 'gitea'] or 'gitea' in domain or domain == 'codeberg.org':
            # For self-hosted Gitea/Forgejo instances
            base_url = f"https://{domain}"
            return f"{base_url}/api/v1/repos/{owner}/{repo_name}"
        else:
            # Try Gitea API format as fallback for unknown self-hosted instances
            base_url = f"https://{domain}"
            return f"{base_url}/api/v1/repos/{owner}/{repo_name}"
    
    def _fetch_api_metadata(self):
        """Try to fetch metadata from various git provider APIs"""
        try:
            api_url = self._build_api_url()
            
            # Prepare headers for authentication
            headers = {}
            if self.api_token:
                git_site = self.repo_data.get('git_site', '')
                if git_site == 'github' or 'github' in self.repo_data['domain']:
                    headers['Authorization'] = f'token {self.api_token}'
                elif git_site == 'gitlab' or 'gitlab' in self.repo_data['domain']:
                    headers['PRIVATE-TOKEN'] = self.api_token
                else:
                    # Generic bearer token for other providers
                    headers['Authorization'] = f'token {self.api_token}'
            
            if self.verbose:
                print(f"   Fetching metadata from API...")
            
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                api_data = response.json()
                self._parse_api_response(api_data)
            elif response.status_code == 404:
                if self.verbose:
                    print(f"   Note: Repository not found via API (may be private or API not available)")
            elif response.status_code == 401:
                if self.verbose:
                    print(f"   Note: API authentication required. Use --api-token for private repositories")
            else:
                if self.verbose:
                    print(f"   Note: Could not fetch API metadata (status {response.status_code})")
        except Exception as e:
            if self.verbose:
                print(f"   Note: Could not fetch API metadata: {e}")
    
    def _parse_api_response(self, api_data):
        """Parse API response based on the git provider"""
        # Detect provider type from response structure if not already known
        if 'stargazers_count' in api_data and 'clone_url' in api_data:
            # GitHub-like API
            self._parse_github_response(api_data)
        elif 'star_count' in api_data and 'path_with_namespace' in api_data:
            # GitLab-like API
            self._parse_gitlab_response(api_data)
        elif 'scm' in api_data and api_data.get('scm') in ['git', 'hg']:
            # Bitbucket API
            self._parse_bitbucket_response(api_data)
        elif 'stars_count' in api_data:
            # Gitea/Forgejo API
            self._parse_gitea_response(api_data)
        else:
            # Try to extract common fields
            self._parse_generic_response(api_data)
    
    def _parse_github_response(self, api_data):
        """Parse GitHub API response"""
        self.repo_data.update({
            'description': api_data.get('description', ''),
            'created_at': api_data.get('created_at', ''),
            'updated_at': api_data.get('updated_at', ''),
            'pushed_at': api_data.get('pushed_at', ''),
            'language': api_data.get('language', ''),
            'stars': api_data.get('stargazers_count', 0),
            'forks': api_data.get('forks_count', 0),
            'watchers': api_data.get('watchers_count', 0),
            'subscribers': api_data.get('subscribers_count', 0),
            'open_issues': api_data.get('open_issues_count', 0),
            'homepage': api_data.get('homepage', ''),
            'topics': api_data.get('topics', []),
            'license': api_data.get('license', {}).get('name', '') if api_data.get('license') else '',
            'default_branch': api_data.get('default_branch', 'main'),
            'has_wiki': api_data.get('has_wiki', False),
            'has_pages': api_data.get('has_pages', False),
            'has_projects': api_data.get('has_projects', False),
            'has_issues': api_data.get('has_issues', False),
            'archived': api_data.get('archived', False),
            'disabled': api_data.get('disabled', False),
            'private': api_data.get('private', False),
            'fork': api_data.get('fork', False),
            'size': api_data.get('size', 0),
            'network_count': api_data.get('network_count', 0),
            'clone_url': api_data.get('clone_url', ''),
            'ssh_url': api_data.get('ssh_url', ''),
            'svn_url': api_data.get('svn_url', ''),
            'mirror_url': api_data.get('mirror_url', ''),
            'visibility': api_data.get('visibility', 'public'),
            'avatar_url': api_data.get('owner', {}).get('avatar_url', '') if api_data.get('owner') else ''
        })
    
    def _parse_gitlab_response(self, api_data):
        """Parse GitLab API response"""
        # Handle GitLab avatar URL - prefer project-level, then namespace, handle relative URLs
        avatar_url = ''
        
        # Try project-level avatar first
        if api_data.get('avatar_url'):
            avatar_url = api_data['avatar_url']
        # Fall back to namespace avatar for group-owned projects
        elif api_data.get('namespace', {}).get('avatar_url'):
            avatar_url = api_data['namespace']['avatar_url']
        
        # Handle relative URLs by prefixing with instance URL
        if avatar_url and not avatar_url.startswith(('http://', 'https://')):
            instance_url = f"https://{self.repo_data['domain']}"
            avatar_url = f"{instance_url}{avatar_url}" if avatar_url.startswith('/') else f"{instance_url}/{avatar_url}"
        
        self.repo_data.update({
            'description': api_data.get('description', ''),
            'created_at': api_data.get('created_at', ''),
            'updated_at': api_data.get('updated_at', ''),
            'pushed_at': api_data.get('last_activity_at', ''),
            'stars': api_data.get('star_count', 0),
            'forks': api_data.get('forks_count', 0),
            'topics': api_data.get('topics', []),
            'default_branch': api_data.get('default_branch', 'main'),
            'archived': api_data.get('archived', False),
            'private': api_data.get('visibility', 'public') != 'public',
            'fork': api_data.get('forked_from_project') is not None,
            'open_issues': api_data.get('open_issues_count', 0),
            'has_wiki': api_data.get('wiki_enabled', False),
            'has_pages': api_data.get('pages_enabled', False),
            'has_issues': api_data.get('issues_enabled', False),
            'clone_url': api_data.get('http_url_to_repo', ''),
            'ssh_url': api_data.get('ssh_url_to_repo', ''),
            'web_url': api_data.get('web_url', ''),
            'namespace': api_data.get('namespace', {}).get('name', ''),
            'path_with_namespace': api_data.get('path_with_namespace', ''),
            'visibility': api_data.get('visibility', 'public'),
            'merge_requests_enabled': api_data.get('merge_requests_enabled', False),
            'ci_enabled': api_data.get('builds_enabled', False),
            'shared_runners_enabled': api_data.get('shared_runners_enabled', False),
            'avatar_url': avatar_url,
            'project_id': api_data.get('id', '')
        })
    
    def _parse_bitbucket_response(self, api_data):
        """Parse Bitbucket API response"""
        self.repo_data.update({
            'description': api_data.get('description', ''),
            'created_at': api_data.get('created_on', ''),
            'updated_at': api_data.get('updated_on', ''),
            'language': api_data.get('language', ''),
            'private': api_data.get('is_private', False),
            'fork': api_data.get('parent') is not None,
            'size': api_data.get('size', 0),
            'has_wiki': api_data.get('has_wiki', False),
            'has_issues': api_data.get('has_issues', False),
            'clone_url': api_data.get('links', {}).get('clone', [{}])[0].get('href', ''),
            'homepage': api_data.get('website', ''),
            'scm': api_data.get('scm', 'git'),
            'mainbranch': api_data.get('mainbranch', {}).get('name', 'main'),
            'project': api_data.get('project', {}).get('name', '') if api_data.get('project') else '',
            'owner_type': api_data.get('owner', {}).get('type', ''),
            'owner_display_name': api_data.get('owner', {}).get('display_name', ''),
            'avatar_url': api_data.get('owner', {}).get('links', {}).get('avatar', {}).get('href', '') if api_data.get('owner') else ''
        })
    
    def _parse_gitea_response(self, api_data):
        """Parse Gitea/Forgejo API response"""
        self.repo_data.update({
            'description': api_data.get('description', ''),
            'created_at': api_data.get('created_at', ''),
            'updated_at': api_data.get('updated_at', ''),
            'language': api_data.get('language', ''),
            'stars': api_data.get('stars_count', 0),
            'forks': api_data.get('forks_count', 0),
            'watchers': api_data.get('watchers_count', 0),
            'open_issues': api_data.get('open_issues_count', 0),
            'homepage': api_data.get('website', ''),
            'default_branch': api_data.get('default_branch', 'main'),
            'archived': api_data.get('archived', False),
            'private': api_data.get('private', False),
            'fork': api_data.get('fork', False),
            'size': api_data.get('size', 0),
            'has_wiki': api_data.get('has_wiki', False),
            'has_issues': api_data.get('has_issues', False),
            'has_projects': api_data.get('has_projects', False),
            'has_pull_requests': api_data.get('has_pull_requests', False),
            'clone_url': api_data.get('clone_url', ''),
            'ssh_url': api_data.get('ssh_url', ''),
            'html_url': api_data.get('html_url', ''),
            'mirror': api_data.get('mirror', False),
            'template': api_data.get('template', False),
            'empty': api_data.get('empty', False),
            'permissions': api_data.get('permissions', {}),
            'internal_tracker': api_data.get('internal_tracker', {}),
            'external_tracker': api_data.get('external_tracker', {}),
            'external_wiki': api_data.get('external_wiki', {}),
            'avatar_url': api_data.get('owner', {}).get('avatar_url', '') if api_data.get('owner') else ''
        })
    
    def _parse_generic_response(self, api_data):
        """Parse generic API response for unknown providers"""
        # Extract common fields that might exist
        self.repo_data.update({
            'description': api_data.get('description', ''),
            'default_branch': api_data.get('default_branch', api_data.get('main_branch', 'main')),
            'private': api_data.get('private', api_data.get('is_private', False)),
            'fork': api_data.get('fork', api_data.get('is_fork', False)),
            'archived': api_data.get('archived', False),
        })
    
    def download_avatar(self, repo_path):
        """Download user avatar if available and save with username as filename"""
        avatar_url = self.repo_data.get('avatar_url', '')
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
            content_type = response.headers.get('content-type', '').lower()
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                # Try to guess from URL
                if avatar_url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    ext = '.' + avatar_url.split('.')[-1].lower()
                else:
                    ext = '.jpg'  # Default fallback
            
            # Save with username as filename
            username = self.repo_data['owner']
            avatar_filename = f"{username}{ext}"
            avatar_path = os.path.join(repo_path, avatar_filename)
            
            with open(avatar_path, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            
            if self.verbose:
                print(f"   Avatar saved as: {avatar_filename}")
            
            return avatar_filename
            
        except Exception as e:
            if self.verbose:
                print(f"   Could not download avatar: {e}")
            return None
    
    def fetch_releases(self):
        """Fetch releases from the git provider API"""
        domain = self.repo_data['domain']
        owner = self.repo_data['owner']
        repo_name = self.repo_data['repo_name']
        
        releases = []
        
        try:
            if domain == 'github.com' or self.repo_data['git_site'] == 'github':
                # GitHub releases API
                url = f"https://api.github.com/repos/{owner}/{repo_name}/releases"
                headers = {}
                if self.api_token and 'github' in domain:
                    headers['Authorization'] = f'token {self.api_token}'
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    api_releases = response.json()
                    for release in api_releases:
                        release_data = {
                            'id': release.get('id'),
                            'tag_name': release.get('tag_name'),
                            'name': release.get('name', release.get('tag_name')),
                            'body': release.get('body', ''),
                            'draft': release.get('draft', False),
                            'prerelease': release.get('prerelease', False),
                            'published_at': release.get('published_at'),
                            'zipball_url': release.get('zipball_url'),
                            'tarball_url': release.get('tarball_url'),
                            'assets': []
                        }
                        
                        # Add assets
                        for asset in release.get('assets', []):
                            release_data['assets'].append({
                                'name': asset.get('name'),
                                'download_url': asset.get('browser_download_url'),
                                'size': asset.get('size'),
                                'content_type': asset.get('content_type')
                            })
                        
                        releases.append(release_data)
            
            elif domain == 'gitlab.com' or self.repo_data['git_site'] == 'gitlab':
                # GitLab releases API
                project_id = self.repo_data.get('project_id')
                if project_id:
                    url = f"https://gitlab.com/api/v4/projects/{project_id}/releases"
                    headers = {}
                    if self.api_token:
                        headers['PRIVATE-TOKEN'] = self.api_token
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        api_releases = response.json()
                        for release in api_releases:
                            release_data = {
                                'tag_name': release.get('tag_name'),
                                'name': release.get('name', release.get('tag_name')),
                                'description': release.get('description', ''),
                                'released_at': release.get('released_at'),
                                'assets': []
                            }
                            
                            # GitLab doesn't provide automatic source archives like GitHub
                            # Add manual download links for source code
                            release_data['zipball_url'] = f"https://gitlab.com/{owner}/{repo_name}/-/archive/{release.get('tag_name')}/{repo_name}-{release.get('tag_name')}.zip"
                            release_data['tarball_url'] = f"https://gitlab.com/{owner}/{repo_name}/-/archive/{release.get('tag_name')}/{repo_name}-{release.get('tag_name')}.tar.gz"
                            
                            # Add release assets/links
                            for link in release.get('assets', {}).get('links', []):
                                release_data['assets'].append({
                                    'name': link.get('name'),
                                    'download_url': link.get('url'),
                                    'link_type': link.get('link_type')
                                })
                            
                            releases.append(release_data)
            
            elif domain in ['codeberg.org', 'gitea.com'] or self.repo_data['git_site'] in ['codeberg', 'gitea']:
                # Gitea/Forgejo releases API
                url = f"https://{domain}/api/v1/repos/{owner}/{repo_name}/releases"
                headers = {}
                if self.api_token:
                    headers['Authorization'] = f'token {self.api_token}'
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    api_releases = response.json()
                    for release in api_releases:
                        release_data = {
                            'id': release.get('id'),
                            'tag_name': release.get('tag_name'),
                            'name': release.get('name', release.get('tag_name')),
                            'body': release.get('body', ''),
                            'draft': release.get('draft', False),
                            'prerelease': release.get('prerelease', False),
                            'published_at': release.get('published_at'),
                            'zipball_url': release.get('zipball_url'),
                            'tarball_url': release.get('tarball_url'),
                            'assets': []
                        }
                        
                        # Add assets
                        for asset in release.get('assets', []):
                            release_data['assets'].append({
                                'name': asset.get('name'),
                                'download_url': asset.get('browser_download_url'),
                                'size': asset.get('size')
                            })
                        
                        releases.append(release_data)
            
            self.repo_data['releases'] = releases
            if self.verbose and releases:
                print(f"   Found {len(releases)} releases")
            elif self.verbose:
                print(f"   No releases found for this repository")
                
        except Exception as e:
            if self.verbose:
                print(f"   Could not fetch releases: {e}")
            self.repo_data['releases'] = []
    
    def download_releases(self, repo_path, all_releases=False):
        """Download releases to the repository directory"""
        if not self.repo_data.get('releases'):
            # Fetch releases if not already done
            self.fetch_releases()
        
        releases = self.repo_data.get('releases', [])
        if not releases:
            if self.verbose:
                print("   No releases available to download")
            return
        
        # Determine which releases to download
        if all_releases:
            releases_to_download = releases
        else:
            # Download only the latest non-prerelease release
            latest_release = None
            for release in releases:
                if not release.get('prerelease', False) and not release.get('draft', False):
                    latest_release = release
                    break
            releases_to_download = [latest_release] if latest_release else []
        
        if not releases_to_download:
            if self.verbose:
                print("   No suitable releases found to download")
            return
        
        releases_dir_name = f"{self.repo_data['owner']}-{self.repo_data['repo_name']}_releases"
        releases_dir = os.path.join(repo_path, releases_dir_name)
        os.makedirs(releases_dir, exist_ok=True)
        
        downloaded_count = 0
        
        for release in releases_to_download:
            tag_name = release.get('tag_name', 'unknown')
            release_name = release.get('name', tag_name)
            
            if self.verbose:
                print(f"   Downloading release: {release_name} ({tag_name})")
            
            # Create directory for this release
            release_dir = os.path.join(releases_dir, tag_name)
            os.makedirs(release_dir, exist_ok=True)
            
            # Create release info file
            release_info = {
                'tag_name': tag_name,
                'name': release_name,
                'published_at': release.get('published_at', release.get('released_at')),
                'description': release.get('body', release.get('description', '')),
                'prerelease': release.get('prerelease', False),
                'draft': release.get('draft', False)
            }
            
            with open(os.path.join(release_dir, f'{tag_name}.info.json'), 'w') as f:
                json.dump(release_info, f, indent=2)
            
            # Download source archives
            if release.get('zipball_url'):
                try:
                    self._download_file(
                        release['zipball_url'], 
                        os.path.join(release_dir, f"{tag_name}.source.zip")
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"     Could not download source zip: {e}")
            
            if release.get('tarball_url'):
                try:
                    self._download_file(
                        release['tarball_url'], 
                        os.path.join(release_dir, f"{tag_name}.source.tar.gz")
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"     Could not download source tarball: {e}")
            
            # Download release assets
            for asset in release.get('assets', []):
                asset_name = asset.get('name', 'unknown_asset')
                download_url = asset.get('download_url')
                
                if download_url:
                    try:
                        self._download_file(
                            download_url,
                            os.path.join(release_dir, asset_name)
                        )
                        if self.verbose:
                            print(f"     Downloaded asset: {asset_name}")
                    except Exception as e:
                        if self.verbose:
                            print(f"     Could not download asset {asset_name}: {e}")
            
            downloaded_count += 1
        
        self.repo_data['downloaded_releases'] = downloaded_count
        self.repo_data['releases_dir_name'] = releases_dir_name
        if self.verbose:
            print(f"   Successfully downloaded {downloaded_count} release(s) to {releases_dir_name}/")
    
    def _download_file(self, url, filepath):
        """Download a file from a URL to a local path"""
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def _sanitize_branch_name(self, branch_name):
        """Sanitize branch name for use as directory name"""
        # Remove forward slashes and other problematic characters
        sanitized = branch_name.replace('/', '-').replace('\\', '-')
        # Remove other potentially problematic characters
        sanitized = re.sub(r'[<>:"|?*]', '-', sanitized)
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
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
        self.temp_dir = tempfile.mkdtemp(prefix='iagitbetter_')
        repo_path = os.path.join(self.temp_dir, self.repo_data['repo_name'])
        
        try:
            # Clone the repository
            if specific_branch:
                # Clone specific branch only
                repo = git.Repo.clone_from(repo_url, repo_path, branch=specific_branch, single_branch=True)
                self.repo_data['specific_branch'] = specific_branch
            else:
                # Clone all branches (default behavior)
                repo = git.Repo.clone_from(repo_url, repo_path)
            
            # Get the first commit date and last commit date
            try:
                # Get all commits and find the first one (oldest)
                commits = list(repo.iter_commits(all=True))
                if commits:
                    first_commit = commits[-1]  # Last in the list is the first chronologically
                    last_commit = commits[0]    # First in the list is the last chronologically
                    
                    self.repo_data['first_commit_date'] = datetime.fromtimestamp(first_commit.committed_date)
                    self.repo_data['last_commit_date'] = datetime.fromtimestamp(last_commit.committed_date)
                    self.repo_data['total_commits'] = len(commits)
                    
                    if self.verbose:
                        print(f"   First commit date: {self.repo_data['first_commit_date']}")
                        print(f"   Last commit date: {self.repo_data['last_commit_date']}")
                        print(f"   Total commits: {self.repo_data['total_commits']}")
                else:
                    # Fallback if no commits found
                    current_time = datetime.now()
                    self.repo_data['first_commit_date'] = current_time
                    self.repo_data['last_commit_date'] = current_time
                    self.repo_data['total_commits'] = 0
            except Exception as e:
                if self.verbose:
                    print(f"   Could not get commit information: {e}")
                current_time = datetime.now()
                self.repo_data['first_commit_date'] = current_time
                self.repo_data['last_commit_date'] = current_time
                self.repo_data['total_commits'] = 0
            
            # Get default branch
            if specific_branch:
                default_branch = specific_branch
            else:
                default_branch = repo.active_branch.name if repo.active_branch else 'main'
            self.repo_data['default_branch'] = default_branch
            
            if all_branches and not specific_branch:
                # Create separate directories for each branch
                self._create_branch_directories(repo, repo_path)
            else:
                # Store branch information for single branch
                if specific_branch:
                    self.repo_data['branches'] = [specific_branch]
                else:
                    self.repo_data['branches'] = [default_branch]
                self.repo_data['branch_count'] = 1
            
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
                if remote_ref.name != 'origin/HEAD':
                    branch_name = remote_ref.name.replace('origin/', '')
                    remote_branches.append(branch_name)
            
            if not remote_branches:
                remote_branches = [self.repo_data['default_branch']]
            
            # Store branch information
            self.repo_data['branches'] = remote_branches
            self.repo_data['branch_count'] = len(remote_branches)
            
            if self.verbose:
                print(f"   Found {len(remote_branches)} branches: {', '.join(remote_branches)}")
                print(f"   Default branch ({self.repo_data['default_branch']}) files will be in root directory")
                print(f"   Other branches will be organized in branches directory")
            
            # Create branches directory for non-default branches: {repo_name}-{owner}_branches
            branches_dir_name = f"{self.repo_data['repo_name']}-{self.repo_data['owner']}_branches"
            branches_dir = os.path.join(repo_path, branches_dir_name)
            
            # Only create if there are other branches
            other_branches = [b for b in remote_branches if b != self.repo_data['default_branch']]
            if other_branches:
                os.makedirs(branches_dir, exist_ok=True)
                self.repo_data['branches_dir_name'] = branches_dir_name
                
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
                        if (item == '.git' or 
                            item == branches_dir_name or 
                            item.endswith('_releases')):
                            continue
                        
                        src_path = os.path.join(repo_path, item)
                        dst_path = os.path.join(branch_dir, item)
                        
                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path, symlinks=True)
                        else:
                            shutil.copy2(src_path, dst_path)
                            
                except Exception as e:
                    if self.verbose:
                        print(f"     Warning: Could not process branch {branch_name}: {e}")
            
            # Checkout default branch to keep files in root
            try:
                repo.heads[self.repo_data['default_branch']].checkout()
                if self.verbose:
                    print(f"   Checked out default branch: {self.repo_data['default_branch']}")
            except Exception as e:
                if self.verbose:
                    print(f"   Warning: Could not checkout default branch: {e}")
                    
        except Exception as e:
            if self.verbose:
                print(f"   Warning: Could not create all branch directories: {e}")
            # Fallback to single branch
            self.repo_data['branches'] = [self.repo_data['default_branch']]
            self.repo_data['branch_count'] = 1
    
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
            subprocess.check_call(['git', 'bundle', 'create', bundle_path, '--all'])
            
            os.chdir(original_dir)
            if self.verbose:
                print(f"   Bundle created: {bundle_name}")
            return bundle_path
        except Exception as e:
            print(f"Error creating bundle: {e}")
            return None
    
    def get_all_files(self, repo_path):
        """Get all files in the repository, preserving directory structure."""
        files_to_upload = {}
        skipped_empty_files = []
        
        for root, dirs, files in os.walk(repo_path):
            # Only skip the .git directory itself, not .github or similar folders
            # Check if the current directory is exactly .git
            dir_name = os.path.basename(root)
            if dir_name == '.git':
                continue
            
            # Also skip if any parent directory is .git
            if os.sep + '.git' + os.sep in root or root.endswith(os.sep + '.git'):
                continue
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if file is empty (0 bytes) and skip it
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size == 0:
                        relative_path = os.path.relpath(file_path, repo_path)
                        skipped_empty_files.append(relative_path)
                        continue
                except OSError:
                    # Skip files that can't be accessed
                    continue
                
                # Get relative path to preserve directory structure
                relative_path = os.path.relpath(file_path, repo_path)
                # Use relative path as key for Internet Archive
                files_to_upload[relative_path] = file_path
        
        # Log information about skipped empty files
        if skipped_empty_files and self.verbose:
            print(f"   Skipping {len(skipped_empty_files)} empty file(s) (0 bytes):")
            for empty_file in skipped_empty_files[:5]:  # Show first 5
                print(f"     - {empty_file}")
            if len(skipped_empty_files) > 5:
                print(f"     ... and {len(skipped_empty_files) - 5} more")
        
        return files_to_upload
    
    def get_description_from_readme(self, repo_path):
        """Get HTML description from README.md using the same method as iagitup"""
        readme_paths = [
            os.path.join(repo_path, 'README.md'),
            os.path.join(repo_path, 'readme.md'),
            os.path.join(repo_path, 'Readme.md'),
            os.path.join(repo_path, 'README.MD')
        ]
        
        for path in readme_paths:
            if os.path.exists(path):
                try:
                    # Use markdown2 to convert to HTML like iagitup does
                    description = markdown_path(path)
                    description = description.replace('\n', '')
                    return description
                except Exception as e:
                    if self.verbose:
                        print(f"Could not parse README.md: {e}")
                    return "This git repository doesn't have a README.md file"
        
        # Fallback for other readme formats
        txt_paths = [
            os.path.join(repo_path, 'README.txt'),
            os.path.join(repo_path, 'readme.txt'),
            os.path.join(repo_path, 'README'),
            os.path.join(repo_path, 'readme')
        ]
        
        for path in txt_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        description = f.readlines()
                        description = ' '.join(description)
                        # Convert to basic HTML
                        description = f"<pre>{description}</pre>"
                        return description
                except:
                    pass
        
        return "This git repository doesn't have a README.md file"
    
    def upload_to_ia(self, repo_path, custom_metadata=None, includes_releases=False, 
                     includes_all_branches=False, specific_branch=None, bundle_only=False):
        """Upload the repository to the Internet Archive"""
        # Generate timestamps - use current time for archival date and identifier
        archive_date = datetime.now()
        
        # Use first commit date for the date metadata, fallback to archive date
        if 'first_commit_date' in self.repo_data:
            repo_date = self.repo_data['first_commit_date']
        else:
            repo_date = archive_date
        
        # Format identifier using archive date: {repo-owner-username}-{repo-name}-%Y%m%d%H%M%S
        identifier = f"{self.repo_data['owner']}-{self.repo_data['repo_name']}-{archive_date.strftime('%Y%m%d%H%M%S')}"
        
        # Item name: {repo-owner-username} - {repo-name}
        item_name = f"{self.repo_data['owner']} - {self.repo_data['repo_name']}"
        
        # Get description from README using iagitup method
        readme_description = self.get_description_from_readme(repo_path)
        
        # Build archive details for description
        archive_details = []
        if bundle_only:
            archive_details.append("Git bundle only")
        else:
            archive_details.append("Repository files")
            
            if includes_all_branches:
                branch_count = self.repo_data.get('branch_count', 0)
                archive_details.append(f"All {branch_count} branches")
            elif specific_branch:
                archive_details.append(f"Branch: {specific_branch}")
            else:
                archive_details.append("Default branch")
            
            if includes_releases:
                release_count = self.repo_data.get('downloaded_releases', 0)
                if release_count > 0:
                    archive_details.append(f"{release_count} release(s) with assets")
        
        # Build full description
        description_footer = f"""<br/><hr/>
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
        <pre><code>wget https://archive.org/download/{identifier}/{self.repo_data['owner']}-{self.repo_data['repo_name']}.bundle</code></pre>
        <p>And then run:</p>
        <pre><code>git clone {self.repo_data['owner']}-{self.repo_data['repo_name']}.bundle</code></pre>
        """
        
        # Add repo description if available from API
        if self.repo_data.get('description'):
            description = f"<br/>{self.repo_data['description']}<br/><br/>{readme_description}{description_footer}"
        else:
            description = f"{readme_description}{description_footer}"
        
        # Prepare subject tags
        subject_tags = [
            'git', 'code', self.repo_data['git_site'], 'repository', 'repo',
            self.repo_data['owner'], self.repo_data['repo_name']
        ]
        
        if bundle_only:
            subject_tags.append('bundle-only')
        else:
            if includes_releases:
                subject_tags.append('releases')
            if includes_all_branches:
                subject_tags.append('branches')
            elif specific_branch:
                subject_tags.extend(['branch', specific_branch])
                
        if self.repo_data.get('language'):
            subject_tags.append(self.repo_data['language'].lower())
        
        # Add topics into the subject tags
        if self.repo_data.get('topics'):
            subject_tags.extend(self.repo_data['topics'])
        
        # Prepare metadata - use first commit date for date field
        metadata = {
            'title': item_name,
            'mediatype': 'software',
            'collection': 'opensource_media',
            'description': description,
            'creator': self.repo_data['owner'],
            'date': repo_date.strftime('%Y-%m-%d'),  # First commit date
            'year': repo_date.year,
            'subject': ';'.join(subject_tags),
            'originalrepo': self.repo_data['url'],
            'gitsite': self.repo_data['git_site'],
            'language': self.repo_data.get('language', 'Unknown'),
            'identifier': identifier,
            'scanner': f"iagitbetter Git Repository Mirroring Application {__version__}",
            'totalcommits': str(self.repo_data.get('total_commits', 0)),
            'bundleonly': str(bundle_only)
        }
        
        # Add branch information
        if includes_all_branches:
            metadata['allbranches'] = 'true'
            metadata['branchcount'] = str(self.repo_data.get('branch_count', 0))
            if self.repo_data.get('branches'):
                metadata['branchlist'] = ';'.join(self.repo_data['branches'])
        elif specific_branch:
            metadata['specificbranch'] = specific_branch
            metadata['allbranches'] = 'false'
        else:
            metadata['allbranches'] = 'false'
        
        # Add release information
        if includes_releases and not bundle_only:
            metadata['includesreleases'] = 'true'
            metadata['releasecount'] = str(self.repo_data.get('downloaded_releases', 0))
            if self.repo_data.get('releases_dir_name'):
                metadata['releasesdirname'] = self.repo_data['releases_dir_name']
        else:
            metadata['includesreleases'] = 'false'
        
        # Add additional metadata from API if available
        if self.repo_data.get('stars') is not None:
            metadata['stars'] = str(self.repo_data['stars'])
        if self.repo_data.get('forks') is not None:
            metadata['forks'] = str(self.repo_data['forks'])
        if self.repo_data.get('license'):
            metadata['license'] = self.repo_data['license']
        if self.repo_data.get('homepage'):
            metadata['homepage'] = self.repo_data['homepage']
        if self.repo_data.get('default_branch'):
            metadata['defaultbranch'] = self.repo_data['default_branch']
        if self.repo_data.get('archived'):
            metadata['repoarchived'] = str(self.repo_data['archived'])
        if self.repo_data.get('fork'):
            metadata['isfork'] = str(self.repo_data['fork'])
        if self.repo_data.get('private') is not None:
            metadata['repoprivate'] = str(self.repo_data['private'])
        
        # Add any additional custom metadata
        if custom_metadata:
            metadata.update(custom_metadata)
        
        if self.verbose:
            print(f"\nUploading to Internet Archive")
            print(f"   Identifier: {identifier}")
            print(f"   Title: {item_name}")
            print(f"   Repository Date: {repo_date.strftime('%Y-%m-%d')} (first commit)")
            print(f"   Archive Date: {archive_date.strftime('%Y-%m-%d')} (today)")
            print(f"   Contents: {', '.join(archive_details)}")
        
        try:
            # Get or create the item
            item = internetarchive.get_item(identifier)
            
            if item.exists:
                if self.verbose:
                    print("\nThis repository version already exists on the Internet Archive")
                    print(f"URL: https://archive.org/details/{identifier}")
                return identifier, metadata
            
            # Create the bundle file first
            bundle_path = self.create_git_bundle(repo_path)
            bundle_filename = os.path.basename(bundle_path) if bundle_path else None
            
            # Prepare files for upload - use dictionary format for proper naming
            files_to_upload = {}
            
            # Add bundle file first
            if bundle_path and os.path.exists(bundle_path):
                files_to_upload[bundle_filename] = bundle_path
            
            # Always check for and include avatar file
            username = self.repo_data['owner']
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                avatar_filename = f"{username}{ext}"
                avatar_path = os.path.join(repo_path, avatar_filename)
                if os.path.exists(avatar_path):
                    files_to_upload[avatar_filename] = avatar_path
                    if self.verbose and bundle_only:
                        print(f"   Including user avatar: {avatar_filename}")
                    break
            
            # If not bundle-only mode, add all repository files
            if not bundle_only:
                if self.verbose:
                    print("Collecting all repository files...")
                repo_files = self.get_all_files(repo_path)
                # Add all repository files with preserved directory structure
                files_to_upload.update(repo_files)
            
            if self.verbose:
                if bundle_only:
                    print(f"Uploading git bundle only to Internet Archive")
                else:
                    print(f"Uploading {len(files_to_upload)} files to Internet Archive")
                print("This may take some time depending on repository size and connection speed")
                
                # Show what major components are being uploaded
                components = []
                if bundle_filename:
                    components.append("Git bundle")
                
                # Check if avatar is included
                avatar_included = any(f.startswith(username) and f.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) 
                                    for f in files_to_upload.keys())
                if avatar_included:
                    components.append("User avatar")
                    
                if not bundle_only:
                    if includes_all_branches:
                        branches_dir = self.repo_data.get('branches_dir_name')
                        if branches_dir:
                            branch_files = [f for f in files_to_upload.keys() if f.startswith(branches_dir)]
                            if branch_files:
                                non_default_count = len([b for b in self.repo_data.get('branches', []) if b != self.repo_data.get('default_branch')])
                                components.append(f"Branches directory ({non_default_count} branches in {branches_dir}/)")
                    if includes_releases and self.repo_data.get('releases_dir_name'):
                        release_files = [f for f in files_to_upload.keys() if f.startswith(self.repo_data['releases_dir_name'])]
                        if release_files:
                            components.append(f"Releases directory ({len(release_files)} files)")
                    if not bundle_only:
                        components.append("Repository files")
                print(f"   Components: {', '.join(components)}")
            
            # Parse internetarchive configuration file to get credentials
            access_key = None
            secret_key = None
            
            try:
                parsed_ia_config = parse_config_file(self.ia_config_path)[2]['s3']
                access_key = parsed_ia_config.get('access')
                secret_key = parsed_ia_config.get('secret')
            except Exception as e:
                if self.verbose:
                    print(f"Note: Using default IA credentials (could not parse config: {e})")
            
            # Upload all files at once with proper metadata and verbose output
            upload_kwargs = {
                'metadata': metadata,
                'retries': 9001,  # Use high retry count
                'request_kwargs': dict(timeout=(9001, 9001)),  # Use tuple timeout
                'verbose': self.verbose,  # Enable verbose output
                'delete': False  # Don't delete local files after upload
            }
            
            # Add credentials if available
            if access_key and secret_key:
                upload_kwargs['access_key'] = access_key
                upload_kwargs['secret_key'] = secret_key
            
            response = item.upload(files_to_upload, **upload_kwargs)
            
            if self.verbose:
                print(f"\nUpload completed successfully!")
                print(f"   Archive URL: https://archive.org/details/{identifier}")
                if bundle_filename:
                    print(f"   Bundle download: https://archive.org/download/{identifier}/{bundle_filename}")
            
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
                if os.name == 'nt':
                    shutil.rmtree(self.temp_dir, onerror=self.handle_remove_readonly)
                else:
                    shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not completely clean up temporary files: {e}")
                print(f"You may need to manually delete: {self.temp_dir}")
    
    def check_ia_credentials(self):
        """Check if Internet Archive credentials are configured."""
        ia_config_paths = [
            os.path.expanduser('~/.ia'),
            os.path.expanduser('~/.config/ia.ini'),
            os.path.expanduser('~/.config/internetarchive/ia.ini')
        ]
        
        if not any(os.path.exists(path) for path in ia_config_paths):
            print("\nInternet Archive credentials not found")
            print("Run: ia configure")
            
            try:
                result = subprocess.call(['ia', 'configure'])
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
        for item in metadata_string.split(','):
            if ':' in item:
                key, value = item.split(':', 1)
                custom_meta[key.strip()] = value.strip()
        
        return custom_meta
    
    def run(self, repo_url, custom_metadata_string=None, verbose=True, check_updates=True, 
           all_branches=False, specific_branch=None, releases=False, all_releases=False, 
           bundle_only=False):
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
        repo_path = self.clone_repository(repo_url, all_branches=all_branches, specific_branch=specific_branch)
        
        # Download releases if requested
        if releases and not bundle_only:
            self.download_releases(repo_path, all_releases=all_releases)
        
        # Upload to Internet Archive
        identifier, metadata = self.upload_to_ia(
            repo_path, 
            custom_metadata,
            includes_releases=releases and not bundle_only,
            includes_all_branches=all_branches,
            specific_branch=specific_branch,
            bundle_only=bundle_only
        )
        
        # Cleanup
        self.cleanup()
        
        return identifier, metadata


def main():
    parser = argparse.ArgumentParser(
        description='iagitbetter - Archive any git repository to the Internet Archive',
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
  
  # Self-hosted instances
  %(prog)s --git-provider-type gitlab --api-url https://gitlab.company.com/api/v4 https://gitlab.company.com/user/repo
  %(prog)s --git-provider-type gitea --api-token TOKEN https://git.company.com/user/repo
        """
    )
    
    parser.add_argument('repo_url', 
                       help='Git repository URL to archive')
    parser.add_argument('--metadata', '-m', 
                       help='Custom metadata in format: key1:value1,key2:value2')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress verbose output')
    parser.add_argument('--no-update-check', action='store_true',
                       help='Skip checking for updates on PyPI')
    parser.add_argument('--bundle-only', action='store_true',
                       help='Only uploads the git bundle, not all files')
    parser.add_argument('--releases', action='store_true',
                       help='Download releases from the repository')
    parser.add_argument('--all-releases', action='store_true',
                       help='Download all releases (default: latest only)')
    parser.add_argument('--all-branches', action='store_true',
                       help='Clone and archive all branches')
    parser.add_argument('--branch', type=str,
                       help='Clone and archive a specific branch')
    parser.add_argument('--git-provider-type', type=str, 
                       choices=['github', 'gitlab', 'gitea', 'bitbucket'],
                       help='Specify the git provider type for self-hosted instances')
    parser.add_argument('--api-url', type=str,
                       help='Custom API URL for self-hosted instances')
    parser.add_argument('--api-token', type=str,
                       help='API token for authentication with private/self-hosted repositories')
    parser.add_argument('--version', '-v', 
                       action='version', 
                       version=f'%(prog)s {__version__}')
    
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
        api_token=args.api_token
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
            bundle_only=args.bundle_only
        )
        if identifier:
            print("\n" + "="*60)
            print("Archive complete")
            print("="*60)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        archiver.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        archiver.cleanup()
        sys.exit(1)


if __name__ == '__main__':
    main()