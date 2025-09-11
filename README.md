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

- Git Support: Works with ALL git providers (GitHub, GitLab, BitBucket, Codeberg, Gitea, and a lot more)
- Complete Repo Archiving: Downloads and uploads the entire repository file structure
- APIs: Automatically fetches repository metadata from git provider APIs when available
- Clean Naming Convention: Uses format `{owner} - {repo}` for item titles
- Metadata: Includes stars, forks, programming language, license, topics, and more
- Directory Structure Preservation: Keeps the original repository folder structure in the archive
- Git Bundle Creation: Creates git bundles
- First Commit Date: Uses the first commit date as the repo creation date
- Custom Metadata Support: Pass additional metadata using `--metadata=<key:value>`
- Automatic Cleanup: Removes temporary files after upload

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
iagitbetter <git_url> [--metadata=<key:value>...] [--bundle-only]
```

Arguments:

- `<git_url>` – Git repository URL to archive (works with any git provider)

Options:

- `--metadata=<key:value>` – custom metadata to add to the IA item
- `--bundle-only` – only upload git bundle, not all files
- `--version` – show version information

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

## Examples

```bash
# Archive GitHub repository
iagitbetter https://github.com/user/repository

# Archive GitLab repository
iagitbetter https://gitlab.com/user/repository

# Archive BitBucket repository
iagitbetter https://bitbucket.org/user/repository

# Archive with custom metadata
iagitbetter https://github.com/user/repo --metadata="collection:software,topic:python"

# Bundle-only
iagitbetter https://github.com/user/repo --bundle-only

# Archive from any git provider
iagitbetter https://git.example.com/user/repository.git
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

The files will be uploaded to Internet Archive as:
- `README.md`
- `src/main.py`
- `src/utils/helper.py`
- `docs/guide.md`
- `tests/test_main.py`
- `{owner}-{repo}.bundle` (git bundle for restoration)

If you use the `--bundle-only` flag, only the git bundle will be uploaded

## How it works

### Repository Analysis
1. `iagitbetter` parses the git URL to identify the provider and repository details
2. It attempts to fetch additional metadata from the provider's API (if it's supported provider)
3. Repository information is extracted including owner, name, and provider details

### Repository Download
1. The git repository is cloned to a temporary directory using GitPython
2. The first commit date is extracted for the creation date
3. A git bundle is created

### Internet Archive Upload
1. Comprehensive metadata is prepared including:
   - title: `{owner} - {repo}`
   - identifier: `{owner}-{repo}-{timestamp}`
   - Original repository URL and git provider information
   - First commit date as the creation date
   - API-fetched metadata (stars, forks, language, etc)
2. All repository files are uploaded preserving directory structure
3. The git bundle is included
4. README.md is converted to HTML for the item description

### Archive Format
- Identifier: `{owner}-{repo}-YYYYMMDD-HHMMSS`
- Title: `{owner} - {repo}`
- Date: First commit date (for historical accuracy)
- Files: Complete repository structure & git bundle

## Repository Restoration

To restore a repository from the archive:

```bash
# Download the git bundle
wget https://archive.org/download/{identifier}/{owner}-{repo}.bundle

# Clone from the bundle
git clone {owner}-{repo}.bundle {repo-name}

# Or restore using git
git clone {owner}-{repo}.bundle
cd {repo-name}
```

## Key Improvements over iagitup

- Works with any git provider
- Uploads the entire repo structure
- Automatically fetches repo information
- Uses first commit date
- Uses provider APIs for metadata

## Requirements

- Python 3.9+
- Git
- Internet Archive account and credentials
- Required dependencies in the [`requirements.txt`](requirements.txt) file