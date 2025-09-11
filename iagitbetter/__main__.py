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
__version__    = "v1.0.0"

import os
import sys
import shutil
import argparse
import json

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

Key improvements over iagitup:
  - Works with ALL git providers (not just GitHub)
  - Uploads complete file structure (not just bundle)
  - Clean naming: {owner} - {repo}
  - Adds originalrepo and gitsite metadata
  - Preserves directory structure
    """
)

parser.add_argument('giturl', type=str, 
                   help='Git repository URL to archive (works with any git provider)')
parser.add_argument('--metadata', '-m', default=None, type=str, required=False, 
                   help="custom metadata to add to the archive.org item (format: key1:value1,key2:value2)")
parser.add_argument('--version', '-v', action='version', version=__version__)
parser.add_argument('--bundle-only', action='store_true', 
                   help="only upload git bundle, not all files (iagitup compatibility mode)")

args = parser.parse_args()

def main():
    """Main entry point for iagitbetter"""
    
    # Create archiver instance
    archiver = iagitbetter.GitArchiver()
    
    # Check IA credentials first
    archiver.check_ia_credentials()
    
    URL = args.giturl
    custom_metadata = args.metadata
    custom_meta_dict = None
    
    print("=" * 60)
    print(f"{__main_name__} {__version__}")
    print("=" * 60)
    print()
    
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
    
    # Extract repository information
    print(f"Analyzing repository: {URL}")
    archiver.extract_repo_info(URL)
    print(f"   Repository: {archiver.repo_data['full_name']}")
    print(f"   Git Provider: {archiver.repo_data['git_site']}")
    print()
    
    # Clone the repository
    print(f"Downloading {URL} repository...")
    repo_path = archiver.clone_repository(URL)
    
    # Upload to Internet Archive
    identifier, metadata = archiver.upload_to_ia(repo_path, custom_metadata=custom_meta_dict)
    
    # Cleanup
    archiver.cleanup()
    
    # Output results
    if identifier:
        print("\nUpload finished, Item information:")
        print("=" * 60)
        print(f"Title: {metadata['title']}")
        print(f"Identifier: {identifier}")
        print(f"Git Provider: {metadata['gitsite']}")
        print(f"Original Repository: {metadata['originalrepo']}")
        print(f"Archived repository URL:")
        print(f"    https://archive.org/details/{identifier}")
        print(f"Archived git bundle file:")
        bundle_name = f"{archiver.repo_data['owner']}-{archiver.repo_data['repo_name']}"
        print(f"    https://archive.org/download/{identifier}/{bundle_name}.bundle")
        print("=" * 60)
        print("Archive complete")
        print()
    else:
        print("\nUpload failed. Please check the errors above")
        sys.exit(1)


if __name__ == '__main__':
    main()