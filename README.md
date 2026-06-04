# mail2feishu - 邮件飞书自动提醒

将网易企业邮箱的新邮件自动推送到飞书群聊。

## 前置条件

1. **himalaya** - CLI 邮件客户端
2. **lark-cli** - 飞书命令行工具
3. **Python 3.8+**

### 安装 himalaya

```bash
# 方式一：Scoop（推荐）
scoop install himalaya

# 方式二：Cargo
cargo install --locked --git https://github.com/pimalaya/himalaya.git
```

### 安装 lark-cli

```bash
npm install -g @larksuite/cli
```

## 配置

### 1. 开启网易企业邮箱 IMAP 服务

1. 登录 [网易企业邮箱网页版](https://mail.qiye.163.com)
2. 进入 **设置** → **POP3/IMAP/SMTP**
3. 开启 **IMAP 服务**
4. 生成 **授权码**（16 位密码，替代登录密码使用）

### 2. 编辑 config.toml

将配置文件中的占位符替换为你的实际信息：

```toml
email = "your-name@your-company.com"        # 你的邮箱地址
backend.auth.raw = "ABCDEFGHIJKLMNOP"       # IMAP 授权码
message.send.backend.auth.raw = "ABCDEFGHIJKLMNOP"  # SMTP 授权码
```

### 3. 获取飞书群聊 ID

- 在飞书群聊中，点击群设置 → 群信息，找到 **群聊 ID**（格式：`oc_xxx`）
- 或使用 lark-cli 搜索：`lark-cli im +chat-search --keyword "群名"`

## 使用

### 启动服务

```bash
python mail2feishu.py --chat-id oc_xxx
```

### 常用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config` | himalaya 配置文件路径 | `./config.toml` |
| `--chat-id` | 飞书目标群聊 ID (必填) | - |
| `--interval` | 轮询间隔（秒） | `60` |
| `--max-keep` | 已推送记录最大保留数 | `500` |
| `--seen-file` | 已推送记录存储文件 | `./seen_ids.json` |
| `--once` | 只运行一次（调试用） | `false` |

### 示例

```bash
# 每 30 秒检查一次
python mail2feishu.py --chat-id oc_xxx --interval 30

# 调试模式：只运行一次
python mail2feishu.py --chat-id oc_xxx --once

# 指定配置文件路径
python mail2feishu.py --config /path/to/config.toml --chat-id oc_xxx
```

### 后台运行（Windows）

#### 方式一：使用 pythonw

```bash
pythonw mail2feishu.py --chat-id oc_xxx
```

#### 方式二：注册为 Windows 计划任务

1. 打开 **任务计划程序**（Task Scheduler）
2. 创建基本任务 → 触发器选「计算机启动时」
3. 操作选「启动程序」：
   - 程序：`pythonw.exe`
   - 参数：`C:\Users\27703\mail2feishu\mail2feishu.py --chat-id oc_xxx`
   - 起始于：`C:\Users\27703\mail2feishu`
4. 勾选「不管用户是否登录都要运行」

## 文件说明

```
mail2feishu/
├── config.toml        # himalaya 邮箱配置（需编辑）
├── mail2feishu.py     # 主脚本
├── seen_ids.json      # 运行时自动生成，记录已推送邮件
├── requirements.txt   # 无额外依赖
└── README.md          # 本文件
```

## 工作原理

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  himalaya CLI    │     │ mail2feishu  │     │  lark-cli   │
│  (IMAP 收件)     │────▶│  (Python)    │────▶│ (飞书推送)   │
└─────────────────┘     └──────────────┘     └─────────────┘
                         │
                         ▼
                    seen_ids.json
                    (去重记录)
```

1. **轮询**：每隔 N 秒调用 `himalaya envelopes list` 获取最新邮件列表
2. **去重**：对比 `seen_ids.json`，筛选未推送过的新邮件
3. **推送**：调用 `lark-cli im +messages-send` 将邮件摘要发送到飞书群
4. **记录**：将已推送邮件 ID 保存到 `seen_ids.json`

## 常见问题

**Q: 提示 himalaya 连接失败？**
A: 检查 config.toml 中的邮箱地址和授权码是否正确，确认 IMAP 服务已开启。

**Q: 飞书推送失败？**
A: 运行 `lark-cli config show` 确认已登录，检查 chat-id 是否正确，确认机器人已加入目标群聊。

**Q: 首次启动会推送所有历史邮件吗？**
A: 不会。首次运行时会将当前收件箱中的邮件标记为已读，只推送之后的新邮件。
