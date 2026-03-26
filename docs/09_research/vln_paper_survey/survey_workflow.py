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
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK_URL", "")

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

    for i, query in enumerate(queries):
        if i > 0:
            time.sleep(2)  # Rate limit delay

        params = {
            "query": query,
            "year": "2024-2026",
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
                if paper_id and paper_id not in seen_ids:
                    seen_ids.add(paper_id)
                    all_papers.append(paper)

            print(f"Query '{query}': found {len(papers)} papers")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"Query '{query}': rate limited (429). Consider adding SEMANTIC_SCHOLAR_API_KEY to .env")
            else:
                print(f"Query '{query}' failed: {e}")
            continue
        except Exception as e:
            print(f"Query '{query}' failed: {e}")
            continue

    print(f"Total unique papers from Semantic Scholar: {len(all_papers)}")
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

    # Generate paper_id
    title_words = re.findall(r'\w+', title.lower())[:3]
    paper_id = f"{venue}_{year}_{'_'.join(title_words)}"

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
        # Fallback: simple keyword matching
        text = f"{paper['title']} {paper.get('abstract', '')}".lower()
        keywords = ["vln", "vision language navigation", "embodied", "navigation", "instruction following"]
        score = sum(1 for kw in keywords if kw in text) / len(keywords)
        return {
            "screening_score": min(score, 1.0),
            "summary": f"Paper about {paper['title'][:50]}...",
            "screening_rationale": "Keyword-based scoring (Claude API not configured)"
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
    """Convert API result to papers.json entry"""
    import re

    title = paper.get("title", "Unknown")
    venue = paper.get("venue", "Unknown")
    year = paper.get("year", 2024)

    # Generate paper_id
    title_words = re.findall(r'\w+', title.lower())[:3]
    paper_id = f"{venue}_{year}_{'_'.join(title_words)}"

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

def deep_review_paper_with_claude(paper):
    """Deep review a paper using Claude API"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None  # Skip if no API key

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        prompt = f"""Deep review this VLN/VLA paper:

Title: {paper['title']}
Abstract: {paper.get('abstract', 'N/A')}
Venue: {paper['venue']} {paper['year']}

Extract:
1. Technical approach (architecture, training, I/O)
2. Benchmark results (R2R, REVERIE, etc.)
3. Kinbot relevance (borrowable ideas for 27B Teacher + 4B Student)
4. Engineering feasibility (model size, speed, open source)
5. Pros and cons

Output JSON with these fields."""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text
    except Exception as e:
        print(f"Deep review failed: {e}")
        return None

def generate_reports(papers_data):
    """Generate Markdown reports"""
    # Generate latest_screening.md
    screening_md = f"""# VLN/VLA 论文筛选报告

生成时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

## 统计

- 总论文数：{len(papers_data['papers'])}
- 待深审：{len([p for p in papers_data['papers'] if p['stage'] == 'pending_deep_review'])}
- 已深审：{len([p for p in papers_data['papers'] if p['stage'] == 'deep_review'])}

## 最新论文

"""
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

    # Stage C: Deep Review (max 5 papers per run)
    print("\n[Stage C] Deep reviewing papers...")
    deep_reviewed_count = 0
    max_deep_review = 5

    pending_papers = [p for p in papers_data["papers"] if p["stage"] == "pending_deep_review"][:max_deep_review]

    for paper in pending_papers:
        print(f"Deep reviewing: {paper['title'][:50]}...")
        result = deep_review_paper_with_claude(paper)

        if result:
            # Update review file
            review_file = DATA_DIR / "reviews" / f"{paper['id']}.json"
            with open(review_file, "r") as f:
                review_data = json.load(f)

            review_data["stage"] = "deep_review"
            review_data["deep_review_content"] = result
            review_data["deep_reviewed_at"] = datetime.utcnow().isoformat() + "Z"

            with open(review_file, "w") as f:
                json.dump(review_data, f, indent=2, ensure_ascii=False)

            paper["stage"] = "deep_review"
            deep_reviewed_count += 1

    if deep_reviewed_count > 0:
        save_papers(papers_data)
        print(f"Deep reviewed {deep_reviewed_count} papers")

    # Stage D: Generate reports
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
- 深度审查：{deep_reviewed_count} 篇
- 剩余待深审：{remaining_pending} 篇

Git commit: {commit_msg if screened_count > 0 else 'no changes'}
"""

    print(summary)
    send_feishu_notification(summary)

    return 0

if __name__ == "__main__":
    sys.exit(main())
