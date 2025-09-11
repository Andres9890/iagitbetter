#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iagitbetter - Archive any git repository to the Internet Archive
Improved version with support for all git providers and full file preservation
"""

__version__ = "1.0.0"
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
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
import requests
import internetarchive
from internetarchive.config import parse_config_file
import git
from markdown2 import markdown_path

class GitArchiver:
    def __init__(self, verbose=True, ia_config_path=None):
        self.temp_dir = None
        self.repo_data = {}
        self.verbose = verbose
        self.ia_config_path = ia_config_path
        
    def extract_repo_info(self, repo_url):
        """Extract repository information from any git URL"""
        # Parse the URL
        parsed = urlparse(repo_url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Extract git site name (without TLD)
        git_site = domain.split('.')[0]
        
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
            'full_name': f"{owner}/{repo_name}"
        }
        
        # Try to fetch additional metadata from API if available
        self._fetch_api_metadata()
        
        return self.repo_data
    
    def _fetch_api_metadata(self):
        """Try to fetch metadata from various git provider APIs"""
        domain = self.repo_data['domain']
        owner = self.repo_data['owner']
        repo_name = self.repo_data['repo_name']
        
        api_endpoints = {
            'github.com': f"https://api.github.com/repos/{owner}/{repo_name}",
            'gitlab.com': f"https://gitlab.com/api/v4/projects/{owner}%2F{repo_name}",
            'bitbucket.org': f"https://api.bitbucket.org/2.0/repositories/{owner}/{repo_name}",
            'codeberg.org': f"https://codeberg.org/api/v1/repos/{owner}/{repo_name}",
            'gitea.com': f"https://gitea.com/api/v1/repos/{owner}/{repo_name}",
        }
        
        if domain in api_endpoints:
            try:
                response = requests.get(api_endpoints[domain], timeout=10)
                if response.status_code == 200:
                    api_data = response.json()
                    self._parse_api_response(api_data, domain)
            except Exception as e:
                if self.verbose:
                    print(f"Note: Could not fetch API metadata: {e}")
    
    def _parse_api_response(self, api_data, domain):
        """Parse API response based on the git provider"""
        if domain == 'github.com':
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
                'visibility': api_data.get('visibility', 'public')
            })
        elif domain == 'gitlab.com':
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
                'shared_runners_enabled': api_data.get('shared_runners_enabled', False)
            })
        elif domain == 'bitbucket.org':
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
                'owner_display_name': api_data.get('owner', {}).get('display_name', '')
            })
        elif domain in ['codeberg.org', 'gitea.com']:
            # Gitea/Forgejo API (Codeberg uses Forgejo)
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
                'external_wiki': api_data.get('external_wiki', {})
            })
    
    def clone_repository(self, repo_url):
        """Clone the git repository to a temporary directory."""
        if self.verbose:
            print(f"Cloning repository from {repo_url}...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix='iagitbetter_')
        repo_path = os.path.join(self.temp_dir, self.repo_data['repo_name'])
        
        try:
            # Clone the repository
            repo = git.Repo.clone_from(repo_url, repo_path)
            if self.verbose:
                print(f"   Successfully cloned to {repo_path}")
            
            # Get the first commit date instead of the last
            try:
                # Get all commits and find the first one (oldest)
                commits = list(repo.iter_commits(all=True))
                if commits:
                    first_commit = commits[-1]  # Last in the list is the first chronologically
                    self.repo_data['first_commit_date'] = datetime.fromtimestamp(first_commit.committed_date)
                    if self.verbose:
                        print(f"   First commit date: {self.repo_data['first_commit_date']}")
                else:
                    # Fallback if no commits found
                    self.repo_data['first_commit_date'] = datetime.now()
            except Exception as e:
                if self.verbose:
                    print(f"   Could not get first commit date: {e}")
                self.repo_data['first_commit_date'] = datetime.now()
            
            return repo_path
        except Exception as e:
            print(f"Error cloning repository: {e}")
            self.cleanup()
            sys.exit(1)
    
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
            
            # Create bundle
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
        
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in root:
                continue
            
            for file in files:
                file_path = os.path.join(root, file)
                # Get relative path to preserve directory structure
                relative_path = os.path.relpath(file_path, repo_path)
                # Use relative path as key for Internet Archive
                files_to_upload[relative_path] = file_path
        
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
    
    def upload_to_ia(self, repo_path, custom_metadata=None):
        """Upload the repository to the Internet Archive"""
        # Generate timestamps - use current time for archival date and identifier
        archive_date = datetime.now()
        
        # Use first commit date for the date metadata, fallback to archive date
        if 'first_commit_date' in self.repo_data:
            repo_date = self.repo_data['first_commit_date']
        else:
            repo_date = archive_date
        
        # Format identifier using archive date: {repo-owner-username}-{repo-name}-%Y%m%d-%H%M%S
        identifier = f"{self.repo_data['owner']}-{self.repo_data['repo_name']}-{archive_date.strftime('%Y%m%d-%H%M%S')}"
        
        # Item name: {repo-owner-username} - {repo-name}
        item_name = f"{self.repo_data['owner']} - {self.repo_data['repo_name']}"
        
        # Get description from README using iagitup method
        readme_description = self.get_description_from_readme(repo_path)
        
        # Build full description
        description_footer = f"""<br/><hr/>
        <p><strong>Repository Information:</strong></p>
        <ul>
            <li>Original Repository: <a href="{self.repo_data['url']}">{self.repo_data['url']}</a></li>
            <li>Git Provider: {self.repo_data['git_site'].title()}</li>
            <li>Owner: {self.repo_data['owner']}</li>
            <li>Repository Name: {self.repo_data['repo_name']}</li>
            <li>First Commit: {repo_date.strftime('%Y-%m-%d %H:%M:%S')}</li>
            <li>Archived: {archive_date.strftime('%Y-%m-%d %H:%M:%S')}</li>
        </ul>
        <p>To restore the repository download the bundle:</p>
        <pre><code>wget https://archive.org/download/{identifier}/{self.repo_data['owner']}-{self.repo_data['repo_name']}.bundle</code></pre>
        <p>and run:</p>
        <pre><code>git clone {self.repo_data['owner']}-{self.repo_data['repo_name']}.bundle</code></pre>
        """
        
        # Add repo description if available from API
        if self.repo_data.get('description'):
            description = f"<br/>{self.repo_data['description']}<br/><br/>{readme_description}{description_footer}"
        else:
            description = f"{readme_description}{description_footer}"
        
        # Prepare metadata - use first commit date for date field
        metadata = {
            'title': item_name,
            'mediatype': 'software',
            'collection': 'opensource_media',
            'description': description,
            'creator': self.repo_data['owner'],
            'date': repo_date.strftime('%Y-%m-%d'),  # First commit date
            'year': repo_date.year,
            'subject': f"git;code;{self.repo_data['git_site']};repository;repo;{self.repo_data['owner']};{self.repo_data['repo_name']}",
            'originalrepo': self.repo_data['url'],
            'gitsite': self.repo_data['git_site'],
            'language': self.repo_data.get('language', 'Unknown'),
            'identifier': identifier,
            'scanner': f"iagitbetter Git Repository Mirroring Application {__version__}"
        }
        
        # Add additional metadata from API if available
        if self.repo_data.get('stars') is not None:
            metadata['stars'] = str(self.repo_data['stars'])
        if self.repo_data.get('forks') is not None:
            metadata['forks'] = str(self.repo_data['forks'])
        if self.repo_data.get('topics'):
            metadata['topics'] = ';'.join(self.repo_data['topics'])
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
            
            # Get all repository files preserving structure
            if self.verbose:
                print("Collecting all repository files...")
            repo_files = self.get_all_files(repo_path)
            
            # Prepare files for upload - use dictionary format for proper naming
            files_to_upload = {}
            
            # Add bundle file first
            if bundle_path and os.path.exists(bundle_path):
                files_to_upload[bundle_filename] = bundle_path
            
            # Add all repository files with preserved directory structure
            files_to_upload.update(repo_files)
            
            if self.verbose:
                print(f"Uploading {len(files_to_upload)} files to Internet Archive")
                print("This may take some time depending on repository size and connection speed")
            
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
            os.path.expanduser('~/.config/ia.ini')
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
    
    def run(self, repo_url, custom_metadata_string=None, verbose=True):
        """Main execution flow."""
        self.verbose = verbose
        
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
        repo_path = self.clone_repository(repo_url)
        
        # Upload to Internet Archive
        identifier, metadata = self.upload_to_ia(repo_path, custom_metadata)
        
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
        """
    )
    
    parser.add_argument('repo_url', 
                       help='Git repository URL to archive')
    parser.add_argument('--metadata', '-m', 
                       help='Custom metadata in format: key1:value1,key2:value2')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress verbose output')
    parser.add_argument('--version', '-v', 
                       action='version', 
                       version=f'%(prog)s {__version__}')
    
    args = parser.parse_args()
    
    # Create archiver instance and run
    archiver = GitArchiver(verbose=not args.quiet)
    try:
        identifier, metadata = archiver.run(args.repo_url, args.metadata, verbose=not args.quiet)
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