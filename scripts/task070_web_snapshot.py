"""TASK_070 P3: one-time web snapshot for category 2 (causal discovery benchmarks).

Collected once and shared by every method (flat RAG, proposed, ablations).
- Search backend: Serper (Google), within the free quota only (user approval
  2026-10-18/19). Hard cap MAX_QUERIES, persisted counter; stops before the cap.
- Queries: one per variable ("<variable> <theme>") and one per unordered
  variable pair ("<a> <b> <theme>"); fixed before collection.
- Pages: the top CRAWL_PER_QUERY organic links, fetched and reduced to text with
  the unchanged official web_utils/web_crawler.py WebScraper (byte-checked).
- Leak screening (rules fixed before collection): pages from blocked domains or
  containing blocked patterns (benchmark network files/repositories, MATMCD and
  related repositories, ground-truth wording) are excluded and recorded.
The API key is read from MATMCD_DATA/secrets/serper_api_key.txt and is never
written to any output.

Usage: python -B task070_web_snapshot.py --plan     (no network)
       python -B task070_web_snapshot.py --collect
"""
import argparse
import itertools
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd
import requests

from task070_common import ASSETS, CAUSAL_DATA_DIR, WORK, import_official, write_json

THEMES = {  # official GTdatasets_experiment.py data_theme
    "Auto_MPG": "Gasoline consumption", "DWD_climate": "Climate change", "Sachs": "Biology",
    "asia": "Lung Cancer", "child": "Infant Health Status",
}
KEY_PATH = ASSETS / "secrets/serper_api_key.txt"
OUT = WORK / "web_snapshot_v1"
MAX_QUERIES = 900          # Serper free tier is 2,500 one-time; keep a wide margin
CRAWL_PER_QUERY = 3
PASSAGE_CHARS = 800
MAX_PASSAGES_PER_PAGE = 6
BLOCKED_DOMAINS = ("bnlearn.com", "github.com", "githubusercontent.com", "huggingface.co",
                   "aclanthology.org", "openreview.net", "paperswithcode.com", "kaggle.com")
BLOCKED_PATTERNS = [r"\.bif\b", r"bnlearn", r"bayesian network repository", r"\bMATMCD\b",
                    r"LLM-and-SCD", r"causal-llm-bfs", r"ground[- ]truth (graph|network|dag|adjacency)",
                    r"adjacency matrix", r"2412\.13667", r"2402\.01454", r"Efficient[- ]CDLMs"]


def variables(name):
    return list(pd.read_csv(CAUSAL_DATA_DIR / "data" / f"{name}_data.csv", nrows=0).columns)


def planned_queries():
    queries = []
    for name, theme in THEMES.items():
        labels = variables(name)
        queries += [{"dataset": name, "kind": "variable", "variables": [v], "q": f"{v} {theme}"} for v in labels]
        queries += [{"dataset": name, "kind": "pair", "variables": [a, b], "q": f"{a} {b} {theme}"}
                    for a, b in itertools.combinations(labels, 2)]
    return queries


def screen(url, text):
    host = urlparse(url).netloc.lower()
    if any(host == d or host.endswith("." + d) for d in BLOCKED_DOMAINS):
        return f"blocked_domain:{host}"
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return f"blocked_pattern:{pattern}"
    return None


def passages(text, limit=MAX_PASSAGES_PER_PAGE):
    """limit=None keeps the whole page (snapshot v2)."""
    words, out, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > PASSAGE_CHARS:
            out.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        out.append(current)
    return out if limit is None else out[:limit]


OUT_V2 = WORK / "web_snapshot_v2"


def recrawl_full():
    """Snapshot v2 (2026-10-25 data audit): v1 kept only the first MAX_PASSAGES_PER_PAGE
    passages of each page (22% of the crawled text). Re-crawl the same top CRAWL_PER_QUERY
    links of the v1 Serper results (no new searches) and keep every passage. Same crawler
    and pre-collection screen."""
    crawler = import_official("matmcd_web_crawler", "web_utils/web_crawler.py").WebScraper()
    OUT_V2.mkdir(parents=True, exist_ok=True)
    out_path = OUT_V2 / "pages.jsonl"
    done = {json.loads(l)["q"] for l in out_path.read_text(encoding="utf-8").splitlines()} if out_path.exists() else set()
    searches = [json.loads(l) for l in (OUT / "search.jsonl").read_text(encoding="utf-8").splitlines()]
    with out_path.open("a", encoding="utf-8") as page_log:
        for query in searches:
            if query["q"] in done:
                continue
            organic = query.pop("organic")
            query.pop("credits", None)
            for hit in organic[:CRAWL_PER_QUERY]:
                url = hit.get("link", "")
                try:
                    text = crawler.scrape_url(url, 0)
                except Exception as exc:  # recorded, not retried
                    text, error = "", f"{type(exc).__name__}"
                else:
                    error = None
                reason = screen(url, f"{hit.get('title', '')} {hit.get('snippet', '')} {text}")
                page_log.write(json.dumps({**query, "url": url, "title": hit.get("title"), "error": error,
                                           "excluded": reason, "chars": len(text),
                                           "passages": [] if reason or not text else passages(text, None)},
                                          ensure_ascii=False) + "\n")
    write_json(OUT_V2 / "summary.json", {"finished_utc": datetime.now(timezone.utc).isoformat(),
                                         "source": "v1 search.jsonl (no new Serper queries)",
                                         "crawl_per_query": CRAWL_PER_QUERY, "passage_limit": None})


def collect():
    key = KEY_PATH.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("Empty Serper key file")
    crawler = import_official("matmcd_web_crawler", "web_utils/web_crawler.py").WebScraper()
    OUT.mkdir(parents=True, exist_ok=True)
    state_path = OUT / "usage.json"
    usage = json.loads(state_path.read_text()) if state_path.exists() else {"serper_queries": 0, "done": []}
    queries = planned_queries()
    if len(queries) > MAX_QUERIES:
        raise SystemExit(f"Planned {len(queries)} queries exceed cap {MAX_QUERIES}")
    with (OUT / "search.jsonl").open("a", encoding="utf-8") as search_log, \
         (OUT / "pages.jsonl").open("a", encoding="utf-8") as page_log:
        for i, query in enumerate(queries):
            if query["q"] in usage["done"]:
                continue
            if usage["serper_queries"] >= MAX_QUERIES:
                raise SystemExit("Query cap reached; stopping")
            resp = requests.post("https://google.serper.dev/search", timeout=30,
                                 headers={"X-API-KEY": key, "Content-Type": "application/json"},
                                 data=json.dumps({"q": query["q"]}))
            usage["serper_queries"] += 1
            if resp.status_code != 200:
                raise SystemExit(f"Serper HTTP {resp.status_code} at query {i}; stopping")
            result = resp.json()
            organic = result.get("organic", [])
            search_log.write(json.dumps({**query, "organic": organic,
                                         "credits": result.get("credits")}, ensure_ascii=False) + "\n")
            for hit in organic[:CRAWL_PER_QUERY]:
                url = hit.get("link", "")
                try:
                    text = crawler.scrape_url(url, 0)
                except Exception as exc:  # recorded, not retried
                    text, error = "", f"{type(exc).__name__}"
                else:
                    error = None
                reason = screen(url, f"{hit.get('title', '')} {hit.get('snippet', '')} {text}")
                page_log.write(json.dumps({**query, "url": url, "title": hit.get("title"), "error": error,
                                           "excluded": reason, "chars": len(text),
                                           "passages": [] if reason or not text else passages(text)},
                                          ensure_ascii=False) + "\n")
            usage["done"].append(query["q"])
            state_path.write_text(json.dumps(usage))
            time.sleep(0.3)
    write_json(OUT / "summary.json", {"finished_utc": datetime.now(timezone.utc).isoformat(),
                                      "serper_queries": usage["serper_queries"], "planned": len(queries)})


POST_AUDIT_PATTERNS = {  # applied after collection to confirm no ground-truth network page is kept
    "asia_network": r"asia (network|model|bayesian)|chest clinic|lauritzen|spiegelhalter",
    "child_network": r"child (network|bayesian)",
    "sachs_network": r"sachs et al|consensus network|sachs (data|dataset)",
    "dataset_names": r"auto ?mpg dataset|uci machine learning|DWD climate",
}


_BINARY = re.compile(r"\bendobj\b|\bendstream\b|%PDF-|/Filter\s*/|\bobj\s*<")


def readable(passage):
    """Reject binary/PDF-structure text; require mostly letters and spaces."""
    if _BINARY.search(passage):
        return False
    letters = sum(c.isalpha() or c.isspace() for c in passage)
    return letters / max(1, len(passage)) >= 0.8


def build_corpus(snapshot=OUT, corpus_dir="causal", exclude_audited=False):
    """Kept passages -> per-dataset evidence units. Role tags: 'definition' units come
    from single-variable queries, 'relation' units from variable-pair queries; the
    variables field lists dataset variables named in the passage text (shared content,
    metadata used only by the proposed method).

    v2 (exclude_audited=True): full pages are much longer, so a page matching a
    post-collection audit pattern is excluded and listed instead of aborting the build."""
    rows = [json.loads(l) for l in (snapshot / "pages.jsonl").read_text(encoding="utf-8").splitlines()]
    audit = {k: [] for k in POST_AUDIT_PATTERNS}
    excluded_audited = []
    units = {name: [] for name in THEMES}
    dropped = {"unreadable": 0}
    seen = {name: set() for name in THEMES}
    for row in rows:
        if not row["passages"]:
            continue
        joined = " ".join(row["passages"])
        hits = [key for key, pattern in POST_AUDIT_PATTERNS.items() if re.search(pattern, joined, re.IGNORECASE)]
        if hits and exclude_audited:
            excluded_audited.append({"url": row["url"], "dataset": row["dataset"], "patterns": hits})
            continue
        for key in hits:
            audit[key].append(row["url"])
        labels = variables(row["dataset"])
        for passage in row["passages"]:
            if passage in seen[row["dataset"]]:
                continue
            if not readable(passage):  # binary PDF bodies served without a .pdf URL
                dropped["unreadable"] += 1
                continue
            seen[row["dataset"]].add(passage)
            mentioned = [v for v in labels if re.search(rf"\b{re.escape(v)}\b", passage, re.IGNORECASE)]
            units[row["dataset"]].append({
                "id": f"w{len(units[row['dataset']]):05d}", "role": "definition" if row["kind"] == "variable" else "relation",
                "kind": "web_passage", "services": mentioned, "query_variables": row["variables"],
                "minutes": [], "url": row["url"], "text": passage})
    if any(audit.values()):
        raise SystemExit(f"Post-collection audit found ground-truth network pages: { {k: v for k, v in audit.items() if v} }")
    for name, items in units.items():
        path = WORK / "corpus" / corpus_dir / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(u, ensure_ascii=False) + "\n" for u in items), encoding="utf-8")
    write_json(snapshot / "corpus_summary.json", {"units_per_dataset": {k: len(v) for k, v in units.items()},
                                             "post_audit": {k: len(v) for k, v in audit.items()},
                                             "excluded_by_post_audit": excluded_audited,
                                             "dropped_passages": dropped,
                                             "pre_collection_exclusions": [r["excluded"] for r in rows if r["excluded"]]})
    return {k: len(v) for k, v in units.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--build-corpus", action="store_true")
    parser.add_argument("--recrawl-full", action="store_true", help="snapshot v2: same links, whole pages")
    parser.add_argument("--build-corpus-v2", action="store_true")
    args = parser.parse_args()
    if args.recrawl_full:
        recrawl_full()
        return
    if args.build_corpus_v2:
        print(build_corpus(OUT_V2, "causal_v2", exclude_audited=True))
        return
    if args.plan:
        queries = planned_queries()
        by = {}
        for q in queries:
            by.setdefault(q["dataset"], {}).setdefault(q["kind"], 0)
            by[q["dataset"]][q["kind"]] += 1
        print(json.dumps({"total_queries": len(queries), "cap": MAX_QUERIES, "by_dataset": by,
                          "page_fetches_upper_bound": len(queries) * CRAWL_PER_QUERY,
                          "key_file_present": KEY_PATH.exists()}, indent=2))
    elif args.collect:
        collect()
    elif args.build_corpus:
        print(build_corpus())


if __name__ == "__main__":
    main()
