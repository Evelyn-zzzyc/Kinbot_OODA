#!/usr/bin/env python3
"""VLN Deep Review Helper - Prepare paper info for Claude review"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PAPERS_JSON = DATA_DIR / "papers.json"

def prepare_review_prompt(paper_id):
    """Generate review prompt for Claude"""
    with open(PAPERS_JSON, "r") as f:
        data = json.load(f)

    paper = next((p for p in data["papers"] if p["id"] == paper_id), None)
    if not paper:
        print(f"论文 {paper_id} 不存在")
        return

    prompt = f"""请深度审查以下 VLN 论文：

**标题**：{paper['title']}
**作者**：{', '.join(paper.get('authors', []))}
**会议**：{paper.get('venue')} {paper.get('year')}
**摘要**：{paper.get('abstract', 'N/A')}
**URL**：{paper.get('url', 'N/A')}

请提取以下信息并生成 JSON 格式的审查报告：

1. **技术方案**：模型架构、训练策略、输入输出接口
2. **Benchmark 结果**：R2R、REVERIE、RxR、SOON 等评测数据
3. **Kinbot 关联度**：对 27B Teacher + 4B Student 路线的可借鉴性
4. **工程化可行性**：模型大小、推理速度、是否开源、训练数据规模
5. **优劣势**：核心创新点和局限性
6. **简评**：一句话总结

输出格式参考 data/reviews/ 目录下的 JSON schema。
"""

    print(prompt)
    return prompt

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 prepare_review.py <paper_id>")
        sys.exit(1)

    prepare_review_prompt(sys.argv[1])
