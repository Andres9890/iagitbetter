# Supported Git Providers

iagitbetter supports a wide range of git providers, public services and self-hosted ones
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

| Provider | Metadata | Releases | Avatar | Self-Hosted | Notes |
|----------|----------|----------|--------|-------------|-------|
| GitHub | ✅ | ✅ | ✅ | ✅ | Full support |
| GitLab | ✅ | ✅ | ✅ | ✅ | Full support |
| Codeberg | ✅ | ✅ | ✅ | N/A | Forgejo-based |
| Gitea | ✅ | ✅ | ✅ | ✅ | Full support |
| Forgejo | ✅ | ✅ | ✅ | ✅ | Use Gitea mode |
| Bitbucket | ✅ | ⚠️ | ✅ | N/A | Limited releases |
| Generic | ❌ | ❌ | ❌ | ✅ | Basic archiving only |

---

## Feature Support by Provider

### Metadata Fields

| Field | GitHub | GitLab | Bitbucket | Gitea/Forgejo |
|-------|--------|--------|-----------|---------------|
| Description | ✅ | ✅ | ✅ | ✅ |
| Stars | ✅ | ✅ | ❌ | ✅ |
| Forks | ✅ | ✅ | ❌ | ✅ |
| Watchers | ✅ | ❌ | ❌ | ✅ |
| Language | ✅ | ❌ | ✅ | ✅ |
| License | ✅ | ❌ | ❌ | ❌ |
| Topics | ✅ | ✅ | ❌ | ✅ |
| Homepage | ✅ | ❌ | ✅ | ✅ |
| Created At | ✅ | ✅ | ✅ | ✅ |
| Updated At | ✅ | ✅ | ✅ | ✅ |
| Default Branch | ✅ | ✅ | ✅ | ✅ |
| Is Private | ✅ | ✅ | ✅ | ✅ |
| Is Fork | ✅ | ✅ | ✅ | ✅ |
| Is Archived | ✅ | ✅ | ❌ | ✅ |

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

## Adding New Provider Support

Want to add support for a new provider? Here's what's needed:

1. **API Endpoint Detection** - Add to `_build_api_url()` method
2. **Response Parsing** - Add parser method like `_parse_provider_response()`
3. **Release API** - Add release fetching in `fetch_releases()`
4. **Testing** - Test with public repositories from that provider

Contributions are welcome

---

## Additional Resources

- [GitHub API Documentation](https://docs.github.com/en/rest)
- [GitLab API Documentation](https://docs.gitlab.com/ee/api/)
- [Gitea API Documentation](https://docs.gitea.io/en-us/api-usage/)
- [Forgejo API Documentation](https://forgejo.org/docs/latest/user/api-usage/)
- [Bitbucket API Documentation](https://developer.atlassian.com/bitbucket/api/2/reference/)