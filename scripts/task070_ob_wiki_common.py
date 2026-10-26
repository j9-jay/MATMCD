"""Shared base for the Online Boutique team wiki (TASK_070 v3 corpus).

Every wiki document is generated deterministically from the pinned repository by
parsers and templates (no LLM text). Rules (user, 2026-10-26/27):
- record only facts found in the original repository; every fact carries its source
  file path and line(s);
- each document header lists the repository URL, Git commit, source files and the
  extraction method;
- items with no implementation or configuration in the repository are not guessed:
  they are listed under "Omitted" with the reason.

Section scripts (`task070_ob_wiki_sNN.py`) define `build() -> list[Doc]`; the runner
`task070_ob_wiki.py` writes them under OUT in the wiki tree.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from project_paths import ASSETS
from task070_common import WORK

REPO_URL = "https://github.com/GoogleCloudPlatform/microservices-demo"
TAG = "v0.9.0"
COMMIT = "d138db567079e2ef982d46b2993f8349cb18e2b2"
REPO = ASSETS / "raw_downloads/github_googlecloudplatform_microservices_demo_v0.9.0/src/microservices-demo-0.9.0"
OUT = WORK / "ob_wiki_v0.9.0"

WIKI = {  # number: (section folder, file stem, title)
    1: ("01_Architecture", "01_System_Architecture_Overview", "System Architecture Overview"),
    2: ("01_Architecture", "02_Service_Catalog", "Service Catalog"),
    3: ("01_Architecture", "03_Service_Dependency_Topology", "Service Dependency Topology"),
    4: ("01_Architecture", "04_Service_Communication_Matrix", "Service Communication Matrix"),
    5: ("02_API", "05_API_Reference_Document", "API Reference Document"),
    6: ("02_API", "06_API_Request_Response_Schema", "API Request/Response Schema"),
    7: ("02_API", "07_API_Provider_Consumer_Mapping", "API Provider-Consumer Mapping"),
    8: ("02_API", "08_HTTP_Route_Document", "HTTP Route Document"),
    9: ("03_Code_and_Behavior", "09_Service_Component_Architecture", "Service Component Architecture"),
    10: ("03_Code_and_Behavior", "10_Service_Call_Flow", "Service Call Flow"),
    11: ("03_Code_and_Behavior", "11_Error_Handling_Specification", "Error Handling Specification"),
    12: ("03_Code_and_Behavior", "12_External_Dependency_Inventory", "External Dependency Inventory"),
    13: ("04_Data_and_Storage", "13_Data_Model_Schema_Document", "Data Model / Schema Document"),
    14: ("04_Data_and_Storage", "14_Cache_and_Storage_Architecture", "Cache & Storage Architecture"),
    15: ("04_Data_and_Storage", "15_Data_Access_Mapping", "Data Access Mapping"),
    16: ("05_Infrastructure", "16_Kubernetes_Deployment_Specification", "Kubernetes Deployment Specification"),
    17: ("05_Infrastructure", "17_Kubernetes_Service_and_Network_Mapping", "Kubernetes Service & Network Mapping"),
    18: ("05_Infrastructure", "18_Container_and_Resource_Configuration", "Container & Resource Configuration"),
    19: ("05_Infrastructure", "19_Environment_Configuration_Reference", "Environment Configuration Reference"),
    20: ("05_Infrastructure", "20_Service_Mesh_and_Routing_Configuration", "Service Mesh & Routing Configuration"),
    21: ("06_Build_and_Test", "21_Build_and_Dependency_Specification", "Build & Dependency Specification"),
    22: ("06_Build_and_Test", "22_CI_CD_Pipeline_Document", "CI/CD Pipeline Document"),
    23: ("06_Build_and_Test", "23_Test_Suite_Inventory", "Test Suite Inventory"),
    24: ("07_Observability", "24_Logging_Specification", "Logging Specification"),
    25: ("07_Observability", "25_Metrics_and_Tracing_Instrumentation", "Metrics & Tracing Instrumentation"),
}


def rel(path):
    """Repository-relative POSIX path."""
    return Path(path).resolve().relative_to(REPO.resolve()).as_posix()


def read_lines(path):
    return Path(REPO / path if not Path(path).is_absolute() else path).read_text(encoding="utf-8", errors="replace").splitlines()


def grep(pattern, glob="**/*", flags=0):
    """[(relative path, 1-based line, line text)] for a regex over files matching glob."""
    rx = re.compile(pattern, flags)
    out = []
    for p in sorted(REPO.glob(glob)):
        if not p.is_file():
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(lines, 1):
            if rx.search(line):
                out.append((rel(p), i, line.strip()))
    return out


def src(path, line=None, end=None):
    """Source reference string, e.g. `src/frontend/main.go:L42-L50`."""
    if line is None:
        return f"`{path}`"
    return f"`{path}:L{line}`" if end is None or end == line else f"`{path}:L{line}-L{end}`"


class Doc:
    def __init__(self, number, method):
        self.number = number
        self.folder, self.stem, self.title = WIKI[number]
        self.method = method          # extraction method, one paragraph
        self.body = []
        self.sources = set()
        self.omitted = []

    def _ref(self, path, line=None, end=None):
        self.sources.add(path)
        return src(path, line, end)

    def section(self, title, level=2):
        self.body += ["", "#" * level + " " + title, ""]

    def text(self, text, path, line=None, end=None):
        """A fact stated in prose, with its source."""
        self.body.append(f"{text} (source: {self._ref(path, line, end)})")

    def fact(self, text, path, line=None, end=None):
        """A bullet fact with its source."""
        self.body.append(f"- {text} (source: {self._ref(path, line, end)})")

    def quote(self, path, line, end):
        """Verbatim excerpt of repository lines."""
        lines = read_lines(path)[line - 1:end]
        self.body += [f"Source: {self._ref(path, line, end)}", "", "```", *lines, "```", ""]

    def table(self, headers, rows):
        """rows: list of (cells..., (path, line[, end])). The last header column is 'Source'."""
        self.body += ["| " + " | ".join(headers + ["Source"]) + " |", "|" + "---|" * (len(headers) + 1)]
        for row in rows:
            *cells, ref = row
            cells = [str(c).replace("|", "\\|").replace("\n", " ") for c in cells]
            self.body.append("| " + " | ".join(cells + [self._ref(*ref)]) + " |")
        self.body.append("")

    def omit(self, item, reason):
        self.omitted.append((item, reason))

    def render(self):
        head = [f"# {self.number:02d}. {self.title}", "",
                f"- Repository: {REPO_URL}",
                f"- Version: tag `{TAG}`, commit `{COMMIT}`",
                f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')} (UTC) by `scripts/task070_ob_wiki.py` (deterministic static extraction, no LLM text)",
                f"- Extraction method: {self.method}",
                "- Source files: " + (", ".join(f"`{s}`" for s in sorted(self.sources)) or "none")]
        tail = ["", "## Omitted", ""]
        tail += [f"- {item}: {reason}" for item, reason in self.omitted] or ["- none"]
        return "\n".join(head + self.body + tail) + "\n"

    def write(self):
        path = OUT / self.folder / f"{self.stem}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        return path


def services():
    """Service directories under src/ (each one is a deployable service in this repository)."""
    return sorted(p.name for p in (REPO / "src").iterdir() if p.is_dir())


def write_manifest(paths):
    import hashlib
    items = {p.relative_to(OUT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (OUT / "manifest.json").write_text(json.dumps({"repository": REPO_URL, "tag": TAG, "commit": COMMIT,
                                                   "documents": items}, indent=2) + "\n", encoding="utf-8")
