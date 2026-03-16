# Supported Git Providers

iagitbetter supports a wide range of git providers, public and self-hosted ones,
This file provides detailed information about each supported provider

## Provider Support Levels

### 🟢 Full Support
- API metadata fetching
- Release downloading
- Avatar downloading
- repository information

### 🟡 Partial Support
- Basic cloning and archiving works
- Limited/no API metadata
- Manual configuration may be needed

### 🔵 Self-Hosted Support
- Works with custom instances
- May require manual configuration
- API support varies by instance

---

## Public Git Providers

### GitHub (github.com)
**Support Level:** 🟢 Full Support

GitHub is fully supported

#### Features
- ✅ Metadata fetching
- ✅ Release downloading
- ✅ Avatar downloading
- ✅ Topics and tags
- ✅ Stars, forks, watchers count
- ✅ License information
- ✅ Primary language detection
- ✅ Issue and wiki status

#### Usage
```bash
# Public repository
iagitbetter https://github.com/user/repository

# With releases
iagitbetter --releases --all-releases https://github.com/user/repository

# Private repository (requires token)
iagitbetter --api-token example https://github.com/user/private-repo
```

#### API Token
1. Go to Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo` (for private repos) or `public_repo` (for public only)
4. Use token with `--api-token ghp_...`

#### API Endpoints
- Base: `https://api.github.com`
- Repository: `https://api.github.com/repos/{owner}/{repo}`
- Releases: `https://api.github.com/repos/{owner}/{repo}/releases`

---

### GitHub Gist (gist.github.com)
**Support Level:** 🟢 Full Support

GitHub Gists are fully supported as they are git repositories

#### Features
- ✅ Metadata fetching
- ✅ File listing
- ✅ Language detection
- ✅ Public/private status
- ✅ Comment count
- ✅ Fork count
- ✅ Avatar downloading
- ❌ Stars (not exposed via API)
- ❌ Releases

#### Usage
```bash
# Public gist
iagitbetter https://gist.github.com/username/gist_id

# Private gist (requires token)
iagitbetter --api-token ghp_... https://gist.github.com/username/gist_id

# With --git-provider-type
iagitbetter --git-provider-type gist https://gist.github.com/username/gist_id
```

#### API Token
Same as GitHub:
1. Go to Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `gist` for gist access
4. Use token with `--api-token ghp_...`

#### API Endpoints
- Base: `https://api.github.com`
- Gist: `https://api.github.com/gists/{gist_id}`

---

### GitLab (gitlab.com)
**Support Level:** 🟢 Full Support

GitLab.com is fully supported

#### Features
- ✅ Metadata fetching
- ✅ Release downloading
- 🟡 Avatar downloading
- ✅ Topics and tags
- ✅ Stars and forks count
- ✅ Visibility settings
- ✅ CI/CD status
- ✅ Wiki and pages status

#### Usage
```bash
# Public repository
iagitbetter https://gitlab.com/user/repository

# With releases
iagitbetter --releases https://gitlab.com/user/repository

# Private repository
iagitbetter --api-token example https://gitlab.com/user/private-repo
```

#### API Token
1. Go to User Settings → Access Tokens
2. Create personal access token
3. Select scopes: `read_api`, `read_repository`
4. Use token with `--api-token glpat-...`

#### API Endpoints
- Base: `https://gitlab.com/api/v4`
- Repository: `https://gitlab.com/api/v4/projects/{owner}%2F{repo}`
- Releases: `https://gitlab.com/api/v4/projects/{id}/releases`

---

### Codeberg (codeberg.org)
**Support Level:** 🟢 Full Support

Codeberg uses Forgejo and is fully supported

#### Features
- ✅ Metadata fetching
- ✅ Release downloading
- ✅ Avatar downloading
- ✅ Stars and forks count
- ✅ Topics
- ✅ Wiki and issue status

#### Usage
```bash
# Public repository
iagitbetter https://codeberg.org/user/repository

# With releases
iagitbetter --releases https://codeberg.org/user/repository
```

#### API Token
1. Go to Settings → Applications → Generate New Token
2. Select permissions: `read:repository`
3. Use token with `--api-token`

#### API Endpoints
- Base: `https://codeberg.org/api/v1`
- Repository: `https://codeberg.org/api/v1/repos/{owner}/{repo}`
- Releases: `https://codeberg.org/api/v1/repos/{owner}/{repo}/releases`

---

### Gitea (gitea.com)
**Support Level:** 🟢 Full Support

Official Gitea hosting is fully supported

#### Features
- ✅ Metadata fetching
- ✅ Release downloading
- ✅ Avatar downloading
- ✅ Stars, forks, watchers
- ✅ Topics
- ✅ Wiki, issues, projects status

#### Usage
```bash
# Public repository
iagitbetter https://gitea.com/user/repository

# With API token
iagitbetter --api-token example https://gitea.com/user/repository
```

#### API Endpoints
- Base: `https://gitea.com/api/v1`
- Repository: `https://gitea.com/api/v1/repos/{owner}/{repo}`
- Releases: `https://gitea.com/api/v1/repos/{owner}/{repo}/releases`

---

### Bitbucket (bitbucket.org)
**Support Level:** 🟢 Full Support

Bitbucket is fully supported

#### Features
- ✅ Metadata fetching
- ✅ Avatar downloading
- ✅ Repository description
- ✅ Language detection
- ✅ Wiki and issue status
- ⚠️ Limited release support

#### Usage
```bash
# Public repository
iagitbetter https://bitbucket.org/user/repository

# With releases (if available)
iagitbetter --releases https://bitbucket.org/user/repository
```

#### API Endpoints
- Base: `https://api.bitbucket.org/2.0`
- Repository: `https://api.bitbucket.org/2.0/repositories/{owner}/{repo}`

#### Notes
- Bitbucket uses downloads instead of releases, release functionality may be limited

---

### GitFlic (gitflic.ru)
**Support Level:** 🟢 Full Support

GitFlic and self-hosted GitFlic instances are fully supported

#### Features
- ✅ Metadata fetching
- ✅ Release downloading
- ❌ Avatar downloading
- ✅ Topics
- ✅ Primary language detection
- ✅ Visibility and fork status

#### Usage
```bash
# Public repository
iagitbetter https://gitflic.ru/user/repository

# With releases
iagitbetter --releases https://gitflic.ru/user/repository

# Private repository (requires token)
iagitbetter --api-token example https://gitflic.ru/user/private-repo

# Self-hosted
iagitbetter --git-provider-type gitflic \
  --api-url https://api.gitflic.example.com \
  https://gitflic.example.com/user/repository
```

#### API Token
1. Go to Profile Settings → API Tokens
2. Generate a new token
3. Use token with `--api-token`

#### API Endpoints
- Base: `https://api.gitflic.ru`
- Repository: `https://api.gitflic.ru/project/{owner}/{repo}`
- Releases: `https://api.gitflic.ru/project/{owner}/{repo}/release`

---

## Self-Hosted Instances

### Self-Hosted GitLab
**Support Level:** 🔵 Self-Hosted Support

Self-hosted GitLab instances are fully supported

#### Features
- ✅ Full API support
- ✅ Release downloading
- ✅ Avatar downloading
- ✅ Comprehensive metadata
- ⚠️ Requires API URL specification

#### Usage
```bash
# With auto-detection (may work)
iagitbetter https://gitlab.example.com/user/repository

# With manual configuration (recommended)
iagitbetter --git-provider-type gitlab \
  --api-url https://gitlab.example.com/api/v4 \
  https://gitlab.example.com/user/repository

# With authentication
iagitbetter --git-provider-type gitlab \
  --api-url https://gitlab.example.com/api/v4 \
  --api-token example \
  https://gitlab.example.com/user/repository
```

#### Configuration
1. Determine your GitLab instance URL (e.g., `https://gitlab.example.com`)
2. API URL is typically: `https://gitlab.example.com/api/v4`
3. Generate personal access token in Settings → Access Tokens
4. Use `--git-provider-type gitlab` and `--api-url`

---

### Self-Hosted Gitea
**Support Level:** 🔵 Self-Hosted Support

Self-hosted Gitea instances are fully supported.

#### Features
- ✅ Full API support
- ✅ Release downloading
- ✅ Avatar downloading
- ✅ Metadata fetching
- ✅ Usually auto-detects API URL

#### Usage
```bash
# Often works with auto-detection
iagitbetter https://git.example.com/user/repository

# With manual configuration
iagitbetter --git-provider-type gitea \
  --api-url https://git.example.com/api/v1 \
  https://git.example.com/user/repository

# With authentication
iagitbetter --git-provider-type gitea \
  --api-token example \
  https://git.example.com/user/repository
```

#### Configuration
1. API URL format: `https://git.example.com/api/v1`
2. Generate token in Settings → Applications
3. Use `--git-provider-type gitea`

---

### Self-Hosted Forgejo
**Support Level:** 🔵 Self-Hosted Support

Forgejo (Gitea fork) is fully supported using Gitea API.

#### Features
- ✅ Full API support
- ✅ Release downloading
- ✅ Avatar downloading
- ✅ Metadata fetching

#### Usage
```bash
# Same as Gitea
iagitbetter --git-provider-type gitea \
  https://forgejo.example.com/user/repository

# With authentication
iagitbetter --git-provider-type gitea \
  --api-token example \
  https://forgejo.example.com/user/repository
```

#### Notes
- Use `--git-provider-type gitea` for Forgejo instances
- API is compatible with Gitea v1 API
- Codeberg.org runs Forgejo

---

### GitHub Enterprise
**Support Level:** 🔵 Self-Hosted Support

GitHub Enterprise servers are supported using GitHub API.

#### Features
- ✅ Full API support
- ✅ Release downloading
- ✅ Avatar downloading
- ✅ Comprehensive metadata
- ⚠️ May require API URL specification

#### Usage
```bash
# Auto-detection (may work if domain contains 'github')
iagitbetter https://github.example.com/user/repository

# With manual configuration
iagitbetter --git-provider-type github \
  --api-url https://github.example.com/api/v3 \
  https://github.example.com/user/repository

# With authentication
iagitbetter --git-provider-type github \
  --api-token example \
  https://github.example.com/user/repository
```

#### Configuration
1. API URL is typically: `https://github.example.com/api/v3`
2. Generate personal access token in Settings
3. Use `--git-provider-type github`

---

## Generic Git Providers

### Any Git Provider
**Support Level:** 🟡 Partial Support

Any git repository accessible via HTTP(S) or SSH can be archived

#### Features
- ✅ Repository cloning
- ✅ Bundle creation
- ✅ File structure preservation
- ❌ No API metadata
- ❌ No release downloading
- ❌ No avatar downloading

#### Usage
```bash
# Basic cloning and archiving
iagitbetter https://git.example.com/user/repository.git

# With authentication (SSH)
iagitbetter git@git.example.com:user/repository.git

# With all branches
iagitbetter --all-branches https://git.example.com/user/repository.git
```

#### What Works
- Complete repository archiving
- Branch archiving
- Git bundle creation
- File structure preservation
- `.github/`, `.gitlab/` folders preserved

#### What Doesn't Work
- API metadata fetching
- Release downloading
- Avatar downloading
- Automatic star/fork counts

---

## Provider Comparison Table

### Fully Supported Providers

| Provider | Metadata | Releases | Avatar | Self-Hosted | Notes |
|----------|----------|----------|--------|-------------|-------|
| GitHub | ✅ | ✅ | ✅ | ✅ | Full support |
| GitHub Gist | ✅ | ❌ | ✅ | N/A | Full support, no releases |
| GitLab | ✅ | ✅ | ✅ | ✅ | Full support |
| Codeberg | ✅ | ✅ | ✅ | N/A | Forgejo-based |
| Gitea | ✅ | ✅ | ✅ | ✅ | Full support |
| Forgejo | ✅ | ✅ | ✅ | ✅ | Use Gitea mode |
| Bitbucket | ✅ | ⚠️ | ✅ | N/A | Limited releases |
| GitFlic | ✅ | ✅ | ❌ | ✅ | Full support |

### Experimental / New Providers

| Provider | Metadata | Releases | Avatar | Self-Hosted | Notes |
|----------|----------|----------|--------|-------------|-------|
| Gitee | ✅ | ✅ | ✅ | ❌ | China's largest platform |
| Gogs | ✅ | ✅ | ✅ | ✅ | Experimental API |
| Notabug | ✅ | ✅ | ✅ | N/A | Uses Gogs |
| SourceForge | ⚠️ | ✅ | ❌ | N/A | Git repos only |
| Launchpad | ⚠️ | ❌ | ❌ | N/A | Primarily Bazaar |
| Gerrit | ⚠️ | ❌ | ❌ | ✅ | Code review focused |

---

## Feature Support by Provider

### Metadata Fields

| Field | GitHub | GitLab | Bitbucket | Gitea/Forgejo | GitFlic |
|-------|--------|--------|-----------|---------------|---------|
| Description | ✅ | ✅ | ✅ | ✅ | ✅ |
| Stars | ✅ | ✅ | ❌ | ✅ | ❌ |
| Forks | ✅ | ✅ | ❌ | ✅ | ❌ |
| Watchers | ✅ | ❌ | ❌ | ✅ | ❌ |
| Language | ✅ | ❌ | ✅ | ✅ | ✅ |
| License | ✅ | ❌ | ❌ | ❌ | ❌ |
| Topics | ✅ | ✅ | ❌ | ✅ | ✅ |
| Homepage | ✅ | ❌ | ✅ | ✅ | ✅ |
| Created At | ✅ | ✅ | ✅ | ✅ | ❌ |
| Updated At | ✅ | ✅ | ✅ | ✅ | ❌ |
| Default Branch | ✅ | ✅ | ✅ | ✅ | ✅ |
| Is Private | ✅ | ✅ | ✅ | ✅ | ✅ |
| Is Fork | ✅ | ✅ | ✅ | ✅ | ✅ |
| Is Archived | ✅ | ✅ | ❌ | ✅ | ❌ |

---

## Troubleshooting by Provider

### GitHub Issues
- **Rate Limiting**: GitHub has API rate limits (60/hour unauthenticated, 5000/hour authenticated)
- **Solution**: Use `--api-token` to increase rate limit

### GitLab Issues
- **Project ID**: Some self-hosted instances may have API quirks
- **Solution**: Ensure API URL includes `/api/v4`

### Self-Hosted Issues
- **API Not Found**: Some instances have APIs disabled
- **Solution**: Use basic cloning without API features
- **SSL Errors**: Self-signed certificates may cause issues
- **Solution**: Configure git to accept certificates or use HTTP

### Generic Provider Issues
- **No Metadata**: Generic providers don't provide API metadata
- **Expected**: This is normal, basic archiving still works
- **No Releases**: Release downloading requires API support
- **Solution**: Manually download releases and add to archive

---

## Experimental / New Providers

### Gitee (gitee.com)
**Support Level:** 🟢 Full Support (Experimental)

Gitee is China's largest code hosting platform with full API support

#### Features
- ✅ Metadata fetching
- ✅ Release downloading (API v5)
- ✅ Avatar downloading
- ✅ Topics and tags
- ✅ Stars and forks count
- ✅ User/organization archiving

#### Usage
```bash
# Public repository
iagitbetter https://gitee.com/user/repository

# With API token
iagitbetter --git-provider-type gitee --api-token TOKEN https://gitee.com/user/repository
```

#### API Documentation
- Base: `https://gitee.com/api/v5`
- Repository: `https://gitee.com/api/v5/repos/{owner}/{repo}`
- Releases: `https://gitee.com/api/v5/repos/{owner}/{repo}/releases`
- Swagger Docs: https://gitee.com/api/v5/swagger

---

### Gogs Self-Hosted
**Support Level:** 🔵 Self-Hosted Support (Experimental)

Gogs is a lightweight Git service, API is experimental but functional

#### Features
- ✅ API metadata fetching
- ✅ Release downloading
- ✅ Avatar downloading
- ⚠️ API is experimental and may change

#### Usage
```bash
# Self-hosted Gogs instance
iagitbetter --git-provider-type gogs \
  --api-url https://gogs.example.com/api/v1 \
  https://gogs.example.com/user/repository

# With authentication
iagitbetter --git-provider-type gogs \
  --api-token TOKEN \
  https://gogs.example.com/user/repository
```

#### API Documentation
- API version: v1
- Format: `/api/v1/*`
- GitHub: https://github.com/gogs/docs-api

---

### Notabug (notabug.org)
**Support Level:** 🟡 Partial Support

Notabug runs a fork of Gogs, should work with Gogs provider type

#### Usage
```bash
# Notabug repository
iagitbetter --git-provider-type gogs https://notabug.org/user/repository
```

---

### SourceForge (sourceforge.net)
**Support Level:** 🟡 Partial Support (Git only)

SourceForge supports Git, SVN, and Mercurial. Only Git repos can be archived

#### Features
- ✅ Allura API support
- ✅ Release API
- ⚠️ Only Git repositories supported
- ❌ SVN/Mercurial not supported

#### Usage
```bash
# Git repository on SourceForge
iagitbetter https://sourceforge.net/p/project/code/

# With OAuth token
iagitbetter --git-provider-type sourceforge --api-token BEARER_TOKEN \
  https://sourceforge.net/p/project/code/
```

#### API Documentation
- Main API: https://sourceforge.net/p/forge/documentation/API/
- Release API: https://sourceforge.net/p/forge/documentation/Using%20the%20Release%20API/
- Interactive docs: https://sourceforge.net/api-docs/

---

### Launchpad (launchpad.net)
**Support Level:** 🟡 Partial Support

Launchpad is Ubuntu's code hosting platform with a REST API

#### Features
- ✅ REST API available
- ⚠️ Primarily for Bazaar (bzr), Git support limited
- ✅ User repository listing
- ⚠️ Complex authentication

#### Usage
```bash
# Launchpad Git repository
iagitbetter https://git.launchpad.net/project

# May require manual configuration
```

#### API Documentation
- API Portal: https://api.launchpad.net/
- Help: https://help.launchpad.net/API
- API Docs: https://launchpad.net/+apidoc/

---

### Gerrit (gerrit-review.googlesource.com)
**Support Level:** 🟡 Partial Support

Gerrit is primarily a code review system, but hosts Git repositories

#### Features
- ✅ Full REST API
- ✅ Repository metadata
- ⚠️ Focused on code review
- ❌ No release concept

#### Usage
```bash
# Gerrit repository
iagitbetter --git-provider-type gerrit \
  https://gerrit.example.com/project

# With authentication
iagitbetter --git-provider-type gerrit \
  --api-url https://gerrit.example.com \
  --api-token TOKEN \
  https://gerrit.example.com/project
```

#### API Documentation
- Main API: https://gerrit-review.googlesource.com/Documentation/rest-api.html
- Projects API: https://gerrit-review.googlesource.com/Documentation/rest-api-projects.html

---

## Adding New Provider Support

Want to add support for a new provider? Here's what's needed:

1. **API Endpoint Detection** - Add to `_build_api_url()` method
2. **Response Parsing** - Add parser method like `_parse_provider_response()`
3. **Release API** - Add release fetching in `fetch_releases()`
4. **Testing** - Test with public repositories from that provider

Contributions are welcome

---

## Additional Resources

### Currently Supported
- [GitHub API Documentation](https://docs.github.com/en/rest)
- [GitHub Gist API Documentation](https://docs.github.com/en/rest/gists)
- [GitLab API Documentation](https://docs.gitlab.com/ee/api/)
- [Gitea API Documentation](https://docs.gitea.io/en-us/api-usage/)
- [Forgejo API Documentation](https://forgejo.org/docs/latest/user/api-usage/)
- [Bitbucket API Documentation](https://developer.atlassian.com/bitbucket/api/2/reference/)
- [GitFlic API Documentation](https://docs.gitflic.ru/latest/en/api/intro/)

### Experimental / New Providers
- [Gitee API Documentation](https://gitee.com/api/v5/swagger)
- [Gogs API Documentation](https://github.com/gogs/docs-api)
- [SourceForge API Documentation](https://sourceforge.net/p/forge/documentation/API/)
- [Launchpad API Documentation](https://api.launchpad.net/)
- [Gerrit REST API Documentation](https://gerrit-review.googlesource.com/Documentation/rest-api.html)
