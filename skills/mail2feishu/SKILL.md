---
name: mail2feishu
description: 邮件飞书自动提醒服务。通过 himalaya CLI 监控企业邮箱新邮件，使用 lark-cli 推送通知到飞书群聊。当用户提到邮件提醒、邮件通知、mail to feishu、邮件推送到飞书、新邮件通知、邮箱监控、邮件飞书、mail2feishu 时使用此技能。也适用于用户想设置邮件自动转发到飞书、想实时收到邮件通知到飞书群、或管理邮件提醒服务的场景。
version: 1.0.0
author: user
prerequisites:
  commands: [himalaya, lark-cli, python]
---

# mail2feishu - 邮件飞书自动提醒

将企业邮箱（网易企业邮箱 mail.qiye.163.com）的新邮件实时推送到飞书群聊。

## 项目位置

所有文件位于 `C:\Users\27703\mail2feishu\`：

```
mail2feishu/
├── config.toml        # himalaya 邮箱配置（邮箱地址 + 授权码）
├── mail2feishu.py     # 主脚本
├── seen_ids.json      # 运行时自动生成（已推送邮件记录）
└── README.md          # 使用说明
```

## 前置条件

1. **himalaya** v1.2.0+ — 已安装在 `C:\Users\27703\bin\himalaya.exe`
2. **lark-cli** — 已全局安装（`npm install -g @larksuite/cli`）
3. **Python** 3.8+ — 无额外依赖
4. **飞书群聊机器人** — 用户需提供 chat_id（格式 `oc_xxx`）
5. **config.toml** — 已填入邮箱地址和授权码

## 用户请求处理流程

根据用户的意图，执行对应的操作：

### 1. 启动邮件提醒服务

当用户说"启动邮件提醒"、"开始监控邮件"、"运行 mail2feishu"时：

```bash
cd C:/Users/27703/mail2feishu
python mail2feishu.py --interval <用户指定的间隔，默认60>
```

说明：
- 默认以用户身份（刘鹏飞 ou_7c515591ebd351055e3f1046ab385117）发私信给自己
- 不需要提供 chat-id，直接发到飞书"飞书机器人"私聊
- himalaya 配置文件在默认路径 `~/.config/himalaya/config.toml`

后台运行（Windows）：
```bash
start /B pythonw C:/Users/27703/mail2feishu/mail2feishu.py --interval 60
```

### 2. 配置邮箱

当用户说"配置邮箱"、"设置邮箱"、"修改 config.toml"时：

1. 询问用户的邮箱地址和授权码
2. 编辑 `C:\Users\27703\mail2feishu\config.toml`，替换 `<YOUR_EMAIL>` 和 `<YOUR_AUTH_CODE>`
3. 授权码获取方式：登录网易企业邮箱网页版 → 设置 → POP3/IMAP/SMTP → 开启 IMAP → 生成授权码
4. 测试连接：`himalaya -c C:/Users/27703/mail2feishu/config.toml envelopes list`

### 3. 测试服务

当用户说"测试一下"、"试运行"时：

```bash
cd C:/Users/27703/mail2feishu
python mail2feishu.py --chat-id <chat_id> --once
```

`--once` 参数只运行一次，适合调试。

### 4. 查看服务状态

当用户说"查看状态"、"邮件提醒在运行吗"时：

```bash
# 检查进程是否在运行
tasklist | findstr python
# 查看 seen_ids.json 中的记录数和最后更新时间
type C:\Users\27703\mail2feishu\seen_ids.json
```

### 5. 停止服务

当用户说"停止邮件提醒"、"关掉监控"时：

```bash
# 找到并终止 mail2feishu 进程
taskkill /F /FI "WINDOWTITLE eq mail2feishu*" 2>nul
# 或按 PID 终止
wmic process where "CommandLine like '%mail2feishu%'" get ProcessId
taskkill /F /PID <pid>
```

## 脚本参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--user-id` | ❌ | `ou_7c515591...` | 飞书用户 open_id（默认当前用户） |
| `--interval` | ❌ | 60 | 轮询间隔（秒） |
| `--max-keep` | ❌ | 500 | 已推送记录最大保留数 |
| `--seen-file` | ❌ | `./seen_ids.json` | 已推送记录存储文件 |
| `--once` | ❌ | false | 只运行一次（调试用） |

## 常见问题处理

- **himalaya 连接失败**：检查 `~/.config/himalaya/config.toml` 中邮箱和授权码是否正确，确认 IMAP 已开启
- **lark-cli 推送失败**：运行 `lark-cli config show` 检查登录状态
- **首次启动**：脚本会自动将当前邮件标记为已读，不会推送历史邮件
- **重复通知**：seen_ids.json 记录已推送邮件 ID，自动去重
