# WorkLog CLI

从 git commits 自动生成工作日志。把技术性的 commit 记录翻译成公司要求的工作日志格式。

## 安装

```bash
pip install git+https://github.com/mjianqing/WorkHelper.git
```

> 如果提示 `externally-managed-environment`，先创建虚拟环境：
> ```bash
> python3 -m venv ~/.worklog-venv
> source ~/.worklog-venv/bin/activate
> pip install git+https://github.com/mjianqing/WorkHelper.git
> ```

## 配置

### 1. 设置 API 密钥

```bash
echo 'export WORKLOG_API_KEY="你的API密钥"' >> ~/.zshrc
source ~/.zshrc
```

### 2. 创建配置文件 `~/.worklog.toml`

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
```

将 `paths` 替换为你自己的 git 仓库路径。

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
```

## 配置说明

| 字段 | 说明 | 可选值 |
|------|------|--------|
| `llm_provider` | LLM 服务商 | `anthropic` / `openai` |
| `llm_endpoint` | API 地址 | 任意兼容的 API 端点 |
| `llm_model` | 模型名称 | 取决于你的服务商 |
| `repos.paths` | Git 仓库路径列表 | 支持 `~` 展开 |
| `style.tone` | 翻译风格 | `professional` / `casual` |
| `style.language` | 输出语言 | `zh-CN` / `en` 等 |

## 工作原理

1. 从配置的 git 仓库提取指定日期的 commits（所有分支）
2. 按仓库名称分组
3. 发送给 LLM，翻译成公司工作日志格式
4. 输出结果（终端 / 剪贴板 / webhook）

如果 LLM 服务不可用，会降级输出结构化的原始 commit 记录。
