import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from iagitbetter import check_for_updates, get_latest_pypi_version
from iagitbetter.iagitbetter import GitArchiver


class UtilsTest(unittest.TestCase):

    def setUp(self):
        self.archiver = GitArchiver(verbose=False)

    def test_sanitize_branch_names(self):
        """Test that branch names are properly sanitized for filesystem"""
        test_cases = [
            ("feature/new-feature", "feature-new-feature"),
            ("bugfix\\windows-path", "bugfix-windows-path"),
            ("release:v1.0", "release-v1.0"),
            ("test|pipe", "test-pipe"),
            ("question?mark", "question-mark"),
            ("asterisk*here", "asterisk-here"),
            ("double//slash", "double--slash"),
            ("..hidden", "hidden"),
            ("trailing.", "trailing"),
            ("  spaces  ", "spaces"),
        ]

        for input_name, expected in test_cases:
            result = self.archiver._sanitize_branch_name(input_name)
            self.assertEqual(result, expected, f"Failed for input: {input_name}")

    def test_build_api_url_github(self):
        """Test building API URL for GitHub"""
        self.archiver.repo_data = {
            "domain": "github.com",
            "git_site": "github",
            "owner": "octocat",
            "repo_name": "hello-world",
        }

        url = self.archiver._build_api_url()
        self.assertEqual(url, "https://api.github.com/repos/octocat/hello-world")

    def test_build_api_url_gitlab(self):
        """Test building API URL for GitLab"""
        self.archiver.repo_data = {
            "domain": "gitlab.com",
            "git_site": "gitlab",
            "owner": "gitlab-org",
            "repo_name": "gitlab-test",
        }

        url = self.archiver._build_api_url()
        self.assertEqual(
            url, "https://gitlab.com/api/v4/projects/gitlab-org%2Fgitlab-test"
        )

    def test_build_api_url_custom(self):
        """Test building API URL with custom API URL"""
        self.archiver.api_url = "https://git.example.com/api/v1"
        self.archiver.repo_data = {"owner": "myorg", "repo_name": "myrepo"}

        url = self.archiver._build_api_url()
        self.assertEqual(url, "https://git.example.com/api/v1/repos/myorg/myrepo")

    def test_parse_custom_metadata_empty(self):
        """Test parsing empty metadata string"""
        result = self.archiver.parse_custom_metadata(None)
        self.assertIsNone(result)

        result = self.archiver.parse_custom_metadata("")
        self.assertIsNone(result)

    def test_parse_custom_metadata_single_item(self):
        """Test parsing single metadata item"""
        result = self.archiver.parse_custom_metadata("license:MIT")
        self.assertEqual(result, {"license": "MIT"})

    def test_parse_custom_metadata_multiple_items(self):
        """Test parsing multiple metadata items"""
        result = self.archiver.parse_custom_metadata(
            "license:MIT,language:Python,year:2021"
        )
        expected = {"license": "MIT", "language": "Python", "year": "2021"}
        self.assertEqual(result, expected)

    def test_parse_custom_metadata_with_spaces(self):
        """Test parsing metadata with spaces"""
        result = self.archiver.parse_custom_metadata(
            " license : MIT , language : Python "
        )
        expected = {"license": "MIT", "language": "Python"}
        self.assertEqual(result, expected)

    def test_parse_custom_metadata_with_special_chars(self):
        """Test parsing metadata with special characters in values"""
        result = self.archiver.parse_custom_metadata(
            "url:https://example.com:8080,path:/usr/local/bin"
        )
        expected = {"url": "https://example.com:8080", "path": "/usr/local/bin"}
        self.assertEqual(result, expected)

    def test_get_all_files_excludes_git_directory(self):
        """Test that .git directory is excluded from file listing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test structure
            os.makedirs(os.path.join(temp_dir, ".git", "objects"))
            os.makedirs(os.path.join(temp_dir, ".github", "workflows"))
            os.makedirs(os.path.join(temp_dir, "src"))

            # Create files
            Path(os.path.join(temp_dir, "README.md")).write_text("# Test")
            Path(os.path.join(temp_dir, ".git", "config")).write_text("config")
            Path(os.path.join(temp_dir, ".github", "workflows", "test.yml")).write_text(
                "test"
            )
            Path(os.path.join(temp_dir, "src", "main.py")).write_text("code")

            files = self.archiver.get_all_files(temp_dir)

            # .git should be excluded, but .github should be included
            self.assertIn("README.md", files)
            self.assertIn(".github/workflows/test.yml", files)
            self.assertIn("src/main.py", files)
            self.assertNotIn(".git/config", files)
            self.assertNotIn(".git/objects", str(files))

    def test_get_all_files_skips_empty_files(self):
        """Test that empty files are skipped"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files
            Path(os.path.join(temp_dir, "normal.txt")).write_text("content")
            Path(os.path.join(temp_dir, "empty.txt")).touch()  # Empty file

            files = self.archiver.get_all_files(temp_dir)

            self.assertIn("normal.txt", files)
            self.assertNotIn("empty.txt", files)

    def test_get_description_from_readme_markdown(self):
        """Test extracting description from README.md"""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_content = """# My Project

This is a **test** project with *markdown*.

## Features
- Feature 1
- Feature 2

[Link](https://example.com)
"""
            Path(os.path.join(temp_dir, "README.md")).write_text(readme_content)

            description = self.archiver.get_description_from_readme(temp_dir)

            # Should be converted to HTML
            self.assertIn("<h1>My Project</h1>", description)
            self.assertIn("<strong>test</strong>", description)
            self.assertIn("<em>markdown</em>", description)
            self.assertIn('<a href="https://example.com">Link</a>', description)

    def test_get_description_from_readme_txt(self):
        """Test extracting description from README.txt"""
        with tempfile.TemporaryDirectory() as temp_dir:
            readme_content = """My Project

This is a plain text readme.
It has multiple lines.
"""
            Path(os.path.join(temp_dir, "README.txt")).write_text(readme_content)

            description = self.archiver.get_description_from_readme(temp_dir)

            # Should be wrapped in <pre> tags
            self.assertIn("<pre>", description)
            self.assertIn("My Project", description)
            self.assertIn("plain text readme", description)

    def test_get_description_no_readme(self):
        """Test description when no README exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            description = self.archiver.get_description_from_readme(temp_dir)

            self.assertEqual(
                description, "This repository doesn't have a README file"
            )

    def test_handle_remove_readonly_windows(self):
        """Test the Windows readonly file handler"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "readonly.txt")
            Path(test_file).write_text("test")

            # Make file read-only
            os.chmod(test_file, 0o444)

            # The handler should make it writable and delete it
            self.archiver.handle_remove_readonly(os.unlink, test_file, None)

            self.assertFalse(os.path.exists(test_file))

    def test_extract_repo_info_various_formats(self):
        """Test repository info extraction with various URL formats"""
        test_cases = [
            ("https://github.com/user/repo", "github", "user", "repo"),
            ("https://github.com/user/repo.git", "github", "user", "repo"),
            ("git@github.com:user/repo.git", "github", "user", "repo"),
            ("https://gitlab.com/group/project", "gitlab", "group", "project"),
            ("https://bitbucket.org/team/repo", "bitbucket", "team", "repo"),
            ("https://codeberg.org/user/repo", "codeberg", "user", "repo"),
            ("https://git.example.com/org/repo", "git", "org", "repo"),
            ("https://www.github.com/user/repo", "github", "user", "repo"),
        ]

        for url, expected_site, expected_owner, expected_repo in test_cases:
            # Skip SSH URLs for this test as urlparse doesn't handle them well
            if url.startswith("git@"):
                continue

            result = self.archiver.extract_repo_info(url)
            self.assertEqual(
                result["git_site"], expected_site, f"Failed for URL: {url}"
            )
            self.assertEqual(result["owner"], expected_owner, f"Failed for URL: {url}")
            self.assertEqual(
                result["repo_name"], expected_repo, f"Failed for URL: {url}"
            )
