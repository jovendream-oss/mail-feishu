#!/usr/bin/env python3
"""
daily_report.py - 每日新邮件报告（飞书私信）

功能：查询自上次报告后收到的新邮件，按接收时间倒序排列，发送摘要到飞书私信。
通过 last_report_ids.json 记录上次已报告的邮件 ID，每次只推送新增邮件。
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("daily_report")

USER_ID = "ou_7c515591ebd351055e3f1046ab385117"
SEEN_FILE = Path(__file__).parent / "last_report_ids.json"
LARK_CLI = os.path.join(
    os.environ.get("APPDATA", ""),
    "npm", "lark-cli.CMD"
)
HIMALAYA = os.path.join(os.path.expanduser("~"), "bin", "himalaya.exe")


def run_cmd(cmd: list[str], timeout: int = 30) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or result.stdout.strip()
        return True, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def parse_field(field_value) -> str:
    if isinstance(field_value, str):
        return field_value
    if isinstance(field_value, dict):
        return field_value.get("name") or field_value.get("addr") or str(field_value)
    return str(field_value) if field_value else ""


def load_seen_ids() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f).get("ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen_ids(ids: set[str]):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "ids": list(ids)[-500:],
                "updated_at": datetime.now().isoformat(),
            }, f, indent=2, ensure_ascii=False)
    except OSError as e:
        log.error(f"保存记录失败: {e}")


def fetch_envelopes() -> list[dict]:
    cmd = [HIMALAYA, "envelopes", "list", "--output", "json", "--page-size", "50"]
    ok, output = run_cmd(cmd, timeout=30)
    if not ok:
        log.error(f"获取邮件失败: {output}")
        return []
    if not output:
        return []
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else data.get("items", data.get("envelopes", []))


def send_feishu_report(mails: list[dict]) -> bool:
    """通过飞书发送新邮件报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    count = len(mails)

    # 构建纯文本消息
    text_lines = [f"[新邮件报告] {now}", "-" * 30]

    if count == 0:
        text_lines.append("没有新邮件。")
    else:
        text_lines.append(f"收到 {count} 封新邮件:\n")
        for i, m in enumerate(mails, 1):
            subject = parse_field(m.get("subject", "(无主题)"))
            sender = parse_field(m.get("from", ""))
            date_str = parse_field(m.get("date", ""))
            attach = " [附件]" if m.get("has_attachment") else ""
            text_lines.append(f"{i}. {subject}{attach}")
            text_lines.append(f"   发件人: {sender} | {date_str}\n")

    msg_text = "\n".join(text_lines)

    # 写入临时文件，用 PowerShell 读取后传递给 lark-cli
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", encoding="utf-8",
        delete=False, prefix="feishu_",
    ) as tmp:
        tmp.write(msg_text)
        tmp_path = tmp.name

    try:
        # 用 PowerShell 读取文件内容，再调用 lark-cli
        # 这样完全避免 subprocess 的编码问题
        ps_script = (
            f"$msg = Get-Content -Path '{tmp_path}' -Encoding UTF8 -Raw; "
            f"& lark-cli im +messages-send --as user --user-id {USER_ID} --text $msg"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace",
        )
        ok = result.returncode == 0
        output = result.stdout.strip() or result.stderr.strip()
        if ok:
            log.info(f"飞书推送成功（{count} 封新邮件）")
        else:
            log.error(f"飞书推送失败: {output}")
        return ok
    finally:
        os.unlink(tmp_path)


def main():
    default_config = Path.home() / ".config" / "himalaya" / "config.toml"
    if not default_config.exists():
        log.error(f"himalaya 配置不存在: {default_config}")
        sys.exit(1)

    log.info("查询新邮件...")
    envelopes = fetch_envelopes()

    # 首次运行：标记所有现有邮件为已报告
    seen_ids = load_seen_ids()
    if not seen_ids and envelopes:
        log.info("首次运行，标记现有邮件为已报告...")
        for env in envelopes:
            msg_id = str(env.get("id", ""))
            if msg_id:
                seen_ids.add(msg_id)
        save_seen_ids(seen_ids)
        log.info(f"已标记 {len(seen_ids)} 封邮件")

    # 筛选新邮件
    new_mails = []
    for env in envelopes:
        msg_id = str(env.get("id", ""))
        if msg_id and msg_id not in seen_ids:
            new_mails.append(env)

    log.info(f"共 {len(envelopes)} 封邮件，其中 {len(new_mails)} 封新邮件")

    send_feishu_report(new_mails)

    # 更新已报告记录
    if new_mails:
        for m in new_mails:
            seen_ids.add(str(m.get("id", "")))
        save_seen_ids(seen_ids)


if __name__ == "__main__":
    main()
