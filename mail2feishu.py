#!/usr/bin/env python3
"""
mail2feishu.py - 基于 Himalaya CLI + Lark CLI 的邮件飞书提醒服务

功能：定时轮询网易企业邮箱新邮件，通过飞书机器人推送到指定群聊。
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ============ 日志配置 ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("mail2feishu")


def run_cmd(cmd: list[str], timeout: int = 30) -> tuple[bool, str]:
    """运行外部命令，返回 (成功与否, 输出文本)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or result.stdout.strip()
        return True, result.stdout.strip()
    except FileNotFoundError:
        return False, f"命令未找到: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, f"命令超时 ({timeout}s): {' '.join(cmd)}"
    except Exception as e:
        return False, str(e)


def load_seen_ids(path: Path) -> set[str]:
    """加载已推送邮件 ID 集合"""
    if not path.exists():
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("ids", []))
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"读取 seen_ids 文件失败，将重新开始: {e}")
        return set()


def save_seen_ids(path: Path, ids: set[str], max_keep: int = 500):
    """保存已推送邮件 ID，超过 max_keep 时截断最早的"""
    if len(ids) > max_keep:
        ids = set(list(ids)[-max_keep:])
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"ids": list(ids), "updated_at": datetime.now().isoformat()}, f, indent=2)
    except OSError as e:
        log.error(f"保存 seen_ids 文件失败: {e}")


def fetch_envelopes() -> list[dict]:
    """通过 himalaya CLI 获取收件箱邮件列表（JSON 格式）
    注意：himalaya Windows 版 -c 参数有路径解析 bug，
    配置文件统一放在默认路径 ~/.config/himalaya/config.toml
    """
    cmd = [
        "himalaya",
        "envelopes", "list",
        "--output", "json",
        "--page-size", "20",
    ]
    ok, output = run_cmd(cmd, timeout=30)
    if not ok:
        log.error(f"获取邮件列表失败: {output}")
        return []

    if not output:
        return []

    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        log.error(f"解析邮件 JSON 失败: {e}")
        return []

    # himalaya 可能返回列表或包含 items 字段的对象
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", data.get("envelopes", []))
    return []


def fetch_message_detail(msg_id: str) -> str:
    """获取邮件正文预览"""
    cmd = [
        "himalaya",
        "messages", "read", msg_id,
    ]
    ok, output = run_cmd(cmd, timeout=15)
    if not ok:
        return ""
    # 截取前 200 字符作为预览
    return output[:200].replace("\n", " ").strip()


def send_to_feishu(user_id: str, subject: str, sender: str, preview: str, msg_date: str = "") -> bool:
    """通过 Lark CLI 以用户身份发送邮件提醒私信给自己"""
    # 构建富文本消息
    preview_escaped = preview.replace('"', '\\"').replace("\n", "\\n")
    subject_escaped = subject.replace('"', '\\"')
    sender_escaped = sender.replace('"', '\\"')

    date_line = f"**时间：** {msg_date}\n" if msg_date else ""

    # 使用飞书 markdown 格式
    msg_content = (
        f"📧 **新邮件提醒**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"**发件人：** {sender_escaped}\n"
        f"**主题：** {subject_escaped}\n"
        f"{date_line}"
        f"**预览：** {preview_escaped}"
    )

    cmd = [
        "lark-cli", "im", "+messages-send",
        "--as", "user",
        "--user-id", user_id,
        "--markdown", msg_content,
    ]

    ok, output = run_cmd(cmd, timeout=15)
    if ok:
        log.info(f"飞书推送成功: [{subject_escaped}]")
    else:
        log.error(f"飞书推送失败: {output}")
    return ok


def parse_sender(from_str: str) -> str:
    """从 From 字段提取可读的发件人名称"""
    if not from_str:
        return "未知发件人"
    # 格式通常为 "Name <email@domain.com>" 或 "email@domain.com"
    from_str = from_str.strip()
    if "<" in from_str and ">" in from_str:
        name = from_str.split("<")[0].strip().strip('"').strip("'")
        if name:
            return name
    # 去掉尖括号
    return from_str.strip("<>").strip()


def parse_field(field_value) -> str:
    """安全提取字符串字段"""
    if isinstance(field_value, str):
        return field_value
    if isinstance(field_value, dict):
        return field_value.get("value", str(field_value))
    return str(field_value) if field_value else ""


def main():
    parser = argparse.ArgumentParser(description="邮件飞书提醒服务 (Himalaya + Lark CLI)")
    parser.add_argument("--user-id", default="ou_7c515591ebd351055e3f1046ab385117",
                        help="飞书用户 open_id，默认为当前用户 (ou_xxx)")
    parser.add_argument("--interval", type=int, default=60, help="轮询间隔秒数 (默认: 60)")
    parser.add_argument("--max-keep", type=int, default=500, help="seen_ids 最大保留数量 (默认: 500)")
    parser.add_argument("--seen-file", default="./seen_ids.json", help="已推送邮件 ID 存储文件 (默认: ./seen_ids.json)")
    parser.add_argument("--once", action="store_true", help="只运行一次，不循环（用于调试）")
    args = parser.parse_args()

    # 解析路径
    seen_path = Path(args.seen_file).resolve()

    # 检查 himalaya 默认配置是否存在
    default_config = Path.home() / ".config" / "himalaya" / "config.toml"
    if not default_config.exists():
        log.error(f"himalaya 配置文件不存在: {default_config}")
        log.error("请将 config.toml 放到 ~/.config/himalaya/config.toml")
        sys.exit(1)

    # 检查 himalaya 是否可用
    ok, _ = run_cmd(["himalaya", "--version"])
    if not ok:
        log.error("himalaya 未安装或不在 PATH 中，请先安装: scoop install himalaya")
        sys.exit(1)

    # 检查 lark-cli 是否可用
    ok, _ = run_cmd(["lark-cli", "--version"])
    if not ok:
        log.error("lark-cli 未安装或不在 PATH 中，请先安装: npm install -g @larksuite/cli")
        sys.exit(1)

    # 加载已推送邮件 ID
    seen_ids = load_seen_ids(seen_path)
    log.info(f"已加载 {len(seen_ids)} 条已推送记录")

    log.info(f"邮件飞书提醒服务已启动")
    log.info(f"  配置文件: {default_config}")
    log.info(f"  飞书用户: {args.user_id}")
    log.info(f"  轮询间隔: {args.interval}s")

    def poll_once():
        nonlocal seen_ids
        envelopes = fetch_envelopes()
        if envelopes is None:
            return

        new_count = 0
        for env in envelopes:
            # 提取邮件 ID — himalaya JSON 中 ID 字段可能是 "id" 或 "pk"
            msg_id = str(env.get("id") or env.get("pk", ""))
            if not msg_id or msg_id in seen_ids:
                continue

            # 提取字段
            subject = parse_field(env.get("subject", "(无主题)"))
            from_raw = parse_field(env.get("from", ""))
            sender = parse_sender(from_raw)
            date_str = parse_field(env.get("date", ""))

            # 获取正文预览
            preview = fetch_message_detail(msg_id)

            # 推送到飞书（以用户身份私信给自己）
            success = send_to_feishu(
                user_id=args.user_id,
                subject=subject,
                sender=sender,
                preview=preview,
                msg_date=date_str,
            )

            if success:
                seen_ids.add(msg_id)
                new_count += 1

        if new_count > 0:
            save_seen_ids(seen_path, seen_ids, args.max_keep)
            log.info(f"本轮发现 {new_count} 封新邮件，已推送")
        else:
            log.debug("暂无新邮件")

    # 首次运行：加载现有邮件 ID 为已读，避免首次启动时大量推送
    if not seen_ids:
        log.info("首次运行，标记当前所有邮件为已读...")
        envelopes = fetch_envelopes()
        if envelopes:
            for env in envelopes:
                msg_id = str(env.get("id") or env.get("pk", ""))
                if msg_id:
                    seen_ids.add(msg_id)
            save_seen_ids(seen_path, seen_ids, args.max_keep)
            log.info(f"已标记 {len(seen_ids)} 封现有邮件为已读")

    if args.once:
        poll_once()
        return

    # 主循环
    while True:
        try:
            poll_once()
        except KeyboardInterrupt:
            log.info("用户中断，服务已停止")
            save_seen_ids(seen_path, seen_ids, args.max_keep)
            break
        except Exception as e:
            log.error(f"轮询异常: {e}")

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
