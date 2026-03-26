#!/usr/bin/env python3
"""VLN Deep Review - Manual deep review trigger for pending papers"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PAPERS_JSON = DATA_DIR / "papers.json"

def list_pending_papers():
    """List papers pending deep review"""
    with open(PAPERS_JSON, "r") as f:
        data = json.load(f)

    pending = [p for p in data["papers"] if p.get("stage") == "pending_deep_review"]

    if not pending:
        print("没有待深审的论文")
        return []

    print(f"待深审论文：{len(pending)} 篇\n")
    for i, p in enumerate(pending, 1):
        print(f"{i}. {p['title']}")
        print(f"   会议：{p.get('venue')} {p.get('year')}")
        print(f"   评分：{p.get('screening_score', 0):.2f}")
        print(f"   URL：{p.get('url', 'N/A')}\n")

    return pending

if __name__ == "__main__":
    list_pending_papers()
