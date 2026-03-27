#!/usr/bin/env python3
"""VLN/VLA Paper Survey Workflow - Automated paper screening and review"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env file
BASE_DIR = Path(__file__).parent
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# Configuration
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
PAPERS_JSON = DATA_DIR / "papers.json"
CONFERENCE_DATES_JSON = BASE_DIR / "conference_dates.json"
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK_URL", "")

def load_conference_dates():
    """Load conference dates configuration"""
    try:
        with open(CONFERENCE_DATES_JSON, "r") as f:
            return json.load(f)
    except:
        return {"conferences": {}, "cutoff_date": "2025-06-01"}

def is_after_cutoff(venue, year):
    """Check if conference is after June 2025 cutoff"""
    conf_data = load_conference_dates()
    if year >= 2026:
        return True
    if venue in conf_data["conferences"]:
        year_data = conf_data["conferences"][venue].get(str(year))
        if year_data:
            return year_data.get("after_june_2025", None)
    return None


def load_papers():
    """Load and validate papers.json"""
    if not PAPERS_JSON.exists():
        return {"schema_version": "1.0", "papers": [], "last_updated": None, "last_run_venues_checked": []}

    with open(PAPERS_JSON) as f:
        data = json.load(f)

    if data.get("schema_version") != "1.0":
        raise ValueError(f"Invalid schema version: {data.get('schema_version')}")

    return data

def save_papers(data):
    """Save papers.json"""
    data["last_updated"] = datetime.utcnow().isoformat() + "Z"
    with open(PAPERS_JSON, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def send_feishu_notification(message):
    """Send notification to Feishu webhook"""
    if not FEISHU_WEBHOOK:
        print("No Feishu webhook configured, skipping notification")
        return

    import requests
    payload = {
        "msg_type": "text",
        "content": {"text": message}
    }
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        resp.raise_for_status()
        print("Feishu notification sent")
    except Exception as e:
        print(f"Failed to send Feishu notification: {e}")

def search_papers_semantic_scholar():
    """Search papers from Semantic Scholar API"""
    import requests
    import time

    # Setup proxy if configured
    proxies = {}
    if os.getenv("http_proxy"):
        proxies["http"] = os.getenv("http_proxy")
        proxies["https"] = os.getenv("https_proxy", os.getenv("http_proxy"))

    # API key (optional, helps with rate limits)
    headers = {}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    url = "https://api.semanticscholar.org/graph/v1/paper/search"

    # Try multiple queries with delay
    queries = [
        "vision language navigation",
        "VLN embodied navigation",
        "visual language action robot"
    ]

    all_papers = []
    seen_ids = set()
    failed_queries = 0

    for i, query in enumerate(queries):
        if i > 0:
            time.sleep(2)  # Rate limit delay

        params = {
            "query": query,
            "year": "2025-2026",
            "fields": "title,authors,venue,year,abstract,externalIds,url,paperId",
            "limit": 20  # Reduced to avoid rate limits
        }

        try:
            resp = requests.get(url, params=params, timeout=30,
                              proxies=proxies if proxies else None,
                              headers=headers)
            resp.raise_for_status()
            data = resp.json()
            papers = data.get("data", [])

            for paper in papers:
                paper_id = paper.get("paperId")
                year = paper.get("year")
                # Filter: only 2025 June onwards (2025 year >= June, or 2026+)
                if year and year >= 2025:
                    # For 2025, check if conference is after June cutoff
                    if year == 2025:
                        venue = paper.get('venue', '')
                        after_cutoff = is_after_cutoff(venue, year)
                        if after_cutoff is False:
                            continue
                    if paper_id and paper_id not in seen_ids:
                        seen_ids.add(paper_id)
                        all_papers.append(paper)

            print(f"Query '{query}': found {len(papers)} papers")
        except requests.exceptions.HTTPError as e:
            failed_queries += 1
            if e.response.status_code == 429:
                print(f"Query '{query}': rate limited (429). Consider adding SEMANTIC_SCHOLAR_API_KEY to .env")
            else:
                print(f"Query '{query}' failed: {e}")
            continue
        except Exception as e:
            failed_queries += 1
            print(f"Query '{query}' failed: {e}")
            continue

    if failed_queries == len(queries):
        raise RuntimeError(f"All {len(queries)} Semantic Scholar queries failed. Check network/API status.")

    print(f"Total unique papers from Semantic Scholar: {len(all_papers)} ({failed_queries}/{len(queries)} queries failed)")
    return all_papers

def normalize_title(title):
    """Normalize title for deduplication"""
    import re
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def deduplicate_papers(new_papers, existing_papers):
    """Deduplicate papers by DOI > normalized title > URL"""
    existing_dois = {p.get("doi") for p in existing_papers if p.get("doi")}
    existing_titles = {normalize_title(p["title"]) for p in existing_papers}
    existing_urls = {p.get("url") for p in existing_papers if p.get("url")}

    unique_papers = []
    for paper in new_papers:
        # Check DOI
        doi = paper.get("externalIds", {}).get("DOI")
        if doi and doi in existing_dois:
            continue

        # Check normalized title
        norm_title = normalize_title(paper.get("title", ""))
        if norm_title in existing_titles:
            continue

        # Check URL
        url = paper.get("url")
        if url and url in existing_urls:
            continue

        unique_papers.append(paper)

    return unique_papers

def get_test_papers():
    """Generate test papers for development"""
    return [
        {
            "paperId": "test1",
            "title": "Vision-Language Navigation with Multimodal Transformers",
            "authors": [{"name": "Test Author 1"}, {"name": "Test Author 2"}],
            "venue": "CVPR",
            "year": 2025,
            "abstract": "We propose a novel approach for vision-language navigation using multimodal transformers...",
            "url": "https://example.com/paper1",
            "externalIds": {"DOI": "10.1234/test1"}
        },
        {
            "paperId": "test2",
            "title": "Embodied Agent Navigation with Language Grounding",
            "authors": [{"name": "Test Author 3"}],
            "venue": "ICLR",
            "year": 2025,
            "abstract": "This paper presents a method for embodied agents to navigate using natural language instructions...",
            "url": "https://example.com/paper2",
            "externalIds": {"DOI": "10.1234/test2"}
        }
    ]

def convert_to_paper_entry(paper):
    """Convert API result to papers.json entry"""
    import re

    title = paper.get("title", "Unknown")
    venue = paper.get("venue", "Unknown")
    year = paper.get("year", 2024)

    # Generate paper_id (sanitize venue to remove invalid filename chars)
    title_words = re.findall(r'\w+', title.lower())[:3]
    venue_safe = re.sub(r'[^\w\s-]', '', venue).replace(' ', '_')
    paper_id = f"{venue_safe}_{year}_{'_'.join(title_words)}"

    return {
        "id": paper_id,
        "title": title,
        "authors": [a.get("name", "") for a in paper.get("authors", [])],
        "venue": venue,
        "year": year,
        "abstract": paper.get("abstract", ""),
        "url": paper.get("url", ""),
        "pdf_url": paper.get("externalIds", {}).get("ArXiv", ""),
        "doi": paper.get("externalIds", {}).get("DOI", ""),
        "keywords": [],
        "discovered_at": datetime.utcnow().isoformat() + "Z",
        "stage": "screening",
        "screening_score": 0.0,
        "relevance_to_kinbot": None
    }

def screen_paper_with_claude(paper):
    """Screen a paper using Claude API"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Fallback: improved keyword matching with weighted scoring
        text = f"{paper['title']} {paper.get('abstract', '')}".lower()

        # Core keywords (high relevance)
        core_keywords = ["vln", "vision-language navigation", "vision language navigation"]
        # Related keywords (medium relevance)
        related_keywords = ["embodied navigation", "embodied agent", "visual navigation", "language grounding", "instruction following"]
        # Supporting keywords (lower relevance)
        support_keywords = ["natural language", "semantic navigation", "object goal", "robot navigation"]

        # Count matches
        core_match = any(kw in text for kw in core_keywords)
        related_count = sum(1 for kw in related_keywords if kw in text)
        support_count = sum(1 for kw in support_keywords if kw in text)

        # Calculate score
        if core_match:
            # Core VLN paper: 0.7 base + bonus for related/support
            score = 0.7 + (related_count * 0.05) + (support_count * 0.02)
        elif related_count >= 2:
            # Related paper: 0.5 base + bonus
            score = 0.5 + (related_count * 0.05) + (support_count * 0.02)
        elif related_count >= 1:
            # Tangentially related: 0.3 base + bonus
            score = 0.3 + (related_count * 0.05) + (support_count * 0.02)
        else:
            # Not relevant
            score = 0.1 + (support_count * 0.02)

        return {
            "screening_score": round(min(score, 1.0), 2),
            "summary": f"Paper about {paper['title'][:50]}...",
            "screening_rationale": "Keyword-based scoring (improved algorithm)"
        }

    # Use Claude API for screening
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        prompt = f"""Review this paper and assess its relevance to VLN/VLA research:

Title: {paper['title']}
Abstract: {paper.get('abstract', 'N/A')}

Score 0-1 based on:
- 0.9-1.0: Core VLN/VLA methodology
- 0.7-0.9: Related (embodied AI, semantic navigation)
- 0.5-0.7: Tangentially related
- 0.0-0.5: Not relevant

Output JSON: {{"score": 0.85, "summary": "brief summary", "rationale": "why this score"}}"""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        import json
        result = json.loads(response.content[0].text)
        return {
            "screening_score": result["score"],
            "summary": result["summary"],
            "screening_rationale": result["rationale"]
        }
    except Exception as e:
        print(f"Claude API screening failed: {e}")
        return {"screening_score": 0.5, "summary": "Screening failed", "screening_rationale": str(e)}

def generate_reports(papers_data):
    """Generate Markdown reports"""

    # Check PDF download status
    pdf_dir = BASE_DIR / "pdfs"
    pdf_dir.mkdir(exist_ok=True)
    total_papers = len(papers_data['papers'])
    downloaded_count = 0
    missing_pdfs = []

    for paper in papers_data['papers']:
        pdf_path = pdf_dir / f"{paper['id']}.pdf"
        if pdf_path.exists():
            downloaded_count += 1
        else:
            missing_pdfs.append({
                'title': paper['title'],
                'venue': paper.get('venue'),
                'reason': 'No PDF URL' if not paper.get('pdf_url') else 'Download failed'
            })

    # Generate latest_screening.md
    screening_md = f"""# VLN/VLA 论文筛选报告

生成时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

## 统计

- 总论文数：{len(papers_data['papers'])}
- 待深审：{len([p for p in papers_data['papers'] if p['stage'] == 'pending_deep_review'])}
- 已深审：{len([p for p in papers_data['papers'] if p['stage'] == 'deep_review'])}
- PDF 已下载：{downloaded_count}/{total_papers} 篇

## PDF 下载状态

"""

    if missing_pdfs:
        screening_md += f"⚠️ 缺失 {len(missing_pdfs)} 篇 PDF：\n\n"
        for m in missing_pdfs:
            screening_md += f"- **{m['title'][:60]}...** ({m['venue']}) - {m['reason']}\n"
        screening_md += "\n"
    else:
        screening_md += "✅ 所有论文 PDF 已下载\n\n"

    screening_md += "## 最新论文\n\n"
    for paper in papers_data['papers'][-10:]:
        screening_md += f"- [{paper['title']}]({paper['url']}) - {paper['venue']} {paper['year']} (score: {paper['screening_score']:.2f})\n"

    with open(REPORTS_DIR / "latest_screening.md", "w") as f:
        f.write(screening_md)

    # Generate changelog.md
    changelog_entry = f"\n## {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
    changelog_entry += f"- 新增论文：{len([p for p in papers_data['papers'] if p.get('discovered_at', '').startswith(datetime.utcnow().strftime('%Y-%m-%d'))])}\n"

    changelog_file = REPORTS_DIR / "changelog.md"
    if changelog_file.exists():
        with open(changelog_file, "r") as f:
            existing = f.read()
        with open(changelog_file, "w") as f:
            f.write(changelog_entry + existing)
    else:
        with open(changelog_file, "w") as f:
            f.write("# VLN Paper Survey Changelog\n" + changelog_entry)

    print("Reports generated")

def main():
    """Main workflow"""
    print("VLN Paper Survey Workflow")
    print("=" * 50)

    # Stage A: Search & Discovery
    print("\n[Stage A] Searching papers...")
    papers_data = load_papers()
    existing_papers = papers_data["papers"]
    print(f"Loaded {len(existing_papers)} existing papers")

    # Use test data for now (remove when API is ready)
    use_test_data = os.getenv("USE_TEST_DATA", "true").lower() == "true"
    if use_test_data:
        print("Using test data (set USE_TEST_DATA=false to use real API)")
        new_papers_raw = get_test_papers()
    else:
        new_papers_raw = search_papers_semantic_scholar()

    new_papers_unique = deduplicate_papers(new_papers_raw, existing_papers)
    print(f"Found {len(new_papers_unique)} new unique papers")

    # Convert and add new papers
    new_paper_ids = []
    for paper in new_papers_unique:
        entry = convert_to_paper_entry(paper)
        papers_data["papers"].append(entry)
        new_paper_ids.append(entry["id"])

    if new_papers_unique:
        save_papers(papers_data)
        print(f"Saved {len(new_papers_unique)} new papers to papers.json")

    # Stage B: Screening
    print("\n[Stage B] Screening papers...")
    screened_count = 0
    pending_deep_review = []

    for paper in papers_data["papers"]:
        if paper["stage"] == "screening" and paper["screening_score"] == 0.0:
            print(f"Screening: {paper['title'][:50]}...")
            result = screen_paper_with_claude(paper)

            paper["screening_score"] = result["screening_score"]

            # Save review
            review_file = DATA_DIR / "reviews" / f"{paper['id']}.json"
            review_data = {
                "paper_id": paper["id"],
                "stage": "screening",
                "reviewed_at": datetime.utcnow().isoformat() + "Z",
                "summary": result["summary"],
                "screening_score": result["screening_score"],
                "screening_rationale": result["screening_rationale"]
            }
            with open(review_file, "w") as f:
                json.dump(review_data, f, indent=2, ensure_ascii=False)

            screened_count += 1

            if result["screening_score"] >= 0.7:
                paper["stage"] = "pending_deep_review"
                pending_deep_review.append(paper["id"])

    if screened_count > 0:
        save_papers(papers_data)
        print(f"Screened {screened_count} papers, {len(pending_deep_review)} pending deep review")

    # Stage C: Generate reports
    print("\n[Stage D] Generating reports...")
    generate_reports(papers_data)

    # Git commit
    print("\n[Stage E] Committing changes...")
    try:
        import subprocess
        os.chdir(BASE_DIR.parent.parent.parent)  # Go to repo root

        # Switch to or create docs/vln-paper-survey branch
        result = subprocess.run(["git", "checkout", "docs/vln-paper-survey"], capture_output=True)
        if result.returncode != 0:
            subprocess.run(["git", "checkout", "-b", "docs/vln-paper-survey"], check=True)
            print("Created branch: docs/vln-paper-survey")
        else:
            print("Switched to branch: docs/vln-paper-survey")

        subprocess.run(["git", "add", "docs/09_research/vln_paper_survey/"], check=True)
        commit_msg = f"vln-survey: add {len(new_papers_unique)} papers, screen {screened_count}"
        result = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Git commit successful: {commit_msg}")
        else:
            print(f"Git commit: {result.stdout.strip()}")

        # Stay on the new branch (don't switch back to avoid file disappearance)
        os.chdir(BASE_DIR)  # Return to survey directory
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
    except Exception as e:
        print(f"Git operation failed: {e}")

    # Summary
    remaining_pending = len([p for p in papers_data["papers"] if p["stage"] == "pending_deep_review"])
    summary = f"""VLN 论文调研工作流执行完成
- 新发现论文：{len(new_papers_unique)} 篇
- 筛选论文：{screened_count} 篇
- 剩余待深审：{remaining_pending} 篇

Git commit: {commit_msg if screened_count > 0 else 'no changes'}
"""

    print(summary)
    send_feishu_notification(summary)

    return 0

if __name__ == "__main__":
    sys.exit(main())
