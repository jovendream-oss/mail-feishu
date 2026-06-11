// send_feishu.js - 读取 JSON 文件，通过 lark-cli 发送飞书消息
// 用法: node send_feishu.js <json文件路径> <user_id>
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');

const jsonFile = process.argv[2];
const userId = process.argv[3];

if (!jsonFile || !userId) {
  console.error('Usage: node send_feishu.js <jsonFile> <userId>');
  process.exit(1);
}

const content = fs.readFileSync(jsonFile, 'utf-8');
const runJs = path.join(process.env.APPDATA || '', 'npm', 'node_modules', '@larksuite', 'cli', 'scripts', 'run.js');

const args = [runJs, 'im', '+messages-send', '--as', 'user', '--user-id', userId, '--content', content];

const child = execFile(process.execPath, args, {
  timeout: 20000,
  maxBuffer: 1024 * 1024,
}, (error, stdout, stderr) => {
  if (error) {
    console.error(stderr || error.message);
    process.exit(1);
  }
  process.stdout.write(stdout);
});
