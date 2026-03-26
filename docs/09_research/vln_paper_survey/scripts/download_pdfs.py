#!/usr/bin/env python3
"""Download PDFs for papers"""

import json
import os
import requests
from pathlib import Path
import time

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = BASE_DIR / "pdfs"
PAPERS_JSON = DATA_DIR / "papers.json"

# Create PDF directory
PDF_DIR.mkdir(exist_ok=True)

def download_pdf(paper):
    """Download PDF for a paper"""
    paper_id = paper['id']
    pdf_path = PDF_DIR / f"{paper_id}.pdf"

    if pdf_path.exists():
        print(f"已存在: {paper['title'][:50]}...")
        return True

    pdf_url = paper.get('pdf_url', '')

    # If pdf_url is just an arXiv ID (no http), construct full URL
    if pdf_url and not pdf_url.startswith('http'):
        pdf_url = f"https://arxiv.org/pdf/{pdf_url}.pdf"

    # Try to extract from main URL
    if not pdf_url:
        url = paper.get('url', '')

    # Try to construct valid arXiv PDF URL
    if not pdf_url and url:
        if 'arxiv.org' in url:
            arxiv_id = url.split('/')[-1]
            if not arxiv_id.endswith('.pdf'):
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            else:
                pdf_url = url
        elif url.replace('.', '').isdigit(): # It might just be an arXiv ID
            pdf_url = f"https://arxiv.org/pdf/{url}.pdf"

    # Check externalIds from Semantic Scholar API
    if not pdf_url and 'externalIds' in paper:
        arxiv_id = paper['externalIds'].get('ArXiv')
        if arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    if not pdf_url:
        print(f"无 PDF URL: {paper['title'][:50]}... (来源: {paper.get('venue')})")
        return False

    try:
        print(f"下载中: {paper['title'][:50]}... ({pdf_url})")

        # Set proxy
        proxies = {}
        if os.getenv("http_proxy"):
            proxies["http"] = os.getenv("http_proxy")
            proxies["https"] = os.getenv("https_proxy", os.getenv("http_proxy"))

        # Headers to look like a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        resp = requests.get(pdf_url, timeout=30, proxies=proxies if proxies else None, headers=headers)
        resp.raise_for_status()

        with open(pdf_path, 'wb') as f:
            f.write(resp.content)

        print(f"✓ 已下载: {paper_id}.pdf")
        return True

    except Exception as e:
        print(f"✗ 下载失败: {e}")
        return False

def main():
    with open(PAPERS_JSON, 'r') as f:
        data = json.load(f)

    # Download pending deep review papers first
    pending = [p for p in data['papers'] if p.get('stage') == 'pending_deep_review']
    others = [p for p in data['papers'] if p.get('stage') != 'pending_deep_review']

    print(f"待深审论文: {len(pending)} 篇")
    print(f"其他论文: {len(others)} 篇\n")

    success = 0
    failed = 0

    for paper in pending + others:
        if download_pdf(paper):
            success += 1
        else:
            failed += 1
        time.sleep(2)  # Rate limit

    print(f"\n完成: 成功 {success} 篇, 失败 {failed} 篇")

if __name__ == "__main__":
    main()
