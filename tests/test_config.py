import tempfile
from pathlib import Path

import pytest

from worklog.config import Config, DEFAULT_CONFIG_PATH


class TestConfigLoad:
    def test_missing_file_returns_defaults(self):
        cfg = Config.load(Path("/nonexistent/config.toml"))
        assert cfg.llm_model == "gpt-4o-mini"
        assert cfg.language == "zh-CN"

    def test_valid_config(self, tmp_path):
        config_file = tmp_path / "test.toml"
        config_file.write_text("""
[general]
llm_model = "deepseek-chat"
template_path = "~/my-template.md"

[repos]
paths = ["~/code/project-a"]

[style]
tone = "casual"
language = "en"
""")
        cfg = Config.load(config_file)
        assert cfg.llm_model == "deepseek-chat"
        assert cfg.repo_paths == ["~/code/project-a"]
        assert cfg.tone == "casual"

    def test_invalid_toml_raises(self, tmp_path):
        config_file = tmp_path / "bad.toml"
        config_file.write_text("this is not valid toml [[[")
        with pytest.raises(SystemExit):
            Config.load(config_file)

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("WORKLOG_API_KEY", "sk-test-123")
        cfg = Config()
        assert cfg.api_key == "sk-test-123"

    def test_api_key_fallback_openai(self, monkeypatch):
        monkeypatch.delenv("WORKLOG_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-456")
        cfg = Config()
        assert cfg.api_key == "sk-openai-456"

    def test_no_api_key(self, monkeypatch):
        monkeypatch.delenv("WORKLOG_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        cfg = Config()
        assert cfg.api_key is None
