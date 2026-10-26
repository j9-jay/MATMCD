"""Build the Online Boutique team wiki (25 documents) and check provenance.

Runs the section extractors (`task070_ob_wiki_s01/s02/s03/s05/s06`), writes every
document under `task070_ob_wiki_common.OUT`, writes `manifest.json` with SHA-256 per
document, and fails if a fact line has no source reference.

Usage: python -B task070_ob_wiki.py
"""
import importlib
import re

from task070_ob_wiki_common import OUT, WIKI, write_manifest

SECTIONS = ["task070_ob_wiki_s01", "task070_ob_wiki_s02", "task070_ob_wiki_s03",
            "task070_ob_wiki_s05", "task070_ob_wiki_s06"]
_SOURCE = re.compile(r"`[^`]+`")


_DERIVED = re.compile(r"\(counts? of the .*rows above\)\s*$")


def check(text):
    """Bullets, prose facts and table rows outside the header and the Omitted section
    must cite a source; code blocks are verbatim quotes preceded by 'Source:'.
    Two exceptions: a label line whose next non-empty line is a 'Source:' quote line,
    and rows of a derived count table under a heading ending '(counts of the ... rows above)'."""
    problems, in_code, header, omitted, derived = [], False, True, False, False
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s:
            continue
        if s.startswith("#"):
            if s.startswith("## "):
                header = False
                omitted = s == "## Omitted"
            derived = bool(_DERIVED.search(s))
            continue
        if header or omitted or derived or s.startswith("Source: ") or re.fullmatch(r"\|?(-+\|)+", s.replace(" ", "")):
            continue
        following = next((l.strip() for l in lines[n:] if l.strip()), "")
        if not s.startswith("|") and following.startswith("Source: "):
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and cells[-1] == "Source":
                continue
            if not _SOURCE.search(cells[-1]):
                problems.append((n, s[:120]))
            continue
        if "(source: " not in s:
            problems.append((n, s[:120]))
    return problems


def main():
    docs = []
    for name in SECTIONS:
        docs += importlib.import_module(name).build()
    numbers = sorted(d.number for d in docs)
    if numbers != sorted(WIKI):
        raise SystemExit(f"Documents missing or duplicated: got {numbers}")
    paths, report = [], {}
    for doc in sorted(docs, key=lambda d: d.number):
        path = doc.write()
        paths.append(path)
        problems = check(path.read_text(encoding="utf-8"))
        report[doc.number] = {"file": path.relative_to(OUT).as_posix(), "sources": len(doc.sources),
                              "omitted": len(doc.omitted), "unsourced_lines": problems}
    write_manifest(paths)
    bad = {n: r for n, r in report.items() if r["unsourced_lines"]}
    for n, r in report.items():
        print(f"{n:02d} {r['file']}: sources={r['sources']} omitted={r['omitted']} unsourced={len(r['unsourced_lines'])}")
    if bad:
        for n, r in bad.items():
            for line in r["unsourced_lines"][:5]:
                print(f"  {n:02d} L{line[0]}: {line[1]}")
        raise SystemExit("Unsourced fact lines found")
    print(OUT)


if __name__ == "__main__":
    main()
