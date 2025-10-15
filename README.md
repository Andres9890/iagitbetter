[License Button]: https://img.shields.io/badge/License-GPL--3.0-black
[License Link]: https://github.com/Andres9890/iagitbetter/blob/main/LICENSE 'GPL-3.0 License.'

[PyPI Button]: https://img.shields.io/pypi/v/iagitbetter?color=yellow&label=PyPI
[PyPI Link]: https://pypi.org/project/iagitbetter/ 'PyPI Package.'

[Downloads Badge]: https://static.pepy.tech/badge/iagitbetter/month
[Downloads Link]: https://pepy.tech/project/iagitbetter 'Downloads Per Month.'

# iagitbetter
[![License Button]][License Link]
[![PyPI Button]][PyPI Link]
[![Lint](https://github.com/Andres9890/iagitbetter/actions/workflows/lint.yml/badge.svg)](https://github.com/Andres9890/iagitbetter/actions/workflows/lint.yml)
[![Unit Tests](https://github.com/Andres9890/iagitbetter/actions/workflows/unit-test.yml/badge.svg)](https://github.com/Andres9890/iagitbetter/actions/workflows/unit-test.yml)
[![Downloads Badge]][Downloads Link]

iagitbetter is a python tool for archiving any git repository to the [Internet Archive](https://archive.org/), An improved version of iagitup with support for all git providers, it downloads the complete repository, creates git bundles, uploads all files preserving structure, and archives to archive.org

- This project is heavily based off [iagitup](https://github.com/gdamdam/iagitup) by Giovanni Damiola, credits to them (also credits to [tubeup](https://github.com/bibanon/tubeup) by bibanon for taking some stuff and modifying them)

## Features

- Works with ALL git providers (GitHub, GitLab, BitBucket, Codeberg, Gitea, Gitee, Gogs, SourceForge, and more)
- Archive all repositories from a user or organization with options
- Self-hosted git instance support (GitLab, Gitea, Forgejo, Gogs, Gerrit, etc)
- Downloads and uploads the entire repository file structure
- Preserves provider directories like `.github/`, `.gitlab/`, `.gitea/` folders
- Download repository releases with assets from supported providers
- Clone and archive all branches of a repository with proper directory structure
- Automatically fetches repository metadata from git provider APIs when available
- API token authentication for private and self-hosted repositories
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
iagitbetter <git_url_or_profile> [options]
```

### Basic Arguments

- `<git_url_or_profile>` – Git repository URL or user/organization profile URL to archive

### Options

- `--metadata=<key:value>` – custom metadata to add to the IA item
- `--bundle-only` – only upload git bundle, not all files
- `--quiet` / `-q` – suppress verbose output
- `--version` – show version information
- `--no-update-check` – skip checking for updates on PyPI
- `--no-repo-info` - skip creating the repository info file

### Release Options

- `--releases` – download releases from the repository (GitHub, GitLab, Codeberg, Gitea)
- `--all-releases` – download all releases (default: latest release only)
- `--latest-release` – download only the latest release (default when `--releases` is used)

### Branch Options

- `--all-branches` – clone and archive all branches of the repository
- `--branch <name>` – clone and archive a specific branch of the repository

### User/Org Archiving Options

- `--skip-forks` – skip forked repositories when archiving profiles
- `--skip-archived` – skip archived repositories when archiving profiles
- `--skip-private` – skip private repositories when archiving profiles
- `--max-repos <number>` – maximum number of repositories to archive from a profile

### Self-Hosted Instance Options

- `--git-provider-type {github,gitlab,gitea,bitbucket,gogs,gitee,gerrit,sourceforge,launchpad}` – specify the git provider type for self-hosted instances
- `--api-url <url>` – custom API URL for self-hosted instances (e.g., `https://git.example.com/api/v1`)
- `--api-token <token>` – API token for authentication with private/self-hosted repositories

## Supported Git Providers

See [`SUPPORTED_PROVIDERS.md`](SUPPORTED_PROVIDERS.md) for detailed information about each provider

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
- User/organization avatar

### Release Support

For providers that support releases (GitHub, GitLab, Codeberg, Gitea, Gitee, Gogs, SourceForge), iagitbetter can:
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

# Archive from Gitee
iagitbetter https://gitee.com/user/repository

# Archive from Gogs instance
iagitbetter --git-provider-type gogs https://gogs.example.com/user/repository

# Archive from SourceForge (Git repos only)
iagitbetter https://sourceforge.net/p/project/dog/

# Archive from GitHub Gist
iagitbetter https://gist.github.com/username/gist_id
```

### User/Org Archiving

Archive all repositories from a user or organization profile:

```bash
# Archive all public repositories from a GitHub user
iagitbetter https://github.com/torvalds

# Archive all repositories from a GitLab organization
iagitbetter https://gitlab.com/gitlab-org

# Archive from Codeberg user
iagitbetter https://codeberg.org/username

# Archive from Gitea user
iagitbetter https://gitea.com/username

# Archive from Bitbucket workspace
iagitbetter https://bitbucket.org/atlassian
```

#### User/Org Archiving with Filters

```bash
# Skip forked repositories
iagitbetter https://github.com/username --skip-forks

# Skip archived repositories
iagitbetter https://github.com/username --skip-archived

# Skip private repositories (useful with API token)
iagitbetter https://github.com/username --api-token TOKEN --skip-private

# Combine multiple filters
iagitbetter https://github.com/username --skip-forks --skip-archived

# Limit number of repositories to archive
iagitbetter https://github.com/username --max-repos 10

# Archive first 5 non-fork repositories
iagitbetter https://github.com/username --skip-forks --max-repos 5
```

#### User/Org Archiving with Additional Features

```bash
# Archive all repos with their releases
iagitbetter https://github.com/username --releases --all-releases

# Archive all repos with all branches
iagitbetter https://github.com/username --all-branches

# Combine profile archiving with multiple features
iagitbetter https://github.com/username --skip-forks --releases --all-branches

# Quiet mode for profile archiving (less verbose output)
iagitbetter https://github.com/username --skip-forks --quiet
```

#### Self-Hosted User/Org Archiving

```bash
# Archive all repos from self-hosted GitLab user
iagitbetter https://gitlab.example.com/username \
  --git-provider-type gitlab \
  --api-token glpat-xxxxxxxxxxxxx

# Archive all repos from self-hosted Gitea organization
iagitbetter https://git.example.com/organization \
  --git-provider-type gitea \
  --api-token your_token_here

# Self-hosted with filters
iagitbetter https://gitlab.company.com/team \
  --git-provider-type gitlab \
  --api-token TOKEN \
  --skip-forks \
  --skip-archived \
  --max-repos 20
```

### Self-Hosted Repositories

```bash
# Self-hosted GitLab (auto-detection)
iagitbetter https://gitlab.example.com/user/repository

# Self-hosted GitLab with API configuration
iagitbetter --git-provider-type gitlab \
  --api-url https://gitlab.example.com/api/v4 \
  https://gitlab.example.com/user/repository

# Self-hosted Gitea/Forgejo with authentication
iagitbetter --git-provider-type gitea \
  --api-token your_token_here \
  https://git.example.com/user/repository

# Private repository on self-hosted instance
iagitbetter --git-provider-type gitlab \
  --api-url https://gitlab.example.com/api/v4 \
  --api-token glpat-xxxxxxxxxxxxx \
  https://gitlab.example.com/user/private-repo
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

# Archive a specific branch
iagitbetter --branch test https://github.com/user/repo

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

# Self-hosted with all features
iagitbetter --git-provider-type gitlab \
  --api-token glpat-xxxxxxxxxxxxx \
  --all-branches \
  --releases --all-releases \
  https://gitlab.example.com/user/repo
```

## Profile Archiving Details

When you provide a user or organization profile URL (e.g., `https://github.com/username`), iagitbetter will:

1. Automatically recognize the URL as a user/org rather than a repository
2. Query the git provider's API to get all repositories for that user/org
3. Filter repositories based on the options (`--skip-forks`, `--skip-archived`, etc)
4. Archive each repository of user/org individually
5. Provide a summary of what was archived and if there was any failures

### Profile Archiving Output

The tool provides detailed progress information:
```
PROFILE ARCHIVING MODE
Username/Organization: torvalds
Git Provider: github

Fetching repositories from profile...
   Found 25 repositories for torvalds
   Filtered out 5 forked repositories
   
Will archive 20 repositories

Repository 1/20: torvalds/linux
   Repository: torvalds/linux
   Git Provider: github
   Will archive: Repository files, Default branch
...
Successfully archived: torvalds/linux
   URL: https://archive.org/details/torvalds-linux-20671005120000

PROFILE ARCHIVING SUMMARY
Username/Organization: torvalds
Total repositories found: 25
Repositories archived: 20
  Successful: 20
  Failed: 0

Successfully archived repositories:
  torvalds/linux
    https://archive.org/details/torvalds-linux-20241005120000
  torvalds/subsurface
    https://archive.org/details/torvalds-subsurface-20241005120100
  ...
```

## API Token Generation

### GitHub - GitHub Enterprise
1. Go to Settings → Developer settings → Personal access tokens
2. Generate new token (classic) with `repo` scope
3. Use with `--api-token ghp_...`

### GitLab - Self-Hosted GitLab
1. Go to User Settings → Access Tokens
2. Create token with `read_api` and `read_repository` scopes
3. Use with `--api-token glpat-...`

### Gitea - Forgejo
1. Go to Settings → Applications → Generate New Token
2. Select `read:repository` permission
3. Use with `--api-token ...`

### Gitee
1. Go to Settings → Private Tokens → Generate New Token
2. Select repository access scopes
3. Use with `--api-token ...`

### Gogs
1. Go to Settings → Applications → Generate New Token
2. This is experimental API support
3. Use with `--api-token ...`

### SourceForge
1. Go to https://sourceforge.net/auth/oauth/
2. Generate OAuth bearer token
3. Use with `--api-token BEARER_TOKEN`

## Repository Structure Preservation

By default, iagitbetter preserves the complete repository structure when uploading to Internet Archive. For example, if your repository contains:

```
README.md
.github/
  └── workflows/
      └── lint.yml
src/
  ├── main.py
  └── utils/
      └── helper.py
docs/
  └── guide.md
tests/
  └── test_main.py
```

The archive will contain all files exactly as shown, including the `.github/` directory with workflows

### With --all-branches
When using `--all-branches`, the structure becomes:
```
README.md
.github/workflows/lint.yml
src/main.py
src/utils/helper.py
docs/guide.md
tests/test_main.py
{repo-name}-{owner}_branches/
  └── develop/
      ├── README.md
      ├── .github/workflows/ci.yml
      ├── src/main.py
      └── ...
  └── feature/
      ├── README.md
      ├── src/main.py
      └── ...
{owner}-{repo}.bundle
```

### With --releases
When using `--releases`, a releases directory is added:
```
README.md
.github/workflows/ci.yml
src/main.py
docs/guide.md
{owner}-{repo}_releases/
  └── v1.0.0/
      ├── v1.0.0.info.json
      ├── v1.0.0-source.zip
      └── v1.0.0-source.tar.gz
{owner}-{repo}.bundle
```

The files will be uploaded to Internet Archive exactly as shown above, preserving the directory structure

If you use the `--bundle-only` flag, only the git bundle will be uploaded.

## How it works

### Repository Analysis
1. `iagitbetter` parses the git URL to identify the provider and repository details
2. For self-hosted instances, it detects or uses the specified provider type
3. It attempts to fetch additional metadata from the provider's API (if supported)
4. Repository information is extracted including owner, name, and provider details

### Profile Analysis (Profile Archiving Mode)
1. Detects profile URL format (username/org)
2. Queries the git provider's API to fetch all repositories
3. Applies filters based on command-line options
4. Archives each repository individually
5. Generates summary report

### Repository Download
1. The git repository is cloned to a temporary directory using GitPython
2. If `--all-branches` is specified, all remote branches are fetched and separate directories are created for each non-default branch
3. The first commit date is extracted for the creation date
4. A git bundle is created with all branches and tags
5. User/organization avatar is downloaded if available

### Branch Processing (when `--all-branches` is used)
1. All remote branches are fetched from the repository
2. For each non-default branch, a separate directory named `{repo-name}-{owner}_branches/{branch-name}` is created
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
3. Provider directories like `.github/`, `.gitlab/`, `.gitea/` are preserved
4. Branches are included (if archived with `--all-branches`)
5. Release files are included (if requested)
6. The git bundle is included
7. User/organization avatar is included
8. README.md is converted to HTML for the item description

### Archive Format
- Identifier: `{owner}-{repo}-{timestamp}`
- Title: `{owner} - {repo}`
- Date: First commit date
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

When releases are archived, they can be found in the `{owner}-{repo}_releases/` directory of the archive, Each release includes:

- `{version}.info.json` - Complete release metadata
- `{version}.source.zip` - Source code archive
- `{version}.source.tar.gz` - Source code tarball
- binaries

## Key Improvements over iagitup

- Works with any git provider (public and self-hosted)
- Archive all repositories from a user or org
- Self-hosted git instance support with authentication
- Uploads the entire repository file structure
- Preserves provider directories (`.github/`, `.gitlab/`, `.gitea/`)
- Can archive all branches of a repository
- Automatically fetches repository information from APIs
- Downloads user/organization avatars
- Uses first commit date for historical accuracy
- Leverages git provider APIs for comprehensive metadata

## Requirements

- Python 3.9+
- Git
- Internet Archive account and credentials
- Required dependencies in the [`requirements.txt`](requirements.txt) file

## Troubleshooting

### Authentication Issues
- Ensure your API token has the correct permissions
- For self-hosted instances, verify the API URL is correct
- Check that the token hasn't expired

### API Metadata Fetching
- If metadata isn't fetched, the repository will still be archived
- Use `--git-provider-type` to help with provider detection
- Some self-hosted instances may have APIs disabled

### Private Repositories
- Always use `--api-token` for private repositories
- Ensure the token has read access to the repository
- For self-hosted instances, you may need both `--api-url` and `--api-token`

### Profile Archiving Issues
- Rate Limiting: Public APIs have rate limits (use `--api-token` to increase limits)
- Large Profiles: Use `--max-repos` to limit the number of repositories
- Failed Repositories: Individual repository failures won't stop the entire process
- Time Consumption: Archiving many repositories takes significant time