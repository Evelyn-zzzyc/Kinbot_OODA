# VLN/VLA 论文自动筛选、审查与对比工作流

## 概述

本目录包含一个全自动的 VLN（视觉语言导航）和 VLA（视觉语言动作）领域论文调研工作流。工作流通过 Claude Code RemoteTrigger 定时执行，自动从顶会论文中筛选、审查和对比最新研究进展。

## 目录结构

```
vln_paper_survey/
├── data/
│   ├── papers.json              # 所有已发现论文的结构化数据
│   ├── reviews/                 # 单篇审查报告 (JSON)
│   └── comparison.json          # 跨论文对比数据
├── reports/
│   ├── latest_screening.md      # 最新一期筛选报告
│   ├── deep_reviews/            # 深度审查 Markdown
│   ├── comparison_table.md      # 跨论文对比汇总表
│   └── changelog.md             # 每次运行的变更记录
├── trigger_prompt.md            # RemoteTrigger 执行的完整工作流指令
└── README.md                    # 本文档
```

## 工作流说明

### 时间过滤规则

本工作流关注 **2025 年 6 月之后** 发表的 VLN/VLA 论文。

**会议时间参考**：
- ✅ CVPR 2025: 2025年6月11-15日（符合）
- ✅ NeurIPS 2025: 2025年12月（符合）
- ❌ ICLR 2025: 2025年4月24-28日（早于6月，已排除）
- ✅ 2026年所有会议（符合）

**预印本处理**：
- arXiv/bioRxiv 论文保留作为参考
- 报告中单独标注"预印本参考"
- 无法确定正式发表时间的论文会特别标注

### 运行频率
- 定时执行：每周一上午 9:00（通过 cron）
- 手动触发：`python3 survey_workflow.py`

### 执行流程

**阶段 A — 搜索与发现**
- 从顶会（CVPR, ICLR, NeurIPS, ICRA, CoRL, ECCV, AAAI, RSS）搜索最新 VLN/VLA 论文
- 使用 WebSearch + Semantic Scholar API 双源搜索
- 去重后写入 papers.json

**阶段 B — 第一阶段筛选**
- 对每篇新论文生成结构化摘要
- 评估相关性打分（0-1）
- 筛选出 score >= 0.7 的论文进入深审队列

**阶段 C — 第二阶段深度审查**
- 每次运行最多深审 5 篇论文（超出部分排队）
- 提取技术方案、Benchmark 性能、Kinbot 关联度等维度
- 生成 JSON 数据 + Markdown 报告

**阶段 D — 跨论文对比汇总**
- 生成多维度对比表
- 更新 comparison_table.md 和 changelog.md

**阶段 E — 提交与通知**
- Git commit + push 所有变更
- 输出运行摘要

### 对比维度

**核心维度（必填）**：
- 技术方案对比
- Benchmark 性能对比
- 与 Kinbot 的关联度
- 工程化可行性
- 优劣势简评

**可选维度（有数据时填充）**：
- 真机实验与平台
- 建图能力

## 如何使用

### 查看最新结果
- 筛选报告：`reports/latest_screening.md`
- 对比汇总：`reports/comparison_table.md`
- 变更记录：`reports/changelog.md`

### 查看单篇论文详情
- JSON 数据：`data/reviews/{paper_id}.json`
- Markdown 报告：`reports/deep_reviews/{paper_id}.md`

### 手动触发运行
使用 RemoteTrigger API 或 Claude Code CLI：
```bash
# 查看 trigger 列表
claude trigger list

# 手动运行
claude trigger run <trigger_id>
```

## 技术细节

### 数据 Schema
- papers.json: schema_version 1.0，包含 DOI 字段用于去重
- 论文 stage: screening → pending_deep_review → deep_review
- 单次深审上限 5 篇，超出自动排队

### 容错机制
- 阶段性 commit：每个阶段完成后立即 commit，失败可恢复
- 搜索源降级：某个源失败不阻塞流程
- PDF 获取降级：无法获取 PDF 时降级为页面内容

### 与 Kinbot 项目的关联
本工作流服务于 Kinbot OODA 项目的 VLN 技术路线（27B Teacher + 4B Student 蒸馏）。审查报告中的"Kinbot 关联度"维度评估每篇论文对项目的可借鉴性和可集成性。

## 维护说明

### 首次部署
1. 确保已完成 `claude login` 认证
2. 使用 RemoteTrigger API 创建定时任务
3. 手动触发一次验证流程

### 调整筛选阈值
如果发现筛选过严或过松，可在 trigger_prompt.md 中调整 `screening_score >= 0.7` 的阈值。

### 调整深审数量
如果需要加快或减慢深审速度，可在 trigger_prompt.md 阶段 C 中调整单次上限（当前 5 篇）。

## 相关文档
- 实施计划：`../../.omc/plans/ralplan-vln-paper-workflow.md`
- 需求规格：`../../.omc/specs/deep-interview-vln-paper-workflow.md`
- VLN 技术路线：`../vln_model_design/kinbot_vln_model_detailed_design.md`
