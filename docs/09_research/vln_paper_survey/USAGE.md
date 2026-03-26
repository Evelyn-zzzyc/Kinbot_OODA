# VLN 论文调研系统 - 使用指南

## 快速开始

### 1. 自动运行（定时任务）

```bash
# 每周一上午 9 点自动执行
# 在 crontab 中添加：
0 9 * * 1 cd /path/to/vln_paper_survey && python3 survey_workflow.py >> cron.log 2>&1
```

### 2. 手动运行

```bash
cd docs/09_research/vln_paper_survey
python3 survey_workflow.py
```

### 3. 查看待深审论文

```bash
python3 scripts/list_pending.py
```

输出示例：
```
待深审论文：2 篇

1. Towards Long-Horizon Vision-Language Navigation...
   会议：CVPR 2025
   评分：0.95
```

### 4. 深度审查（手动触发）

```bash
# 生成审查提示
python3 scripts/prepare_review.py CVPR_2025_long_horizon_vln

# 然后将输出的提示发给 Claude，Claude 会生成审查报告
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

## 文件结构

```
vln_paper_survey/
├── survey_workflow.py          # 主工作流
├── conference_dates.json       # 会议时间配置
├── scripts/
│   ├── list_pending.py        # 列出待深审论文
│   └── prepare_review.py      # 生成审查提示
├── data/
│   ├── papers.json            # 论文数据库
│   └── reviews/               # 审查报告
└── reports/
    ├── latest_screening.md    # 筛选报告
    └── changelog.md           # 变更记录
```

## 工作流程

1. **自动搜索**：每周搜索新论文（Semantic Scholar API）
2. **第一阶段筛选**：关键词匹配评分
3. **标记待深审**：评分 ≥0.7 的论文
4. **手动深度审查**：你触发时 Claude 帮你完成
5. **生成报告**：自动更新 Markdown 报告
6. **Git 提交**：提交到 `docs/vln-paper-survey` 分支
7. **飞书通知**：发送运行摘要

## 深度审查流程

当你需要深度审查论文时：

1. 运行 `python3 scripts/list_pending.py` 查看待审论文
2. 选择一篇，运行 `python3 scripts/prepare_review.py <paper_id>`
3. 将输出的提示发给 Claude
4. Claude 会生成 JSON 格式的审查报告
5. 将报告保存到 `data/reviews/<paper_id>.json`
6. 运行工作流更新报告：`python3 survey_workflow.py`

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

## 常见问题

**Q: 为什么有些论文是 arXiv？**
A: arXiv 是预印本，论文可能还未正式发表。系统保留这些论文作为参考，并在报告中单独标注。

**Q: 如何调整筛选阈值？**
A: 修改 `survey_workflow.py` 中的 `screening_score >= 0.7`。

**Q: 深度审查需要 API key 吗？**
A: 不需要。深度审查是手动触发，由你和 Claude 协作完成。

**Q: 如何更新会议时间？**
A: 编辑 `conference_dates.json`，添加或更新会议日期。

## 相关文档

- 实施计划：`.omc/plans/ralplan-vln-paper-workflow.md`
- 需求规格：`.omc/specs/deep-interview-vln-paper-workflow.md`
- OMC 案例：`OMC_WORKFLOW_CASE_STUDY.md`
