# VLN/VLA 论文自动筛选、审查与对比工作流

## 概述

全自动 VLN（视觉语言导航）和 VLA（视觉语言动作）领域论文调研工作流。通过 Python + cron 定时执行，自动从顶会论文中筛选、审查和对比最新研究进展。

## 快速开始

### 手动运行
```bash
cd docs/09_research/vln_paper_survey
python3 survey_workflow.py
```

### 定时运行（cron）
```bash
# 每周一上午 9 点执行
0 9 * * 1 cd /path/to/vln_paper_survey && python3 survey_workflow.py >> cron.log 2>&1
```

### 查看待深审论文
```bash
python3 scripts/list_pending.py
```

### 下载论文 PDF
```bash
python3 scripts/download_pdfs.py
```

### 深度审查（手动触发）
```bash
# 生成审查提示
python3 scripts/prepare_review.py <paper_id>
# 将输出的提示发给 Claude，Claude 会生成审查报告
```

## 目录结构

```
vln_paper_survey/
├── survey_workflow.py          # 主工作流
├── conference_dates.json       # 会议时间配置
├── scripts/
│   ├── list_pending.py        # 列出待深审论文
│   ├── prepare_review.py      # 生成审查提示
│   └── download_pdfs.py       # 下载论文 PDF
├── data/
│   ├── papers.json            # 论文数据库
│   └── reviews/               # 审查报告
├── pdfs/                      # 论文 PDF（已下载 15/19 篇）
├── reports/
│   ├── latest_screening.md    # 筛选报告
│   └── changelog.md           # 变更记录
├── .env                       # 配置文件（Feishu webhook）
└── .env.example               # 配置模板
```

## 时间过滤规则

系统只关注 **2025 年 6 月之后** 发表的论文。

**会议时间配置**（`conference_dates.json`）：
- ✅ CVPR 2025: 6月11-15日
- ✅ NeurIPS 2025: 12月
- ❌ ICLR 2025: 4月（已排除）
- ✅ 2026年所有会议

**预印本处理**：
- arXiv 论文保留但标注为"预印本参考"
- 报告中单独分类显示

## 工作流程

1. **自动搜索**：每周搜索新论文（Semantic Scholar API）
2. **第一阶段筛选**：关键词匹配评分
3. **标记待深审**：评分 ≥0.7 的论文
4. **手动深度审查**：你触发时 Claude 帮你完成
5. **生成报告**：自动更新 Markdown 报告
6. **Git 提交**：提交到 `docs/vln-paper-survey` 分支
7. **飞书通知**：发送运行摘要

## 配置说明

### .env 文件

```bash
# 飞书通知
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# 使用真实 API
USE_TEST_DATA=false

# 网络代理（可选）
http_proxy=http://127.0.0.1:7893
https_proxy=http://127.0.0.1:7893
```

### conference_dates.json

添加新会议时间：

```json
{
  "conferences": {
    "新会议名": {
      "2025": {
        "date": "2025-XX-XX",
        "after_june_2025": true/false
      }
    }
  }
}
```

## 深度审查流程

1. 运行 `python3 scripts/list_pending.py` 查看待审论文
2. 选择一篇，运行 `python3 scripts/prepare_review.py <paper_id>`
3. 将输出的提示发给 Claude
4. Claude 会生成 JSON 格式的审查报告
5. 将报告保存到 `data/reviews/<paper_id>.json`
6. 运行工作流更新报告：`python3 survey_workflow.py`

## 常见问题

**Q: 为什么有些论文是 arXiv？**
A: arXiv 是预印本，论文可能还未正式发表。系统保留这些论文作为参考，并在报告中单独标注。

**Q: 如何调整筛选阈值？**
A: 修改 `survey_workflow.py` 中的 `screening_score >= 0.7`。

**Q: 深度审查需要 API key 吗？**
A: 不需要。深度审查是手动触发，由你和 Claude 协作完成。

**Q: 如何更新会议时间？**
A: 编辑 `conference_dates.json`，添加或更新会议日期。

## 对比维度

**核心维度**：
- 技术方案对比
- Benchmark 性能对比
- 与 Kinbot 的关联度
- 工程化可行性
- 优劣势简评

**可选维度**：
- 真机实验与平台
- 建图能力

## 与 Kinbot 项目的关联

本工作流服务于 Kinbot OODA 项目的 VLN 技术路线。审查报告中的"Kinbot 关联度"维度评估每篇论文对项目的可借鉴性和可集成性。
