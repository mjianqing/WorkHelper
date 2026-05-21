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


def _generate(config_path, target_date: date, week: bool):
    cfg = Config.load(config_path)

    if not cfg.repo_paths:
        cfg.repo_paths = ["."]

    commits = parse_commits(cfg.repo_paths, target_date, week=week)
    content = format_commits(commits, cfg)
    to_stdout(content)
