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
    branch: str = ""


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


def _get_branches(repo_path: Path) -> dict[str, str]:
    """Get a mapping of commit hash -> branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "-a", "--format=%(refname:short) %(objectname:short)"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}

    branch_map: dict[str, str] = {}
    for line in result.stdout.strip().splitlines():
        parts = line.rsplit(" ", 1)
        if len(parts) == 2:
            branch_map[parts[1]] = parts[0]
    return branch_map


def _get_commits(repo_path: Path, since: str, until: str) -> list[Commit]:
    branches = _get_branch_commits(repo_path, since, until)

    seen: dict[str, Commit] = {}
    for branch, commits in branches.items():
        for c in commits:
            if c.hash not in seen:
                c.branch = branch
                seen[c.hash] = c
            elif not seen[c.hash].branch or seen[c.hash].branch in ("master", "main"):
                seen[c.hash].branch = branch

    return sorted(seen.values(), key=lambda c: c.date, reverse=True)


def _get_branch_commits(repo_path: Path, since: str, until: str) -> dict[str, list[Commit]]:
    """Get commits grouped by branch."""
    try:
        result = subprocess.run(
            ["git", "branch", "--format=%(refname:short)"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}

    if result.returncode != 0:
        return {}

    branches_with_commits: dict[str, list[Commit]] = {}
    for branch in result.stdout.strip().splitlines():
        if not branch:
            continue
        commits = _get_commits_for_ref(repo_path, branch, since, until)
        if commits:
            branches_with_commits[branch] = commits

    return branches_with_commits


def _get_commits_for_ref(
    repo_path: Path, ref: str, since: str, until: str
) -> list[Commit]:
    try:
        result = subprocess.run(
            [
                "git", "log", ref,
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
            branch=ref,
        ))

    return commits
