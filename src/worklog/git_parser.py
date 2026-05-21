import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


@dataclass
class Commit:
    hash: str
    message: str
    author: str
    date: datetime
    repo_name: str


def parse_commits(
    repo_paths: list[str], target_date: date | None = None, week: bool = False
) -> dict[str, list[Commit]]:
    if target_date is None:
        target_date = date.today()

    if week:
        start = target_date - timedelta(days=target_date.weekday())
        end = start + timedelta(days=6)
    else:
        start = target_date
        end = target_date

    since = start.strftime("%Y-%m-%dT00:00:00")
    until = (end + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")

    grouped: dict[str, list[Commit]] = {}

    for repo_path in repo_paths:
        path = Path(repo_path).expanduser()
        if not path.exists():
            continue

        repo_name = path.name
        commits = _get_commits(path, since, until)
        if commits:
            grouped[repo_name] = commits

    return grouped


def _get_commits(repo_path: Path, since: str, until: str) -> list[Commit]:
    try:
        result = subprocess.run(
            [
                "git", "log", "--all",
                f"--since={since}",
                f"--until={until}",
                "--format=%H|%s|%an|%aI",
                "--no-merges",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0:
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        commits.append(Commit(
            hash=parts[0][:8],
            message=parts[1],
            author=parts[2],
            date=datetime.fromisoformat(parts[3]),
            repo_name=repo_path.name,
        ))

    return commits
