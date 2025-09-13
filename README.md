[License Button]: https://img.shields.io/badge/License-GPL--3.0-black
[License Link]: https://github.com/Andres9890/iagitbetter/blob/main/LICENSE 'GPL-3.0 License.'

[PyPI Button]: https://img.shields.io/pypi/v/iagitbetter?color=yellow&label=PyPI
[PyPI Link]: https://pypi.org/project/iagitbetter/ 'PyPI Package.'

# iagitbetter
[![License Button]][License Link]
[![PyPI Button]][PyPI Link]

iagitbetter is a python tool for archiving any git repository to the [Internet Archive](https://archive.org/). An improved version of iagitup with support for all git providers, it downloads the complete repository, creates git bundles, uploads all files preserving structure, and archives to archive.org.

- This project is heavily based off [iagitup](https://github.com/gdamdam/iagitup) by Giovanni Damiola, credits to them

## Features

- Works with ALL git providers (GitHub, GitLab, BitBucket, Codeberg, Gitea, and more)
- Downloads and uploads the entire repository file structure
- Download repository releases with assets from supported providers
- Clone and archive all branches of a repository with proper directory structure
- Automatically fetches repository metadata from git provider APIs when available
- Uses format `{owner} - {repo}` for item titles
- Includes stars, forks, programming language, license, topics, and more metadata
- Keeps the original repository folder structure in the archive
- Creates git bundles for complete repository restoration
- Uses the first commit date as the repo creation date
- Pass additional metadata using `--metadata=<key:value>`
- Removes temporary files after upload

## Installation

Requires Python 3.9 or newer

```bash
pip install iagitbetter
```

The package makes a console script named `iagitbetter` once installed. You can also install from the source using `pip install .`

## Configuration

```bash
ia configure
```

You'll be prompted to enter your Internet Archive account's email and password.

## Usage

```bash
iagitbetter <git_url> [options]
```

### Basic Arguments

- `<git_url>` – Git repository URL to archive (works with any git provider)

### Options

- `--metadata=<key:value>` – custom metadata to add to the IA item
- `--bundle-only` – only upload git bundle, not all files
- `--quiet` / `-q` – suppress verbose output
- `--version` – show version information
- `--no-update-check` – skip checking for updates on PyPI

### Release Options

- `--releases` – download releases from the repository (GitHub, GitLab, Codeberg, Gitea)
- `--all-releases` – download all releases (default: latest release only)
- `--latest-release` – download only the latest release (default when `--releases` is used)

### Branch Options

- `--all-branches` – clone and archive all branches of the repository
- `--branch` – clone and archive a branch of the repository

## Supported Git Providers

iagitbetter works with any git repository that can be cloned publicly. It has enhanced support with automatic metadata fetching for:

- GitHub (github.com)
- GitLab (gitlab.com)
- BitBucket (bitbucket.org)
- Codeberg (codeberg.org)
- Gitea (gitea.com)
- Any other git provider

### Automatic Metadata Collection

For supported providers, iagitbetter automatically fetches:
- Repository description
- Star count, fork count, watcher count
- Primary programming language
- License information
- Topics/tags
- Creation and last update dates
- Default branch name
- Repository size and statistics
- Homepage URL
- Issue and wiki availability

### Release Support

For providers that support releases (GitHub, GitLab, Codeberg, Gitea), iagitbetter can:
- Download the latest release or all releases
- Include release assets and attachments
- Download source code archives (zip/tar.gz)
- Save release metadata and descriptions
- Organized releases in a `{owner}-{repo}_releases/` folder

## Examples

### Basic Repository Archiving

```bash
# Archive GitHub repository
iagitbetter https://github.com/user/repository

# Archive GitLab repository
iagitbetter https://gitlab.com/user/repository

# Archive BitBucket repository
iagitbetter https://bitbucket.org/user/repository

# Archive from any git provider
iagitbetter https://git.example.com/user/repository.git
```

### Release Archiving

```bash
# Archive repository with latest release
iagitbetter --releases https://github.com/user/repo

# Archive repository with all releases
iagitbetter --releases --all-releases https://github.com/user/repo

# Explicitly specify latest release only
iagitbetter --releases --latest-release https://github.com/user/repo
```

### Branch Archiving

```bash
# Archive all branches of a repository
iagitbetter --all-branches https://github.com/user/repo

# Archive all branches AND all releases
iagitbetter --all-branches --releases --all-releases https://github.com/user/repo
```

### Advanced Usage

```bash
# Archive with custom metadata
iagitbetter --metadata="collection:software,topic:python" https://github.com/user/repo

# Bundle-only (compatibility mode)
iagitbetter --bundle-only https://github.com/user/repo

# Quiet mode with all features
iagitbetter --quiet --all-branches --releases --all-releases https://github.com/user/repo
```

## Repository Structure Preservation

By default, iagitbetter preserves the complete repository structure when uploading to Internet Archive. For example, if your repository contains:

```
README.md
src/
  ├── main.py
  └── utils/
      └── helper.py
docs/
  └── guide.md
tests/
  └── test_main.py
```

### With --all-branches
When using `--all-branches`, the structure becomes:
```
README.md
src/main.py
src/utils/helper.py
docs/guide.md
tests/test_main.py
develop_branch/
  ├── README.md
  ├── src/main.py
  └── ...
feature-xyz_branch/
  ├── README.md
  ├── src/main.py
  └── ...
{owner}-{repo}.bundle
```

### With --releases
When using `--releases`, a releases directory is added:
```
README.md
src/main.py
docs/guide.md
{owner}-{repo}_releases/
  └── v1.0.0/
      ├── v1.0.0.info.json
      ├── v1.0.0-source.zip
      ├── v1.0.0-source.tar.gz
      └── assets/
          └── example.exe
{owner}-{repo}.bundle
```

The files will be uploaded to Internet Archive exactly as shown above, preserving the directory structure

If you use the `--bundle-only` flag, only the git bundle will be uploaded.

## How it works

### Repository Analysis
1. `iagitbetter` parses the git URL to identify the provider and repository details
2. It attempts to fetch additional metadata from the provider's API (if it's a supported provider)
3. Repository information is extracted including owner, name, and provider details

### Repository Download
1. The git repository is cloned to a temporary directory using GitPython
2. If `--all-branches` is specified, all remote branches are fetched and separate directories are created for each non-default branch
3. The first commit date is extracted for the creation date
4. A git bundle is created with all branches and tags

### Branch Processing (when `--all-branches` is used)
1. All remote branches are fetched from the repository
2. For each non-default branch, a separate directory named `{owner}-{repo}_branches/{branch-name}` is created
3. Each branch is checked out and its files are copied to the respective branch directory
4. The default branch files remain in the root directory
5. This creates a clear separation of branches in the archive

### Release Processing (when `--releases` is used)
1. Release information is fetched from the provider's API
2. Latest release or all releases are downloaded based on options
3. Source code archives (zip/tar.gz) are downloaded
4. Release assets and attachments are downloaded
5. Release metadata is saved as JSON files
6. All content is organized in a `{owner}-{repo}_releases/` directory structure

### Internet Archive Upload
1. Comprehensive metadata is prepared including:
   - title: `{owner} - {repo}`
   - identifier: `{owner}-{repo}-{timestamp}`
   - Original repository URL and git provider information
   - First commit date as the creation date
   - API-fetched metadata (stars, forks, language, etc)
   - Branch and releases information
2. All repository files are uploaded preserving directory structure
3. Branches are included (if archived with `--all-branches`)
4. Release files are included (if requested)
5. The git bundle is included
6. README.md is converted to HTML for the item description

### Archive Format
- Identifier: `{owner}-{repo}-YYYYMMDD-HHMMSS`
- Title: `{owner} - {repo}`
- Date: First commit date (for historical accuracy)
- Files: Complete repository structure, branches (if requested), releases (if requested), and git bundle

## Repository Restoration

To restore a repository from the archive:

```bash
# Download the git bundle
wget https://archive.org/download/{identifier}/{owner}-{repo}.bundle

# Clone from the bundle (includes all branches if archived with --all-branches)
git clone {owner}-{repo}.bundle {repo-name}

# Or restore using git
git clone {owner}-{repo}.bundle
cd {repo-name}

# List all available branches (if --all-branches was used)
git branch -a

# Check out a specific branch
git checkout branch-name
```

## Release Information

When releases are archived, they can be found in the `{repo-owner}-{repo}_releases/` directory of the archive, Each release includes:

- `{version}.info.json` - Complete release metadata
- `{version}-source.zip` - Source code archive
- `{version}-source.tar.gz` - Source code tarball
- Asset files

## Key Improvements over iagitup

- Works with any git provider
- Uploads the entire repository file structure
- Can archive all branches of a repository
- Automatically fetches repository information
- Uses first commit date
- Leverages git provider APIs for metadata

## Requirements

- Python 3.9+
- Git
- Internet Archive account and credentials
- Required dependencies in the [`requirements.txt`](requirements.txt) file