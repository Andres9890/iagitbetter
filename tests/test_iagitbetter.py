import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import requests_mock

from iagitbetter import __version__
from iagitbetter.iagitbetter import GitArchiver

from .constants import bitbucket_api_response, gitea_api_response, github_api_response, gitlab_api_response

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
    test_repo_dir = os.path.join(current_path, "test_iagitbetter_files", "test_repository")
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

        m.get("https://api.github.com/repos/testuser/testrepo", json=github_api_response)

        self.archiver._fetch_api_metadata()

        self.assertEqual(self.archiver.repo_data["description"], "Test repository for iagitbetter")
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
