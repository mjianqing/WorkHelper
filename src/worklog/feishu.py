"""Feishu (Lark) integration for weekly report automation."""

import json
import subprocess
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class FeishuTask:
    record_id: str
    description: str
    status: str
    priority: str | None = None
    due_date: str | None = None


def get_week_friday(target_date: date | None = None) -> date:
    d = target_date or date.today()
    days_until_friday = (4 - d.weekday()) % 7
    if days_until_friday == 0 and d.weekday() == 4:
        return d
    return d + timedelta(days=days_until_friday)


def _run_lark_cli(args: list[str]) -> dict | None:
    cmd = ["lark-cli"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def get_my_tasks(config) -> list[FeishuTask]:
    all_rows = []
    all_record_ids = []
    fields = []
    has_more = True

    while has_more:
        args = [
            "base", "+record-list",
            "--base-token", config.feishu_base_token,
            "--table-id", config.feishu_task_table,
            "--limit", "500",
            "--format", "json",
        ]
        if len(all_record_ids) > 0:
            args.extend(["--offset", str(len(all_record_ids))])
        data = _run_lark_cli(args)
        if not data or not data.get("ok"):
            break

        fields = data["data"].get("fields", [])
        new_rows = data["data"].get("data", [])
        all_rows.extend(new_rows)
        all_record_ids.extend(data["data"].get("record_id_list", []))
        has_more = data["data"].get("has_more", False)
        if not new_rows:
            break

    if not fields:
        return []

    desc_idx = fields.index("任务描述") if "任务描述" in fields else -1
    status_idx = fields.index("状态") if "状态" in fields else -1
    exec_idx = fields.index("任务执行人") if "任务执行人" in fields else -1
    due_idx = fields.index("预计完成时间") if "预计完成时间" in fields else -1

    tasks = []
    for i, row in enumerate(all_rows):
        executor = row[exec_idx] if exec_idx >= 0 else None
        if not executor or not any(
            e.get("id") == config.feishu_member_id for e in executor
        ):
            continue
        desc = row[desc_idx] if desc_idx >= 0 else ""
        status_raw = row[status_idx] if status_idx >= 0 else None
        status = status_raw[0] if isinstance(status_raw, list) else (status_raw or "")
        due_raw = row[due_idx] if due_idx >= 0 else None
        due_date = due_raw[:10] if isinstance(due_raw, str) and len(due_raw) >= 10 else None
        tasks.append(FeishuTask(
            record_id=all_record_ids[i],
            description=desc or "",
            status=status,
            due_date=due_date,
        ))
    return tasks


def create_task(config, description: str, requirement_id: str = "", hours: float | None = None) -> str | None:
    req_id = requirement_id or config.feishu_default_requirement_id
    fields = ["任务描述", "状态", "优先级", "任务执行人", "所属需求"]
    row = [description, "研发中", "P2", [{"id": config.feishu_member_id}], [{"id": req_id}]]
    if hours:
        fields.append("计划工时")
        row.append(hours)

    payload = {"fields": fields, "rows": [row]}
    data = _run_lark_cli([
        "base", "+record-batch-create",
        "--base-token", config.feishu_base_token,
        "--table-id", config.feishu_task_table,
        "--json", json.dumps(payload),
    ])
    if data and data.get("ok"):
        record_ids = data.get("data", {}).get("record_id_list", [])
        if record_ids:
            return record_ids[0]
    return None


def submit_weekly_report(config, entries: list[dict]) -> bool:
    friday = get_week_friday()
    friday_ts = int(friday.strftime("%s")) * 1000

    fields = ["周期", "✅  任务", "任务状态", "工作内容及卡点"]
    rows = []
    for entry in entries:
        rows.append([
            friday_ts,
            [{"id": entry["task_id"]}],
            entry.get("status", "研发中（正常）"),
            entry.get("content", ""),
        ])

    payload = {"fields": fields, "rows": rows}
    data = _run_lark_cli([
        "base", "+record-batch-create",
        "--base-token", config.feishu_base_token,
        "--table-id", config.feishu_weekly_table,
        "--json", json.dumps(payload),
    ])
    return bool(data and data.get("ok"))


def get_existing_weekly_task_ids(config) -> set[str]:
    """Get task IDs already submitted in this week's report."""
    friday = get_week_friday()
    friday_ts = int(friday.strftime("%s")) * 1000

    data = _run_lark_cli([
        "base", "+record-list",
        "--base-token", config.feishu_base_token,
        "--table-id", config.feishu_weekly_table,
        "--limit", "200",
        "--format", "json",
    ])
    if not data or not data.get("ok"):
        return set()

    fields = data["data"].get("fields", [])
    rows = data["data"].get("data", [])

    period_idx = fields.index("周期") if "周期" in fields else -1
    task_idx = fields.index("✅  任务") if "✅  任务" in fields else -1
    creator_idx = fields.index("创建人") if "创建人" in fields else -1

    existing_ids = set()
    for row in rows:
        period_raw = row[period_idx] if period_idx >= 0 else None
        if not period_raw:
            continue
        # period can be timestamp string like "2026-05-22 00:00:00" or int
        period_str = str(period_raw)[:10] if isinstance(period_raw, str) else ""
        if isinstance(period_raw, str) and period_str == friday.isoformat():
            task_links = row[task_idx] if task_idx >= 0 else []
            if task_links:
                for link in task_links:
                    existing_ids.add(link.get("id", ""))
    return existing_ids


def match_commits_to_tasks(grouped_commits: dict, tasks: list[FeishuTask], config) -> list[dict]:
    from .llm_formatter import _commits_to_text, _call_llm

    commits_text = _commits_to_text(grouped_commits)
    friday = get_week_friday()
    monday = friday - timedelta(days=4)
    tasks_text = "\n".join(
        f"- [{t.record_id}] {t.description} (状态: {t.status}, 截止: {t.due_date or '无'})"
        for t in tasks
    ) or "（当前无进行中的任务）"

    prompt = f"""你是一个工作匹配助手。请将以下 git commits 分配到对应的任务中。

当前周期: {monday} ~ {friday}

重要规则：
1. 分支名是最强的匹配信号！匹配方式包括：
   - 英文全称：feat_niuzhubo_xxx → 匹配"牛主播"
   - 拼音首字母缩写：ybs → 影帮手，nzb → 牛主播，sljq → 算力计器
   - 语义关联：fix_payment → "支付"，home_page → "首页"
2. 如果分支名包含 hotfix 或 fix（如 hotfix/xxx, fix_xxx），这是工单修复类工作，task_id 必须填 null，会自动新建任务到工单需求下。
3. 对每条记录估算一个合理的人类工时（小时），填入 hours 字段。工时要偏大估算，参考：小bug修复=1-2h，普通功能开发=8-12h，复杂功能/多模块联调=16-24h，大型功能完整开发=24-40h。
4. 当任务名比较模糊时，优先匹配截止日期在本周（{monday} ~ {friday}）内的任务。截止日期越接近本周，匹配优先级越高。
5. 多个分支的工作如果都属于同一个任务，合并为一条记录。

已有任务列表：
{tasks_text}

本周 Git 提交记录（含分支名）：
{commits_text}

请按以下 JSON 格式输出（不要输出其他内容）：
[
  {{
    "task_id": "任务的record_id，如果没有匹配的任务或分支含hotfix/fix则填 null",
    "task_desc": "如果task_id为null，这里填新任务的描述（简洁中文）",
    "content": "工作内容及卡点（合并相关commits，用自然语言描述）",
    "status": "任务状态：研发中/已完成/测试中",
    "hours": 预估工时（数字，单位小时）,
    "is_hotfix": 是否为hotfix/fix分支（true/false）
  }}
]

规则：
- 优先用分支名做语义匹配（英文分支名 → 对应中文任务）
- 同一分支的 commits 合并到同一条记录
- 工作内容用简洁自然的中文，不要AI腔
- hotfix/fix 分支的任务描述要简洁明确，如"修复xxx问题"
- hours 要合理，不要虚报"""

    try:
        result = _call_llm(prompt, config)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        matches = json.loads(result)
        valid_task_ids = {t.record_id for t in tasks}
        for m in matches:
            m["status"] = _normalize_status(m.get("status", ""))
            tid = m.get("task_id")
            if tid and tid not in valid_task_ids:
                m["task_id"] = None
            if m.get("is_hotfix"):
                m["task_id"] = None
        return matches
    except (json.JSONDecodeError, Exception):
        return []


def _normalize_status(raw: str) -> str:
    s = raw.strip()
    if "完成" in s:
        return "已完成"
    if "测试" in s:
        return "测试中"
    if "风险" in s:
        return "研发中（有风险）"
    if "暂停" in s:
        return "暂停"
    if "未开始" in s:
        return "未开始"
    return "研发中（正常）"
