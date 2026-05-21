import sys

import pyperclip
import requests


def to_stdout(content: str) -> None:
    print(content)


def to_clipboard(content: str) -> None:
    try:
        pyperclip.copy(content)
        print("已复制到剪贴板 ✓", file=sys.stderr)
    except pyperclip.PyperclipException:
        print("剪贴板不可用，输出到 stdout：", file=sys.stderr)
        print(content)


def to_webhook(content: str, url: str) -> None:
    if not url:
        print("未配置 webhook_url，输出到 stdout：", file=sys.stderr)
        print(content)
        return

    try:
        resp = requests.post(
            url,
            json={"content": content},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"已推送到 webhook ✓ (status: {resp.status_code})", file=sys.stderr)
    except requests.RequestException as e:
        print(f"Webhook 推送失败: {e}", file=sys.stderr)
        print(content)
