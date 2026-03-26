# VLN Paper Survey 部署指南（Python + Cron + 飞书）

## 方案说明

使用 Python 脚本 + cron 定时任务 + 飞书 webhook 通知，不依赖 Claude Code RemoteTrigger。

## 前置条件

### 1. Python 环境

需要 Python 3.8+，安装依赖：

```bash
cd docs/09_research/vln_paper_survey
pip install anthropic requests python-dotenv
```

### 2. 飞书 Webhook

在飞书群聊中添加机器人，获取 webhook URL。

### 3. Claude API Key

从 https://console.anthropic.com/ 获取 API key。

## 部署步骤

### Step 1: 配置环境变量

```bash
cd docs/09_research/vln_paper_survey
cp .env.example .env
```

编辑 `.env` 文件，填入：
- `FEISHU_WEBHOOK_URL`: 飞书机器人 webhook URL
- `ANTHROPIC_API_KEY`: Claude API key

### Step 2: 测试脚本

```bash
python survey_workflow.py
```

应该看到输出并收到飞书通知。

### Step 3: 配置 cron 定时任务

```bash
crontab -e
```

添加以下行（每周一上午 9:00 执行）：

```cron
0 9 * * 1 cd /mnt/yczhou11/Kinbot_OODA/docs/09_research/vln_paper_survey && /usr/bin/python3 survey_workflow.py >> workflow.log 2>&1
```

保存退出。验证 cron 任务：

```bash
crontab -l
```

### Step 4: 查看日志

```bash
tail -f docs/09_research/vln_paper_survey/workflow.log
```

## 当前状态

**注意**：当前 `survey_workflow.py` 是最小骨架，仅包含：
- papers.json 加载和保存
- 飞书通知发送
- 基础错误处理

**完整实现需要补充**：
- 论文搜索（WebSearch API 或 Semantic Scholar API）
- PDF 下载和解析
- 使用 Claude API 进行论文审查
- 生成对比表和 Markdown 报告
- Git commit 和 push

你可以选择：
1. 让我继续实现完整的 Python 版本
2. 保持当前骨架，手动补充逻辑
3. 回到 Claude Code RemoteTrigger 方案（需要 claude login）

## 故障排查

### 问题：飞书通知未收到

检查 webhook URL 是否正确，测试：

```bash
curl -X POST $FEISHU_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"msg_type":"text","content":{"text":"测试消息"}}'
```

### 问题：cron 任务未执行

检查 cron 日志：

```bash
grep CRON /var/log/syslog
```

确保脚本路径和 Python 路径正确。
