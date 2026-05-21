from pathlib import Path

from .config import Config
from .git_parser import Commit


DEFAULT_PROMPT = """你是一个工作日志助手。请将以下 git commit 记录转换为公司工作日志格式。

要求：
- 使用{language}撰写
- 语气{tone}
- 按项目分组
- 将技术性描述转换为业务导向的表述
- 每条日志简洁明了，突出工作价值

{template}

今日 Git 提交记录：
{commits}

请生成工作日志："""


def format_commits(
    grouped_commits: dict[str, list[Commit]], config: Config
) -> str:
    if not grouped_commits:
        return "今日无工作记录。"

    template_content = _load_template(config.template_path)
    prompt = _build_prompt(grouped_commits, config, template_content)

    if not config.api_key:
        return _fallback_output(grouped_commits)

    try:
        return _call_llm(prompt, config)
    except Exception:
        return _fallback_output(grouped_commits)


def _load_template(template_path: str) -> str:
    if not template_path:
        return ""
    path = Path(template_path).expanduser()
    if not path.exists():
        return ""
    return f"参考模板格式：\n{path.read_text(encoding='utf-8')}"


def _build_prompt(
    grouped_commits: dict[str, list[Commit]],
    config: Config,
    template_content: str,
) -> str:
    commits_text = _commits_to_text(grouped_commits)
    prompt_path = Path(config.template_path).expanduser() if config.template_path else None

    if prompt_path and prompt_path.with_suffix(".prompt.md").exists():
        custom_prompt = prompt_path.with_suffix(".prompt.md").read_text(encoding="utf-8")
        return custom_prompt.replace(
            "{{commits}}", commits_text
        ).replace(
            "{{date}}", str(grouped_commits)
        ).replace(
            "{{language}}", config.language
        ).replace(
            "{{tone}}", config.tone
        )

    return DEFAULT_PROMPT.format(
        language=config.language,
        tone=config.tone,
        template=template_content,
        commits=commits_text,
    )


def _commits_to_text(grouped_commits: dict[str, list[Commit]]) -> str:
    lines = []
    for repo_name, commits in grouped_commits.items():
        lines.append(f"## {repo_name}")
        for c in commits:
            lines.append(f"- {c.message} ({c.hash})")
        lines.append("")
    return "\n".join(lines)


def _call_llm(prompt: str, config: Config) -> str:
    if config.llm_provider == "anthropic":
        return _call_anthropic(prompt, config)
    return _call_openai(prompt, config)


def _call_openai(prompt: str, config: Config) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=config.api_key,
        base_url=config.llm_endpoint,
    )
    response = client.chat.completions.create(
        model=config.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        timeout=30,
    )
    return response.choices[0].message.content or _fallback_output({})


def _call_anthropic(prompt: str, config: Config) -> str:
    import anthropic

    client = anthropic.Anthropic(
        api_key=config.api_key,
        base_url=config.llm_endpoint,
    )
    response = client.messages.create(
        model=config.llm_model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return _fallback_output({})


def _fallback_output(grouped_commits: dict[str, list[Commit]]) -> str:
    if not grouped_commits:
        return "今日无工作记录。"

    lines = ["# 工作日志（原始记录）\n"]
    for repo_name, commits in grouped_commits.items():
        lines.append(f"## {repo_name}")
        for c in commits:
            lines.append(f"- {c.message}")
        lines.append("")
    lines.append("---")
    lines.append("*注：LLM 服务不可用，以上为原始 commit 记录*")
    return "\n".join(lines)
