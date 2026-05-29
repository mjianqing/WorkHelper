from pathlib import Path

from .config import Config
from .git_parser import Commit


DEFAULT_PROMPT = """你是一个工作日志助手。请将以下 git commit 记录转换为简洁的工作日志。

要求：
- 使用{language}
- 语气自然随意，像真人快速写的日报，不要AI腔
- 不要用加粗、不要用标题层级、不要用"一、二、三"编号
- 直接用短句列表，每条一行，用「-」开头
- 把技术术语翻译成普通人能懂的话，但不要过度美化
- 相似的 commit 合并成一条，不要逐条翻译
- 不要写"价值说明"、"工作总结"之类的套话
- 总条数控制在 5-10 条以内
- 不要在开头写日期，不要写"今日工作"之类的标题

示例风格：
- 修了支付流程里几个状态判断的bug，之前会导致重复验签
- 算力明细页面做完了，对接了真实接口，加了筛选和分页
- 优化了loading样式，统一成项目里其他页面的风格

{template}

Git 提交记录：
{commits}

工作日志："""


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
        by_branch: dict[str, list[Commit]] = {}
        for c in commits:
            branch = c.branch or "unknown"
            by_branch.setdefault(branch, []).append(c)
        for branch, branch_commits in by_branch.items():
            lines.append(f"  [分支: {branch}]")
            for c in branch_commits:
                lines.append(f"  - {c.message} ({c.hash})")
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
        max_tokens=8192,
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
