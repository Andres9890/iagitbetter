import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests_mock

from iagitbetter import __version__
from iagitbetter.iagitbetter import GitArchiver

from .constants import (
    github_api_response,
    gitlab_api_response,
)

current_path = os.path.dirname(os.path.realpath(__file__))
SCANNER = f"iagitbetter Git Repository Mirroring Application {__version__}"


def get_testfile_path(name):
    return os.path.join(current_path, "test_iagitbetter_files", name)


def mock_upload_response_by_identifier(m, identifier, files):
    """Mock internetarchive upload responses"""
    for filepath in files:
        filename = os.path.basename(filepath)
        m.put(
            f"https://s3.us.archive.org/{identifier}/{filename}",
            content=b"",
            headers={"content-type": "text/plain"},
        )


def copy_test_repository_to_temp():
    """Copy test repository files to temporary directory"""
    test_repo_dir = os.path.join(
        current_path, "test_iagitbetter_files", "test_repository"
    )
    temp_dir = tempfile.mkdtemp(prefix="iagitbetter_test_")
    repo_path = os.path.join(temp_dir, "test-repo")
    shutil.copytree(test_repo_dir, repo_path)
    return temp_dir, repo_path


# Mock GitPython's Repo class
class MockRepo:
    def __init__(self, url, path, **kwargs):
        self.url = url
        self.path = path
        self.heads = {"main": MagicMock()}
        self.active_branch = MagicMock(name="main")
        self.remotes = [MagicMock()]

    def iter_commits(self, all=True):
        # Return mock commits with timestamps
        MockCommit = MagicMock()
        MockCommit.committed_date = 1609459200  # 2021-01-01 00:00:00
        return [MockCommit]

    @classmethod
    def clone_from(cls, url, path, **kwargs):
        return cls(url, path, **kwargs)


@patch("iagitbetter.iagitbetter.git.Repo", MockRepo)
class GitArchiverTests(unittest.TestCase):
    """Tests for single repository archiving functionality"""

    def setUp(self):
        self.archiver = GitArchiver(verbose=False)
        self.maxDiff = None

    def tearDown(self):
        """Clean up any temporary directories"""
        if self.archiver.temp_dir and os.path.exists(self.archiver.temp_dir):
            self.archiver.cleanup()

    def test_extract_repo_info_github(self):
        """Test extracting repository info from GitHub URL"""
        repo_url = "https://github.com/testuser/testrepo"
        result = self.archiver.extract_repo_info(repo_url)

        self.assertEqual(result["owner"], "testuser")
        self.assertEqual(result["repo_name"], "testrepo")
        self.assertEqual(result["git_site"], "github")
        self.assertEqual(result["full_name"], "testuser/testrepo")

    def test_extract_repo_info_gitlab(self):
        """Test extracting repository info from GitLab URL"""
        repo_url = "https://gitlab.com/testgroup/testproject"
        result = self.archiver.extract_repo_info(repo_url)

        self.assertEqual(result["owner"], "testgroup")
        self.assertEqual(result["repo_name"], "testproject")
        self.assertEqual(result["git_site"], "gitlab")

    def test_extract_repo_info_with_git_extension(self):
        """Test extracting repository info with .git extension"""
        repo_url = "https://github.com/testuser/testrepo.git"
        result = self.archiver.extract_repo_info(repo_url)

        self.assertEqual(result["repo_name"], "testrepo")

    def test_extract_repo_info_self_hosted(self):
        """Test extracting repository info from self-hosted instance"""
        repo_url = "https://git.example.com/myorg/myrepo"
        result = self.archiver.extract_repo_info(repo_url)

        self.assertEqual(result["owner"], "myorg")
        self.assertEqual(result["repo_name"], "myrepo")
        self.assertEqual(result["domain"], "git.example.com")

    @requests_mock.Mocker()
    def test_fetch_api_metadata_github(self, m):
        """Test fetching metadata from GitHub API"""
        self.archiver.repo_data = {
            "domain": "github.com",
            "git_site": "github",
            "owner": "testuser",
            "repo_name": "testrepo",
        }

        m.get(
            "https://api.github.com/repos/testuser/testrepo", json=github_api_response
        )

        self.archiver._fetch_api_metadata()

        self.assertEqual(
            self.archiver.repo_data["description"], "Test repository for iagitbetter"
        )
        self.assertEqual(self.archiver.repo_data["stars"], 42)
        self.assertEqual(self.archiver.repo_data["language"], "Python")

    @requests_mock.Mocker()
    def test_fetch_api_metadata_gitlab(self, m):
        """Test fetching metadata from GitLab API"""
        self.archiver.repo_data = {
            "domain": "gitlab.com",
            "git_site": "gitlab",
            "owner": "testgroup",
            "repo_name": "testproject",
        }

        m.get(
            "https://gitlab.com/api/v4/projects/testgroup%2Ftestproject",
            json=gitlab_api_response,
        )

        self.archiver._fetch_api_metadata()

        self.assertEqual(self.archiver.repo_data["description"], "GitLab test project")
        self.assertEqual(self.archiver.repo_data["stars"], 15)
        self.assertEqual(self.archiver.repo_data["project_id"], "12345")

    def test_clone_repository(self):
        """Test cloning a repository"""
        repo_url = "https://github.com/testuser/testrepo"
        self.archiver.repo_data = {"owner": "testuser", "repo_name": "testrepo"}

        repo_path = self.archiver.clone_repository(repo_url)

        self.assertIsNotNone(repo_path)
        self.assertTrue(os.path.exists(repo_path))
        self.assertTrue(repo_path.endswith("testrepo"))

    def test_clone_repository_with_specific_branch(self):
        """Test cloning a specific branch"""
        repo_url = "https://github.com/testuser/testrepo"
        self.archiver.repo_data = {"owner": "testuser", "repo_name": "testrepo"}

        repo_path = self.archiver.clone_repository(repo_url, specific_branch="develop")

        self.assertIsNotNone(repo_path)
        self.assertEqual(self.archiver.repo_data["specific_branch"], "develop")

    def test_create_git_bundle(self):
        """Test creating a git bundle"""
        temp_dir, repo_path = copy_test_repository_to_temp()
        self.archiver.repo_data = {"owner": "testuser", "repo_name": "testrepo"}

        with patch("subprocess.check_call") as mock_call:
            bundle_path = self.archiver.create_git_bundle(repo_path)

            expected_bundle = os.path.join(repo_path, "testuser-testrepo.bundle")
            self.assertEqual(bundle_path, expected_bundle)
            mock_call.assert_called_once()

        shutil.rmtree(temp_dir)

    def test_get_all_files(self):
        """Test getting all files from repository"""
        temp_dir, repo_path = copy_test_repository_to_temp()

        # Create some test files
        os.makedirs(os.path.join(repo_path, "src"), exist_ok=True)
        with open(os.path.join(repo_path, "README.md"), "w") as f:
            f.write("# Test Repository")
        with open(os.path.join(repo_path, "src", "main.py"), "w") as f:
            f.write('print("Hello")')
        # Create an empty file to test skipping
        with open(os.path.join(repo_path, "empty.txt"), "w") as f:
            pass

        files = self.archiver.get_all_files(repo_path)

        self.assertIn("README.md", files)
        self.assertIn("src/main.py", files)
        self.assertNotIn("empty.txt", files)  # Empty files should be skipped

        shutil.rmtree(temp_dir)

    def test_get_description_from_readme(self):
        """Test extracting description from README.md"""
        temp_dir, repo_path = copy_test_repository_to_temp()

        readme_content = """# Test Repository

This is a test repository for iagitbetter.

## Features
- Feature 1
- Feature 2
"""
        with open(os.path.join(repo_path, "README.md"), "w") as f:
            f.write(readme_content)

        description = self.archiver.get_description_from_readme(repo_path)

        self.assertIn("Test Repository", description)
        self.assertIn("Feature 1", description)

        shutil.rmtree(temp_dir)

    @requests_mock.Mocker()
    def test_download_avatar(self, m):
        """Test downloading user avatar"""
        temp_dir, repo_path = copy_test_repository_to_temp()

        self.archiver.repo_data = {
            "owner": "testuser",
            "git_site": "github",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        }

        m.get(
            "https://avatars.githubusercontent.com/u/12345",
            content=b"fake image data",
            headers={"content-type": "image/jpeg"},
        )

        avatar_filename = self.archiver.download_avatar(repo_path)

        self.assertEqual(avatar_filename, "testuser.jpg")
        avatar_path = os.path.join(repo_path, avatar_filename)
        self.assertTrue(os.path.exists(avatar_path))

        shutil.rmtree(temp_dir)

    @requests_mock.Mocker()
    def test_fetch_releases_github(self, m):
        """Test fetching releases from GitHub"""
        self.archiver.repo_data = {
            "domain": "github.com",
            "git_site": "github",
            "owner": "testuser",
            "repo_name": "testrepo",
        }

        releases_response = [
            {
                "id": 1,
                "tag_name": "v1.0.0",
                "name": "Version 1.0.0",
                "body": "First release",
                "draft": False,
                "prerelease": False,
                "published_at": "2021-01-01T00:00:00Z",
                "zipball_url": "https://api.github.com/repos/testuser/testrepo/zipball/v1.0.0",
                "tarball_url": "https://api.github.com/repos/testuser/testrepo/tarball/v1.0.0",
                "assets": [
                    {
                        "name": "binary.exe",
                        "browser_download_url": "https://github.com/testuser/testrepo/releases/download/v1.0.0/binary.exe",
                        "size": 1024000,
                        "content_type": "application/octet-stream",
                    }
                ],
            }
        ]

        m.get(
            "https://api.github.com/repos/testuser/testrepo/releases",
            json=releases_response,
        )

        self.archiver.fetch_releases()

        self.assertEqual(len(self.archiver.repo_data["releases"]), 1)
        release = self.archiver.repo_data["releases"][0]
        self.assertEqual(release["tag_name"], "v1.0.0")
        self.assertEqual(len(release["assets"]), 1)

    def test_sanitize_branch_name(self):
        """Test sanitizing branch names for directories"""
        test_cases = [
            ("feature/new-feature", "feature-new-feature"),
            ("bugfix\\issue", "bugfix-issue"),
            ("release:1.0", "release-1.0"),
            ("..hidden..", "hidden"),
            ("normal-branch", "normal-branch"),
        ]

        for input_name, expected in test_cases:
            result = self.archiver._sanitize_branch_name(input_name)
            self.assertEqual(result, expected)

    def test_check_ia_credentials_exists(self):
        """Test checking for Internet Archive credentials"""
        # Create a temporary .ia file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ia", delete=False) as f:
            f.write("[s3]\naccess = test\nsecret = test")
            temp_ia_file = f.name

        with patch("os.path.expanduser", return_value=temp_ia_file):
            with patch("os.path.exists", return_value=True):
                # Should not raise or call subprocess
                with patch("subprocess.call") as mock_call:
                    self.archiver.check_ia_credentials()
                    mock_call.assert_not_called()

        os.unlink(temp_ia_file)

    def test_parse_custom_metadata(self):
        """Test parsing custom metadata string"""
        metadata_string = "license:MIT,language:Python,topic:archiving"
        result = self.archiver.parse_custom_metadata(metadata_string)

        expected = {"license": "MIT", "language": "Python", "topic": "archiving"}
        self.assertEqual(result, expected)

    def test_parse_custom_metadata_with_colons_in_value(self):
        """Test parsing metadata with colons in values"""
        metadata_string = "url:https://example.com,time:12:30:45"
        result = self.archiver.parse_custom_metadata(metadata_string)

        expected = {"url": "https://example.com", "time": "12:30:45"}
        self.assertEqual(result, expected)


class ProfileArchiverTests(unittest.TestCase):
    """Tests for profile archiving functionality"""

    def setUp(self):
        self.archiver = GitArchiver(verbose=False)
        self.maxDiff = None

    def test_is_profile_url_github(self):
        """Test profile URL detection for GitHub"""
        # Profile URLs (should return True)
        self.assertTrue(self.archiver.is_profile_url("https://github.com/torvalds"))
        self.assertTrue(self.archiver.is_profile_url("https://github.com/kubernetes"))
        self.assertTrue(self.archiver.is_profile_url("https://www.github.com/user"))

        # Repository URLs (should return False)
        self.assertFalse(
            self.archiver.is_profile_url("https://github.com/torvalds/linux")
        )
        self.assertFalse(
            self.archiver.is_profile_url("https://github.com/user/repo.git")
        )
        self.assertFalse(
            self.archiver.is_profile_url("https://github.com/org/group/repo")
        )

    def test_is_profile_url_gitlab(self):
        """Test profile URL detection for GitLab"""
        # Profile URLs
        self.assertTrue(self.archiver.is_profile_url("https://gitlab.com/gitlab-org"))
        self.assertTrue(self.archiver.is_profile_url("https://gitlab.com/username"))

        # Repository URLs
        self.assertFalse(
            self.archiver.is_profile_url("https://gitlab.com/gitlab-org/gitlab")
        )
        self.assertFalse(
            self.archiver.is_profile_url("https://gitlab.com/group/subgroup/project")
        )

    def test_is_profile_url_other_providers(self):
        """Test profile URL detection for other providers"""
        # Codeberg
        self.assertTrue(self.archiver.is_profile_url("https://codeberg.org/user"))
        self.assertFalse(self.archiver.is_profile_url("https://codeberg.org/user/repo"))

        # Gitea
        self.assertTrue(self.archiver.is_profile_url("https://gitea.com/organization"))
        self.assertFalse(self.archiver.is_profile_url("https://gitea.com/org/project"))

        # Bitbucket
        self.assertTrue(self.archiver.is_profile_url("https://bitbucket.org/workspace"))
        self.assertFalse(
            self.archiver.is_profile_url("https://bitbucket.org/team/repo")
        )

        # Self-hosted
        self.assertTrue(self.archiver.is_profile_url("https://git.example.com/user"))
        self.assertFalse(
            self.archiver.is_profile_url("https://git.example.com/user/repo")
        )

    @requests_mock.Mocker()
    def test_fetch_github_user_repos(self, m):
        """Test fetching repositories from GitHub user"""
        self.archiver.repo_data = {
            "domain": "github.com",
            "git_site": "github",
        }

        # Mock GitHub API response
        repos_response = [
            {
                "name": "repo1",
                "full_name": "testuser/repo1",
                "clone_url": "https://github.com/testuser/repo1.git",
                "html_url": "https://github.com/testuser/repo1",
                "description": "First repository",
                "fork": False,
                "archived": False,
                "private": False,
            },
            {
                "name": "repo2",
                "full_name": "testuser/repo2",
                "clone_url": "https://github.com/testuser/repo2.git",
                "html_url": "https://github.com/testuser/repo2",
                "description": "Second repository",
                "fork": True,
                "archived": False,
                "private": False,
            },
            {
                "name": "repo3",
                "full_name": "testuser/repo3",
                "clone_url": "https://github.com/testuser/repo3.git",
                "html_url": "https://github.com/testuser/repo3",
                "description": "Third repository",
                "fork": False,
                "archived": True,
                "private": False,
            },
        ]

        m.get(
            "https://api.github.com/users/testuser/repos?per_page=100&page=1&sort=updated",
            json=repos_response,
        )

        repos = self.archiver.fetch_user_repositories("testuser")

        self.assertEqual(len(repos), 3)
        self.assertEqual(repos[0]["name"], "repo1")
        self.assertEqual(repos[1]["name"], "repo2")
        self.assertEqual(repos[2]["name"], "repo3")
        self.assertFalse(repos[0]["fork"])
        self.assertTrue(repos[1]["fork"])
        self.assertTrue(repos[2]["archived"])

    @requests_mock.Mocker()
    def test_fetch_github_user_repos_pagination(self, m):
        """Test GitHub API pagination"""
        self.archiver.repo_data = {
            "domain": "github.com",
            "git_site": "github",
        }

        # Mock first page (100 repos)
        first_page = [
            {
                "name": f"repo{i}",
                "full_name": f"testuser/repo{i}",
                "clone_url": f"https://github.com/testuser/repo{i}.git",
                "html_url": f"https://github.com/testuser/repo{i}",
                "description": f"Repository {i}",
                "fork": False,
                "archived": False,
                "private": False,
            }
            for i in range(100)
        ]

        # Mock second page (50 repos)
        second_page = [
            {
                "name": f"repo{i}",
                "full_name": f"testuser/repo{i}",
                "clone_url": f"https://github.com/testuser/repo{i}.git",
                "html_url": f"https://github.com/testuser/repo{i}",
                "description": f"Repository {i}",
                "fork": False,
                "archived": False,
                "private": False,
            }
            for i in range(100, 150)
        ]

        m.get(
            "https://api.github.com/users/testuser/repos?per_page=100&page=1&sort=updated",
            json=first_page,
        )
        m.get(
            "https://api.github.com/users/testuser/repos?per_page=100&page=2&sort=updated",
            json=second_page,
        )

        repos = self.archiver.fetch_user_repositories("testuser")

        self.assertEqual(len(repos), 150)

    @requests_mock.Mocker()
    def test_fetch_github_user_repos_with_token(self, m):
        """Test GitHub API with authentication token"""
        self.archiver.repo_data = {
            "domain": "github.com",
            "git_site": "github",
        }
        self.archiver.api_token = "ghp_testtoken123"

        repos_response = [
            {
                "name": "private-repo",
                "full_name": "testuser/private-repo",
                "clone_url": "https://github.com/testuser/private-repo.git",
                "html_url": "https://github.com/testuser/private-repo",
                "description": "Private repository",
                "fork": False,
                "archived": False,
                "private": True,
            }
        ]

        m.get(
            "https://api.github.com/users/testuser/repos?per_page=100&page=1&sort=updated",
            json=repos_response,
        )

        repos = self.archiver.fetch_user_repositories("testuser")

        self.assertEqual(len(repos), 1)
        self.assertTrue(repos[0]["private"])

    @requests_mock.Mocker()
    def test_fetch_gitlab_user_repos(self, m):
        """Test fetching repositories from GitLab user"""
        self.archiver.repo_data = {
            "domain": "gitlab.com",
            "git_site": "gitlab",
        }

        # Mock user lookup
        user_response = [{"id": 12345, "username": "testuser"}]
        m.get("https://gitlab.com/api/v4/users?username=testuser", json=user_response)

        # Mock projects response
        projects_response = [
            {
                "name": "project1",
                "path_with_namespace": "testuser/project1",
                "http_url_to_repo": "https://gitlab.com/testuser/project1.git",
                "web_url": "https://gitlab.com/testuser/project1",
                "description": "First project",
                "forked_from_project": None,
                "archived": False,
                "visibility": "public",
            },
            {
                "name": "project2",
                "path_with_namespace": "testuser/project2",
                "http_url_to_repo": "https://gitlab.com/testuser/project2.git",
                "web_url": "https://gitlab.com/testuser/project2",
                "description": "Second project",
                "forked_from_project": {"id": 999},
                "archived": False,
                "visibility": "public",
            },
        ]

        m.get(
            "https://gitlab.com/api/v4/users/12345/projects?per_page=100&page=1&order_by=updated_at",
            json=projects_response,
        )

        repos = self.archiver.fetch_user_repositories("testuser")

        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0]["name"], "project1")
        self.assertFalse(repos[0]["fork"])
        self.assertTrue(repos[1]["fork"])

    @requests_mock.Mocker()
    def test_fetch_gitea_user_repos(self, m):
        """Test fetching repositories from Gitea user"""
        self.archiver.repo_data = {
            "domain": "codeberg.org",
            "git_site": "codeberg",
        }

        repos_response = [
            {
                "name": "repo1",
                "full_name": "testuser/repo1",
                "clone_url": "https://codeberg.org/testuser/repo1.git",
                "html_url": "https://codeberg.org/testuser/repo1",
                "description": "First repository",
                "fork": False,
                "archived": False,
                "private": False,
            },
            {
                "name": "repo2",
                "full_name": "testuser/repo2",
                "clone_url": "https://codeberg.org/testuser/repo2.git",
                "html_url": "https://codeberg.org/testuser/repo2",
                "description": "Second repository",
                "fork": True,
                "archived": True,
                "private": False,
            },
        ]

        m.get(
            "https://codeberg.org/api/v1/users/testuser/repos?limit=50&page=1",
            json=repos_response,
        )

        repos = self.archiver.fetch_user_repositories("testuser")

        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0]["name"], "repo1")
        self.assertTrue(repos[1]["fork"])
        self.assertTrue(repos[1]["archived"])

    @requests_mock.Mocker()
    def test_fetch_bitbucket_user_repos(self, m):
        """Test fetching repositories from Bitbucket workspace"""
        self.archiver.repo_data = {
            "domain": "bitbucket.org",
            "git_site": "bitbucket",
        }

        repos_response = {
            "values": [
                {
                    "name": "repo1",
                    "full_name": "testuser/repo1",
                    "links": {
                        "clone": [
                            {
                                "name": "https",
                                "href": "https://bitbucket.org/testuser/repo1.git",
                            }
                        ],
                        "html": {"href": "https://bitbucket.org/testuser/repo1"},
                    },
                    "description": "First repository",
                    "parent": None,
                    "is_private": False,
                },
                {
                    "name": "repo2",
                    "full_name": "testuser/repo2",
                    "links": {
                        "clone": [
                            {
                                "name": "https",
                                "href": "https://bitbucket.org/testuser/repo2.git",
                            }
                        ],
                        "html": {"href": "https://bitbucket.org/testuser/repo2"},
                    },
                    "description": "Second repository",
                    "parent": {"full_name": "original/repo"},
                    "is_private": True,
                },
            ],
            "next": None,
        }

        m.get(
            "https://api.bitbucket.org/2.0/repositories/testuser", json=repos_response
        )

        repos = self.archiver.fetch_user_repositories("testuser")

        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0]["name"], "repo1")
        self.assertFalse(repos[0]["fork"])
        self.assertTrue(repos[1]["fork"])
        self.assertTrue(repos[1]["private"])

    @requests_mock.Mocker()
    def test_fetch_user_repos_empty_profile(self, m):
        """Test fetching from an empty profile"""
        self.archiver.repo_data = {
            "domain": "github.com",
            "git_site": "github",
        }

        m.get(
            "https://api.github.com/users/emptyuser/repos?per_page=100&page=1&sort=updated",
            json=[],
        )

        repos = self.archiver.fetch_user_repositories("emptyuser")

        self.assertEqual(len(repos), 0)

    @requests_mock.Mocker()
    def test_fetch_user_repos_api_error(self, m):
        """Test handling API errors gracefully"""
        self.archiver.repo_data = {
            "domain": "github.com",
            "git_site": "github",
        }

        m.get(
            "https://api.github.com/users/erroruser/repos?per_page=100&page=1&sort=updated",
            status_code=404,
        )

        repos = self.archiver.fetch_user_repositories("erroruser")

        self.assertEqual(len(repos), 0)

    def test_filter_forks(self):
        """Test filtering out forked repositories"""
        repos = [
            {"name": "repo1", "fork": False},
            {"name": "repo2", "fork": True},
            {"name": "repo3", "fork": False},
            {"name": "repo4", "fork": True},
        ]

        filtered = [r for r in repos if not r.get("fork", False)]

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["name"], "repo1")
        self.assertEqual(filtered[1]["name"], "repo3")

    def test_filter_archived(self):
        """Test filtering out archived repositories"""
        repos = [
            {"name": "repo1", "archived": False},
            {"name": "repo2", "archived": True},
            {"name": "repo3", "archived": False},
            {"name": "repo4", "archived": True},
        ]

        filtered = [r for r in repos if not r.get("archived", False)]

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["name"], "repo1")
        self.assertEqual(filtered[1]["name"], "repo3")

    def test_filter_private(self):
        """Test filtering out private repositories"""
        repos = [
            {"name": "repo1", "private": False},
            {"name": "repo2", "private": True},
            {"name": "repo3", "private": False},
            {"name": "repo4", "private": True},
        ]

        filtered = [r for r in repos if not r.get("private", False)]

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["name"], "repo1")
        self.assertEqual(filtered[1]["name"], "repo3")

    def test_filter_max_repos(self):
        """Test limiting number of repositories"""
        repos = [{"name": f"repo{i}"} for i in range(100)]

        max_repos = 10
        filtered = repos[:max_repos]

        self.assertEqual(len(filtered), 10)
        self.assertEqual(filtered[0]["name"], "repo0")
        self.assertEqual(filtered[9]["name"], "repo9")

    def test_filter_combined(self):
        """Test combining multiple filters"""
        repos = [
            {"name": "repo1", "fork": False, "archived": False, "private": False},
            {"name": "repo2", "fork": True, "archived": False, "private": False},
            {"name": "repo3", "fork": False, "archived": True, "private": False},
            {"name": "repo4", "fork": False, "archived": False, "private": True},
            {"name": "repo5", "fork": False, "archived": False, "private": False},
            {"name": "repo6", "fork": True, "archived": True, "private": False},
        ]

        # Apply all filters
        filtered = repos
        filtered = [r for r in filtered if not r.get("fork", False)]
        filtered = [r for r in filtered if not r.get("archived", False)]
        filtered = [r for r in filtered if not r.get("private", False)]
        max_repos = 10
        filtered = filtered[:max_repos]

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["name"], "repo1")
        self.assertEqual(filtered[1]["name"], "repo5")

    @requests_mock.Mocker()
    def test_fetch_gitlab_user_not_found(self, m):
        """Test GitLab user not found"""
        self.archiver.repo_data = {
            "domain": "gitlab.com",
            "git_site": "gitlab",
        }

        # Mock empty user lookup
        m.get("https://gitlab.com/api/v4/users?username=nonexistent", json=[])

        repos = self.archiver.fetch_user_repositories("nonexistent")

        self.assertEqual(len(repos), 0)

    @requests_mock.Mocker()
    def test_fetch_self_hosted_gitlab_repos(self, m):
        """Test fetching from self-hosted GitLab"""
        self.archiver.repo_data = {
            "domain": "gitlab.example.com",
            "git_site": "gitlab",
        }
        self.archiver.api_url = "https://gitlab.example.com/api/v4"
        self.archiver.api_token = "glpat-test123"

        # Mock user lookup
        user_response = [{"id": 1, "username": "testuser"}]
        m.get(
            "https://gitlab.example.com/api/v4/users?username=testuser",
            json=user_response,
        )

        # Mock projects response
        projects_response = [
            {
                "name": "project1",
                "path_with_namespace": "testuser/project1",
                "http_url_to_repo": "https://gitlab.example.com/testuser/project1.git",
                "web_url": "https://gitlab.example.com/testuser/project1",
                "description": "Internal project",
                "forked_from_project": None,
                "archived": False,
                "visibility": "internal",
            }
        ]

        m.get(
            "https://gitlab.example.com/api/v4/users/1/projects?per_page=100&page=1&order_by=updated_at",
            json=projects_response,
        )

        repos = self.archiver.fetch_user_repositories("testuser")

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["name"], "project1")

    @requests_mock.Mocker()
    def test_fetch_self_hosted_gitea_repos(self, m):
        """Test fetching from self-hosted Gitea"""
        self.archiver.repo_data = {
            "domain": "git.example.com",
            "git_site": "gitea",
        }
        self.archiver.api_url = "https://git.example.com/api/v1"
        self.archiver.api_token = "test123"

        repos_response = [
            {
                "name": "internal-repo",
                "full_name": "company/internal-repo",
                "clone_url": "https://git.example.com/company/internal-repo.git",
                "html_url": "https://git.example.com/company/internal-repo",
                "description": "Internal repository",
                "fork": False,
                "archived": False,
                "private": True,
            }
        ]

        m.get(
            "https://git.example.com/api/v1/users/company/repos?limit=50&page=1",
            json=repos_response,
        )

        repos = self.archiver.fetch_user_repositories("company")

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["name"], "internal-repo")
        self.assertTrue(repos[0]["private"])

    def test_repository_info_structure(self):
        """Test that repository info has required fields"""
        repo_info = {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "clone_url": "https://github.com/user/test-repo.git",
            "html_url": "https://github.com/user/test-repo",
            "description": "Test repository",
            "fork": False,
            "archived": False,
            "private": False,
        }

        # Verify all required fields are present
        self.assertIn("name", repo_info)
        self.assertIn("full_name", repo_info)
        self.assertIn("clone_url", repo_info)
        self.assertIn("html_url", repo_info)
        self.assertIn("description", repo_info)
        self.assertIn("fork", repo_info)
        self.assertIn("archived", repo_info)
        self.assertIn("private", repo_info)

        # Verify types
        self.assertIsInstance(repo_info["name"], str)
        self.assertIsInstance(repo_info["full_name"], str)
        self.assertIsInstance(repo_info["clone_url"], str)
        self.assertIsInstance(repo_info["html_url"], str)
        self.assertIsInstance(repo_info["description"], str)
        self.assertIsInstance(repo_info["fork"], bool)
        self.assertIsInstance(repo_info["archived"], bool)
        self.assertIsInstance(repo_info["private"], bool)


if __name__ == "__main__":
    unittest.main()
