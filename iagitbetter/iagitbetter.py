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
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
import requests
import internetarchive
import git
from markdown2 import markdown_path

class GitArchiver:
    def __init__(self):
        self.temp_dir = None
        self.repo_data = {}
        
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
                print(f"Note: Could not fetch API metadata: {e}")
    
    def _parse_api_response(self, api_data, domain):
        """Parse API response based on the git provider"""
        if domain == 'github.com':
            self.repo_data.update({
                'description': api_data.get('description', ''),
                'created_at': api_data.get('created_at', ''),
                'pushed_at': api_data.get('pushed_at', ''),
                'language': api_data.get('language', ''),
                'stars': api_data.get('stargazers_count', 0),
                'forks': api_data.get('forks_count', 0),
                'homepage': api_data.get('homepage', ''),
                'topics': api_data.get('topics', [])
            })
        elif domain == 'gitlab.com':
            self.repo_data.update({
                'description': api_data.get('description', ''),
                'created_at': api_data.get('created_at', ''),
                'pushed_at': api_data.get('last_activity_at', ''),
                'stars': api_data.get('star_count', 0),
                'forks': api_data.get('forks_count', 0),
                'topics': api_data.get('topics', [])
            })
    
    def clone_repository(self, repo_url):
        """Clone the git repository to a temporary directory."""
        print(f"Cloning repository from {repo_url}...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix='iagitbetter_')
        repo_path = os.path.join(self.temp_dir, self.repo_data['repo_name'])
        
        try:
            # Clone the repository
            repo = git.Repo.clone_from(repo_url, repo_path)
            print(f"   Successfully cloned to {repo_path}")
            
            # Get the last commit date
            last_commit = repo.head.commit
            self.repo_data['last_commit_date'] = datetime.fromtimestamp(last_commit.committed_date)
            
            return repo_path
        except Exception as e:
            print(f"Error cloning repository: {e}")
            self.cleanup()
            sys.exit(1)
    
    def create_git_bundle(self, repo_path):
        """Create a git bundle of the repository."""
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
            print(f"   Bundle created: {bundle_name}")
            return bundle_path
        except Exception as e:
            print(f"Error creating bundle: {e}")
            return None
    
    def get_all_files(self, repo_path):
        """Get all files in the repository, preserving directory structure."""
        files_to_upload = []
        
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in root:
                continue
            
            for file in files:
                file_path = os.path.join(root, file)
                # Get relative path to preserve directory structure
                relative_path = os.path.relpath(file_path, repo_path)
                files_to_upload.append((file_path, relative_path))
        
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
                    print(f"Warning: Could not parse README.md: {e}")
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
        # Generate timestamps
        now = datetime.now()
        if 'last_commit_date' in self.repo_data:
            timestamp = self.repo_data['last_commit_date']
        else:
            timestamp = now
        
        # Format: {repo-owner-username}-{repo-name}-%Y%m%d-%H%M%S
        identifier = f"{self.repo_data['owner']}-{self.repo_data['repo_name']}-{timestamp.strftime('%Y%m%d-%H%M%S')}"
        
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
            <li>Archived: {now.strftime('%Y-%m-%d %H:%M:%S')}</li>
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
        
        # Prepare metadata
        metadata = {
            'title': item_name,
            'mediatype': 'software',
            'collection': 'opensource_media',
            'description': description,
            'creator': self.repo_data['owner'],
            'date': timestamp.strftime('%Y-%m-%d'),
            'year': timestamp.year,
            'subject': f"git;code;{self.repo_data['git_site']};repository;repo;{self.repo_data['owner']};{self.repo_data['repo_name']}",
            'originalrepo': self.repo_data['url'],
            'gitsite': self.repo_data['git_site'],
            'language': self.repo_data.get('language', 'Unknown'),
            'identifier': identifier,
            'uploader': f"iagitbetter Git Repository Mirroring Application {__version__}"
        }
        
        # Add any additional custom metadata
        if custom_metadata:
            metadata.update(custom_metadata)
        
        print(f"\nUploading to Internet Archive")
        print(f"   Identifier: {identifier}")
        print(f"   Title: {item_name}")
        
        try:
            # Get or create the item
            item = internetarchive.get_item(identifier)
            
            if item.exists:
                print("\nThis repository version already exists on the Internet Archive")
                print(f"URL: https://archive.org/details/{identifier}")
                return identifier, metadata
            
            # Get all files to upload
            files_to_upload = []
            
            # Add the bundle file
            bundle_path = self.create_git_bundle(repo_path)
            if bundle_path:
                files_to_upload.append(bundle_path)
            
            # Add all repository files preserving structure
            print("Collecting all repository files...")
            repo_files = self.get_all_files(repo_path)
            
            # Upload files
            print(f"Uploading {len(repo_files) + 1} files to Internet Archive...")
            
            # Upload bundle first
            if bundle_path:
                item.upload(bundle_path, metadata=metadata, retries=3, 
                           request_kwargs=dict(timeout=9001))
            
            # Upload all other files with preserved directory structure
            for file_path, relative_path in repo_files:
                # Internet Archive will create directories automatically
                # based on the file key (relative path)
                print(f"   Uploading: {relative_path}")
                item.upload(file_path, key=relative_path, retries=3,
                           request_kwargs=dict(timeout=9001))
            
            print(f"\nUpload completed successfully!")
            print(f"   Archive URL: https://archive.org/details/{identifier}")
            print(f"   Bundle download: https://archive.org/download/{identifier}/{os.path.basename(bundle_path)}")
            
            return identifier, metadata
            
        except Exception as e:
            print(f"Error uploading to Internet Archive: {e}")
            return None, None
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            print("Cleaning up temporary files...")
            shutil.rmtree(self.temp_dir)
    
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
    
    def run(self, repo_url, custom_metadata_string=None):
        """Main execution flow."""
        # Check IA credentials
        self.check_ia_credentials()
        
        # Parse custom metadata
        custom_metadata = self.parse_custom_metadata(custom_metadata_string)
        
        # Extract repository information
        print(f"\n:: Analyzing repository: {repo_url}")
        self.extract_repo_info(repo_url)
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
        """
    )
    
    parser.add_argument('repo_url', 
                       help='Git repository URL to archive')
    parser.add_argument('--metadata', '-m', 
                       help='Custom metadata in format: key1:value1,key2:value2')
    parser.add_argument('--version', '-v', 
                       action='version', 
                       version=f'%(prog)s {__version__}')
    
    args = parser.parse_args()
    
    # Create archiver instance and run
    archiver = GitArchiver()
    try:
        identifier, metadata = archiver.run(args.repo_url, args.metadata)
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