"""Online Boutique team wiki, section 01 Architecture (documents 01-04).

All facts are parsed from the pinned repository (README, docs, Dockerfiles, build files,
kubernetes-manifests, protos/demo.proto, service source code). Only template wording is fixed.
"""
import re
from pathlib import Path

from task070_ob_wiki_common import Doc, REPO, read_lines, rel, services

CODE_EXT = {".go", ".py", ".js", ".java", ".cs"}
SKIP_DIRS = {"genproto", "node_modules", "proto", "protos", "obj", "bin", "gradle"}
PB2 = re.compile(r"_pb2(_grpc)?\.py$")
MANIFEST_DIR = "kubernetes-manifests"


# ---------------------------------------------------------------- helpers

def lineno(text, offset):
    return text.count("\n", 0, offset) + 1


def code_files(svc):
    """Hand-written source files of one service directory (generated stubs excluded)."""
    out = []
    for p in sorted((REPO / "src" / svc).rglob("*")):
        if not p.is_file() or p.suffix not in CODE_EXT or PB2.search(p.name):
            continue
        parts = set(p.relative_to(REPO / "src" / svc).parts[:-1])
        if parts & SKIP_DIRS:
            continue
        out.append(rel(p))
    return out


def text_of(path):
    return (REPO / path).read_text(encoding="utf-8", errors="replace")


def dockerfile(svc):
    found = sorted(p for p in (REPO / "src" / svc).rglob("Dockerfile") if "node_modules" not in p.parts)
    return rel(found[0]) if found else None


def refs(doc, items):
    """In-cell source references (path, line) -> text; registered as document sources."""
    return ", ".join(doc._ref(p, ln) for p, ln in items)


# ---------------------------------------------------------------- README

def readme_section(heading):
    """(start, end) 1-based lines of a level-2 README section, heading included."""
    lines = read_lines("README.md")
    start = next(i for i, l in enumerate(lines, 1) if l.strip() == f"## {heading}")
    end = next((i - 1 for i, l in enumerate(lines, 1) if i > start and l.startswith("## ")), len(lines))
    while end > start and not lines[end - 1].strip():
        end -= 1
    return start, end


def readme_service_table():
    """[(service, language, description, line)] from the README Architecture table."""
    start, end = readme_section("Architecture")
    rx = re.compile(r"^\|\s*\[([\w-]+)\]\(/src/[\w-]+\)\s*\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|\s*$")
    out = []
    for i, l in enumerate(read_lines("README.md")[start - 1:end], start):
        m = rx.match(l)
        if m:
            out.append((m.group(1), m.group(2), m.group(3), i))
    return out


# ---------------------------------------------------------------- manifests

def manifest_docs():
    """Parsed YAML documents of kubernetes-manifests/*.yaml (line based, line numbers kept)."""
    docs = []
    for p in sorted((REPO / MANIFEST_DIR).glob("*.yaml")):
        path = rel(p)
        lines = read_lines(path)
        chunks, cur = [], []
        for i, l in enumerate(lines, 1):
            if l.startswith("---"):
                chunks.append(cur)
                cur = []
            else:
                cur.append((i, l))
        chunks.append(cur)
        for chunk in chunks:
            d = parse_manifest_doc(path, chunk)
            if d:
                docs.append(d)
    return docs


def parse_manifest_doc(path, chunk):
    kind = name = None
    d = {"path": path, "containers": [], "selector": None, "ports": []}
    in_meta = in_selector = False
    section = None          # (header indent, item indent, kind)
    container = None
    pending_port = None
    for idx, (i, l) in enumerate(chunk):
        s = l.strip()
        if not s or s.startswith("#"):
            continue
        ind = len(l) - len(l.lstrip())
        m = re.match(r"^kind:\s*(\w+)", l)
        if m:
            kind = m.group(1)
            d["kind_line"] = i
            continue
        if re.match(r"^metadata:\s*$", l):
            in_meta = True
            continue
        if in_meta:
            m = re.match(r"^  name:\s*(\S+)", l)
            if m and name is None:
                name, d["name_line"] = m.group(1), i
            if ind == 0:
                in_meta = False
        if kind == "Service":
            if re.match(r"^  selector:\s*$", l):
                in_selector = True
                continue
            if in_selector:
                m = re.match(r"^\s{4}app:\s*(\S+)", l)
                if m:
                    d["selector"] = (m.group(1), i)
                if ind <= 2:
                    in_selector = False
            m = re.match(r"^\s*-?\s*port:\s*(\d+)", l)
            if m:
                pending_port = (m.group(1), i)
            m = re.match(r"^\s*targetPort:\s*(\d+)", l)
            if m and pending_port:
                d["ports"].append((pending_port[0], m.group(1), pending_port[1], i))
                pending_port = None
        if kind == "Deployment":
            m = re.match(r"^(\s*)(initContainers|containers):\s*$", l)
            if m:
                section = [len(m.group(1)), None, m.group(2)]
                continue
            if section:
                if ind <= section[0] and not s.startswith("- "):
                    section = None
                else:
                    if s.startswith("- ") and (section[1] is None or ind == section[1]):
                        section[1] = ind
                        container = {"name": None, "list": section[2], "env": [], "ports": [], "line": i}
                        d["containers"].append(container)
                    mm = re.match(r"^\s*-?\s*name:\s*(\S+)\s*$", l)
                    if mm and container["name"] is None and ind in (section[1], section[1] + 2):
                        container["name"] = mm.group(1)
                    mm = re.match(r"^\s*-\s*name:\s*\"?([A-Za-z0-9_]+)\"?\s*$", l)
                    if mm and ind > section[1]:
                        nxt = next(((j, t) for j, t in chunk[idx + 1:] if t.strip()), None)
                        vm = re.match(r"^\s*value:\s*\"?([^\"]*)\"?\s*$", nxt[1]) if nxt else None
                        if vm:
                            container["env"].append((mm.group(1), vm.group(1), i, nxt[0]))
                    mm = re.match(r"^\s*-?\s*containerPort:\s*(\d+)", l)
                    if mm:
                        container["ports"].append((mm.group(1), i))
    if kind is None:
        return None
    d["kind"], d["name"] = kind, name
    return d


# ---------------------------------------------------------------- protos / gRPC code

def proto_services():
    """{service: {"line": n, "rpcs": {rpc: line}}} from protos/demo.proto."""
    out, cur = {}, None
    for i, l in enumerate(read_lines("protos/demo.proto"), 1):
        m = re.match(r"^service\s+(\w+)", l)
        if m:
            cur = m.group(1)
            out[cur] = {"line": i, "rpcs": {}}
            continue
        m = re.match(r"^\s*rpc\s+(\w+)\s*\(", l)
        if m and cur:
            out[cur]["rpcs"][m.group(1)] = i
        if l.startswith("}"):
            cur = None
    return out


REGISTER = [
    r"\bpb\.Register(\w+)Server\(",                      # Go
    r"\w+_pb2_grpc\.add_(\w+)Servicer_to_server\(",      # Python
    r"\b(\w+)Grpc\.\1ImplBase\b",                        # Java
    r"\.(\w+)\.\1Base\b",                                # C#
    r"addService\(\s*(?:\w+\.)*(\w+)\.service\b",        # Node.js
]

CLIENT = [
    ("go", r"\bpb\.New(\w+)Client\(\s*([\w.]+)\s*\)"),
    ("py", r"\w+_pb2_grpc\.(\w+)Stub\(\s*([^)]+?)\s*\)"),
    ("java", r"\b(\w+)Grpc\.new\w*Stub\(\s*([^)]+?)\s*\)"),
    ("js", r"\bnew\s+(?:\w+\.)+(\w+)\(\s*([^,]+?)\s*,"),
    ("cs", r"\bnew\s+(?:[\w.]+\.)?(\w+)Client\(\s*([^)]+?)\s*\)"),
]
LANG_EXT = {"go": ".go", "py": ".py", "java": ".java", "js": ".js", "cs": ".cs"}


def registrations(protos):
    """[(gRPC service, src dir, path, line)] server registrations of demo.proto services."""
    out = []
    for svc in services():
        for path in code_files(svc):
            t = text_of(path)
            for rx in REGISTER:
                for m in re.finditer(rx, t):
                    if m.group(1) in protos:
                        out.append((m.group(1), svc, path, lineno(t, m.start(1))))
    return sorted(set(out))


def match_rpc(method, rpcs):
    for r in rpcs:
        if method.lower() in (r.lower(), r.lower() + "async"):
            return r
    return None


def clients(protos):
    """Client stub constructions and the stub method calls made through them."""
    out = []
    for svc in services():
        for path in code_files(svc):
            t = text_of(path)
            lines = t.splitlines()
            for lang, rx in CLIENT:
                if LANG_EXT[lang] != Path(path).suffix:
                    continue
                for m in re.finditer(rx, t):
                    g = m.group(1)
                    if g not in protos:
                        continue
                    ln = lineno(t, m.start())
                    prefix = lines[ln - 1][:m.start() - (t.rfind("\n", 0, m.start()) + 1)]
                    var = re.search(r"(\w+)\s*:?=\s*(?:\w+\.)*$", prefix)
                    var = var.group(1) if var else None
                    calls = []
                    chain = re.match(r"\s*\.\s*(\w+)\(", t[m.end():])
                    if chain:
                        calls.append((chain.group(1), lineno(t, m.end() + chain.start(1))))
                    elif var:
                        stop = len(lines)
                        if lang == "go":
                            stop = next((j for j in range(ln, len(lines)) if lines[j].startswith("func ")), len(lines))
                        lo = ln if lang == "go" else 0
                        for j in range(lo, stop):
                            for cm in re.finditer(rf"\b{re.escape(var)}\.(\w+)\(", lines[j]):
                                calls.append((cm.group(1), j + 1))
                    out.append({"caller": svc, "grpc": g, "lang": lang, "path": path, "line": ln,
                                "arg": m.group(2).strip(), "var": var, "calls": calls})
    return sorted(out, key=lambda c: (c["caller"], c["path"], c["line"], c["grpc"]))


def trace_address(c):
    """Follow the client's connection argument back to an address environment variable."""
    svc, path, lang, arg = c["caller"], c["path"], c["lang"], c["arg"]
    if lang == "go":
        field = arg.split(".")[-1]
        for p in code_files(svc):
            t = text_of(p)
            m = re.search(rf"(\w+)\(\s*\w+,\s*&\w+\.{re.escape(field)},\s*\w+\.(\w+)\s*\)", t)
            if not m:
                continue
            fn, addr = m.group(1), m.group(2)
            res = {"conn": (p, lineno(t, m.start()))}
            for q in code_files(svc):
                u = text_of(q)
                e = re.search(rf"\w+\(\s*&\w+\.{re.escape(addr)},\s*\"([A-Z0-9_]+)\"\s*\)", u)
                if e:
                    res.update(env=e.group(1), env_ref=(q, lineno(u, e.start())))
                f = re.search(rf"^func {re.escape(fn)}\(", u, re.M)
                if f:
                    d = re.search(r"grpc\.Dial\w*\(", u[f.start():])
                    if d:
                        res["dial"] = (q, lineno(u, f.start() + d.start()))
            return res
        return {}
    if lang == "py":
        lines = read_lines(path)
        for j in range(c["line"] - 1, -1, -1):
            m = re.search(rf"\b{re.escape(arg)}\s*=\s*grpc\.\w*channel\(\s*(.+?)\s*\)\s*$", lines[j])
            if not m:
                continue
            res = {"conn": (path, j + 1), "dial": (path, j + 1), "expr": m.group(1)}
            ident = m.group(1)
            if re.fullmatch(r"\w+", ident):
                for k in range(j, -1, -1):
                    e = re.search(rf"\b{re.escape(ident)}\s*=\s*os\.(?:environ\.get|getenv)\(\s*['\"]([A-Z0-9_]+)['\"]", lines[k])
                    if e:
                        res.update(env=e.group(1), env_ref=(path, k + 1))
                        break
            return res
    return {}


ENV_ADDR = re.compile(r"[\"']([A-Z][A-Z0-9_]*_ADDR)[\"']|process\.env\.([A-Z][A-Z0-9_]*_ADDR)\b|\$\{?([A-Z][A-Z0-9_]*_ADDR)\b")


def code_addr_reads():
    """[(src dir, env var, path, line, line text)] address env vars referenced in code and Dockerfiles."""
    out = []
    for svc in services():
        files = list(code_files(svc))
        df = dockerfile(svc)
        if df:
            files.append(df)
        for path in files:
            for i, l in enumerate(read_lines(path), 1):
                for m in ENV_ADDR.finditer(l):
                    out.append((svc, next(g for g in m.groups() if g), path, i, l.strip()))
    return sorted(set(out))


# ---------------------------------------------------------------- document 01

def doc01():
    d = Doc(1, "README.md and docs/purpose.md sections located by heading text and quoted verbatim; "
               "the service list is parsed from the Markdown table in the README `## Architecture` section "
               "(columns Service, Language, Description); `src/` directories are listed from the file system.")
    lines = read_lines("README.md")
    d.section("Repository description")
    s = next(i for i, l in enumerate(lines, 1) if re.match(r"^\*\*Online Boutique\*\* is a", l))
    e = next(i - 1 for i, l in enumerate(lines, 1) if i > s and not l.strip())
    d.quote("README.md", s, e)

    d.section("Architecture (README)")
    a_s, a_e = readme_section("Architecture")
    t_s = next(i for i, l in enumerate(lines, 1) if i > a_s and l.startswith("|"))
    q_e = t_s - 1
    while not lines[q_e - 1].strip():
        q_e -= 1
    d.quote("README.md", a_s, q_e)
    for i in range(a_s, a_e + 1):
        for img in sorted(set(re.findall(r"\]\((/docs/img/[^)]+)\)", lines[i - 1]))):
            img = img.lstrip("/")
            exists = (REPO / img).is_file()
            d.fact(f"The README links the architecture image `{img}`; "
                   f"the file {'is present' if exists else 'is not present'} in the repository.", "README.md", i)
            d.omit(f"Content of `{img}`", "binary image; this extractor reads text only")
        for m in re.finditer(r"\]\((/protos)\)", lines[i - 1]):
            d.fact(f"The README points to Protocol Buffers descriptions at `{m.group(1).lstrip('/')}`.", "README.md", i)

    d.section("Service list (README table)")
    table = readme_service_table()
    d.table(["Service", "Language", "Description"], [(n, lang, desc, ("README.md", ln)) for n, lang, desc, ln in table])
    listed = {n for n, *_ in table}
    dirs = services()
    d.fact(f"The README table lists {len(table)} services; `src/` contains {len(dirs)} directories "
           f"({', '.join(dirs)}).", "README.md", table[0][3], table[-1][3])
    for n in sorted(set(dirs) - listed):
        d.fact(f"`src/{n}` is not listed in the README service table.", "README.md", table[0][3], table[-1][3])
    for n in sorted(listed - set(dirs)):
        d.fact(f"README service `{n}` has no `src/{n}` directory.", "README.md", table[0][3], table[-1][3])

    d.section("Features (README)")
    d.quote("README.md", *readme_section("Features"))

    d.section("Purpose (docs/purpose.md)")
    p = read_lines("docs/purpose.md")
    ps = next(i for i, l in enumerate(p, 1) if l.strip() == "## Purpose")
    pe = next((i - 1 for i, l in enumerate(p, 1) if i > ps and l.startswith("#")), len(p))
    while not p[pe - 1].strip():
        pe -= 1
    d.quote("docs/purpose.md", ps, pe)
    return d


# ---------------------------------------------------------------- document 02

BUILD_FILES = ["go.mod", "package.json", "requirements.in", "requirements.txt", "build.gradle",
               "settings.gradle", "*.csproj", "*.sln"]
BUILD_KEY = [r"^go\s+\S+", r"<TargetFramework>", r"(source|target)Compatibility", r"^\s*\"name\"\s*:",
             r"autogenerated by pip-compile with"]


def doc02():
    d = Doc(2, "Per `src/` directory: README table row (language, description); every `FROM` line of the "
               "service Dockerfile; build files found by name (go.mod, package.json, requirements.in/.txt, "
               "build.gradle, settings.gradle, *.csproj, *.sln) with their version/name directive line; Dockerfile "
               "`ENTRYPOINT`; entry source file (Go: non-test file with `func main()`; Python/Node.js: ENTRYPOINT "
               "argument that is a file in the service directory; Java: build.gradle `applicationName` equal to the "
               "ENTRYPOINT binary name and its `mainClass`; C#: .cs file in the .csproj directory whose first "
               "statement is a top-level statement); port evidence from code (`PORT` environment reads and port literals in the entry source file and gRPC server registration files"
               "), Dockerfile (`EXPOSE`, `*PORT*=` in `ENV`) and kubernetes-manifests (containerPort, env "
               "`PORT`, Service port/targetPort).")
    readme = {n: (lang, desc, ln) for n, lang, desc, ln in readme_service_table()}
    svcs = services()

    d.section("Language and role stated in README")
    rows = []
    for s in svcs:
        if s in readme:
            lang, desc, ln = readme[s]
            rows.append((s, lang, desc, ("README.md", ln)))
        else:
            d.omit(f"{s} language/role", "no row in the README service table")
    d.table(["Service", "Language (README)", "Role (README)"], rows)

    d.section("Dockerfile base images")
    rows = []
    for s in svcs:
        df = dockerfile(s)
        if not df:
            d.omit(f"{s} base image", "no Dockerfile in the service directory")
            continue
        for i, l in enumerate(read_lines(df), 1):
            m = re.match(r"^FROM\s+(\S+)(?:\s+[aA][sS]\s+(\S+))?", l)
            if m:
                rows.append((s, m.group(1), m.group(2) or "", (df, i)))
    d.table(["Service", "FROM image", "Stage name"], rows)

    d.section("Build files")
    rows = []
    for s in svcs:
        base = REPO / "src" / s
        found = sorted({p for pat in BUILD_FILES for p in base.rglob(pat) if "node_modules" not in p.parts})
        for p in found:
            path = rel(p)
            key = None
            for i, l in enumerate(read_lines(path), 1):
                if any(re.search(rx, l) for rx in BUILD_KEY):
                    key = (l.strip(), i)
                    break
            rows.append((s, f"`{path}`", key[0] if key else "", (path, key[1]) if key else (path,)))
        if not found:
            d.omit(f"{s} build file", "none of the listed build file names present")
    d.table(["Service", "Build file", "Directive line"], rows)

    d.section("Entry point")
    ep_rows, file_rows, entries = [], [], {}
    for s in svcs:
        df = dockerfile(s)
        ep = None
        if df:
            for i, l in enumerate(read_lines(df), 1):
                if l.startswith("ENTRYPOINT"):
                    ep = (l[len("ENTRYPOINT"):].strip(), i)
            if ep:
                ep_rows.append((s, f"`{ep[0]}`", (df, ep[1])))
        entry = entry_file(s, df, ep)
        if entry:
            entries[s] = entry[0]
            file_rows.append((s, f"`{entry[0]}`", entry[3], (entry[1], entry[2])))
        else:
            d.omit(f"{s} entry source file", "the Dockerfile ENTRYPOINT names no source file of the service and no "
                                             "extraction rule applies")
    d.table(["Service", "Dockerfile ENTRYPOINT"], ep_rows)
    d.table(["Service", "Entry source file", "Evidence line"], file_rows)

    d.section("Listening port evidence")
    rows = []
    mdocs = manifest_docs()
    server_files = {p for _, _, p, _ in registrations(proto_services())} | set(entries.values())
    for s in svcs:
        for path in code_files(s):
            if path not in server_files:
                continue
            for i, l in enumerate(read_lines(path), 1):
                if re.search(r"(Getenv|LookupEnv|getOrDefault|environ\.get|getenv)\(\s*[\"']PORT[\"']|process\.env(\.PORT\b|\[[\"']PORT[\"']\])", l):
                    rows.append((s, "code: PORT environment read", l.strip(), (path, i)))
                m = re.search(r"[\"']PORT[\"']\s*,\s*[\"'](\d+)[\"']", l) or re.match(r"^\s*(?:const\s+)?(\w*[pP]ort)\s*=\s*\"(\d+)\"", l)
                if m:
                    rows.append((s, "code: default port literal", m.group(m.lastindex), (path, i)))
        df = dockerfile(s)
        if df:
            for i, l in enumerate(read_lines(df), 1):
                m = re.match(r"^EXPOSE\s+(\S+)", l)
                if m:
                    rows.append((s, "Dockerfile EXPOSE", m.group(1), (df, i)))
                m = re.search(r"\b(\w*PORTS?)=(\d+)", l)
                if m:
                    rows.append((s, f"Dockerfile ENV {m.group(1)}", m.group(2), (df, i)))
        for md in mdocs:
            if md["kind"] == "Deployment" and md["name"] == s:
                for c in md["containers"]:
                    for v, i in c["ports"]:
                        rows.append((s, f"manifest containerPort ({c['name']})", v, (md["path"], i)))
                    for n, v, i, vi in c["env"]:
                        if n == "PORT":
                            rows.append((s, f"manifest env PORT ({c['name']})", v, (md["path"], i, vi)))
            if md["kind"] == "Service" and md["selector"] and md["selector"][0] == s:
                for port, target, pi, ti in md["ports"]:
                    rows.append((s, f"manifest Service `{md['name']}` port -> targetPort", f"{port} -> {target}", (md["path"], pi, ti)))
    d.table(["Service", "Evidence", "Value"], rows)
    for s in svcs:
        if not any(r[0] == s for r in rows):
            d.omit(f"{s} listening port", "no port evidence found")
        elif not any(r[0] == s and r[1].startswith("code") for r in rows):
            d.omit(f"{s} listening port in code", "no `PORT` read or port literal found in the entry source file or "
                                                          "gRPC server registration files")
    return d


def entry_file(s, df, ep):
    base = REPO / "src" / s
    for path in code_files(s):
        if path.endswith(".go") and not path.endswith("_test.go") and Path(path).parent == Path("src") / s:
            for i, l in enumerate(read_lines(path), 1):
                if l.startswith("func main()"):
                    return path, path, i, "`func main()`"
    if ep and df:
        for tok in re.findall(r"[\w./-]+", ep[0]):
            p = REPO / Path(df).parent / tok
            if p.suffix in (".py", ".js") and p.is_file():
                return rel(p), df, ep[1], "named in Dockerfile ENTRYPOINT"
        gradle = base / "build.gradle"
        if gradle.is_file():
            gl = read_lines(rel(gradle))
            binary = Path(re.findall(r"[\w./-]+", ep[0])[0]).name
            for i, l in enumerate(gl, 1):
                if re.search(rf"applicationName\s*=\s*'{re.escape(binary)}'", l):
                    for j in range(i - 1, 0, -1):
                        m = re.search(r"mainClass\.set\('([\w.]+)'\)", gl[j - 1])
                        if m:
                            jf = base / "src/main/java" / (m.group(1).replace(".", "/") + ".java")
                            if jf.is_file():
                                for k, t in enumerate(read_lines(rel(jf)), 1):
                                    if "public static void main(" in t:
                                        return rel(jf), rel(jf), k, f"build.gradle mainClass `{m.group(1)}`; `main` method"
                            break
        for proj in sorted(base.rglob("*.csproj")):
            if "tests" in proj.relative_to(base).parts:
                continue
            for cs in sorted(proj.parent.glob("*.cs")):
                for k, t in enumerate(read_lines(rel(cs)), 1):
                    st = t.strip()
                    if not st or st.startswith(("//", "using ", "/*", "*")):
                        continue
                    if not re.match(r"^(namespace|class|public|internal|static|\[|\{|\})", st):
                        return rel(cs), rel(cs), k, "first top-level statement"
                    break
    return None


# ---------------------------------------------------------------- document 03

def doc03():
    d = Doc(3, "(a) kubernetes-manifests/*.yaml: for each Deployment container, env entries whose name ends in "
               "`_ADDR`; caller = Deployment name, callee = host part of the value; the Service manifest whose "
               "metadata name equals the host is looked up. (b) service source code: gRPC client stub "
               "constructors for services declared in protos/demo.proto (Go `pb.New<X>Client`, Python "
               "`<X>Stub`, Java `<X>Grpc.new*Stub`, Node.js `new <pkg>.<X>`, C# `new <X>Client`), the connection "
               "argument traced back to the connection call and the address environment variable read; caller = "
               "`src/` directory, callee = `src/` directory that registers the <X> gRPC server. Comparison of (a) "
               "and (b) is by exact caller and callee name strings. Storage configuration: C# `Configuration[...]` "
               "keys and `AddSingleton<ICartStore, ...>` registrations.")
    mdocs = manifest_docs()
    protos = proto_services()
    regs = registrations(protos)
    owner = {}
    for g, svc, path, ln in regs:
        owner.setdefault(g, []).append(svc)

    d.section("Manifest note (kubernetes-manifests/README.md)")
    kr = read_lines(f"{MANIFEST_DIR}/README.md")
    d.quote(f"{MANIFEST_DIR}/README.md", 1, len(kr))
    kl = read_lines(f"{MANIFEST_DIR}/kustomization.yaml")
    ks = next((i for i, l in enumerate(kl, 1) if l.startswith("resources:")), None)
    if ks:
        ke = ks
        while ke < len(kl) and re.match(r"^\s*#?\s*-\s", kl[ke]):
            ke += 1
        d.quote(f"{MANIFEST_DIR}/kustomization.yaml", ks, ke)

    d.section("(a) Edges from Kubernetes manifest address environment variables", 2)
    services_by_name = {m["name"]: m for m in mdocs if m["kind"] == "Service"}
    a_rows, a_edges = [], {}
    for md in sorted(mdocs, key=lambda m: (m["name"] or "", m["path"])):
        if md["kind"] != "Deployment":
            continue
        for c in md["containers"]:
            for n, v, i, vi in c["env"]:
                if not n.endswith("_ADDR"):
                    continue
                host, _, port = v.partition(":")
                sv = services_by_name.get(host)
                svc_ref = refs(d, [(sv["path"], sv["name_line"])]) if sv else "no Service named by the host"
                a_rows.append((md["name"], host, port, n, f"{c['name']} ({c['list']})", svc_ref, (md["path"], i, vi)))
                a_edges.setdefault((md["name"], host), []).append((md["path"], i))
    d.table(["Caller (Deployment)", "Callee (address host)", "Port", "Env var", "Container", "Service manifest"], a_rows)

    d.section("(b) Edges from source code gRPC clients", 2)
    d.section("gRPC server registrations (callee resolution)", 3)
    d.table(["gRPC service (protos/demo.proto)", "Registered by (src dir)"], [(g, s, (p, ln)) for g, s, p, ln in regs])
    for g in sorted(protos):
        if g not in owner:
            d.omit(f"server registration of {g}", "no registration found in service source code")

    cl = clients(protos)
    b_rows, b_edges, other = [], {}, []
    by_key = {}
    for c in cl:
        tr = trace_address(c)
        c["trace"] = tr
        callees = owner.get(c["grpc"], [])
        if tr.get("env") and callees and c["caller"] not in callees:
            for callee in callees:
                by_key.setdefault((c["caller"], callee, c["grpc"], tr["env"]), {"tr": tr, "ctors": []})["ctors"].append((c["path"], c["line"]))
        else:
            other.append(c)
    for (caller, callee, g, env), v in sorted(by_key.items()):
        tr = v["tr"]
        b_rows.append((caller, callee, g, env, refs(d, [tr["conn"]]), refs(d, [tr["dial"]]) if tr.get("dial") else "",
                       refs(d, sorted(v["ctors"])), tr["env_ref"]))
        b_edges.setdefault((caller, callee), []).append(tr["env_ref"])
    d.section("Client edges", 3)
    d.table(["Caller (src dir)", "Callee (src dir)", "gRPC service", "Address env var read", "Connection call",
             "Dial call", "Client constructors"], b_rows)

    d.section("Client stubs not counted as edges", 3)
    rows = []
    for c in other:
        callees = owner.get(c["grpc"], [])
        reason = []
        if not c["trace"].get("env"):
            reason.append("no address environment variable traced; address expression `" +
                          c["trace"].get("expr", c["arg"]) + "`")
        if c["caller"] in callees:
            reason.append("gRPC service is registered by the same src dir")
        if not callees:
            reason.append("no server registration found")
        rows.append((c["caller"], c["grpc"], "; ".join(reason), (c["path"], c["line"])))
    d.table(["Src dir", "gRPC service", "Reason"], rows)

    d.section("Address environment variables referenced in code and Dockerfiles without a demo.proto client", 3)
    bound = {(c["caller"], c["trace"]["env"]) for c in cl if c["trace"].get("env")}
    rows = [(s, n, f"`{t}`", (p, ln)) for s, n, p, ln, t in code_addr_reads() if (s, n) not in bound]
    d.table(["Src dir", "Env var", "Line"], rows)

    d.section("Storage configuration in code", 3)
    rows = []
    for s in services():
        for path in code_files(s):
            lines = read_lines(path)
            for i, l in enumerate(lines, 1):
                m = re.search(r"\b[cC]onfiguration\[\"(\w+)\"\]", l)
                if m:
                    var = re.search(r"(\w+)\s*=\s*[cC]onfiguration\[", l)
                    uses = []
                    if var:
                        uses = [(path, j) for j, t in enumerate(lines, 1)
                                if j != i and re.search(rf"\b{re.escape(var.group(1))}\b", t)]
                    rows.append((s, m.group(1), f"`{l.strip()}`", refs(d, uses), (path, i)))
    d.table(["Src dir", "Configuration key", "Read", "Variable used at"], rows)
    rows = []
    for s in services():
        for path in code_files(s):
            for i, l in enumerate(read_lines(path), 1):
                m = re.search(r"AddSingleton<(\w*Store\w*),\s*(\w+)>", l) or re.search(r"(Add\w*(?:Redis|Memory)\w*Cache)\(", l)
                if m:
                    rows.append((s, m.group(m.lastindex), f"`{l.strip()}`", (path, i)))
    d.table(["Src dir", "Store / cache registration", "Line"], rows)

    d.section("Edges present in only one of (a) and (b)", 2)
    rows = []
    for k in sorted(set(a_edges) - set(b_edges)):
        rows.append((k[0], k[1], "(a) manifests only", min(a_edges[k])))
    for k in sorted(set(b_edges) - set(a_edges)):
        rows.append((k[0], k[1], "(b) source code only", min(b_edges[k])))
    d.table(["Caller", "Callee", "Present in"], rows)
    return d


# ---------------------------------------------------------------- document 04

def doc04():
    d = Doc(4, "Stub method calls made through the gRPC client stubs found for document 03 (chained call on "
               "the constructor result, or calls on the variable the stub is assigned to; Go: within the "
               "enclosing function). Method names are matched case-insensitively to `rpc` names of the same "
               "service in protos/demo.proto (a trailing `Async` is accepted). Callee = `src/` directory that "
               "registers the gRPC server. Calls whose callee is the caller's own directory are listed separately.")
    protos = proto_services()
    regs = registrations(protos)
    owner = {}
    for g, svc, path, ln in regs:
        owner.setdefault(g, []).append(svc)
    cross, self_calls, used = [], [], set()
    for c in clients(protos):
        for method, ln in c["calls"]:
            rpc = match_rpc(method, protos[c["grpc"]]["rpcs"])
            if rpc is None:
                d.omit(f"call `{method}` at {c['path']}:L{ln}", f"no rpc of {c['grpc']} in protos/demo.proto matches")
                continue
            used.add((c["grpc"], rpc))
            for callee in owner.get(c["grpc"], []) or ["(no registration)"]:
                row = (c["caller"], callee, c["grpc"], rpc, f"`{method}`", (c["path"], ln))
                (self_calls if callee == c["caller"] else cross).append(row)
    cross = sorted(set(cross), key=lambda r: (r[0], r[1], r[3], r[5]))
    self_calls = sorted(set(self_calls), key=lambda r: (r[0], r[1], r[3], r[5]))

    d.section("Cross-service RPC calls")
    d.table(["Caller (src dir)", "Callee (src dir)", "gRPC service", "RPC", "Call in code"], cross)

    d.section("Calls to the caller's own gRPC service (sample clients and tests)")
    d.table(["Src dir", "Callee (src dir)", "gRPC service", "RPC", "Call in code"], self_calls)

    d.section("RPC definitions in protos/demo.proto")
    rows = []
    for g in sorted(protos):
        for rpc, ln in sorted(protos[g]["rpcs"].items()):
            invoked = "yes" if any(r[2] == g and r[3] == rpc for r in cross) else "no"
            rows.append((g, rpc, invoked, ("protos/demo.proto", ln)))
    d.table(["gRPC service", "RPC", "Invoked cross-service in code"], rows)
    for g, rpc, inv, ref in rows:
        if inv == "no":
            d.omit(f"{g}.{rpc} cross-service caller", "no cross-service stub call found in service source code")
    return d


def build():
    return [doc01(), doc02(), doc03(), doc04()]
