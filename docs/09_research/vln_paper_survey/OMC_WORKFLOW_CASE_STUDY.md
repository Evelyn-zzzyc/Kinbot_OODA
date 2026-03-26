# OMC 工具链实战案例：VLN 论文自动调研系统

## 案例概述

**目标**：搭建一个全自动的 VLN/VLA 论文筛选、审查与对比工作流

**时间**：2026-03-26

**使用工具**：oh-my-claudecode (OMC) 三阶段工具链
- Deep Interview（需求澄清）
- Ralplan（共识规划）
- Autopilot（自动执行）

**成果**：从模糊想法到可运行的自动化系统，全程 AI 辅助完成

---

## 第一阶段：Deep Interview - 需求澄清

### 初始需求（模糊）

```
我想要搭建一个 agent 或者工作流，来帮我筛选最新的和 vln 视觉语言导航相关的优秀论文，
下载下来，进行详细的审查，并且能自动整合不同方案的信息进行汇总和对比
```

### Deep Interview 过程

通过 8 轮 Socratic 提问，逐步澄清需求：

**Round 1**: 筛选标准？
- 回答：广泛覆盖 VLN/VLA 前沿

**Round 2**: 论文来源？
- 回答：只看顶会发表（CVPR, ICLR, NeurIPS, ICRA, CoRL, ECCV, AAAI, RSS）

**Round 3**: 审查深度？
- 回答：两阶段——先快速筛选，再深度审查重点论文

**Round 4**: 运行方式？
- 回答：全自动定时执行

**Round 5**: 输出格式？
- 回答：结构化数据（JSON）+ Markdown 报告双层

**Round 6**: 对比维度？
- 回答：技术方案、Benchmark 性能、Kinbot 关联度、工程化可行性、优劣势简评

**Round 7**: 技术栈？
- 回答：Claude Code 定时任务

**Round 8**: 成功标准？
- 回答：文档更新 + 推送通知

### 输出成果

**最终明确度**：82.5%（模糊度 17.5%，低于 20% 阈值）

**生成文档**：`.omc/specs/deep-interview-vln-paper-workflow.md`
- 明确的目标陈述
- 清晰的约束条件
- 可测试的验收标准
- 完整的技术上下文
- 实体本体论（8 个核心实体）

---

## 第二阶段：Ralplan - 共识规划

### 三方评审机制

**Planner** → 创建初始实现计划
**Architect** → 架构审查与改进建议
**Critic** → 质量标准验证

### 关键设计决策

**1. 最小可行实现原则**
- 使用 Claude Code 原生能力（RemoteTrigger + WebSearch + WebFetch + PDF Read）
- 不引入外部框架，降低维护成本

**2. 两阶段渐进审查**
- 第一阶段：快速筛选，生成结构化摘要
- 第二阶段：深度审查，每次最多 5 篇（控制成本和时间）

**3. 增量更新 + 检查点恢复**
- 每次只处理新论文
- 阶段性 commit 确保失败可恢复

**4. 结构化优先**
- JSON 为底层数据源（含 schema 版本号）
- Markdown 报告从 JSON 自动生成

### Architect 改进建议（已整合）

- ✅ 阶段性 commit 检查点机制
- ✅ 单次深审上限 5 篇
- ✅ Semantic Scholar API 作为补充论文源
- ✅ papers.json 增加 schema_version 和格式校验
- ✅ 对比维度拆分为核心 5 维 + 可选 2 维

### Critic 质量验证（已通过）

- ✅ 原则-选项一致性
- ✅ 替代方案公平性
- ✅ 风险缓解清晰度
- ✅ 可测试验收标准
- ✅ 具体验证步骤

### 输出成果

**生成文档**：`.omc/plans/ralplan-vln-paper-workflow.md`
- 完整的实现计划（4 个 Phase）
- ADR（架构决策记录）
- 验收标准映射表

---

## 第三阶段：Autopilot - 自动执行

### 执行策略调整

**原计划**：使用 Claude Code RemoteTrigger
**实际调整**：Python + cron + Feishu webhook
- 原因：RemoteTrigger 认证问题
- 用户建议：使用飞书通知，更符合实际需求

### 实现过程

**Phase 0 & 1**：跳过（已由 deep-interview + ralplan 完成）

**Phase 2**：执行实现
1. 创建目录结构
   ```
   vln_paper_survey/
   ├── data/
   │   ├── papers.json
   │   └── reviews/
   ├── reports/
   │   ├── latest_screening.md
   │   ├── changelog.md
   │   └── comparison_table.md
   ├── survey_workflow.py
   ├── .env
   └── README.md
   ```

2. 实现核心功能
   - 论文搜索（Semantic Scholar API + 测试数据模式）
   - 三级去重（DOI > 标题归一化 > URL）
   - 第一阶段筛选（Claude API + 关键词回退）
   - 第二阶段深度审查（最多 5 篇/次）
   - 报告生成（Markdown）
   - Git 分支管理
   - 飞书通知

**Phase 3**：QA 循环
- 修复 NameError（函数位置错误）
- 修复 FileNotFoundError（目录缺失）
- 修复 Git 操作导致文件消失（分支切换问题）
- 优化分支策略（使用固定 vln-survey 分支）

**Phase 4**：验证（跳过正式验证，用户直接测试）

**Phase 5**：清理（待完成）

### 关键问题与解决

**问题 1**：Semantic Scholar API 429 速率限制
- 解决：添加 USE_TEST_DATA 模式，支持 API key，减少查询限制

**问题 2**：Git 操作后文件消失
- 原因：工作流切换回原分支导致文件不可见
- 解决：使用固定 vln-survey 分支，不切换回去

**问题 3**：临时分支过多
- 原因：每次运行创建带时间戳的新分支
- 解决：改用固定分支名 vln-survey

---

## 最终成果

### 功能清单

✅ **自动论文发现**
- 支持 8 个顶会（CVPR, ICLR, NeurIPS, ICRA, CoRL, ECCV, AAAI, RSS）
- Semantic Scholar API 集成
- 智能去重（DOI/标题/URL）

✅ **两阶段审查**
- 第一阶段：结构化摘要 + 相关性评分
- 第二阶段：深度审查（最多 5 篇/次）

✅ **自动报告生成**
- latest_screening.md（最新筛选）
- changelog.md（变更记录）
- comparison_table.md（对比表）

✅ **Git 集成**
- 自动创建 vln-survey 分支
- 阶段性 commit
- 失败可恢复

✅ **通知机制**
- 飞书 webhook 集成
- 运行摘要推送

### 文件结构

```
docs/09_research/vln_paper_survey/
├── data/
│   ├── papers.json              # 论文数据库（schema v1.0）
│   ├── reviews/                 # 单篇审查报告
│   │   └── {paper_id}.json
│   └── comparison.json          # 跨论文对比数据
├── reports/
│   ├── latest_screening.md      # 最新筛选报告
│   ├── changelog.md             # 变更记录
│   └── comparison_table.md      # 对比汇总表
├── survey_workflow.py           # 主工作流脚本
├── .env                         # 配置文件（Feishu webhook）
├── .env.example                 # 配置模板
├── README.md                    # 说明文档
├── DEPLOYMENT.md                # 部署指南
└── trigger_prompt.md            # 原 RemoteTrigger prompt（参考）
```

### 配置说明

**.env 文件**：
```bash
# Feishu webhook URL
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# Claude API key (optional, for deep review)
CLAUDE_API_KEY=sk-ant-xxx

# Semantic Scholar API key (optional, for higher rate limit)
SEMANTIC_SCHOLAR_API_KEY=xxx

# Use test data for development
USE_TEST_DATA=true
```

### 运行方式

**手动运行**：
```bash
cd docs/09_research/vln_paper_survey
python3 survey_workflow.py
```

**定时运行**（cron）：
```bash
# 每周一上午 9 点执行
0 9 * * 1 cd /path/to/vln_paper_survey && python3 survey_workflow.py >> cron.log 2>&1
```

---

## 经验总结

### OMC 工具链的价值

**1. 需求澄清的重要性**
- 初始需求往往模糊不清
- Deep Interview 通过 Socratic 提问逐步澄清
- 数学化的模糊度评分确保质量门槛

**2. 多方评审机制**
- Planner 提供初始方案
- Architect 从架构角度审查
- Critic 从质量标准验证
- 三方共识确保方案可行性

**3. 灵活调整策略**
- 原计划使用 RemoteTrigger
- 遇到认证问题后快速调整为 Python + cron
- 保持核心功能不变，调整实现方式

### 关键成功因素

**1. 分阶段实现**
- 先实现核心功能（搜索、筛选）
- 再添加高级功能（深度审查、报告）
- 最后优化细节（Git 分支、通知）

**2. 测试数据模式**
- 开发阶段使用测试数据
- 避免 API 速率限制
- 加快迭代速度

**3. 检查点恢复机制**
- 阶段性 Git commit
- 失败后可从检查点恢复
- 提高系统健壮性

### 改进空间

**1. 深度审查功能**
- 当前使用关键词回退（无 Claude API key 时）
- 可集成真实的 Claude API 进行深度分析

**2. 对比表生成**
- comparison_table.md 功能待完善
- 需要实现跨论文的多维度对比

**3. 错误处理**
- 增强网络请求的重试机制
- 添加更详细的日志记录

---

## 时间线

- **2026-03-26 14:00** - 开始 Deep Interview
- **2026-03-26 14:30** - 完成需求澄清（8 轮，17.5% 模糊度）
- **2026-03-26 15:00** - Ralplan 共识规划
- **2026-03-26 15:30** - 开始 Autopilot 执行
- **2026-03-26 16:00** - 完成核心功能实现
- **2026-03-26 16:10** - 修复 Git 分支问题，系统可用

**总耗时**：约 2 小时 10 分钟

---

## 结论

通过 OMC 三阶段工具链（Deep Interview → Ralplan → Autopilot），成功将一个模糊的想法转化为可运行的自动化系统。整个过程展示了：

1. **需求澄清的价值**：从 100% 模糊度降到 17.5%
2. **多方评审的必要性**：Planner/Architect/Critic 共识确保质量
3. **灵活调整的重要性**：遇到问题快速调整实现方案
4. **分阶段实现的优势**：逐步构建，持续验证

这个案例可以作为使用 OMC 工具链的参考模板。
