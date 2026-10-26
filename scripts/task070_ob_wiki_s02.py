"""Online Boutique team wiki, section 02 API (documents 05-08).

Deterministic static extraction from the pinned repository (see task070_ob_wiki_common).
Every fact is parsed from repository files and carries its path and line.
"""
import re
from pathlib import Path

from task070_ob_wiki_common import REPO, Doc, grep, read_lines, rel, services

# proto3 scalar value types (language specification; used only to label a field type kind)
PROTO_SCALARS = {"double", "float", "int32", "int64", "uint32", "uint64", "sint32", "sint64",
                 "fixed32", "fixed64", "sfixed32", "sfixed64", "bool", "string", "bytes"}
PRIMARY_DIR = "protos/"


# --------------------------------------------------------------------------- proto parsing

def proto_files():
    return sorted(rel(p) for p in REPO.glob("**/*.proto") if p.is_file() and "node_modules" not in p.parts)


def _comment_above(lines, idx):
    """Contiguous `//` comment lines directly above 0-based line idx -> (text, first, last) or None."""
    j = idx - 1
    block = []
    while j >= 0 and lines[j].strip().startswith("//"):
        block.insert(0, lines[j].strip()[2:].strip())
        j -= 1
    if not block:
        return None
    return " ".join(block), j + 2, idx


def _trailing(line):
    m = re.search(r"//\s*(.*)$", line)
    return m.group(1).strip() if m else ""


def parse_proto(path):
    lines = read_lines(path)
    info = {"path": path, "lines": lines, "syntax": None, "package": None, "options": [], "imports": [],
            "services": [], "messages": [], "enums": [], "free_comments": []}
    stack = []
    attached = set()
    header_end = 0
    for i, raw in enumerate(lines):
        n = i + 1
        line = raw.split("//")[0].strip()
        if not line:
            continue
        m = re.match(r'syntax\s*=\s*"(\w+)"\s*;', line)
        if m:
            info["syntax"] = (m.group(1), n)
            header_end = header_end or n
            continue
        m = re.match(r"package\s+([\w.]+)\s*;", line)
        if m:
            info["package"] = (m.group(1), n)
            continue
        m = re.match(r'option\s+(\w+)\s*=\s*(.+?)\s*;', line)
        if m:
            info["options"].append((m.group(1), m.group(2), n))
            continue
        m = re.match(r'import\s+(?:public\s+|weak\s+)?"([^"]+)"\s*;', line)
        if m:
            info["imports"].append((m.group(1), n))
            continue
        m = re.match(r"(service|message|enum)\s+(\w+)\s*\{(.*)$", line)
        if m:
            kind, name, rest = m.groups()
            parent = [b for b in stack if b["kind"] == "message"]
            qual = ".".join([b["name"] for b in parent] + [name])
            com = _comment_above(lines, i)
            if com:
                attached.update(range(com[1], com[2] + 1))
            block = {"kind": kind, "name": name, "qual": qual, "start": n, "end": n,
                     "comment": com, "items": [], "parent": parent[-1]["qual"] if parent else None}
            {"service": info["services"], "message": info["messages"], "enum": info["enums"]}[kind].append(block)
            if "}" in rest:
                continue
            stack.append(block)
            continue
        if line.startswith("}"):
            if stack:
                stack.pop()["end"] = n
            continue
        if not stack:
            continue
        cur = stack[-1]
        com = _comment_above(lines, i)
        if com:
            attached.update(range(com[1], com[2] + 1))
        ctext = " ".join(x for x in [com[0] if com else "", _trailing(raw)] if x)
        if cur["kind"] == "service":
            m = re.match(r"rpc\s+(\w+)\s*\(\s*(stream\s+)?([\w.]+)\s*\)\s*returns\s*\(\s*(stream\s+)?([\w.]+)\s*\)", line)
            if m:
                cur["items"].append({"name": m.group(1), "req": m.group(3), "req_stream": bool(m.group(2)),
                                     "resp": m.group(5), "resp_stream": bool(m.group(4)), "line": n,
                                     "comment": ctext})
        elif cur["kind"] == "message":
            m = re.match(r"(repeated\s+|optional\s+)?([\w.]+)\s+(\w+)\s*=\s*(\d+)\s*;", line)
            if m:
                cur["items"].append({"label": (m.group(1) or "").strip(), "type": m.group(2), "name": m.group(3),
                                     "number": int(m.group(4)), "line": n, "comment": ctext})
        elif cur["kind"] == "enum":
            m = re.match(r"(\w+)\s*=\s*(-?\d+)\s*;", line)
            if m:
                cur["items"].append({"name": m.group(1), "number": int(m.group(2)), "line": n, "comment": ctext})
    # comment blocks not attached to a definition (after the file header that precedes `syntax`)
    # the file header is the comment block that starts on line 1 (license text); it is skipped
    start = 0
    while start < len(lines) and lines[start].strip().startswith("//"):
        start += 1
    i = start
    while i < len(lines):
        if lines[i].strip().startswith("//") and (i + 1) not in attached:
            j = i
            block = []
            while j < len(lines) and lines[j].strip().startswith("//") and (j + 1) not in attached:
                block.append(lines[j].strip()[2:].strip())
                j += 1
            info["free_comments"].append((" ".join(block), i + 1, j))
            i = j
        else:
            i += 1
    return info


def _sig(block, lines):
    """Normalized definition text (whitespace collapsed) for cross-file comparison."""
    return " ".join(" ".join(lines[block["start"] - 1:block["end"]]).split())


def load_protos():
    return {p: parse_proto(p) for p in proto_files()}


def primary_of(protos, path):
    """Primary file (under protos/) with identical bytes, or None."""
    data = (REPO / path).read_bytes()
    for p in sorted(protos):
        if p.startswith(PRIMARY_DIR) and p != path and (REPO / p).read_bytes() == data:
            return p
    return None


def defs_index(protos, only_primary=True):
    """qualified name -> (kind, block, file info) over primary files."""
    idx = {}
    for p, info in sorted(protos.items()):
        if only_primary and not p.startswith(PRIMARY_DIR):
            continue
        pkg = info["package"][0] if info["package"] else ""
        for kind in ("services", "messages", "enums"):
            for b in info[kind]:
                idx[(pkg, b["qual"])] = (kind, b, info)
    return idx


# --------------------------------------------------------------------------- doc 05

def doc05(protos):
    d = Doc(5, "All `*.proto` files in the repository are parsed line by line (regular expressions for "
               "`syntax`, `package`, `option`, `import`, `service`, `rpc`, `message`, `enum`); a comment is "
               "attached to a definition when `//` lines directly precede it. Files under `protos/` are the "
               "primary definitions; every other `.proto` file is compared byte-for-byte and per definition "
               "against them.")
    d.section("Proto file inventory")
    rows = []
    for p, info in sorted(protos.items()):
        prim = primary_of(protos, p)
        pkg = info["package"][0] if info["package"] else "(none)"
        rel_txt = "primary definition file" if p.startswith(PRIMARY_DIR) else (
            f"byte-identical copy of `{prim}`" if prim else "differs from every file under `protos/`; see below")
        rows.append((f"`{p}`", info["syntax"][0] if info["syntax"] else "(none)", pkg,
                     len(info["services"]), len(info["messages"]), len(info["enums"]), rel_txt, (p, 1, len(info["lines"]))))
    d.body.append("")
    d.table(["File", "Syntax", "Package", "Services", "Messages", "Enums", "Relation"], rows)

    idx = defs_index(protos)
    for p, info in sorted(protos.items()):
        if p.startswith(PRIMARY_DIR) or primary_of(protos, p):
            continue
        d.section(f"Definitions in `{p}` compared with `{PRIMARY_DIR}`", 3)
        pkg = info["package"][0] if info["package"] else ""
        rows = []
        for kind in ("services", "messages", "enums"):
            for b in info[kind]:
                hit = idx.get((pkg, b["qual"]))
                if hit:
                    same = _sig(b, info["lines"]) == _sig(hit[1], hit[2]["lines"])
                    cmpt = (f"identical text (whitespace-normalized) to `{hit[2]['path']}:L{hit[1]['start']}-L{hit[1]['end']}`"
                            if same else f"text differs from `{hit[2]['path']}:L{hit[1]['start']}-L{hit[1]['end']}`")
                else:
                    cmpt = "no definition with this name in the same package under `protos/`"
                rows.append((kind[:-1], f"`{b['qual']}`", cmpt, (p, b["start"], b["end"])))
        d.body.append("")
        d.table(["Kind", "Name", "Comparison"], rows)

    for p, info in sorted(protos.items()):
        if not p.startswith(PRIMARY_DIR):
            continue
        d.section(f"`{p}`")
        if info["syntax"]:
            d.fact(f"Syntax: `{info['syntax'][0]}`", p, info["syntax"][1])
        if info["package"]:
            d.fact(f"Package: `{info['package'][0]}`", p, info["package"][1])
        else:
            d.omit(f"package of `{p}`", "no `package` statement in the file")
        for name, val, n in info["options"]:
            d.fact(f"Option `{name}` = `{val}`", p, n)
        for imp, n in info["imports"]:
            d.fact(f"Import `{imp}`", p, n)
        for text, a, b in info["free_comments"]:
            d.fact(f"Comment not attached to a definition: \"{text}\"", p, a, b)
        if not info["services"]:
            d.omit(f"services in `{p}`", "the file defines no `service`")
        pkg = info["package"][0] if info["package"] else ""
        for s in info["services"]:
            d.section(f"Service `{pkg}.{s['name']}`", 3)
            d.fact(f"Service `{s['name']}` defined with {len(s['items'])} RPC(s)", p, s["start"], s["end"])
            if s["comment"]:
                d.fact(f"Service comment: \"{s['comment'][0]}\"", p, s["comment"][1], s["comment"][2])
            rows = []
            for r in s["items"]:
                rows.append((f"`{r['name']}`", f"`{r['req']}`", f"`{r['resp']}`",
                             "yes" if r["req_stream"] else "no", "yes" if r["resp_stream"] else "no",
                             r["comment"] or "(no comment)", (p, r["line"])))
            d.body.append("")
            d.table(["RPC", "Request type", "Response type", "Client streaming", "Server streaming", "Proto comment"], rows)
            d.quote(p, s["start"], s["end"])
    return d


# --------------------------------------------------------------------------- doc 06

def doc06(protos):
    d = Doc(6, "Messages and enums of the primary `.proto` files under `protos/` are parsed line by line "
               "(field pattern `[repeated|optional] <type> <name> = <number>;`, enum value pattern "
               "`<NAME> = <number>;`); comments are the `//` lines directly above a field or after it on the "
               "same line. Type kind: `scalar` for proto3 scalar types, otherwise resolved against the "
               "messages and enums parsed from the same package. Usage is computed from RPC signatures and "
               "field types in the same files.")
    idx = defs_index(protos)
    # usage maps
    used_rpc, used_field = {}, {}
    for p, info in sorted(protos.items()):
        if not p.startswith(PRIMARY_DIR):
            continue
        pkg = info["package"][0] if info["package"] else ""
        for s in info["services"]:
            for r in s["items"]:
                for role, t in (("request", r["req"]), ("response", r["resp"])):
                    used_rpc.setdefault((pkg, t), []).append((f"{s['name']}.{r['name']} {role}", p, r["line"]))
        for m in info["messages"]:
            for f in m["items"]:
                used_field.setdefault((pkg, _resolve(idx, pkg, m["qual"], f["type"])), []).append(
                    (f"{m['qual']}.{f['name']}", p, f["line"]))

    for p, info in sorted(protos.items()):
        if not p.startswith(PRIMARY_DIR):
            continue
        pkg = info["package"][0] if info["package"] else ""
        d.section(f"`{p}` (package `{pkg}`)")
        if not info["messages"]:
            d.omit(f"messages in `{p}`", "the file defines no `message`")
        for m in info["messages"]:
            d.section(f"Message `{pkg}.{m['qual']}`", 3)
            d.fact(f"Message `{m['qual']}` defined with {len(m['items'])} field(s)"
                   + (f", nested in `{m['parent']}`" if m["parent"] else ""), p, m["start"], m["end"])
            if m["comment"]:
                d.fact(f"Message comment: \"{m['comment'][0]}\"", p, m["comment"][1], m["comment"][2])
            if m["items"]:
                rows = []
                for f in sorted(m["items"], key=lambda x: x["number"]):
                    rows.append((f["number"], f"`{f['name']}`", f"`{f['type']}`",
                                 "yes" if f["label"] == "repeated" else "no",
                                 _kind(idx, pkg, m["qual"], f["type"]), f["comment"] or "(no comment)",
                                 (p, f["line"])))
                d.body.append("")
                d.table(["Field number", "Name", "Type", "Repeated", "Type kind", "Proto comment"], rows)
                nums = sorted(f["number"] for f in m["items"])
                gaps = [x for x in range(1, nums[-1] + 1) if x not in nums]
                if gaps:
                    d.fact(f"Field numbers between 1 and {nums[-1]} not assigned to any field: "
                           + ", ".join(map(str, gaps)), p, m["start"], m["end"])
            else:
                d.fact(f"Message `{m['qual']}` has no fields", p, m["start"], m["end"])
            for label, path, line in sorted(used_rpc.get((pkg, m["qual"]), [])):
                d.fact(f"Used by RPC {label}", path, line)
            for label, path, line in sorted(used_field.get((pkg, m["qual"]), [])):
                d.fact(f"Used as the type of field `{label}`", path, line)
        for e in info["enums"]:
            d.section(f"Enum `{pkg}.{e['qual']}`", 3)
            d.fact(f"Enum `{e['qual']}` defined with {len(e['items'])} value(s)"
                   + (f", nested in `{e['parent']}`" if e["parent"] else ""), p, e["start"], e["end"])
            if e["comment"]:
                d.fact(f"Enum comment: \"{e['comment'][0]}\"", p, e["comment"][1], e["comment"][2])
            d.body.append("")
            d.table(["Number", "Value name", "Proto comment"],
                    [(v["number"], f"`{v['name']}`", v["comment"] or "(no comment)", (p, v["line"]))
                     for v in sorted(e["items"], key=lambda x: x["number"])])
            for label, path, line in sorted(used_field.get((pkg, e["qual"]), [])):
                d.fact(f"Used as the type of field `{label}`", path, line)
        if not info["enums"]:
            d.omit(f"enums in `{p}`", "the file defines no `enum`")
    return d


def _resolve(idx, pkg, scope, t):
    """Qualified name of a referenced message/enum, searching the nesting scope outward."""
    parts = scope.split(".")
    for k in range(len(parts), -1, -1):
        cand = ".".join(parts[:k] + [t]) if k else t
        if (pkg, cand) in idx:
            return cand
    return t


def _kind(idx, pkg, scope, t):
    if t in PROTO_SCALARS:
        return "scalar"
    q = _resolve(idx, pkg, scope, t)
    hit = idx.get((pkg, q))
    if hit:
        return f"{hit[0][:-1]} `{q}` (`{hit[2]['path']}:L{hit[1]['start']}`)"
    return "not defined in the repository protos"


# --------------------------------------------------------------------------- doc 07

def generated(path):
    return ("/genproto/" in "/" + path or path.endswith((".pb.go", "_pb2.py", "_pb2_grpc.py"))
            or "node_modules/" in path)


def code_files(svc):
    out = []
    for p in sorted((REPO / "src" / svc).rglob("*")):
        if p.is_file() and p.suffix in (".go", ".py", ".js", ".cs", ".java") and not generated(rel(p)):
            out.append(rel(p))
    return out


def lc_first(s):
    return s[:1].lower() + s[1:]


def find_registrations(svc):
    """[(proto service name or None, registration text, path, line, note)]"""
    regs = []
    for p in code_files(svc):
        lines = read_lines(p)
        for i, line in enumerate(lines):
            n = i + 1
            s = line.strip()
            if p.endswith(".go"):
                m = re.search(r"\b\w+\.Register(\w+)Server\(", s)
                if m:
                    regs.append((m.group(1), s, p, n, "", None))
            elif p.endswith(".py"):
                m = re.search(r"\badd_(\w+)Servicer_to_server\(", s)
                if m and not s.startswith("def "):
                    regs.append((m.group(1), s, p, n, _py_servicer_note(lines, i, s, p), None))
            elif p.endswith(".js"):
                if re.search(r"\.addService\(", s):
                    window = " ".join(x.strip() for x in lines[i:i + 3])
                    m = re.search(r"\.addService\(\s*[\w.]*?\.(\w+)\.service\b", window)
                    end = next((k for k in range(i, min(i + 3, len(lines))) if ".service" in lines[k]), i)
                    regs.append((m.group(1) if m else None, " ".join(x.strip() for x in lines[i:end + 1]), p, n, "", None))
            elif p.endswith(".cs"):
                m = re.search(r"MapGrpcService<([\w.]+)>", s)
                if m:
                    cls = m.group(1).split(".")[-1]
                    regs.append(_class_base(svc, cls, s, p, n, r"class\s+%s\s*:\s*([\w.]+)", r"(\w+)Base$"))
            elif p.endswith(".java"):
                m = re.search(r"\.addService\((.+)\)\s*$", s)
                if m:
                    m2 = re.match(r"new\s+(\w+)\(\)", m.group(1))
                    if m2:
                        regs.append(_class_base(svc, m2.group(1), s, p, n, r"class\s+%s\s+extends\s+([\w.]+)",
                                                r"(\w+)ImplBase$"))
                    else:
                        regs.append((None, s, p, n, "", None))
    return regs


def _py_servicer_note(lines, i, s, path):
    """Assignments of the servicer argument inside the enclosing function, scanning upward."""
    arg = re.search(r"Servicer_to_server\(\s*(\w+)\s*,", s)
    if not arg:
        return ""
    found = []
    for k in range(i - 1, -1, -1):
        if re.match(r"\s*def\s", lines[k]):
            break
        m = re.match(r"\s*%s\s*=\s*(\w+)\(\)" % re.escape(arg.group(1)), lines[k])
        if m:
            found.append(f"argument `{arg.group(1)}` assigned `{m.group(1)}()` at `{path}:L{k + 1}`")
    return "; ".join(reversed(found))


def consumer_label(path, svc):
    """Deterministic caller class from the file path/name (rule stated in the doc 07 method text)."""
    name = Path(path).name
    parts = Path(path).parts
    if "tests" in parts or "test" in parts or re.search(r"Test|test_|_test", name):
        return f"test code ({svc} folder)", False
    if name in ("client.js", "client.py") or name.endswith("_client.py") or name.endswith("Client.java"):
        return f"client script ({svc} folder)", False
    return svc, True


def _class_base(svc, cls, s, p, n, class_rx, base_rx):
    for q in code_files(svc):
        for j, line in enumerate(read_lines(q), 1):
            m = re.search(class_rx % re.escape(cls), line)
            if m:
                base = m.group(1).split(".")[-1]
                b = re.search(base_rx, base)
                return (b.group(1) if b else None, s, p, n,
                        f"class `{cls}` declared with base `{m.group(1)}` at `{q}:L{j}`", q)
    return (None, s, p, n, f"declaration of class `{cls}` not found", None)


def find_impl(svc, reg, rpc):
    """Handler definitions for one RPC in the provider service: [(text, path, line)]."""
    _, regtext, regpath, regline, _, declfile = reg
    out = []
    files = [declfile] if declfile else code_files(svc)
    if regpath.endswith(".js"):
        lines = read_lines(regpath)
        window = " ".join(x.strip() for x in lines[regline - 1:regline + 6])
        body = re.search(r"\{([^}]*)\}", window)
        entries = [e.strip() for e in body.group(1).split(",")] if body else []
        for e in entries:
            key, _, val = (x.strip() for x in e.partition(":"))
            if key.lower() != rpc.lower():
                continue
            target = val.split(".bind")[0].split(".")[-1] if val else key
            rx = re.compile(r"^\s*(?:function\s+%s\s*\(|static\s+%s\s*\()" % (re.escape(target), re.escape(target)))
            for j, line in enumerate(lines, 1):
                if rx.search(line):
                    out.append((f"handler key `{key}` -> `{line.strip()}`", regpath, j))
        return out
    pats = {".go": r"^func\s+\([^)]*\)\s+%s\(" % rpc, ".py": r"^\s*def\s+%s\(self" % rpc,
            ".cs": r"\boverride\b.*\b%s\(" % rpc, ".java": r"^\s*public\s+void\s+%s\(" % lc_first(rpc)}
    for p in files:
        rx = pats.get(Path(p).suffix)
        if not rx:
            continue
        lines = read_lines(p)
        for j, line in enumerate(lines, 1):
            if re.search(rx, line):
                owner = ""
                if p.endswith(".py"):
                    for k in range(j - 1, 0, -1):
                        mm = re.match(r"class\s+(\w+)", lines[k - 1])
                        if mm:
                            owner = f" in class `{mm.group(1)}`"
                            break
                out.append((f"`{line.strip()}`{owner}", p, j))
    return out


def find_consumers(rpcs_by_service):
    """[(proto service, rpc, consumer service dir, path, line, code)]"""
    out = []
    for svc in services():
        for p in code_files(svc):
            lines = read_lines(p)
            text_lines = [x.strip() for x in lines]
            stub_vars = {}  # var -> proto service
            for i, s in enumerate(text_lines):
                n = i + 1
                if p.endswith(".go"):
                    for m in re.finditer(r"\bpb\.New(\w+)Client\([^)]*\)", s):
                        ps = m.group(1)
                        tail = s[m.end():]
                        mm = re.match(r"\.(\w+)\(", tail)
                        if mm:
                            out.append((ps, mm.group(1), svc, p, n, s))
                        elif tail == "." and i + 1 < len(text_lines):
                            mm = re.match(r"(\w+)\(", text_lines[i + 1])
                            if mm:
                                out.append((ps, mm.group(1), svc, p, n + 1, s + " " + text_lines[i + 1]))
                        else:
                            va = re.match(r"(\w+)\s*:?=\s*pb\.New", s)
                            if va:
                                for j in range(i + 1, len(text_lines)):
                                    if lines[j].startswith("func "):
                                        break
                                    for mc in re.finditer(r"\b%s\.(\w+)\(" % va.group(1), text_lines[j]):
                                        out.append((ps, mc.group(1), svc, p, j + 1, text_lines[j]))
                    continue
                m = None
                if p.endswith(".py"):
                    m = re.search(r"\b(\w+)\s*=\s*\w+_pb2_grpc\.(\w+)Stub\(", s)
                elif p.endswith(".js"):
                    m = re.search(r"\b(?:const|let|var)\s+(\w+)\s*=\s*new\s+[\w.]*?\.?(\w+)\(", s)
                    if m and m.group(2) not in rpcs_by_service:
                        m = None
                elif p.endswith(".java"):
                    m = re.search(r"\b(\w+)\s*=\s*[\w.]*?(\w+)Grpc\.new\w*Stub\(", s)
                elif p.endswith(".cs"):
                    m = re.search(r"\bvar\s+(\w+)\s*=\s*new\s+(\w+)Client\(", s)
                if m:
                    stub_vars[m.group(1)] = (m.group(2), n)
            for var, (ps, decl) in sorted(stub_vars.items()):
                names = {r.lower(): r for r in rpcs_by_service.get(ps, [])}
                for j, s in enumerate(text_lines, 1):
                    for mc in re.finditer(r"\b%s\.(\w+?)(?:Async)?\(" % re.escape(var), s):
                        name = mc.group(1)
                        if name.lower() in names:
                            out.append((ps, names[name.lower()], svc, p, j, s))
    return sorted(set(out), key=lambda x: (x[0], x[1], x[2], x[3], x[4]))


def doc07(protos):
    d = Doc(7, "Provider: non-generated source files of each `src/<service>` directory are scanned for gRPC "
               "server registration calls (Go `pb.Register<Service>Server`, Python "
               "`add_<Service>Servicer_to_server`, Node.js `server.addService(<pkg>.<Service>.service, ...)`, "
               "C# `MapGrpcService<Class>` resolved through the class base `<Service>Base`, Java "
               "`addService(new Class())` resolved through the base `<Service>ImplBase`); handler definitions "
               "are located by RPC name in the same service. Consumer: stub constructions (Go "
               "`pb.New<Service>Client(...)`, Python `<Service>Stub(...)`, Node.js `new <pkg>.<Service>(...)`, "
               "Java `<Service>Grpc.new*Stub(...)`, C# `new <Service>Client(...)`) and the stub method calls "
               "on them. Generated code (`genproto/`, `*.pb.go`, `*_pb2.py`, `*_pb2_grpc.py`) is excluded. "
               "The service name is the `src/` directory that contains the file. Consumer files are classified "
               "by path/name: a file under a `tests/` or `test/` directory or whose name contains `Test`, "
               "`test_` or `_test` is labelled `test code (<service> folder)`; a file named `client.js`, "
               "`client.py`, `*_client.py` or `*Client.java` is labelled `client script (<service> folder)`; "
               "every other file is service code labelled with its service. For Python registrations the "
               "assignment of the servicer argument in the enclosing function is recorded.")
    rpcs = {}       # proto service -> [(rpc, proto path, line, pkg)]
    for p, info in sorted(protos.items()):
        if not p.startswith(PRIMARY_DIR):
            continue
        pkg = info["package"][0] if info["package"] else ""
        for s in info["services"]:
            rpcs[s["name"]] = [(r["name"], p, r["line"], pkg) for r in s["items"]]
    rpc_names = {k: [r[0] for r in v] for k, v in rpcs.items()}
    pkg_of = {k: v[0][3] for k, v in rpcs.items() if v}

    regs = []
    for svc in services():
        for r in find_registrations(svc):
            regs.append((svc,) + r)
    d.section("gRPC server registrations")
    d.body.append("")
    d.table(["Provider service", "Proto service", "Registration code", "Resolution"],
            [(f"`{svc}`", f"`{ps}`" if ps else "(not resolved from repository code)", f"`{t}`", note or "-", (p, n))
             for svc, ps, t, p, n, note, decl in regs])
    for svc, ps, t, p, n, note, decl in regs:
        if ps is None:
            d.omit(f"proto service registered by `{t}` in `{p}:L{n}`",
                   "the registered object is produced by a library call; the repository code does not name the proto service")
        elif ps not in rpcs:
            d.omit(f"proto service `{ps}` registered in `{p}:L{n}`", "not defined in the primary `.proto` files")
    no_server = [s for s in services() if not any(r[0] == s for r in regs)]
    for s in no_server:
        d.omit(f"gRPC server in `src/{s}`", "no gRPC server registration call found in its non-generated code")

    d.section("Provider handler implementations")
    rows = []
    for svc, ps, t, p, n, note, decl in regs:
        if ps not in rpcs:
            continue
        for rpc, pp, pl, pkg in rpcs[ps]:
            impls = find_impl(svc, (ps, t, p, n, note, decl), rpc)
            for text, ip, il in impls:
                rows.append((f"`{pkg}.{ps}/{rpc}`", f"`{svc}`", text, (ip, il)))
            if not impls:
                d.omit(f"handler of `{ps}/{rpc}` in `src/{svc}`", "no handler definition matching the RPC name found")
    d.body.append("")
    d.table(["RPC", "Provider service", "Handler definition"], rows)

    # handler methods for Health not declared in the repository health.proto (Go only)
    extra = []
    health = set(rpc_names.get("Health", []))
    for svc, ps, t, p, n, note, decl in regs:
        if ps != "Health":
            continue
        for f in code_files(svc):
            if not f.endswith(".go"):
                continue
            for j, line in enumerate(read_lines(f), 1):
                m = re.match(r"func\s+\([^)]*\)\s+(\w+)\(.*healthpb\.", line)
                if m and m.group(1) not in health:
                    extra.append((f"`{svc}`", f"`{m.group(1)}`", f"`{line.strip()}`", (f, j)))
    if extra:
        d.section("Health handler methods not declared in the repository `health.proto`")
        d.body.append("")
        d.table(["Service", "Method", "Definition"], sorted(set(extra), key=lambda x: (x[0], x[3])))

    cons = find_consumers(rpc_names)
    labelled = [(ps, rpc, consumer_label(p, svc), p, n, code) for ps, rpc, svc, p, n, code in cons]
    d.section("Consumer call sites")
    d.section("Service-to-service calls", 3)
    d.body.append("")
    d.table(["RPC", "Consumer service", "File", "Calling code"],
            [(f"`{pkg_of.get(ps, '')}.{ps}/{rpc}`", f"`{lab}`", f"`{p}`", f"`{code}`", (p, n))
             for ps, rpc, (lab, real), p, n, code in labelled if real])
    d.section("Non-service callers", 3)
    d.body.append("")
    d.table(["RPC", "Caller", "File", "Calling code"],
            [(f"`{pkg_of.get(ps, '')}.{ps}/{rpc}`", lab, f"`{p}`", f"`{code}`", (p, n))
             for ps, rpc, (lab, real), p, n, code in labelled if not real])

    d.section("Per-RPC summary")
    rows = []
    for ps in sorted(rpcs):
        for rpc, pp, pl, pkg in rpcs[ps]:
            prov = sorted({(svc, p, n) for svc, rps, t, p, n, note, decl in regs if rps == ps})
            con = sorted({(lab, p, n) for cps, crpc, (lab, real), p, n, code in labelled
                          if cps == ps and crpc == rpc and real})
            other = sorted({(lab, p, n) for cps, crpc, (lab, real), p, n, code in labelled
                            if cps == ps and crpc == rpc and not real})
            prov_txt = "; ".join(f"`{s}` ({d._ref(p, n)})" for s, p, n in prov) or "none found"
            con_txt = "; ".join(f"`{s}` ({d._ref(p, n)})" for s, p, n in con) or "none found"
            oth_txt = "; ".join(f"{s} ({d._ref(p, n)})" for s, p, n in other) or "none found"
            rows.append((f"`{pkg}.{ps}/{rpc}`", prov_txt, con_txt, oth_txt, (pp, pl)))
            if not prov:
                d.omit(f"provider of `{pkg}.{ps}/{rpc}`", "no server registration for this proto service found")
            if not con:
                d.omit(f"service consumer of `{pkg}.{ps}/{rpc}`", "no stub method call found in non-generated service code")
    d.body.append("")
    d.table(["RPC", "Provider (registration)", "Service consumers (call site)", "Non-service callers (call site)"], rows)
    return d


# --------------------------------------------------------------------------- doc 08

def doc08():
    d = Doc(8, "Go files of `src/frontend` are scanned for gorilla/mux router registrations "
               "(`<router>.HandleFunc(path, handler).Methods(...)` and `<router>.PathPrefix(path).Handler(...)`); "
               "handler functions are resolved to their `func (... ) <name>(` definitions; the handler wrapping "
               "chain and the listen call are read from the same file. Other HTTP endpoint registrations are "
               "searched in all non-generated service code (`HandleFunc`, `MapGet/MapPost`, `http.Handle`). HTTP "
               "requests to these paths in `src/loadgenerator` and frontend templates are listed as callers.")
    fe = [p for p in code_files("frontend") if p.endswith(".go")]
    defs = {}
    for p in fe:
        for j, line in enumerate(read_lines(p), 1):
            m = re.match(r"func\s+\([^)]*\)\s+(\w+)\(", line)
            if m:
                defs.setdefault(m.group(1), (p, j, line.strip()))
    routes, router_facts = [], []
    for p in fe:
        lines = read_lines(p)
        for j, raw in enumerate(lines, 1):
            s = raw.strip()
            m = re.match(r'(\w+)\.NewRouter\(\)', s.split(":=")[-1].strip()) if ":=" in s else None
            if m:
                router_facts.append((f"Router created: `{s}`", p, j))
            m = re.match(r'(\w+)\.HandleFunc\("([^"]*)",\s*(.*)$', s)
            if m:
                router, path, rest = m.groups()
                meth = re.search(r"\.Methods\(([^)]*)\)\s*$", rest)
                if meth:
                    consts = [x.strip() for x in meth.group(1).split(",")]
                    methods = ", ".join(f"{c.replace('http.Method', '').upper()} (`{c}`)" for c in consts)
                    hexpr = rest[:meth.start()].rstrip()
                    hexpr = hexpr[:-1] if hexpr.endswith(")") else hexpr
                else:
                    methods = "no `.Methods(...)` restriction registered"
                    hexpr = rest[:-1] if rest.endswith(")") else rest
                if hexpr.startswith("func("):
                    handler, hdef = f"inline function `{hexpr}`", "-"
                else:
                    name = hexpr.split(".")[-1]
                    hd = defs.get(name)
                    handler = f"`{hexpr}`"
                    hdef = f"`{hd[2]}` ({d._ref(hd[0], hd[1])})" if hd else "definition not found"
                    if not hd:
                        d.omit(f"definition of handler `{hexpr}`", "no matching function definition in `src/frontend`")
                routes.append((f"`{path}`", "exact path", methods, handler, hdef, (p, j)))
            m = re.match(r'(\w+)\.PathPrefix\("([^"]*)"\)\.Handler\((.*)\)\s*$', s)
            if m:
                routes.append((f"`{m.group(2)}`", "path prefix", "no `.Methods(...)` restriction registered",
                               f"`{m.group(3)}`", "-", (p, j)))
    d.section("Frontend HTTP routes")
    for t, p, j in router_facts:
        d.fact(t, p, j)
    d.body.append("")
    d.table(["Path", "Match", "HTTP methods", "Handler", "Handler definition"], routes)

    d.section("Frontend request handling chain")
    for p in fe:
        for j, raw in enumerate(read_lines(p), 1):
            s = raw.strip()
            m = re.match(r"(?:var\s+)?handler\s*(?:http\.Handler\s*)?=\s*(.+?)\s*(?://\s*(.*))?$", s)
            if m:
                code = s.split("//")[0].strip()
                d.fact(f"Handler assignment: `{code}`" + (f" (code comment: \"{m.group(2)}\")" if m.group(2) else ""), p, j)
            if "ListenAndServe(" in s:
                d.fact(f"Server start: `{s}`", p, j)
            m = re.match(r'(port|srvPort|addr)\s*(?::=|=)\s*(.+)$', s)
            if m:
                d.fact(f"Listen setting: `{s}`", p, j)

    d.section("Other HTTP endpoints in service code")
    other = []
    for svc in services():
        if svc == "frontend":
            continue
        for p in code_files(svc):
            for j, raw in enumerate(read_lines(p), 1):
                s = raw.strip()
                m = re.search(r'\.(MapGet|MapPost|MapPut|MapDelete|HandleFunc|Handle)\("([^"]*)"', s) or \
                    re.search(r'@\w+\.route\("([^"]*)"', s)
                if m:
                    verb = m.group(1) if m.lastindex == 2 else "route"
                    path = m.group(m.lastindex)
                    meth = {"MapGet": "GET", "MapPost": "POST", "MapPut": "PUT", "MapDelete": "DELETE"}.get(verb, "not restricted in the registration")
                    other.append((f"`{svc}`", f"`{path}`", f"{meth} (`{verb}`)", f"`{s}`", (p, j)))
    if other:
        d.body.append("")
        d.table(["Service", "Path", "HTTP method", "Registration code"], other)
    else:
        d.omit("HTTP endpoints outside `src/frontend`", "no HTTP route registration found in non-generated service code")

    d.section("Callers of frontend routes")
    callers = []
    for p in sorted(rel(x) for x in (REPO / "src/loadgenerator").rglob("*.py")):
        for j, raw in enumerate(read_lines(p), 1):
            for m in re.finditer(r'\.client\.(get|post|put|delete)\(\s*"([^"]*)"(\s*\+)?', raw):
                callers.append(("`loadgenerator`", m.group(1).upper(), f"`{m.group(2)}`" + (" + (expression)" if m.group(3) else ""),
                                f"`{raw.strip()}`", (p, j)))
    for p in sorted(rel(x) for x in (REPO / "src/frontend/templates").rglob("*.html")):
        for j, raw in enumerate(read_lines(p), 1):
            if "<form" in raw:
                a = re.search(r'action="([^"]*)"', raw)
                mth = re.search(r'method="([^"]*)"', raw)
                if a:
                    callers.append(("`frontend` template form", mth.group(1).upper() if mth else "(method attribute absent)",
                                    f"`{a.group(1)}`", f"`{raw.strip()}`", (p, j)))
    d.body.append("")
    d.table(["Caller", "HTTP method", "Path", "Code"], callers)
    return d


def build():
    protos = load_protos()
    return [doc05(protos), doc06(protos), doc07(protos), doc08()]
