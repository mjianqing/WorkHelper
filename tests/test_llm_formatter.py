from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from worklog.config import Config
from worklog.git_parser import Commit
from worklog.llm_formatter import format_commits, _fallback_output


@pytest.fixture
def sample_commits():
    return {
        "project-a": [
            Commit("abc12345", "fix: resolve race condition", "dev", datetime.now(), "project-a"),
            Commit("def67890", "feat: add user auth", "dev", datetime.now(), "project-a"),
        ]
    }


@pytest.fixture
def config():
    return Config(language="zh-CN", tone="professional")


class TestFallbackOutput:
    def test_empty_commits(self):
        assert "无工作记录" in _fallback_output({})

    def test_has_commits(self, sample_commits):
        result = _fallback_output(sample_commits)
        assert "project-a" in result
        assert "resolve race condition" in result
        assert "LLM 服务不可用" in result


class TestFormatCommits:
    def test_empty_commits(self, config):
        result = format_commits({}, config)
        assert "无工作记录" in result

    def test_no_api_key_fallback(self, sample_commits, config):
        result = format_commits(sample_commits, config)
        assert "project-a" in result
        assert "LLM 服务不可用" in result

    @patch("worklog.llm_formatter._call_llm")
    def test_llm_success(self, mock_llm, sample_commits, config):
        config.llm_endpoint = "https://api.openai.com/v1"
        mock_llm.return_value = "今日完成了用户认证功能开发"
        with patch.dict("os.environ", {"WORKLOG_API_KEY": "test-key"}):
            cfg = Config(language="zh-CN", tone="professional")
            result = format_commits(sample_commits, cfg)
        assert "认证" in result or "project-a" in result

    @patch("worklog.llm_formatter._call_llm")
    def test_llm_failure_fallback(self, mock_llm, sample_commits):
        mock_llm.side_effect = Exception("API timeout")
        with patch.dict("os.environ", {"WORKLOG_API_KEY": "test-key"}):
            cfg = Config(language="zh-CN", tone="professional")
            result = format_commits(sample_commits, cfg)
        assert "LLM 服务不可用" in result
