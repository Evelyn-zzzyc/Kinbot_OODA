# VLN/VLA 论文自动筛选、审查与对比工作流

你是一个论文调研助手，负责自动筛选、审查和对比 VLN（视觉语言导航）和 VLA（视觉语言动作）领域的最新顶会论文。

工作目录：本项目根目录
数据目录：`docs/09_research/vln_paper_survey/`

## 执行前检查

1. 读取 `docs/09_research/vln_paper_survey/data/papers.json`
2. 校验 `schema_version` 字段存在且为 `"1.0"`，校验 `papers` 字段为数组
3. 如果校验失败，输出错误日志并终止执行
4. 记录已知论文列表（用于去重）

## 阶段 A — 搜索与发现

### A1: WebSearch 搜索

对以下每个会议，用 WebSearch 搜索最新 VLN/VLA 论文：

会议列表：CVPR 2025, CVPR 2026, ICLR 2025, ICLR 2026, NeurIPS 2025, ICRA 2025, ICRA 2026, CoRL 2025, ECCV 2024, AAAI 2025, AAAI 2026, RSS 2025

搜索关键词组合（每个会议至少搜索以下 3 组）：
- `"{会议名} {年份} vision language navigation"`
- `"{会议名} {年份} embodied navigation VLN"`
- `"{会议名} {年份} visual language action VLA robot navigation"`

补充关键词（可选，用于扩大覆盖）：
- semantic navigation, object goal navigation, image goal navigation
- embodied agent navigation, instruction following navigation

### A2: Semantic Scholar API 补充搜索

用 WebFetch 调用 Semantic Scholar API 作为补充：

```
https://api.semanticscholar.org/graph/v1/paper/search?query=vision+language+navigation+OR+embodied+navigation+OR+VLN+OR+VLA&year=2024-2026&fields=title,authors,venue,year,abstract,externalIds,url&limit=100
```

如果 API 返回错误或为空，跳过此步继续（不阻塞流程）。

### A3: 去重与新论文识别

对所有搜索结果，按以下优先级去重：
1. 如果有 DOI，优先用 DOI 去重
2. 否则用 title 归一化匹配（转小写、去标点、去多余空格）
3. 最后用 url 去重

与 papers.json 中已知论文对比，识别新论文。

### A4: 写入新论文并 commit

将新论文元数据写入 papers.json，字段包括：
- `id`: 生成规则 `{venue}_{year}_{title前3个单词snake_case}`，如有冲突加数字后缀
- `title`, `authors`, `venue`, `year`, `abstract`, `url`, `pdf_url`（如有）, `doi`（如有）
- `keywords`: 从 abstract 提取的关键词
- `discovered_at`: 当前时间 ISO8601
- `stage`: 初始为 `"screening"`
- `screening_score`: 初始为 0.0
- `relevance_to_kinbot`: 初始为 `null`

**检查点 commit**：
```bash
git add docs/09_research/vln_paper_survey/data/papers.json
git commit -m "vln-survey: add {N} new papers from {venues}"
```

---

## 阶段 B — 第一阶段筛选

### B1: 对每篇新论文生成筛选摘要

对 `stage: "screening"` 且无 review 文件的论文：

1. 用 WebFetch 获取论文页面或摘要（如果 pdf_url 可用，尝试用 Read 读取 PDF 前 2 页）
2. 生成结构化筛选摘要，评估相关性打分（0-1）：
   - 0.9-1.0: 核心 VLN/VLA 方法论文，直接相关
   - 0.7-0.9: 相关领域（embodied AI, semantic navigation, instruction following）
   - 0.5-0.7: 边缘相关（vision-language 但非导航，或导航但非 VL）
   - 0.0-0.5: 不相关

3. 写入 `data/reviews/{paper_id}.json`：
```json
{
  "paper_id": "...",
  "stage": "screening",
  "reviewed_at": "ISO8601",
  "summary": "1-2 句话概括论文核心内容",
  "screening_score": 0.85,
  "screening_rationale": "为什么给这个分数"
}
```

### B2: 标记待深审论文

筛选出 `screening_score >= 0.7` 的论文，在 papers.json 中将其 `stage` 更新为 `"pending_deep_review"`。

**检查点 commit**：
```bash
git add docs/09_research/vln_paper_survey/data/reviews/
git add docs/09_research/vln_paper_survey/data/papers.json
git commit -m "vln-survey: screening {M} papers, {K} pending deep review"
```

---

## 阶段 C — 第二阶段深度审查

### C1: 选择本次深审论文

从 papers.json 中筛选 `stage: "pending_deep_review"` 的论文，**排除已有 `stage: "deep_review"` review 文件的论文**（恢复路径），按 `screening_score` 降序排序，取前 **5 篇**（单次运行上限）。

### C2: 逐篇深度审查

对每篇论文：

1. 尝试获取 PDF 并用 Read 工具读取（如果无法获取 PDF，用 WebFetch 获取论文页面详细内容）
2. 生成深度审查报告，提取以下维度：

**核心维度（必填）**：
- 技术方案：模型架构、训练策略、输入输出接口、部署方式
- Benchmark 性能：R2R, REVERIE, RxR, SOON 等标准评测结果
- Kinbot 关联度：可借鉴性、可集成性（参考 Kinbot 27B Teacher + 4B Student 蒸馏路线）
- 工程化可行性：模型大小、推理速度、训练数据量、是否开源
- 优劣势简评

**可选维度（有数据时填充）**：
- 真机实验与平台：是否有真机实验、实验平台类型
- 建图能力：是否能建图、建图方式

3. 更新 `data/reviews/{paper_id}.json`（完整 schema，包含上述所有维度）
4. 生成 Markdown 深度审查报告到 `reports/deep_reviews/{paper_id}.md`
5. 在 papers.json 中将该论文 `stage` 更新为 `"deep_review"`

**逐篇 commit**（每完成一篇即 commit）：
```bash
git add docs/09_research/vln_paper_survey/data/reviews/{paper_id}.json
git add docs/09_research/vln_paper_survey/reports/deep_reviews/{paper_id}.md
git add docs/09_research/vln_paper_survey/data/papers.json
git commit -m "vln-survey: deep review {paper_title}"
```

---

## 阶段 D — 跨论文对比汇总

### D1: 读取所有深审数据

读取所有 `stage: "deep_review"` 的 review JSON 文件。

### D2: 生成对比数据

更新 `data/comparison.json`，包含：
- 核心 5 维对比表（技术方案、Benchmark、Kinbot 关联度、工程化、优劣势）
- 可选 2 维对比表（真机实验、建图能力）

### D3: 生成 Markdown 报告

生成/更新以下文件：
- `reports/comparison_table.md`：多维度对比表
- `reports/latest_screening.md`：本次筛选报告（新发现论文列表、筛选结果）
- `reports/changelog.md`：追加本次运行记录（时间、新增论文数、深审论文数、剩余 pending 数）

---

## 阶段 E — 最终提交与通知

### E1: 最终 commit

```bash
git add docs/09_research/vln_paper_survey/data/comparison.json
git add docs/09_research/vln_paper_survey/reports/
git commit -m "vln-survey: update comparison table and reports"
```

### E2: Push 到远程

```bash
git push
```

### E3: 输出运行摘要

输出格式：
```
VLN 论文调研工作流执行完成
- 新发现论文：{N} 篇
- 筛选论文：{M} 篇
- 深度审查：{K} 篇
- 剩余待深审：{L} 篇
- 对比表已更新：{comparison_table.md}
```

---

## 错误处理

- 如果 papers.json schema 校验失败，终止并输出错误
- 如果某个搜索源失败（WebSearch 无结果、Semantic Scholar API 报错），跳过该源继续
- 如果某篇论文 PDF 无法获取，降级为 WebFetch 页面内容
- 如果 git push 失败（冲突），输出警告但不阻塞（下次运行会重试）

---

## 注意事项

1. 本 prompt 由 Claude Code RemoteTrigger 定时执行（每周一上午 9 点）
2. 首次运行前需确保已完成 `claude login` 认证
3. 去重逻辑优先级：DOI > title 归一化 > url
4. 单次深审上限 5 篇，超出部分自动排队到下次运行
5. 阶段性 commit 确保失败可恢复，下次运行会跳过已完成的论文
