"""공식 WebScraper의 HTML 파싱/본문 추출만 로컬 입력으로 점검한다."""
import hashlib
import json
import socket
import sys
import traceback
from datetime import datetime, timezone

from project_paths import ASSETS, PROJECT, SOURCE, asset_path


def main():
    if sys.platform != "linux" or sys.prefix != str(asset_path("environment")):
        raise SystemExit("기존 WSL 실험 환경의 Python으로 실행하세요.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = ASSETS / "logs/lxml_runtime" / stamp
    log_dir.mkdir(parents=True, exist_ok=False)
    attempts = []

    def denied(*args, **kwargs):
        attempts.append("socket connection denied")
        raise RuntimeError("lxml local check: network disabled")

    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied
    sys.path.insert(0, str(SOURCE))
    report = {"checked_utc": stamp, "experiments_executed": False, "model_api_calls": False,
              "live_web_fetches": False, "network_connections_denied": attempts,
              "log_directory": str(log_dir.relative_to(ASSETS)), "cases": []}
    try:
        import importlib.metadata
        import requests
        from lxml import etree
        from web_utils.web_crawler import WebScraper

        report["versions"] = {name: importlib.metadata.version(name) for name in ("lxml", "beautifulsoup4", "requests")}
        report["native_versions"] = {name: list(getattr(etree, name)) for name in
                                    ("LIBXML_VERSION", "LIBXML_COMPILED_VERSION", "LIBXSLT_VERSION", "LIBXSLT_COMPILED_VERSION")}
        scraper = WebScraper()
        heading = "Heading one two three four five six seven eight nine ten eleven"
        paragraph = "This local paragraph contains more than ten words & preserves the expected text."
        div = "This div contains enough words to pass the original eleven word threshold."
        korean = "이 문장은 외부 웹 요청 없이 한글 본문 추출 동작을 확인하기 위한 시험 문장입니다."
        first = "The first unfinished paragraph contains enough words for the original extraction rule."
        second = "The second unfinished paragraph also contains enough words for the original extraction rule."
        cases = [
            ("normal_rule0", f"<html><body><h1>{heading}</h1><p>one two three four five six seven eight nine ten</p><p>{paragraph.replace('&', '&amp;')}</p><div>{div}</div><script>{div}</script></body></html>", 0, heading + "\n" + paragraph),
            ("normal_rule1", f"<html><body><div>{div}</div></body></html>", 1, div),
            ("utf8", f"<html><body><p>{korean}</p></body></html>", 0, korean),
            ("unclosed_paragraphs", f"<html><body><p>{first}<p>{second}", 0, first + "\n" + second),
        ]
        for name, html, rule, expected in cases:
            response = requests.Response()
            response._content = html.encode("utf-8")
            response.encoding = "utf-8"
            soup = scraper.convert_html_to_soup(response)
            output = scraper.extract_main_content(soup, rule=rule)
            item = {"name": name, "rule": rule, "parser": soup.builder.NAME,
                    "input_sha256": hashlib.sha256(response.content).hexdigest(),
                    "expected": expected, "actual": output,
                    "ok": soup.builder.NAME == "lxml" and output == expected}
            report["cases"].append(item)
            assert item["ok"], item
        assert not attempts, attempts
        report["success"] = True
    except Exception:
        report["success"] = False
        report["error"] = traceback.format_exc()
    report["limitations"] = ["Local fixtures only; no live page or full RAG experiment",
                             "Author lxml/libxml2/libxslt versions remain unknown; malformed HTML equivalence is not established"]
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (log_dir / "report.json").write_text(text, encoding="utf-8")
    (PROJECT / "docs/evidence/lxml_runtime.json").write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
