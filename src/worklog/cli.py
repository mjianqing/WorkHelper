from datetime import date

import click

from .config import Config
from .git_parser import parse_commits
from .llm_formatter import format_commits
from .output import to_clipboard, to_stdout, to_webhook


@click.group()
def main():
    """WorkLog - 从 git commits 自动生成工作日志"""
    pass


@main.command()
@click.option("--config", "-c", default=None, help="配置文件路径")
def today(config):
    """生成今日工作日志"""
    _generate(config, date.today(), week=False)


@main.command()
@click.option("--config", "-c", default=None, help="配置文件路径")
def week(config):
    """生成本周工作日志"""
    _generate(config, date.today(), week=True)


@main.command()
@click.argument("date_str")
@click.option("--config", "-c", default=None, help="配置文件路径")
def day(date_str, config):
    """生成指定日期的工作日志"""
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        raise click.BadParameter(
            f"无效的日期格式: {date_str}，请使用 YYYY-MM-DD"
        )
    _generate(config, target, week=False)


@main.command()
@click.option("--webhook", is_flag=True, help="推送到 webhook")
@click.option("--config", "-c", default=None, help="配置文件路径")
def push(webhook, config):
    """生成并推送今日工作日志"""
    cfg = Config.load(config)
    commits = parse_commits(cfg.repo_paths, date.today())
    content = format_commits(commits, cfg)

    if webhook:
        to_webhook(content, cfg.webhook_url)
    else:
        to_clipboard(content)


@main.command()
@click.option("--config", "-c", default=None, help="配置文件路径")
@click.option("--requirement", "-r", default=None, help="新建任务关联的需求ID")
@click.option("--yes", "-y", is_flag=True, help="跳过确认直接提交")
def feishu(config, requirement, yes):
    """自动生成并提交飞书周报"""
    import json
    import sys
    from .feishu import (
        get_my_tasks, match_commits_to_tasks, create_task,
        submit_weekly_report, get_week_friday,
    )

    cfg = Config.load(config)
    if not cfg.repo_paths:
        cfg.repo_paths = ["."]

    if not cfg.feishu_base_token:
        click.echo("错误：请在 ~/.worklog.toml 中配置 [feishu] 段。")
        return

    friday = get_week_friday()
    click.echo(f"周报周期: 本周五 {friday}")
    click.echo("正在获取本周 git commits...")

    commits = parse_commits(cfg.repo_paths, date.today(), week=True)
    if not commits:
        click.echo("本周无 git 提交记录。")
        return

    total = sum(len(v) for v in commits.values())
    click.echo(f"找到 {total} 条 commits")

    click.echo("正在获取飞书任务列表...")
    tasks = get_my_tasks(cfg)
    click.echo(f"找到 {len(tasks)} 个进行中的任务")

    click.echo("正在匹配 commits 到任务...")
    matches = match_commits_to_tasks(commits, tasks, cfg)

    if not matches:
        click.echo("匹配失败，请检查 LLM 配置。")
        return

    click.echo(f"\n{'='*50}")
    click.echo("周报预览：")
    click.echo(f"{'='*50}\n")

    new_tasks = []
    entries = []

    for i, m in enumerate(matches):
        task_id = m.get("task_id")
        content = m.get("content", "")
        status = m.get("status", "研发中（正常）")
        hours = m.get("hours", 0)
        is_hotfix = m.get("is_hotfix", False)

        if task_id:
            task_desc = next(
                (t.description for t in tasks if t.record_id == task_id),
                "未知任务"
            )
            click.echo(f"[{i+1}] 任务: {task_desc}")
        else:
            task_desc = m.get("task_desc", "新任务")
            if is_hotfix:
                click.echo(f"[{i+1}] 新建工单任务(XQ767): {task_desc}")
            else:
                click.echo(f"[{i+1}] 新建任务: {task_desc}")
            new_tasks.append(i)

        click.echo(f"    状态: {status}")
        if hours:
            click.echo(f"    工时: {hours}h")
        click.echo(f"    内容: {content}")
        click.echo()

        entries.append({
            "task_id": task_id,
            "task_desc": m.get("task_desc", ""),
            "content": content,
            "status": status,
            "hours": hours,
            "is_hotfix": is_hotfix,
        })

    if not yes:
        click.echo(f"{'='*50}")
        if not click.confirm("确认提交以上周报？"):
            click.echo("已取消。")
            return

    req_id = requirement or cfg.feishu_default_requirement_id
    for idx in new_tasks:
        entry = entries[idx]
        is_hotfix = entry.get("is_hotfix", False)
        task_req = cfg.feishu_default_requirement_id if is_hotfix else req_id
        hours = entry.get("hours") or None
        click.echo(f"正在创建任务: {entry['task_desc']}...")
        if is_hotfix:
            click.echo(f"  关联工单需求，工时: {hours}h")
        new_id = create_task(cfg, entry["task_desc"], task_req, hours)
        if new_id:
            entry["task_id"] = new_id
            click.echo(f"  创建成功: {new_id}")
        else:
            click.echo(f"  创建失败，跳过该条目")
            entries[idx] = None

    entries = [e for e in entries if e and e.get("task_id")]

    if not entries:
        click.echo("没有可提交的记录。")
        return

    click.echo("正在提交周报...")
    if submit_weekly_report(cfg, entries):
        click.echo(f"周报提交成功！共 {len(entries)} 条记录。")
    else:
        click.echo("周报提交失败，请检查飞书权限。")


def _generate(config_path, target_date: date, week: bool):
    cfg = Config.load(config_path)

    if not cfg.repo_paths:
        cfg.repo_paths = ["."]

    commits = parse_commits(cfg.repo_paths, target_date, week=week)
    content = format_commits(commits, cfg)
    to_stdout(content)
