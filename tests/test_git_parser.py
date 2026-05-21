from datetime import date, datetime

import pytest

from worklog.git_parser import Commit, parse_commits


class TestParseCommits:
    def test_no_repos(self):
        result = parse_commits([], date(2026, 5, 20))
        assert result == {}

    def test_nonexistent_repo(self):
        result = parse_commits(["/nonexistent/path"], date(2026, 5, 20))
        assert result == {}

    def test_real_repo_no_commits(self, tmp_path, monkeypatch):
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path, capture_output=True,
        )
        result = parse_commits([str(tmp_path)], date(2026, 5, 20))
        assert result == {}
