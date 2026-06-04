---
name: himalaya
description: CLI to manage emails via IMAP/SMTP. Use himalaya to list, read, write, reply, forward, search, and organize emails from the terminal. Supports multiple accounts and message composition with MML (MIME Meta Language).
version: 1.0.0
author: community
license: MIT
metadata:
  hermes:
    tags: [Email, IMAP, SMTP, CLI, Communication]
    homepage: https://github.com/pimalaya/himalaya
prerequisites:
  commands: [himalaya]
---

# Himalaya Email CLI

Himalaya is a CLI email client that lets you manage emails from the terminal using IMAP, SMTP, Notmuch, or Sendmail backends.

## References

- `references/configuration.md` (config file setup + IMAP/SMTP authentication)
- `references/message-composition.md` (MML syntax for composing emails)

## Prerequisites

1. Himalaya CLI installed (`himalaya --version` to verify)
2. A configuration file at `~/.config/himalaya/config.toml`
3. IMAP/SMTP credentials configured (password stored securely)

### Installation

```bash
# Pre-built binary (Linux/macOS — recommended)
curl -sSL https://raw.githubusercontent.com/pimalaya/himalaya/master/install.sh | PREFIX=~/.local sh

# macOS via Homebrew
brew install himalaya

# Or via cargo (any platform with Rust)
cargo install himalaya --locked
```

## Configuration Setup

Run the interactive wizard to set up an account:

```bash
himalaya account configure
```

Or create `~/.config/himalaya/config.toml` manually:

```toml
[accounts.personal]
email = "you@example.com"
display-name = "Your Name"
default = true

backend.type = "imap"
backend.host = "imap.example.com"
backend.port = 993
backend.encryption.type = "tls"
backend.login = "you@example.com"
backend.auth.type = "password"
backend.auth.cmd = "pass show email/imap"  # or use keyring

message.send.backend.type = "smtp"
message.send.backend.host = "smtp.example.com"
message.send.backend.port = 587
message.send.backend.encryption.type = "start-tls"
message.send.backend.login = "you@example.com"
message.send.backend.auth.type = "password"
message.send.backend.auth.cmd = "pass show email/smtp"
```

## Hermes Integration Notes

- **Reading, listing, searching, moving, deleting** all work directly through the terminal tool
- **Composing/replying/forwarding** — piped input (`cat << EOF | himalaya template send`) is recommended for reliability. Interactive `$EDITOR` mode works with `pty=true` + background + process tool, but requires knowing the editor and its commands
- Use `--output json` for structured output that's easier to parse programmatically
- The `himalaya account configure` wizard requires interactive input — use PTY mode: `terminal(command="himalaya account configure", pty=true)`

## Common Operations

### List Folders

```bash
himalaya folder list
```

### List Emails

List emails in INBOX (default):

```bash
himalaya envelope list
```

List emails in a specific folder:

```bash
himalaya envelope list --folder "Sent"
```

List with pagination:

```bash
himalaya envelope list --page 1 --page-size 20
```

### Search Emails

```bash
himalaya envelope list from john@example.com subject meeting
```

### Read an Email

Read email by ID (shows plain text):

```bash
himalaya message read 42
```

Export raw MIME:

```bash
himalaya message export 42 --full
```

### Reply to an Email

To reply non-interactively from Hermes, read the original message, compose a reply, and pipe it:

```bash
# Get the reply template, edit it, and send
himalaya template reply 42 | sed 's/^$/\nYour reply text here\n/' | himalaya template send
```

Or build the reply manually:

```bash
cat << 'EOF' | himalaya template send
From: you@example.com
To: sender@example.com
Subject: Re: Original Subject
In-Reply-To: <original-message-id>

Your reply here.
EOF
```

Reply-all (interactive — needs $EDITOR, use template approach above instead):

```bash
himalaya message reply 42 --all
```

### Forward an Email

```bash
# Get forward template and pipe with modifications
himalaya template forward 42 | sed 's/^To:.*/To: newrecipient@example.com/' | himalaya template send
```

### Write a New Email

**Non-interactive (use this from Hermes)** — pipe the message via stdin:

```bash
cat << 'EOF' | himalaya template send
From: you@example.com
To: recipient@example.com
Subject: Test Message

Hello from Himalaya!
EOF
```

Or with headers flag:

```bash
himalaya message write -H "To:recipient@example.com" -H "Subject:Test" "Message body here"
```

Note: `himalaya message write` without piped input opens `$EDITOR`. This works with `pty=true` + background mode, but piping is simpler and more reliable.

#### 备用方案：himalaya不可用时直接使用Python操作邮箱（网易企业邮箱专用）
当himalaya安装失败/不可用，且使用网易企业邮箱时，可以直接用Python代码收发邮件，密码已存储在Hermes内存中：

##### 1. 发送邮件
```python
import smtplib
from email.mime.text import MIMEText
from email.header import Header

sender = 'wangyabo@lifetechmed.com'
# 从Hermes memory读取SMTP密码
password = 'Ks$y4CW@29vtkZqf'

def send_email(receiver, subject, content, content_type='plain'):
    message = MIMEText(content, content_type, 'utf-8')
    message['From'] = Header(f'王亚博 <{sender}>', 'utf-8')
    message['To'] = Header(receiver, 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')
    
    smtp = smtplib.SMTP_SSL('smtp.qiye.163.com', 465)
    smtp.login(sender, password)
    smtp.sendmail(sender, [receiver], message.as_string())
    smtp.quit()

# 调用示例
# send_email('1417611676@qq.com', 'Hermes安装完成通知', '您好，Hermes 已经安装完成。')
```

##### 2. 读取收件箱邮件（支持按时间筛选）
```python
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta

# 配置信息
IMAP_SERVER = 'imap.qiye.163.com'
IMAP_PORT = 993
EMAIL = 'wangyabo@lifetechmed.com'
PASSWORD = 'Ks$y4CW@29vtkZqf'

def get_recent_emails(days=1, max_count=50):
    """
    获取最近N天的邮件
    :param days: 最近几天
    :param max_count: 最多返回多少封
    :return: 邮件列表，包含date/from/subject字段
    """
    # 计算时间窗口
    time_window = datetime.now() - timedelta(days=days)
    local_tz = time_window.astimezone().tzinfo
    time_window = time_window.replace(tzinfo=local_tz)

    # 连接IMAP服务器
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(EMAIL, PASSWORD)

    # 选择收件箱
    mail.select('INBOX')

    # 搜索所有邮件
    status, messages = mail.search(None, 'ALL')
    mail_ids = messages[0].split()

    # 存储符合条件的邮件
    emails = []

    # 遍历最新的max_count封邮件
    for mail_id in reversed(mail_ids[-max_count:]):
        status, msg_data = mail.fetch(mail_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # 解析发件人
                from_ = decode_header(msg['From'])[0][0]
                if isinstance(from_, bytes):
                    from_ = from_.decode()
                
                # 解析主题
                subject = decode_header(msg['Subject'])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                # 解析时间
                date_str = msg['Date']
                mail_date = email.utils.parsedate_to_datetime(date_str)
                mail_date_local = mail_date.astimezone()
                
                # 筛选时间范围内的邮件
                if mail_date_local >= time_window:
                    emails.append({
                        'date': mail_date_local.strftime('%Y-%m-%d %H:%M'),
                        'from': from_,
                        'subject': subject
                    })

    # 关闭连接
    mail.close()
    mail.logout()
    return emails

# 调用示例：获取最近24小时的邮件
# recent_emails = get_recent_emails(days=1)
```

### Move/Copy Emails

Move to folder:

```bash
himalaya message move 42 "Archive"
```

Copy to folder:

```bash
himalaya message copy 42 "Important"
```

### Delete an Email

```bash
himalaya message delete 42
```

### Manage Flags

Add flag:

```bash
himalaya flag add 42 --flag seen
```

Remove flag:

```bash
himalaya flag remove 42 --flag seen
```

## Multiple Accounts

List accounts:

```bash
himalaya account list
```

Use a specific account:

```bash
himalaya --account work envelope list
```

## Attachments

Save attachments from a message:

```bash
himalaya attachment download 42
```

Save to specific directory:

```bash
himalaya attachment download 42 --dir ~/Downloads
```

## Output Formats

Most commands support `--output` for structured output:

```bash
himalaya envelope list --output json
himalaya envelope list --output plain
```

## Debugging

Enable debug logging:

```bash
RUST_LOG=debug himalaya envelope list
```

Full trace with backtrace:

```bash
RUST_LOG=trace RUST_BACKTRACE=1 himalaya envelope list
```

## 网易企业邮箱备用方案（无需安装himalaya CLI）
当无法安装himalaya CLI时，可直接使用Python标准库完成收发邮件操作，已验证适配网易企业邮箱：
### 配置信息
- SMTP服务器：smtp.qiye.163.com 端口465（SSL）
- IMAP服务器：imap.qiye.163.com 端口993（SSL）
### 发送邮件代码示例
```python
import smtplib
from email.mime.text import MIMEText
from email.header import Header

sender = "你的邮箱@lifetechmed.com"
password = "你的SMTP密码"
receiver = "收件人邮箱"

message = MIMEText("邮件内容", "plain", "utf-8")
message["From"] = Header(f"发件人姓名 <{sender}>", "utf-8")
message["To"] = Header(receiver, "utf-8")
message["Subject"] = Header("邮件主题", "utf-8")

smtp = smtplib.SMTP_SSL("smtp.qiye.163.com", 465)
smtp.login(sender, password)
smtp.sendmail(sender, [receiver], message.as_string())
smtp.quit()
```
### 收取并分类本周邮件代码示例
```python
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta

IMAP_SERVER = "imap.qiye.163.com"
IMAP_PORT = 993
EMAIL_ACCOUNT = "你的邮箱@lifetechmed.com"
EMAIL_PASSWORD = "你的SMTP密码"

# 计算本周一日期
today = datetime.now()
monday = today - timedelta(days=today.weekday())
date_filter = monday.strftime("%d-%b-%Y")

# 连接服务器
mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
mail.select("INBOX")

# 搜索本周邮件
status, messages = mail.search(None, f'SINCE "{date_filter}"')
email_ids = messages[0].split()

# 分类逻辑
categories = {
    "工作邮件": [],
    "通知类": [],
    "广告/推广": [],
    "其他": []
}

for eid in reversed(email_ids):
    status, msg_data = mail.fetch(eid, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            # 解码主题、发件人、时间
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8")
            from_ = msg.get("From")
            date_str = msg.get("Date")
            try:
                mail_date = email.utils.parsedate_to_datetime(date_str)
                date_formatted = mail_date.strftime("%Y-%m-%d %H:%M")
            except:
                date_formatted = date_str
            # 分类规则可自定义
            work_keywords = ["工作", "项目", "会议", "周报", "审批", "需求", "开发", "测试", "团队", "公司"]
            notify_keywords = ["验证码", "通知", "账单", "订阅", "提醒", "确认", "系统"]
            ad_keywords = ["优惠", "广告", "推广", "特惠", "促销", "抽奖"]
            is_work = any(k in subject for k in work_keywords) or any("lifetechmed.com" in part for part in from_.split())
            is_notify = any(k in subject for k in notify_keywords)
            is_ad = any(k in subject for k in ad_keywords)
            
            mail_info = f"[{date_formatted}] {from_} - {subject}"
            if is_work:
                categories["工作邮件"].append(mail_info)
            elif is_notify:
                categories["通知类"].append(mail_info)
            elif is_ad:
                categories["广告/推广"].append(mail_info)
            else:
                categories["其他"].append(mail_info)

mail.logout()
```

## Tips

- Use `himalaya --help` or `himalaya <command> --help` for detailed usage.
- Message IDs are relative to the current folder; re-list after folder changes.
- For composing rich emails with attachments, use MML syntax (see `references/message-composition.md`).
- Store passwords securely using `pass`, system keyring, or a command that outputs the password.
