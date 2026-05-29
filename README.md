# WorkLog CLI

从 git commits 自动生成工作日志。把技术性的 commit 记录翻译成公司要求的工作日志格式。

## 安装

### macOS / Linux

```bash
pip install git+https://github.com/mjianqing/WorkHelper.git
```

> 如果提示 `externally-managed-environment`，先创建虚拟环境：
> ```bash
> python3 -m venv ~/.worklog-venv
> source ~/.worklog-venv/bin/activate
> pip install git+https://github.com/mjianqing/WorkHelper.git
> ```

### Windows

前提：已安装 [Python 3.11+](https://www.python.org/downloads/) 和 [Git](https://git-scm.com/download/win)。

```powershell
pip install git+https://github.com/mjianqing/WorkHelper.git
```

> 如果提示权限问题，使用虚拟环境：
> ```powershell
> python -m venv %USERPROFILE%\.worklog-venv
> %USERPROFILE%\.worklog-venv\Scripts\activate
> pip install git+https://github.com/mjianqing/WorkHelper.git
> ```

## 配置

### 1. 设置 API 密钥

**macOS / Linux：**
```bash
echo 'export WORKLOG_API_KEY="你的API密钥"' >> ~/.zshrc
source ~/.zshrc
```

**Windows（PowerShell）：**
```powershell
[Environment]::SetEnvironmentVariable("WORKLOG_API_KEY", "你的API密钥", "User")
```

设置后重启终端生效。

### 2. 创建配置文件

**macOS / Linux：** `~/.worklog.toml`

**Windows：** `C:\Users\你的用户名\.worklog.toml`

```toml
[general]
llm_provider = "anthropic"
llm_endpoint = "https://token-plan-cn.xiaomimimo.com/anthropic"
llm_model = "mimo-v2-pro"

[repos]
paths = [
  "~/code/project-a",
  "~/code/project-b",
]

[style]
tone = "professional"
language = "zh-CN"

# 飞书周报自动化（可选，仅 worklog feishu 需要）
[feishu]
base_token = "你的多维表格 app_token"
task_table = "任务表 table_id"
weekly_table = "周报表 table_id"
member_id = "你的飞书 open_id"
creator_name = "你在飞书中的姓名"
default_requirement_id = "默认需求工单的 record_id"
```

将 `paths` 替换为你自己的 git 仓库路径。

> Windows 用户路径示例：
> ```toml
> [repos]
> paths = [
>   "C:/Users/你的用户名/code/project-a",
>   "D:/work/project-b",
> ]
> ```
> 用正斜杠 `/` 即可，不需要反斜杠。

## 使用

```bash
# 生成今日工作日志
worklog today

# 生成本周工作日志
worklog week

# 生成指定日期的工作日志
worklog day 2026-05-20

# 生成并复制到剪贴板
worklog push

# 生成并推送到 webhook
worklog push --webhook

# 自动生成并提交本周飞书周报（需先配置 [feishu] 段）
worklog feishu

# 跳过预览确认直接提交
worklog feishu -y

# 为新建任务指定关联的需求工单
worklog feishu -r <requirement_record_id>
```

### 飞书周报自动化（`worklog feishu`）

把本周 git commits 自动整理成飞书多维表格周报：

1. 拉取本周所有仓库的 commits；
2. 拉取你在飞书任务表中进行中的任务；
3. 通过 LLM 把 commits 匹配到对应任务，并生成周报内容、状态、工时；
4. 打印预览，确认后写入周报表；未匹配到的 commits 会自动建任务（hotfix 自动关联默认工单需求）。

内置去重：同一周内已提交过的任务会自动跳过，可以反复执行而不会产生重复记录。

## 配置说明

| 字段 | 说明 | 可选值 |
|------|------|--------|
| `llm_provider` | LLM 服务商 | `anthropic` / `openai` |
| `llm_endpoint` | API 地址 | 任意兼容的 API 端点 |
| `llm_model` | 模型名称 | 取决于你的服务商 |
| `repos.paths` | Git 仓库路径列表 | 支持 `~` 展开 |
| `style.tone` | 翻译风格 | `professional` / `casual` |
| `style.language` | 输出语言 | `zh-CN` / `en` 等 |
| `feishu.base_token` | 飞书多维表格 app_token | 仅 `worklog feishu` 需要 |
| `feishu.task_table` | 任务表 table_id | 用于读取进行中的任务 |
| `feishu.weekly_table` | 周报表 table_id | 用于写入和去重周报记录 |
| `feishu.member_id` | 你的飞书 open_id | 用于过滤本人任务 |
| `feishu.creator_name` | 你在飞书中的姓名 | 用于按创建人去重本周记录 |
| `feishu.default_requirement_id` | 默认需求工单 record_id | hotfix / 未指定 `-r` 时使用 |

## 工作原理

1. 从配置的 git 仓库提取指定日期的 commits（所有分支）
2. 按仓库名称分组
3. 发送给 LLM，翻译成公司工作日志格式
4. 输出结果（终端 / 剪贴板 / webhook）

如果 LLM 服务不可用，会降级输出结构化的原始 commit 记录。
