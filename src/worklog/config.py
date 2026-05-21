import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


DEFAULT_CONFIG_PATH = Path.home() / ".worklog.toml"


@dataclass
class Config:
    llm_endpoint: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_provider: str = "openai"  # "openai" or "anthropic"
    template_path: str = ""
    repo_paths: list[str] = field(default_factory=list)
    push_default: str = "clipboard"
    webhook_url: str = ""
    tone: str = "professional"
    language: str = "zh-CN"

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Config":
        if isinstance(path, str):
            config_path = Path(path)
        else:
            config_path = path or DEFAULT_CONFIG_PATH
        if not config_path.exists():
            return cls()

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise SystemExit(
                f"配置文件格式错误: {config_path}\n{e}"
            )

        general = data.get("general", {})
        repos = data.get("repos", {})
        push = data.get("push", {})
        style = data.get("style", {})

        return cls(
            llm_endpoint=general.get("llm_endpoint", cls.llm_endpoint),
            llm_model=general.get("llm_model", cls.llm_model),
            llm_provider=general.get("llm_provider", cls.llm_provider),
            template_path=general.get("template_path", ""),
            repo_paths=repos.get("paths", []),
            push_default=push.get("default", "clipboard"),
            webhook_url=push.get("webhook_url", ""),
            tone=style.get("tone", "professional"),
            language=style.get("language", "zh-CN"),
        )

    @property
    def api_key(self) -> str | None:
        return os.environ.get("WORKLOG_API_KEY") or os.environ.get(
            "OPENAI_API_KEY"
        )
