#!/usr/bin/env python3
"""
morning_digest.py - 每日早间邮件摘要（飞书私信）

每天早上9点运行，取最近3封邮件的标题+简要内容，发送到飞书私聊。
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 确保 Windows 子进程使用 UTF-8
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.platform == "win32":
    os.environ.setdefault("CHCP", "65001")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("morning_digest")

USER_ID = "ou_7c515591ebd351055e3f1046ab385117"
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


def fetch_envelopes() -> list[dict]:
    cmd = [HIMALAYA, "envelopes", "list", "--output", "json", "--page-size", "10"]
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


def fetch_preview(msg_id: str) -> str:
    """获取邮件正文前150字作为预览"""
    cmd = [HIMALAYA, "messages", "read", msg_id]
    ok, output = run_cmd(cmd, timeout=15)
    if not ok or not output:
        return ""
    # 去掉头部信息（From/To/Subject等），只取正文
    lines = output.strip().splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "" and i > 3:
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]) if body_start > 0 else output
    # 去掉 MML 附件标记 <#part ... > 和 <#/part>、<#/multipart>
    body = re.sub(r'<#[^>]*>', '', body).strip()
    # 截断引用的回复内容
    for marker in ["---- 回复的原邮件", "-----Original Message", "发件人：", "2026-", "2025-"]:
        idx = body.find(marker)
        if idx > 20:
            body = body[:idx]
    return body.strip()[:150]


def send_to_feishu(mails: list[dict]) -> bool:
    """发送邮件摘要到飞书"""
    now = datetime.now().strftime("%Y-%m-%d")
    count = len(mails)

    lines = [
        f"[每日邮件摘要] {now}",
        "-" * 25,
        "",
    ]

    if count == 0:
        lines.append("暂无邮件。")
    else:
        lines.append(f"共 {count} 封邮件：\n")
        for i, m in enumerate(mails, 1):
            subject = parse_field(m.get("subject", "(无主题)"))
            sender = parse_field(m.get("from", ""))
            date_str = parse_field(m.get("date", ""))
            # 去掉时区偏移 +08:00，只保留日期时间
            if "+" in date_str:
                date_str = date_str.split("+")[0]
            attach = " [有附件]" if m.get("has_attachment") else ""
            msg_id = str(m.get("id", ""))

            # 获取简要内容
            preview = ""
            if msg_id:
                preview = fetch_preview(msg_id)

            lines.append(f">> 第{i}封{attach}")
            lines.append(f"  主题：{subject}")
            lines.append(f"  发件人：{sender}")
            lines.append(f"  时间：{date_str}")
            if preview:
                lines.append(f"  摘要：{preview}")
            lines.append("")

    msg_text = "\n".join(lines)
    log.info(f"准备发送飞书消息（{count} 封邮件）")

    # 构建 JSON，通过 send_feishu.js (Node.js) 发送，绕过 Windows 参数传递问题
    content_json = json.dumps({"text": msg_text}, ensure_ascii=False)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", encoding="utf-8",
        delete=False, prefix="digest_",
    ) as tmp:
        tmp.write(content_json)
        tmp_path = tmp.name

    try:
        js_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "send_feishu.js")
        result = subprocess.run(
            ["node", js_script, tmp_path, USER_ID],
            capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace",
        )
        ok = result.returncode == 0
        output = result.stdout.strip() or result.stderr.strip()
        if ok:
            log.info(f"飞书推送成功")
        else:
            log.error(f"飞书推送失败: {output}")
        return ok
    finally:
        os.unlink(tmp_path)


def main():
    # 检查 himalaya 配置
    default_config = Path.home() / ".config" / "himalaya" / "config.toml"
    if not default_config.exists():
        log.error(f"himalaya 配置不存在: {default_config}")
        sys.exit(1)

    log.info("开始获取邮件摘要...")
    envelopes = fetch_envelopes()

    # 取最近3封
    recent = envelopes[:3] if envelopes else []
    log.info(f"获取到 {len(envelopes)} 封邮件，取最近 {len(recent)} 封")

    send_to_feishu(recent)
    log.info("完成")


if __name__ == "__main__":
    main()
