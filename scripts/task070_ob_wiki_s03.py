"""Online Boutique team wiki, sections 03 Code & Behavior and 04 Data & Storage (documents 09-15).

Every row is produced by regex / line scanning of the pinned repository (see
`task070_ob_wiki_common.py`). Only template wording is fixed text; names, values,
counts and line numbers come from repository content. Repository code is never built
or executed.
"""
import json
import re
import sys
from collections import Counter, defaultdict

from task070_ob_wiki_common import Doc, REPO, read_lines, rel, services

LANG = {".go": "Go", ".cs": "C#", ".js": "Node.js", ".py": "Python", ".java": "Java"}
GEN_NOTE = ("Generated code is skipped: files under `genproto/`, Python `*_pb2*.py` modules, "
            "`node_modules/`, and `proto/` / `protos/` copies inside service directories.")
TEST_NOTE = "Test files are `*_test.go`, files under `tests/`, and `*Tests.cs`."


# ----------------------------------------------------------------------------- basics

def is_generated(p):
    parts = p.split("/")
    return ("genproto" in parts or "_pb2" in parts[-1] or "node_modules" in parts
            or "proto" in parts[:-1] or "protos" in parts[:-1])


def is_test(p):
    name = p.rsplit("/", 1)[-1]
    return name.endswith("_test.go") or "/tests/" in p or name.endswith("Tests.cs")


def lang_of(p):
    for ext, lang in LANG.items():
        if p.endswith(ext):
            return lang
    return None


_FILES = {}


def code_files(svc, tests=True):
    if svc not in _FILES:
        out = []
        for f in sorted((REPO / "src" / svc).rglob("*")):
            if f.is_file() and f.suffix in LANG:
                r = rel(f)
                if not is_generated(r):
                    out.append(r)
        _FILES[svc] = out
    return [f for f in _FILES[svc] if tests or not is_test(f)]


_LINES = {}


def lines_of(path):
    if path not in _LINES:
        _LINES[path] = read_lines(path)
    return _LINES[path]


_STR = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`')


def code_only(line, lang):
    s = _STR.sub('""', line)
    return s.split("#", 1)[0] if lang == "Python" else s.split("//", 1)[0]


def is_comment(line, lang):
    s = line.strip()
    if lang == "Python":
        return s.startswith("#")
    return s.startswith(("//", "/*", "*"))


def brace_end(path, line):
    """1-based last line of the brace block that opens at or after `line`."""
    lines, lang = lines_of(path), lang_of(path)
    depth, started = 0, False
    for j in range(line - 1, len(lines)):
        for ch in code_only(lines[j], lang):
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}" and started:
                depth -= 1
                if depth == 0:
                    return j + 1
    return len(lines)


def indent(s):
    return len(s) - len(s.lstrip())


def py_block_end(path, line):
    lines = lines_of(path)
    base = indent(lines[line - 1])
    last = line
    for j in range(line, len(lines)):
        s = lines[j]
        if not s.strip():
            continue
        if indent(s) <= base:
            break
        last = j + 1
    return last


def block_end(path, line):
    return py_block_end(path, line) if lang_of(path) == "Python" else brace_end(path, line)


def first_literal(text):
    m = re.search(r'\$?"((?:\\.|[^"\\])*)"|\'((?:\\.|[^\'\\])*)\'|`([^`]*)`', text)
    if not m:
        return None
    return next(g for g in m.groups() if g is not None)


def code(s):
    s = s.strip().replace("`", "'")
    return f"`{s}`"


def svc_of(path):
    return path.split("/")[1] if path.startswith("src/") else "-"


# ----------------------------------------------------------------------------- symbols

class Sym:
    def __init__(self, path, line, kind, name, container="", detail="", recv=""):
        self.path, self.line, self.kind, self.name = path, line, kind, name
        self.container, self.detail, self.recv = container, detail, recv
        self.end = line

    @property
    def callable(self):
        return self.kind in ("function", "method", "constructor")


GO_METH = re.compile(r'^func\s+\((\w+)\s+(\*?\w+)\)\s+(\w+)\s*\(')
GO_FUNC = re.compile(r'^func\s+(\w+)\s*\(')
GO_TYPE = re.compile(r'^type\s+(\w+)\s+(struct|interface)\b')
TYPE = r'[\w\.\[\]?]+(?:<[^()]*>)?(?:\[\])*'
CS_MODS = r'(?:public|private|protected|internal|static|async|override|virtual|abstract|sealed|extern|readonly|unsafe)'
JAVA_MODS = r'(?:public|private|protected|static|final|synchronized|abstract|native)'
CS_METH = re.compile(rf'^\s*((?:{CS_MODS}\s+)*)(?:({TYPE})\s+)?(\w+)\s*\(')
JAVA_METH = re.compile(rf'^\s*((?:{JAVA_MODS}\s+)*)(?:({TYPE})\s+)?(\w+)\s*\(')
CS_CLASS = re.compile(r'^\s*(?:(?:public|private|protected|internal|static|sealed|abstract|partial)\s+)*(class|interface)\s+(\w+)(?:\s*:\s*([\w\.<>, ]+))?')
JAVA_CLASS = re.compile(r'^\s*(?:(?:public|private|protected|static|final|abstract)\s+)*(class|interface|enum)\s+(\w+)(?:\s+extends\s+([\w\.]+))?')
JS_CLASS = re.compile(r'^\s*class\s+(\w+)(?:\s+extends\s+(\w+))?')
JS_FUNC = re.compile(r'(?:^|[\s=(])(?:async\s+)?function\s+(\w+)\s*\(')
JS_METH = re.compile(r'^\s*((?:static|async)\s+)*(\w+)\s*\([^)]*\)\s*\{\s*$')
PY_DEF = re.compile(r'^(\s*)def\s+(\w+)\s*\(')
PY_CLASS = re.compile(r'^(\s*)class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:')
KW = {"if", "for", "foreach", "while", "switch", "catch", "using", "lock", "return", "new", "await", "throw",
      "else", "this", "super", "base", "typeof", "nameof", "sizeof", "default", "case", "var", "yield", "in",
      "is", "as", "do", "try", "finally", "synchronized", "function", "await"}


def close_paren(s, i):
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                return j
    return None


_SYMS = {}


def symbols(path):
    if path in _SYMS:
        return _SYMS[path]
    lang, lines = lang_of(path), lines_of(path)
    out = []
    if lang == "Go":
        for i, s in enumerate(lines, 1):
            m = GO_METH.match(s)
            if m:
                out.append(Sym(path, i, "method", m.group(3), m.group(2).lstrip("*"), f"receiver ({m.group(1)} {m.group(2)})", m.group(1)))
                continue
            m = GO_FUNC.match(s)
            if m:
                out.append(Sym(path, i, "function", m.group(1)))
                continue
            m = GO_TYPE.match(s)
            if m:
                out.append(Sym(path, i, f"{m.group(2)} type", m.group(1)))
        for y in out:
            y.end = brace_end(path, y.line)
    elif lang in ("C#", "Java"):
        crx, mrx = (CS_CLASS, CS_METH) if lang == "C#" else (JAVA_CLASS, JAVA_METH)
        classes = []
        for i, s in enumerate(lines, 1):
            if is_comment(s, lang):
                continue
            m = crx.match(s)
            if m:
                y = Sym(path, i, m.group(1), m.group(2), detail=(f"base: {m.group(3).strip()}" if m.group(3) else ""))
                y.end = brace_end(path, i)
                classes.append(y)
                out.append(y)
        for i, s in enumerate(lines, 1):
            if is_comment(s, lang) or crx.match(s):
                continue
            cs = code_only(s, lang)
            m = mrx.match(cs)
            if not m:
                continue
            mods, typ, name = m.group(1).strip(), m.group(2), m.group(3)
            if "=" in cs[:m.end() - 1] or name in KW or (typ and typ in KW) or not (mods or typ):
                continue
            encl = [c for c in classes if c.line < i <= c.end]
            container = encl[-1] if encl else None
            cp = close_paren(cs, m.end() - 1)
            if cp is not None:
                rest = cs[cp + 1:].strip()
                ok = rest in ("", "{") or rest.startswith(("{", "=>", ":", "throws"))
                if rest == ";" and container is not None and container.kind == "interface":
                    ok = True
                if not ok:
                    continue
            prev = next((lines[k].strip() for k in range(i - 2, -1, -1) if lines[k].strip()), "")
            kind = "constructor" if container is not None and name == container.name and not typ else "method"
            y = Sym(path, i, kind, name, container.name if container else "",
                    " ".join(x for x in [mods, (f"returns {typ}" if typ else ""), ("@Override" if prev.startswith("@Override") else "")] if x))
            y.end = i if cs.rstrip().endswith(";") else brace_end(path, i)
            out.append(y)
        out.sort(key=lambda y: y.line)
    elif lang == "Node.js":
        classes = []
        for i, s in enumerate(lines, 1):
            if is_comment(s, lang):
                continue
            m = JS_CLASS.match(s)
            if m:
                y = Sym(path, i, "class", m.group(1), detail=(f"extends {m.group(2)}" if m.group(2) else ""))
                y.end = brace_end(path, i)
                classes.append(y)
                out.append(y)
                continue
            m = JS_FUNC.search(s)
            if m:
                y = Sym(path, i, "function", m.group(1), detail=("module.exports" if "module.exports" in s else ""))
                y.end = brace_end(path, i)
                out.append(y)
                continue
            m = re.match(r'^\s*module\.exports(?:\.(\w+))?\s*=\s*(.+?);?\s*$', s)
            if m:
                out.append(Sym(path, i, "module.exports", m.group(1) or m.group(2)))
        for c in classes:
            depth = 0
            for i in range(c.line, c.end + 1):
                cs = code_only(lines[i - 1], lang)
                m = JS_METH.match(cs)
                if i > c.line and depth == 1 and m and m.group(2) not in KW:
                    y = Sym(path, i, "constructor" if m.group(2) == "constructor" else "method", m.group(2), c.name,
                            (m.group(1) or "").strip())
                    y.end = brace_end(path, i)
                    out.append(y)
                depth += cs.count("{") - cs.count("}")
        out.sort(key=lambda y: y.line)
    elif lang == "Python":
        stack = []
        for i, s in enumerate(lines, 1):
            m = PY_CLASS.match(s) or PY_DEF.match(s)
            if not m:
                continue
            ind = len(m.group(1))
            while stack and stack[-1][0] >= ind:
                stack.pop()
            container = stack[-1][1] if stack and stack[-1][2] == "class" else ""
            if s.lstrip().startswith("class"):
                y = Sym(path, i, "class", m.group(2), container, f"bases: {m.group(3)}" if m.group(3) else "")
                stack.append((ind, m.group(2), "class"))
            else:
                y = Sym(path, i, "method" if container else "function", m.group(2), container)
                stack.append((ind, m.group(2), "def"))
            y.end = py_block_end(path, i)
            out.append(y)
    _SYMS[path] = out
    return out


def enclosing(path, line):
    best = None
    for y in symbols(path):
        if y.callable and y.line <= line <= y.end:
            if best is None or y.line >= best.line:
                best = y
    return best


def encl_name(path, line):
    y = enclosing(path, line)
    if y is None:
        return "(top level)"
    return f"{y.container}.{y.name}" if y.container else y.name


# ----------------------------------------------------------------------------- proto / registrations

def proto_services():
    out = {}
    for path in ("protos/demo.proto", "protos/grpc/health/v1/health.proto"):
        cur = None
        for i, s in enumerate(lines_of(path), 1):
            m = re.match(r'^\s*service\s+(\w+)', s)
            if m:
                cur = m.group(1)
                out[cur] = {"path": path, "line": i, "rpcs": []}
                continue
            m = re.match(r'^\s*rpc\s+(\w+)\s*\(', s)
            if m and cur:
                out[cur]["rpcs"].append((m.group(1), i))
    return out


def registrations(svc):
    """[(proto service, path, line, handler symbols)] found by registration call regexes."""
    protos = proto_services()
    regs = []
    files = code_files(svc, tests=False)
    allsyms = [y for f in files for y in symbols(f)]
    for f in files:
        lang, lines = lang_of(f), lines_of(f)
        if lang == "Go":
            for i, s in enumerate(lines, 1):
                m = re.search(r'\b\w+\.Register(\w+)Server\(', s)
                if m:
                    name = m.group(1)
                    rpcs = {r for r, _ in protos.get(name, {}).get("rpcs", [])}
                    hs = [y for y in allsyms if y.kind == "method" and y.name in rpcs]
                    regs.append((name, f, i, hs))
        elif lang == "Python":
            for i, s in enumerate(lines, 1):
                m = re.search(r'add_(\w+)Servicer_to_server\(', s)
                if m:
                    name = m.group(1)
                    rpcs = {r for r, _ in protos.get(name, {}).get("rpcs", [])}
                    hs = [y for y in allsyms if y.kind == "method" and y.name in rpcs and lang_of(y.path) == "Python"
                          and y.path == f]
                    regs.append((name, f, i, hs))
        elif lang == "Node.js":
            text = "\n".join(lines)
            for m in re.finditer(r'addService\(\s*[\w\.]*?(\w+)\.service\s*,\s*\{([^}]*)\}', text, re.S):
                line = text.count("\n", 0, m.start()) + 1
                hs = []
                for entry in m.group(2).split(","):
                    entry = entry.strip()
                    if not entry:
                        continue
                    target = entry.split(":", 1)[-1].strip()
                    target = re.sub(r'\.bind\(.*$', "", target).split(".")[-1]
                    hs += [y for y in allsyms if y.callable and y.name == target]
                regs.append((m.group(1), f, line, hs))
        elif lang == "C#":
            for i, s in enumerate(lines, 1):
                m = re.search(r'MapGrpcService<([\w\.]+)>', s)
                if m:
                    cname = m.group(1).split(".")[-1]
                    cls = [y for y in allsyms if y.kind == "class" and y.name == cname]
                    name = cname
                    if cls:
                        bm = re.search(r'(\w+)Base\b', cls[0].detail)
                        if bm:
                            name = bm.group(1)
                    rpcs = {r for r, _ in protos.get(name, {}).get("rpcs", [])}
                    hs = [y for y in allsyms if y.kind == "method" and y.container == cname and y.name in rpcs]
                    regs.append((name, f, i, hs))
        elif lang == "Java":
            for i, s in enumerate(lines, 1):
                m = re.search(r'extends\s+[\w\.]*?(\w+)Grpc\.\w+ImplBase', s)
                if m:
                    name = m.group(1)
                    rpcs = {r.lower() for r, _ in protos.get(name, {}).get("rpcs", [])}
                    cname = JAVA_CLASS.match(s).group(2)
                    hs = [y for y in allsyms if y.kind == "method" and y.container == cname and y.name.lower() in rpcs]
                    regs.append((name, f, i, hs))
                m = re.search(r'addService\((\w+)\.getHealthService\(\)\)', s)
                if m:
                    regs.append(("Health", f, i, []))
    return regs


def http_routes():
    out = []
    path = "src/frontend/main.go"
    for i, s in enumerate(lines_of(path), 1):
        m = re.search(r'\.HandleFunc\("([^"]+)",\s*(\w+)\.(\w+)\)(?:\.Methods\(([^)]*)\))?', s)
        if m:
            meth = ", ".join(x.replace("http.Method", "").strip() for x in (m.group(4) or "").split(",") if x.strip())
            out.append((m.group(1), meth, m.group(3), path, i, False))
            continue
        m = re.search(r'\.HandleFunc\("([^"]+)",\s*func\(', s)
        if m:
            out.append((m.group(1), "", "(inline func)", path, i, True))
    return out


# ----------------------------------------------------------------------------- call scanning

def stub_bindings(svc):
    """{variable: proto service} for stub/client variables (all non-test files of the service)."""
    rx = [r'(\w+)\s*:?=\s*pb\.New(\w+)Client\([^()]*\)\s*$',
          r'(\w+)\s*=\s*demo_pb2_grpc\.(\w+)Stub\(',
          r'(\w+)\s*=\s*new\s+\w+\.(\w+Service)\(',
          r'(\w+)\s*=\s*[\w\.]*?(\w+)Grpc\.new\w*Stub\(']
    out = {}
    for f in code_files(svc, tests=False):
        for i, s in enumerate(lines_of(f), 1):
            for r in rx:
                m = re.search(r, code_only(s, lang_of(f)))
                if m:
                    out[m.group(1)] = (m.group(2), f, i)
    return out


DATA_RX = [  # (regex, operation, data source label template using groups)
    (r'_cache\.(GetAsync)\((\w+)', "read", "IDistributedCache `_cache`, key `{2}`"),
    (r'_cache\.(SetAsync)\((\w+)', "write", "IDistributedCache `_cache`, key `{2}`"),
    (r'\.(CreateSelectCommand)\(', "read", "Spanner command `{1}`"),
    (r'\.(CreateInsertOrUpdateCommand)\((\w+)', "write", "Spanner command `{1}` on `{2}`"),
    (r'\.(CreateDmlCommand)\(', "write", "Spanner command `{1}`"),
    (r'dataSource\.(CreateCommand)\((\w+)\)', "sql", "Npgsql `dataSource.{1}({2})`"),
    (r'\.(AccessSecretVersion)\(', "read", "Secret Manager `{1}`"),
    (r'os\.(ReadFile)\("([^"]+)"\)', "read", "file `{2}`"),
    (r'\br\.(Cookie)\((\w+)\)', "read", "HTTP cookie `{2}`"),
    (r'\br\.(Cookies)\(\)', "read", "all HTTP cookies"),
    (r'http\.(SetCookie)\(w,', "write", "HTTP cookie"),
    (r'templates\.(ExecuteTemplate)\(w,\s*"(\w+)"', "read", "HTML template `{2}`"),
    (r'\.(ParseGlob)\("([^"]+)"\)', "read", "HTML templates `{2}`"),
    (r'(deploymentDetailsMap)\["(\w+)"\]\s*=', "write", "in-memory map `{1}[{2}]`"),
    (r'metaServerClient\.(\w+)\(', "read", "GCE metadata server `{1}`"),
    (r"require\('(\./data/[^']+)'\)", "read", "file `{1}`"),
    (r"get_template\('([^']+)'\)", "read", "Jinja2 template `{1}`"),
    (r"FileSystemLoader\('([^']+)'\)", "read", "Jinja2 template directory `{1}`"),
    (r'\btemplate\.(render)\(', "read", "Jinja2 template object `template`"),
    (r'\b(adsMap)\.(get|values)\(', "read", "in-memory multimap `{1}`"),
    (r'\bp\.(catalog)\.Products\b', "read", "in-memory catalog `p.{1}`"),
]
SQL_VERB = re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE)\b')


def data_hits(path, line):
    s = lines_of(path)[line - 1]
    if is_comment(s, lang_of(path)):
        return []
    out = []
    for rx, op, label in DATA_RX:
        for m in re.finditer(rx, s):
            g = (m.group(0),) + m.groups()
            lab = label.format(*g)
            sql = None
            window = " ".join(x.strip() for x in lines_of(path)[line - 1:line + 1])
            vm = SQL_VERB.search(window)
            if label.startswith("Npgsql"):
                var = m.group(2)
                for k in range(line - 1, max(0, line - 15), -1):
                    am = re.search(rf'\b{var}\s*=\s*\$?"(.*)"', lines_of(path)[k - 1])
                    if am:
                        sql = (am.group(1), k)
                        break
                vm = SQL_VERB.search(sql[0]) if sql else None
            elif "Spanner" in label:
                sm = re.search(r'\$?"((?:SELECT|INSERT|UPDATE|DELETE)[^"]*)"', window)
                sql = (sm.group(1), line) if sm else None
            opx = op
            if op == "sql" or (vm and "Spanner" in label and op == "write"):
                opx = ("read" if vm and vm.group(1) == "SELECT" else "write") if vm else "UNRESOLVED"
            out.append({"col": m.start(), "kind": "data", "op": opx, "label": lab, "sql": sql,
                        "path": path, "line": line, "end": line})
    return out


def scan(svc, sym, chain=(), loops=(), seen=None, index=None, stubs=None):
    """Ordered events (stub calls, HTTP calls, data access) reachable from `sym` inside the service."""
    seen = set() if seen is None else seen
    if (sym.path, sym.line) in seen:
        return []
    seen = seen | {(sym.path, sym.line)}
    if index is None:
        index = defaultdict(list)
        for f in code_files(svc, tests=False):
            for y in symbols(f):
                if y.callable:
                    index[y.name].append(y)
        stubs = stub_bindings(svc)
    lang, lines = lang_of(sym.path), lines_of(sym.path)
    loop_spans = []
    for i in range(sym.line + 1, sym.end + 1):
        s = lines[i - 1]
        if (lang == "Python" and re.match(r'^\s*for\b.*:\s*$', s)) or (lang != "Python" and re.match(r'^\s*(for|foreach|while)\b', s)):
            loop_spans.append((i, block_end(sym.path, i)))
    events = []
    first = sym.line if sym.end == sym.line else sym.line + 1
    for i in range(first, sym.end + 1):
        raw = lines[i - 1]
        if is_comment(raw, lang):
            continue
        s = code_only(raw, lang)
        here = []
        lp = tuple(loops) + tuple((sym.path, a) for a, b in loop_spans if a <= i <= b and a != i)
        nxt = code_only(lines[i], lang) if i < len(lines) else ""
        for m in re.finditer(r'pb\.New(\w+)Client\([^()]*\)\s*\.\s*(\w+)\s*\(', s):
            here.append({"col": m.start(), "kind": "gRPC", "target": m.group(1), "method": m.group(2), "end": i})
        m = re.search(r'pb\.New(\w+)Client\([^()]*\)\s*\.\s*$', s)
        if m:
            m2 = re.match(r'^\s*(\w+)\s*\(', nxt)
            if m2:
                here.append({"col": m.start(), "kind": "gRPC", "target": m.group(1), "method": m2.group(1), "end": i + 1})
        for m in re.finditer(r'\b(\w+)\.(\w+)\s*\(', s):
            if m.group(1) in stubs:
                here.append({"col": m.start(), "kind": "gRPC", "target": stubs[m.group(1)][0], "method": m.group(2),
                             "end": i, "stub": stubs[m.group(1)]})
        for m in re.finditer(r'\bhttp\.(Get|Post|Head|PostForm)\s*\(([^)]*)\)', s):
            here.append({"col": m.start(), "kind": "HTTP", "target": f"http.{m.group(1)}({m.group(2)})", "method": m.group(1).upper(), "end": i})
        for e in here:
            e.update(path=sym.path, line=i, chain=chain, loops=lp)
        for d in data_hits(sym.path, i):
            d.update(chain=chain, loops=lp)
            here.append(d)
        # calls to other functions of the same service
        for m in re.finditer(r'(?:(\w+)\.)?(\w+)\s*\(', s):
            qual, name = m.group(1), m.group(2)
            if name == sym.name or name not in index or qual in stubs:
                continue
            if lang == "Go" and qual and qual != sym.recv:
                continue
            if lang == "Go" and not qual and m.start() > 0 and s[m.start() - 1] == ".":
                continue
            for tgt in index[name]:
                if lang == "Go" and qual and tgt.kind != "method":
                    continue
                if lang == "Go" and not qual and tgt.kind != "function":
                    continue
                if lang_of(tgt.path) != lang:
                    continue
                sub = scan(svc, tgt, chain + ((f"{tgt.container}.{tgt.name}" if tgt.container else tgt.name, sym.path, i),),
                           lp, seen, index, stubs)
                for e in sub:
                    e.setdefault("col_outer", m.start())
                here += [dict(e, col=m.start(), sub=True) for e in sub]
        here.sort(key=lambda e: (e["col"], e.get("sub", False)))
        events += here
    return events


def handlers(svc):
    """[(label, handler Sym)] for gRPC handlers and HTTP handlers."""
    out = []
    for name, f, i, hs in registrations(svc):
        for y in sorted(hs, key=lambda y: (y.path, y.line)):
            out.append((f"gRPC {name}.{y.name}", y, (f, i)))
    if svc == "frontend":
        allsyms = [y for f in code_files(svc, tests=False) for y in symbols(f)]
        for route, meth, hname, path, line, inline in http_routes():
            if inline:
                y = Sym(path, line, "function", "(inline)")
                y.end = line
                out.append((f"HTTP {route} (inline func, no .Methods)", y, (path, line)))
                continue
            for y in allsyms:
                if y.kind == "method" and y.name == hname:
                    out.append((f"HTTP {meth} {route} -> {hname}", y, (path, line)))
    return out


# ============================================================================= 09

def doc09():
    d = Doc(9, "Source files are all `.go`, `.cs`, `.js`, `.py`, `.java` files under each `src/<service>/`. "
               + GEN_NOTE + " " + TEST_NOTE + " Definitions are matched line by line: Go `^func` (with receiver for methods) "
               "and `^type X struct|interface`; C# and Java class/interface declarations and method/constructor "
               "signatures (modifier and/or return type, identifier, `(`; lines with `=` before `(` and statement keywords "
               "are excluded); Node.js `class`, named `function`, class methods at class brace depth 1, and "
               "`module.exports` assignments; Python `class` and `def` with the enclosing class from indentation. "
               "End lines come from brace matching (Python: indentation). Anonymous functions and lambdas are not listed.")
    total = Counter()
    for svc in services():
        files = code_files(svc)
        d.section(svc)
        if not files:
            d.omit(f"{svc} source code", "no source file with a listed extension under `src/" + svc + "/`")
            continue
        d.section("Source files", 3)
        d.table(["File", "Language", "Lines", "Test file"],
                [(code(f), lang_of(f), len(lines_of(f)), "yes" if is_test(f) else "no", (f, 1, len(lines_of(f)))) for f in files])
        rows = []
        for f in files:
            for y in symbols(f):
                total[(lang_of(f), y.kind)] += 1
                rows.append((y.kind, code(y.name), code(y.container) if y.container else "-", y.detail or "-", (f, y.line, y.end)))
        d.section("Top-level definitions", 3)
        if rows:
            d.table(["Kind", "Name", "Container", "Detail"], rows)
        else:
            d.omit(f"{svc} definitions", "no definition matched the extraction rules")
    d.section("Totals by language and kind (counts of the definition rows above)")
    d.body += ["| Language | Kind | Count |", "|---|---|---|"]
    d.body += [f"| {l} | {k} | {n} |" for (l, k), n in sorted(total.items())] + [""]
    return d


# ============================================================================= 10

def fmt_chain(e):
    if not e["chain"]:
        return "direct"
    return " -> ".join(f"{n} (called at `{p}:L{l}`)" for n, p, l in e["chain"])


def fmt_loops(e):
    return ", ".join(f"`{p}:L{l}`" for p, l in e["loops"]) or "-"


def doc10():
    d = Doc(10, "Handlers are (a) methods implementing an RPC of a gRPC service that the service registers "
                "(`RegisterXServer`, `add_XServicer_to_server`, `addService(...)`, `MapGrpcService<T>`, `extends XGrpc.XImplBase`), "
                "matched by RPC name from `protos/demo.proto` and `protos/grpc/health/v1/health.proto`, and (b) frontend HTTP "
                "handlers registered with `HandleFunc` in `src/frontend/main.go`. Each handler body is scanned line by line in "
                "source order for outgoing calls: Go `pb.NewXClient(conn).Method(` (also split over two lines and through a "
                "client variable), calls on stub variables (`demo_pb2_grpc.XStub`, `pb.NewXClient`), and `http.Get/Post`. Calls "
                "to functions of the same service are followed recursively (Go: receiver methods via the receiver variable and "
                "package functions) and shown with the call chain. 'Loop' lists `for`/`foreach`/`while` headers whose block "
                "contains the call. Calls inside `go func` goroutines or callbacks are listed at their source position. "
                + GEN_NOTE + " Test files are not scanned.")
    summary = []
    for svc in services():
        hs = handlers(svc)
        if not hs:
            continue
        d.section(svc)
        for label, y, reg in hs:
            evs = [e for e in scan(svc, y) if e["kind"] in ("gRPC", "HTTP")]
            d.section(f"{label} (`{y.path}:L{y.line}`)", 3)
            d.fact(f"Handler `{(y.container + '.') if y.container else ''}{y.name}` registered at `{reg[0]}:L{reg[1]}`", y.path, y.line, y.end)
            if not evs:
                d.fact("No outgoing service call found in the handler body or in same-service functions it calls", y.path, y.line, y.end)
                summary.append((svc, label, "none", (y.path, y.line, y.end)))
                continue
            rows = []
            for n, e in enumerate(evs, 1):
                tgt = e["target"] if e["kind"] == "HTTP" else f"{e['target']}.{e['method']}"
                rows.append((n, e["kind"], code(tgt), fmt_chain(e), fmt_loops(e),
                             code(lines_of(e["path"])[e["line"] - 1]), (e["path"], e["line"], e["end"])))
            d.table(["#", "Kind", "Target", "Via", "Loop", "Call line"], rows)
            seq = " -> ".join((e["target"] if e["kind"] == "HTTP" else f"{e['target']}.{e['method']}") for e in evs)
            summary.append((svc, label, seq, (y.path, y.line, y.end)))
    d.section("Summary: ordered outgoing calls per handler")
    d.table(["Service", "Handler", "Sequence"], summary)
    # non-handler HTTP client code (load generator)
    rows = []
    for f in code_files("loadgenerator", tests=False):
        for i, s in enumerate(lines_of(f), 1):
            m = re.search(r'\.client\.(get|post)\((.*)$', s)
            if m:
                rows.append((code(encl_name(f, i)), m.group(1).upper(), code(s), (f, i)))
    if rows:
        d.section("Load generator HTTP requests (client code, no server handler)")
        d.table(["Task function", "Method", "Call line"], rows)
    for svc in services():
        if svc != "loadgenerator" and not handlers(svc):
            d.omit(f"{svc} handlers", "no gRPC registration or HTTP route matched the extraction rules")
    return d


# ============================================================================= 11

def scan_lines(svcs=None, tests=False):
    for svc in (svcs or services()):
        for f in code_files(svc, tests=tests):
            lang = lang_of(f)
            for i, s in enumerate(lines_of(f), 1):
                if not is_comment(s, lang):
                    yield svc, f, lang, i, s


def msg(text):
    lit = first_literal(text)
    return code(lit) if lit is not None else code(text)


def doc11():
    d = Doc(11, "All non-test source files are scanned line by line (comment lines skipped). gRPC status: Go "
                "`status.Errorf(codes.X, ...)`, C# `new Status(StatusCode.X, ...)`, Python `context.set_code(grpc.StatusCode.X)` "
                "with the nearest preceding `context.set_details(...)` within 5 lines. Error values: Go `fmt.Errorf`, "
                "`errors.New/Wrap/Wrapf`; `throw new`; Python `raise`. HTTP errors: frontend `renderHTTPError(..., http.StatusX)`. "
                "Handlers: `catch (...)`, Python `except ...:`, Go `recover()`, plus the first statement of the handler. "
                "Termination: Go `panic(`/`log.Fatal*`. Timeouts: `context.WithTimeout/WithDeadline`, `awaitTermination(`, "
                "`timeout=`. Retries: loop headers whose block contains a sleep call, and `RunWithRetriable*` calls. "
                "Message column shows the first string literal of the call, or the argument expression when there is none. "
                + GEN_NOTE + " " + TEST_NOTE)
    st, errs, http_e, catches, term, tmo, retry, health, custom, discard = ([] for _ in range(10))
    hp = "protos/grpc/health/v1/health.proto"
    hl = lines_of(hp)
    es = next(i for i, s in enumerate(hl, 1) if re.match(r'^\s*enum\s+ServingStatus', s))
    serving = {m.group(1).replace("_", "") for s in hl[es:brace_end(hp, es)] for m in [re.match(r'^\s*(\w+)\s*=\s*\d+;', s)] if m}
    d.fact("Health `ServingStatus` enum values: " + ", ".join(f"`{m.group(1)}`" for s in hl[es:brace_end(hp, es)]
                                                           for m in [re.match(r'^\s*(\w+)\s*=\s*\d+;', s)] if m), hp, es, brace_end(hp, es))
    for svc, f, lang, i, s in scan_lines():
        lines = lines_of(f)
        where = code(encl_name(f, i))
        m = re.search(r'status\.Errorf\(codes\.(\w+),\s*(.+)\)\s*$', s)
        if m:
            st.append((svc, code(m.group(1)), msg(m.group(2)), where, (f, i)))
        m = re.search(r'new Status\(StatusCode\.(\w+),\s*(.+?)\)\)?;?\s*$', s)
        if m:
            st.append((svc, code(m.group(1)), msg(m.group(2)), where, (f, i)))
        m = re.search(r'context\.set_code\(grpc\.StatusCode\.(\w+)\)', s)
        if m:
            det = next((re.search(r'set_details\((.*)\)', lines[k - 1]).group(1) for k in range(i - 1, max(0, i - 6), -1)
                        if "set_details(" in lines[k - 1]), None)
            st.append((svc, code(m.group(1)), msg(det) if det else "-", where, (f, i)))
        for m in re.finditer(r'\b(fmt\.Errorf|errors\.New|errors\.Wrapf?)\((.*)', s):
            if "renderHTTPError" in s:
                continue
            errs.append((svc, code(m.group(1)), msg(m.group(2)), where, (f, i)))
        m = re.search(r'\bthrow new (\w+)\(', s)
        if m:
            cp = close_paren(s, m.end() - 1)
            args = s[m.end():cp].strip() if cp is not None else s[m.end():].strip()
            errs.append((svc, code(f"throw new {m.group(1)}"), msg(args) if args else "-", where, (f, i)))
        m = re.search(r'^\s*raise (\w+)\((.*)\)', s)
        if m:
            errs.append((svc, code(f"raise {m.group(1)}"), msg(m.group(2)) if m.group(2) else "-", where, (f, i)))
        m = re.search(r'renderHTTPError\(.*?(errors\.\w+\(.*?\)),\s*http\.(Status\w+)\)', s)
        if m:
            http_e.append((svc, code(m.group(2)), msg(m.group(1)), where, (f, i)))
        m = (re.search(r'\bcatch\s*\(\s*([\w\.]+)?', s) if lang != "Python" else re.search(r'^\s*except\b\s*(.*?)\s*:\s*$', s))
        if m or re.search(r'\brecover\(\)', s):
            nxt = next((lines[k].strip() for k in range(i, min(len(lines), i + 4))
                        if lines[k].strip() and lines[k].strip() != "{" and not is_comment(lines[k], lang)), "")
            caught = (m.group(1) if m and m.group(1) else ("recover()" if not m else "(any)"))
            catches.append((svc, code(caught), code(nxt) if nxt else "-", where, (f, i)))
        m = re.search(r'\b(panic|log\.Fatal\w*)\((.*)\)\s*$', s)
        if m and lang == "Go":
            term.append((svc, code(m.group(1)), code(m.group(2)), where, (f, i)))
        for rx in (r'context\.(WithTimeout|WithDeadline)\(\s*[^,]+,\s*(.+?)\)\s*$', r'\b(awaitTermination)\((.*?)\);',
                   r'\b(timeout)\s*=\s*([^,)]+)'):
            m = re.search(rx, s)
            if m and m.group(2).strip():
                tmo.append((svc, code(m.group(1)), code(m.group(2)), where, (f, i)))
        if (lang == "Python" and re.match(r'^\s*for\b.*:\s*$', s)) or (lang != "Python" and re.match(r'^\s*for\b', s)):
            end = block_end(f, i)
            sl = [k for k in range(i + 1, end + 1) if re.search(r'\b(time\.Sleep|time\.sleep|Thread\.sleep)\s*\(', lines[k - 1])]
            if sl:
                retry.append((svc, code(s), "; ".join(f"{code(lines[k - 1])} (L{k})" for k in sl), where, (f, i, end)))
        m = re.search(r'\b(RunWith\w*Retriable\w*)\(', s)
        if m:
            retry.append((svc, code(m.group(1)), "-", where, (f, i)))
        for rx in (r'HealthCheckResponse_(\w+)', r'HealthCheckResponse\.(\w+)\b', r'ServingStatus\.(\w+)', r"status:\s*'(\w+)'"):
            for m in re.finditer(rx, s):
                if m.group(1).replace("_", "").upper() in serving:
                    health.append((svc, code(m.group(1)), where, (f, i)))
        m = re.search(r'^\s*class\s+(\w+)\s+extends\s+(\w*Error)\b', s)
        if m:
            body = [k for k in range(i, block_end(f, i) + 1) if re.search(r'super\(|this\.code', lines[k - 1])]
            custom.append((svc, code(m.group(1)), code(m.group(2)),
                           "; ".join(f"{code(lines[k - 1])} (L{k})" for k in body) or "-", (f, i, block_end(f, i))))
        m = re.search(r'^\s*_\s*=\s*(.+)$', s)
        if m and lang == "Go":
            discard.append((svc, code(m.group(1)), where, (f, i)))
    d.section("gRPC status codes set by server code")
    d.table(["Service", "Status code", "Message", "Function"], st)
    d.section("Status code counts (counts of the rows above)")
    d.body += ["| Status code | Count |", "|---|---|"]
    d.body += [f"| {c} | {n} |" for c, n in sorted(Counter(r[1] for r in st).items())] + [""]
    d.section("Error values created or wrapped")
    d.table(["Service", "Construct", "Message", "Function"], errs)
    d.section("Custom error classes")
    if custom:
        d.table(["Service", "Class", "Extends", "Constructor lines"], custom)
    else:
        d.omit("Custom error classes", "no `class X extends ...Error` found")
    d.section("Frontend HTTP error responses (`renderHTTPError`)")
    d.table(["Service", "HTTP status", "Message", "Handler"], http_e)
    rh = [(f, i) for svc, f, lang, i, s in scan_lines(["frontend"]) if re.match(r'^func renderHTTPError\(', s)]
    for f, i in rh:
        d.quote(f, i, brace_end(f, i))
    d.section("Exception / error handlers")
    d.table(["Service", "Caught", "First statement", "Function"], catches)
    d.section("Process-terminating calls (Go)")
    d.table(["Service", "Call", "Argument", "Function"], term)
    d.section("Timeouts and deadlines")
    d.table(["Service", "Construct", "Value", "Function"], tmo)
    d.section("Retries")
    d.table(["Service", "Loop / call", "Sleep calls in loop", "Function"], retry)
    d.section("Discarded return values (Go `_ =`)")
    d.table(["Service", "Expression", "Function"], discard)
    d.section("Health-check status values")
    d.table(["Service", "Value", "Function"], health)
    if not [1 for _, f, lang, i, s in scan_lines() if re.search(r'\brecover\(\)', s)]:
        d.omit("Go panic recovery", "no `recover()` call in Go source")
    if not [1 for _, f, lang, i, s in scan_lines() if re.search(r'grpc\.(WithTimeout|WithBlock)|WithDeadline|withDeadline', s)]:
        d.omit("Per-RPC deadlines on gRPC client calls", "no `WithDeadline`/`withDeadline` call in source; the only client-side timeouts are the `context.WithTimeout` rows above")
    if not [1 for _, f, lang, i, s in scan_lines() if re.search(r'retry|Retry', s) and "grpc" in s.lower() and "Retriable" not in s]:
        d.omit("gRPC client retry policy", "no gRPC retry configuration in source")
    return d


# ============================================================================= 12

STDLIB = set(sys.stdlib_module_names)


def go_module(svc):
    p = REPO / "src" / svc / "go.mod"
    if not p.exists():
        return None
    for s in read_lines(p):
        m = re.match(r'^module\s+(\S+)', s)
        if m:
            return m.group(1)


def imports(f):
    """[(line, import name, verbatim)] third-party imports per language rule."""
    lang, lines = lang_of(f), lines_of(f)
    svc = svc_of(f)
    out = []
    if lang == "Go":
        mod = go_module(svc) or "\0"
        inblock = False
        for i, s in enumerate(lines, 1):
            t = s.strip()
            if t.startswith("import ("):
                inblock = True
                continue
            if inblock and t == ")":
                inblock = False
                continue
            m = re.match(r'^(?:import\s+)?(?:(\w+|\.|_)\s+)?"([^"]+)"', t) if (inblock or t.startswith("import ")) else None
            if m:
                p = m.group(2)
                if "." in p.split("/")[0] and not p.startswith(mod):
                    out.append((i, p, t))
    elif lang == "Python":
        here = {x.stem for x in (REPO / f).parent.glob("*.py")}
        for i, s in enumerate(lines, 1):
            m = re.match(r'^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))', s)
            if m:
                name = m.group(1) or m.group(2)
                top = name.split(".")[0]
                if top not in STDLIB and top not in here:
                    out.append((i, name, s.strip()))
    elif lang == "Node.js":
        for i, s in enumerate(lines, 1):
            for m in re.finditer(r"require\(['\"]([^'\"]+)['\"]\)", s):
                if not m.group(1).startswith("."):
                    out.append((i, m.group(1), s.strip()))
    elif lang == "Java":
        for i, s in enumerate(lines, 1):
            m = re.match(r'^import\s+(?:static\s+)?([\w\.\*]+);', s)
            if m and not m.group(1).startswith(("java.", "hipstershop.")):
                out.append((i, m.group(1), s.strip()))
    elif lang == "C#":
        own = set()
        for g in code_files(svc):
            for s in lines_of(g):
                m = re.match(r'^\s*namespace\s+([\w\.]+)', s)
                if m:
                    own.add(m.group(1).split(".")[0])
        for p in sorted((REPO / "src" / svc).rglob("*.proto")):
            for s in read_lines(p):
                m = re.match(r'^package\s+(\w+);', s)
                if m:
                    own.add(m.group(1)[:1].upper() + m.group(1)[1:])
        for i, s in enumerate(lines, 1):
            m = re.match(r'^using\s+(?:static\s+)?([\w\.]+)\s*;', s)
            if m and m.group(1).split(".")[0] not in own | {"System"}:
                out.append((i, m.group(1), s.strip()))
    return out


def package_json_deps(svc):
    p = REPO / "src" / svc / "package.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return {**data.get("dependencies", {}), **data.get("devDependencies", {})}


SDK_RX = [
    r'\bprofiler\.Start\(', r'googlecloudprofiler\.start\(', r"require\('@google-cloud/[\w-]+'\)\.start\(",
    r'otlptracegrpc\.New\(', r'sdktrace\.NewTracerProvider\(', r'otelgrpc\.\w+\(', r'otel\.Set\w+\(',
    r'\bOTLPSpanExporter\(', r'\bTracerProvider\(\)', r'\bGrpcInstrumentor\w+\(\)', r'\bBatchSpanProcessor\(',
    r'new OTLPTraceExporter\(', r'new NodeTracerProvider\(', r'new GrpcInstrumentation\(', r'registerInstrumentations\(',
    r'new SimpleSpanProcessor\(', r'metadata\.NewClient\(', r'\bhttp\.Get\(', r'\.send_message\(', r'\.sender_path\(',
    r'SecretManagerServiceClient\.Create\(', r'\.AccessSecretVersion\(', r'NpgsqlDataSource\.Create\(',
    r'SpannerConnection\s+\w+\s*=\s*new\(', r'AddStackExchangeRedisCache\(', r'AddDistributedMemoryCache\(',
    r'HealthStatusManager\(\)', r'\bcardValidator\(',
]


def provider_import(f, s, m):
    tok = [t for t in re.findall(r'[A-Za-z_]\w*', m.group(0)) if t not in ("new", "require", "start", "Create", "New")]
    if tok:
        t = tok[0]
        for i, name, verb in imports(f):
            if re.search(rf'\b{re.escape(t)}\b', verb) or name.split("/")[-1] == t or name.split(".")[-1] == t:
                return f"{code(name)} (L{i})"
    rm = re.search(r"require\('([^']+)'\)", s)
    if rm:
        return f"{code(rm.group(1))} (same line)"
    return "-"


ENV_RX = [r'os\.Getenv\("(\w+)"\)', r'os\.LookupEnv\("(\w+)"\)', r'mustMapEnv\(&[\w\.]+,\s*"(\w+)"\)',
          r'os\.environ\[["\'](\w+)["\']\]', r'os\.environ\.get\(["\'](\w+)["\']', r'os\.getenv\(["\'](\w+)["\']',
          r'["\'](\w+)["\']\s+in\s+os\.environ', r'process\.env\.(\w+)', r'process\.env\[["\'](\w+)["\']\]',
          r'System\.getenv\(\)\.getOrDefault\("(\w+)"', r'System\.getenv\("(\w+)"\)', r'[Cc]onfiguration\["(\w+)"\]']


def env_reads(s):
    out = []
    for rx in ENV_RX:
        for m in re.finditer(rx, s):
            out.append((m.start(), m.group(1)))
    return [v for _, v in sorted(out)]


def calls_in(f, a, b):
    lang, lines = lang_of(f), lines_of(f)
    out = []
    for k in range(a, b + 1):
        if is_comment(lines[k - 1], lang):
            continue
        s = code_only(lines[k - 1], lang)
        for m in re.finditer(r'(?<![\w\.])((?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*)\s*\(', s):
            n = m.group(1)
            if n.split(".")[-1] in KW or n in ("if", "for", "while"):
                continue
            if n not in out:
                out.append(n)
    return out


def doc12():
    d = Doc(12, "Third-party imports: Go import paths whose first element contains a dot and that are outside the "
                "service's own module (`go.mod`); Python modules that are not in `sys.stdlib_module_names` of the "
                "generating Python (3.11) and not a `.py` file in the same directory; Node.js non-relative `require()` "
                "names (with whether `package.json` declares them); Java imports outside `java.*` and the `hipstershop` "
                "package; C# `using` directives outside `System*` and the project's own namespaces. SDK initialisation and "
                "use sites are matched with a fixed list of call patterns (profiler start, OpenTelemetry exporters/"
                "providers/instrumentation, GCE metadata client, HTTP GET, mail API calls, Secret Manager, Npgsql, Spanner, "
                "Redis cache registration, health manager, card validator). Environment variables are read expressions "
                "(`os.Getenv`, `os.environ`, `process.env`, `System.getenv`, `Configuration[...]`); gated blocks are `if` "
                "statements whose condition reads an environment variable, with the calls inside the block and its `else` "
                "block. " + GEN_NOTE + " Test files are not scanned.")
    d.section("Third-party imports by service")
    for svc in services():
        rows = []
        deps = package_json_deps(svc)
        for f in code_files(svc, tests=False):
            for i, name, verb in imports(f):
                extra = ""
                if lang_of(f) == "Node.js":
                    root = "/".join(name.split("/")[:2]) if name.startswith("@") else name.split("/")[0]
                    extra = "declared in package.json" if root in deps else "not in package.json"
                rows.append((code(name), lang_of(f), extra or "-", (f, i)))
        if rows:
            d.section(svc, 3)
            d.table(["Import", "Language", "Note"], rows)
    d.section("External SDK initialisation and use sites")
    rows = []
    for svc, f, lang, i, s in scan_lines():
        for rx in SDK_RX:
            m = re.search(rx, s)
            if m:
                rows.append((svc, code(m.group(0)), code(s), provider_import(f, s, m), code(encl_name(f, i)), (f, i)))
    d.table(["Service", "Matched", "Line", "Import of first identifier", "Function"], rows)
    d.section("Instrumentation placeholders (TODO comments)")
    rows = []
    for svc in services():
        for f in code_files(svc, tests=False):
            for i, s in enumerate(lines_of(f), 1):
                if re.search(r'TODO\(\w+\)\s*Implement', s):
                    rows.append((svc, code(s), code(encl_name(f, i)), (f, i)))
    d.table(["Service", "Comment", "Function"], rows)
    d.section("Environment-variable-gated blocks")
    rows = []
    for svc, f, lang, i, s in scan_lines():
        if not re.match(r'^\s*(?:\}\s*else\s+)?(?:if|elif)\b', s):
            continue
        envs = env_reads(s)
        if not envs:
            continue
        end = block_end(f, i)
        lines = lines_of(f)
        inner = calls_in(f, i + 1, end) if lang == "Python" else calls_in(f, i, end)
        if lang != "Python":
            inner = [c for c in inner if not any(c == x for x in re.findall(r'[\w\.]+(?=\s*\()', code_only(s, lang)))]
        els, els_rng = [], ""
        if lang == "Python":
            k = end + 1
            while k <= len(lines) and not lines[k - 1].strip():
                k += 1
            if k <= len(lines) and indent(lines[k - 1]) == indent(s) and re.match(r'^\s*else\s*:', lines[k - 1]):
                e2 = py_block_end(f, k)
                els, els_rng = calls_in(f, k + 1, e2), f"L{k}-L{e2}"
        else:
            if re.search(r'\}\s*else\s*\{', code_only(lines[end - 1], lang)):
                e2 = brace_end(f, end)
                els, els_rng = calls_in(f, end, e2), f"L{end}-L{e2}"
            elif end < len(lines) and re.match(r'^\s*else\s*\{?\s*$', lines[end]):
                e2 = brace_end(f, end + 1)
                els, els_rng = calls_in(f, end + 1, e2), f"L{end + 1}-L{e2}"
        rows.append((svc, ", ".join(code(e) for e in envs), code(s), ", ".join(code(c) for c in inner) or "-",
                     (", ".join(code(c) for c in els) + f" ({els_rng})") if els_rng else "-", (f, i, end)))
    d.table(["Service", "Env var", "Condition", "Calls in block", "Calls in else block"], rows)
    d.section("All environment variable reads in code")
    rows = []
    for svc, f, lang, i, s in scan_lines():
        for e in env_reads(s):
            rows.append((svc, code(e), code(s), code(encl_name(f, i)), (f, i)))
    d.table(["Service", "Env var", "Line", "Function"], rows)
    if not [s for s in services() if "packaging" in s]:
        d.omit("Packaging service server", "`PACKAGING_SERVICE_URL` is read in `src/frontend/packaging_info.go`, but no service directory for it exists under `src/`")
    return d


# ============================================================================= 13

def json_key_line(path, key, value=None, start=1):
    lines = lines_of(path)
    pat = re.compile(rf'"{re.escape(key)}"\s*:' + (rf'\s*"?{re.escape(str(value))}"?' if value is not None else ""))
    for i in range(start, len(lines) + 1):
        if pat.search(lines[i - 1]):
            return i
    return None


def go_structs():
    out = []
    for svc in services():
        for f in code_files(svc, tests=False):
            if lang_of(f) != "Go":
                continue
            for y in symbols(f):
                if y.kind != "struct type":
                    continue
                fields = []
                for k in range(y.line + 1, y.end):
                    s = lines_of(f)[k - 1].strip()
                    m = re.match(r'^(\w+(?:\s*,\s*\w+)*)\s+([^\s`/]+)\s*(`[^`]*`)?', s)
                    if m:
                        fields.append(f"{m.group(1)} {m.group(2)}" + (f" {m.group(3)}" if m.group(3) else ""))
                out.append((svc, y, fields))
    return out


def doc13():
    d = Doc(13, "JSON data files are parsed with `json` and counted; line numbers are the first line where a key "
                "(and value) appears in the file. Template variables are `{{ ... }}` / `{% ... %}` expressions (Jinja2) and "
                "`.Field` references inside `{{ }}` (Go html/template). In-code structures: Go `type X struct` blocks with "
                "fields, Go map literals with string keys, Java `Ad.newBuilder()` chains and `putAll(category, ...)` entries, "
                "Python module-level list literals, and cart storage columns from SQL text and Spanner parameter collections. "
                "Readers of each data file are found by searching the service code for the file name. " + GEN_NOTE)
    # products.json
    p = "src/productcatalogservice/products.json"
    data = json.loads((REPO / p).read_text(encoding="utf-8"))
    d.section("Product catalog (`products.json`)")
    for k in sorted(data):
        d.fact(f"Top-level key `{k}` holds a {type(data[k]).__name__} of {len(data[k])} entries", p, json_key_line(p, k))
    prods = data["products"]
    fc = Counter(k for x in prods for k in x)
    d.table(["Field", "Products having it", "Value type"],
            [(code(k), n, type(prods[0].get(k)).__name__ if k in prods[0] else "-", (p, json_key_line(p, k)))
             for k, n in sorted(fc.items())])
    pc = Counter(k for x in prods for k in x.get("priceUsd", {}))
    d.table(["`priceUsd` field", "Products having it"], [(code(k), n, (p, json_key_line(p, k))) for k, n in sorted(pc.items())])
    rows = []
    for x in prods:
        ln = json_key_line(p, "id", x["id"])
        pr = x.get("priceUsd", {})
        rows.append((code(x["id"]), x["name"], ", ".join(x.get("categories", [])),
                     f"{pr.get('currencyCode')} {pr.get('units')}.{int(pr.get('nanos', 0)):09d}", code(x.get("picture", "-")), (p, ln)))
    d.table(["id", "name", "categories", "priceUsd (units.nanos)", "picture"], rows)
    cats = Counter(c for x in prods for c in x.get("categories", []))
    def cat_line(c):
        return next(i for i, s in enumerate(lines_of(p), 1) if '"categories"' in s and f'"{c}"' in s)
    d.table(["Category", "Products", "(source: first product line listing it)"][:2],
            [(code(c), n, (p, cat_line(c))) for c, n in sorted(cats.items())])
    for svc, f, lang, i, s in scan_lines(["productcatalogservice"]):
        if "products.json" in s:
            d.fact(f"Read by {code(s)} in `{encl_name(f, i)}`", f, i)
    # currency data
    c = "src/currencyservice/data/currency_conversion.json"
    cur = json.loads((REPO / c).read_text(encoding="utf-8"))
    d.section("Currency conversion data (`currency_conversion.json`)")
    d.fact(f"Top-level JSON object with {len(cur)} currency-code keys; values are strings", c, 1, len(lines_of(c)))
    d.table(["Currency code", "Rate (string value)"], [(code(k), v, (c, json_key_line(c, k))) for k, v in cur.items()])
    for svc, f, lang, i, s in scan_lines(["currencyservice"]):
        if "currency_conversion.json" in s or re.search(r'//\s*Convert:', s):
            d.fact(f"{code(s)} in `{encl_name(f, i)}`", f, i)
    # email template
    e = "src/emailservice/templates/confirmation.html"
    d.section("Order confirmation email template (`confirmation.html`)")
    rows = []
    for i, s in enumerate(lines_of(e), 1):
        for m in re.finditer(r'\{\{.*?\}\}|\{%.*?%\}', s):
            rows.append((code(m.group(0)), (e, i)))
    d.table(["Template expression"], rows)
    for svc, f, lang, i, s in scan_lines(["emailservice"]):
        if "confirmation.html" in s or "template.render(" in s:
            d.fact(f"{code(s)} in `{encl_name(f, i)}`", f, i)
    # frontend templates
    d.section("Frontend HTML templates (`src/frontend/templates/`)")
    rows = []
    for t in sorted((REPO / "src/frontend/templates").glob("*.html")):
        t = rel(t)
        defs, incl, fields = [], [], {}
        for i, s in enumerate(lines_of(t), 1):
            for m in re.finditer(r'\{\{-?\s*define\s+"([^"]+)"', s):
                defs.append(f"{m.group(1)} (L{i})")
            for m in re.finditer(r'\{\{-?\s*template\s+"([^"]+)"', s):
                incl.append(f"{m.group(1)} (L{i})")
            for blk in re.findall(r'\{\{(.*?)\}\}', s):
                for m in re.finditer(r'(?<![\w\)\]])(\$?\.[A-Za-z_][\w\.]*)', blk):
                    fields.setdefault(m.group(1), i)
        rows.append((code(t.rsplit("/", 1)[-1]), ", ".join(defs) or "-", ", ".join(incl) or "-",
                     ", ".join(f"`{k}` (L{v})" for k, v in sorted(fields.items(), key=lambda kv: kv[1])) or "-", (t, 1, len(lines_of(t)))))
    d.table(["File", "Defines", "Includes", "Data references (first line)"], rows)
    # Go structs
    d.section("Go struct types")
    d.table(["Service", "Struct", "Fields"],
            [(svc, code(y.name), "; ".join(code(x) for x in fl) or "(no fields)", (y.path, y.line, y.end)) for svc, y, fl in go_structs()])
    # map literals
    d.section("Go map literals with string keys")
    rows = []
    for svc, f, lang, i, s in scan_lines():
        m = re.search(r'(\w+)\s*=\s*map\[(\w+)\](\w+)\{', s) if lang == "Go" else None
        if m:
            end = brace_end(f, i)
            keys = [k for j in range(i, end + 1) for k in re.findall(r'"(\w+)":', lines_of(f)[j - 1])]
            rows.append((svc, code(m.group(1)), code(f"map[{m.group(2)}]{m.group(3)}"), ", ".join(code(k) for k in keys), (f, i, end)))
    d.table(["Service", "Variable", "Type", "Keys"], rows)
    # Java ads
    d.section("Ad service in-memory ads (Java)")
    rows, put = [], []
    for svc, f, lang, i, s in scan_lines(["adservice"]):
        m = re.match(r'^\s*Ad\s+(\w+)\s*=\s*$', s)
        if m:
            end = next(k for k in range(i, len(lines_of(f)) + 1) if ".build();" in lines_of(f)[k - 1])
            blk = " ".join(lines_of(f)[i - 1:end])
            url = re.search(r'setRedirectUrl\("([^"]*)"\)', blk)
            txt = re.search(r'setText\("([^"]*)"\)', blk)
            rows.append((code(m.group(1)), code(url.group(1)) if url else "-", txt.group(1) if txt else "-", (f, i, end)))
        m = re.search(r'\.putAll\("(\w+)",\s*(.*)\)\s*$', s)
        if m:
            put.append((code(m.group(1)), ", ".join(code(x.strip()) for x in m.group(2).split(",")), (f, i)))
        m = re.search(r'static int (MAX_\w+)\s*=\s*(\d+);', s)
        if m:
            d.fact(f"Constant `{m.group(1)}` = {m.group(2)}", f, i)
    d.table(["Variable", "redirect_url", "text"], rows)
    d.table(["Category key", "Ads"], put)
    # python lists
    d.section("Python list literals (module level)")
    rows = []
    for svc, f, lang, i, s in scan_lines():
        if lang != "Python":
            continue
        m = re.match(r'^(\w+)\s*=\s*\[\s*$', s)
        if m:
            end = next(k for k in range(i + 1, len(lines_of(f)) + 1) if "]" in code_only(lines_of(f)[k - 1], lang))
            items = re.findall(r"'([^']*)'|\"([^\"]*)\"", " ".join(lines_of(f)[i:end]))
            vals = [a or b for a, b in items]
            rows.append((svc, code(m.group(1)), len(vals), ", ".join(code(v) for v in vals), (f, i, end)))
    d.table(["Service", "Variable", "Items", "Values"], rows)
    # cart storage schema
    d.section("Cart storage record shapes")
    rows = []
    for svc, f, lang, i, s in scan_lines(["cartservice"]):
        for m in re.finditer(r'\{\s*"(\w+)",\s*SpannerDbType\.(\w+)\s*\}', s):
            rows.append((code(f.rsplit("/", 1)[-1]), "Spanner parameter", code(m.group(1)), code(m.group(2)), (f, i)))
        m = re.search(r'INSERT INTO \{(\w+)\} \(([^)]*)\)', s)
        if m:
            for col in m.group(2).split(","):
                rows.append((code(f.rsplit("/", 1)[-1]), "SQL INSERT column", code(col.strip()), "-", (f, i)))
        m = re.search(r'SELECT (.+?) FROM \{(\w+)\}', s)
        if m:
            rows.append((code(f.rsplit("/", 1)[-1]), "SQL SELECT list", code(m.group(1)), "-", (f, i)))
        m = re.search(r'static readonly string (TableName)\s*=\s*"([^"]+)"', s)
        if m:
            rows.append((code(f.rsplit("/", 1)[-1]), "table name constant", code(m.group(2)), "-", (f, i)))
        m = re.search(r'_cache\.SetAsync\((\w+),\s*(.+?)\);', s)
        if m:
            rows.append((code(f.rsplit("/", 1)[-1]), "cache entry (key, value)", code(m.group(1)), code(m.group(2)), (f, i)))
        m = re.search(r'Cart\.Parser\.ParseFrom\((\w+)\)', s)
        if m:
            rows.append((code(f.rsplit("/", 1)[-1]), "cache value decode", code(m.group(0)), "-", (f, i)))
    d.table(["File", "Element", "Name / value", "Type"], rows)
    d.omit("Protobuf message schemas", "API message definitions in `protos/demo.proto` belong to document 06 API Request/Response Schema")
    d.section("Cart table DDL documented in kustomize component READMEs")
    ddl = []
    for p in sorted((REPO / "kustomize").rglob("README.md")):
        r = rel(p)
        for i, s in enumerate(lines_of(r), 1):
            if "CREATE TABLE" in s:
                ddl.append((r, i))
    for r, i in ddl:
        d.quote(r, i, i)
    if not ddl:
        d.omit("Cart table DDL", "no `CREATE TABLE` statement under `kustomize/`")
    return d


# ============================================================================= 14

def yaml_leaves(path, start=1, end=None, lines=None, prefix=""):
    """[(key path, value, line)] from a simple indentation scan of YAML (block scalars parsed recursively)."""
    lines = lines if lines is not None else lines_of(path)
    end = end or len(lines)
    stack, out = [], []
    i = start
    while i <= end:
        raw = lines[i - 1]
        t = raw.strip()
        if t == "---":
            stack = []
            i += 1
            continue
        if not t or t.startswith("#") or t.startswith("{{"):
            i += 1
            continue
        m = re.match(r'^(\s*)(-\s+)?([\w\.\-/$]+):(?:\s+(.*))?$', raw)
        if not m:
            m2 = re.match(r'^(\s*)-\s+(.*)$', raw)
            if m2:
                di = len(m2.group(1))
                while stack and (stack[-1][0] > di or (stack[-1][0] == di and stack[-1][1] == "[]")):
                    stack.pop()
                out.append((prefix + ".".join(k for _, k in stack).replace(".[]", "[]") + "[]", m2.group(2), i))
            i += 1
            continue
        di = len(m.group(1))
        ki = di + (len(m.group(2)) if m.group(2) else 0)
        if m.group(2):
            while stack and (stack[-1][0] > di or (stack[-1][0] == di and stack[-1][1] == "[]")):
                stack.pop()
            stack.append((di, "[]"))
        while stack and stack[-1][0] >= ki:
            stack.pop()
        key, val = m.group(3), (m.group(4) or "").strip()
        pathk = prefix + ".".join([k for _, k in stack] + [key]).replace(".[]", "[]").replace("[].", "[].")
        if val in ("|", "|-", ">", ">-"):
            j = i + 1
            while j <= end and (not lines[j - 1].strip() or indent(lines[j - 1]) > ki):
                j += 1
            sub = [x[ki + 2:] if len(x) > ki + 2 else x.strip() for x in lines[i:j - 1]]
            for kp, v, ln in yaml_leaves(path, 1, len(sub), sub, pathk + " | "):
                out.append((kp, v, ln + i))
            i = j
            continue
        if val:
            out.append((pathk, val, i))
        else:
            stack.append((ki, key))
        i += 1
    return out


def doc14():
    d = Doc(14, "Cart store selection is read from `src/cartservice/src/Startup.cs` (`Configuration[...]` reads, `if`/`else` "
                "branches and `services.Add*` registrations in order). Store implementations are C# classes with base "
                "`ICartStore`; their settings are `configuration[...]` keys, `static readonly string` constants, string "
                "literals assigned to locals, and connection-string assignments (quoted verbatim). Kubernetes, Helm, "
                "kustomize and Terraform files are scanned as text: YAML leaves via an indentation key-path scan (block "
                "scalars such as kustomize `patch: |-` are scanned recursively, shown after ` | `), Terraform `key = value` "
                "lines inside `resource \"google_redis_instance\"`. Kustomize components are those whose `kustomization.yaml` "
                "mentions `REDIS_ADDR`. In-process caches are found from `reloadCatalog`, `signal.Notify` and mutex lines.")
    st = "src/cartservice/src/Startup.cs"
    lines = lines_of(st)
    d.section("Cart store selection (cartservice)")
    rows = []
    for i, s in enumerate(lines, 1):
        m = re.search(r'string (\w+) = Configuration\["(\w+)"\];', s)
        if m:
            rows.append((code(m.group(1)), code(m.group(2)), (st, i)))
    d.table(["Variable", "Configuration key"], rows)
    cfg = next(y for y in symbols(st) if y.name == "ConfigureServices")
    rows = []
    for i in range(cfg.line + 1, cfg.end):
        t = lines[i - 1].strip()
        if re.match(r'^(if|else if|else)\b', t):
            e = brace_end(st, i)
            regs = [m.group(1) for k in range(i + 1, e + 1)
                    for m in re.finditer(r'services\.(Add\w+(?:<[^>]*>)?)\(', lines[k - 1])]
            rows.append((code(t), ", ".join(code(x) for x in regs) or "-", (st, i, e)))
    d.table(["Branch", "Registrations"], rows)
    for i in range(cfg.line + 1, cfg.end):
        if re.search(r'services\.(Add\w+)\(', lines[i - 1]) and not any(r[2][1] <= i <= r[2][2] for r in rows):
            d.fact(f"Unconditional registration {code(lines[i - 1])}", st, i)
    for i, s in enumerate(lines, 1):
        if "Console.WriteLine" in s:
            d.fact(f"Log line {code(s)}", st, i)
    # store implementations
    d.section("ICartStore implementations and connection settings")
    for f in code_files("cartservice", tests=False):
        for y in symbols(f):
            if y.kind in ("class", "interface") and ("ICartStore" in y.detail or y.name == "ICartStore"):
                d.section(f"{y.name} (`{f}`)", 3)
                members = [z for z in symbols(f) if z.container == y.name and z.callable]
                d.fact(f"{y.kind} `{y.name}` {y.detail}; members: " + ", ".join(f"`{z.name}` (L{z.line})" for z in members), f, y.line, y.end)
                for i, s in enumerate(lines_of(f), 1):
                    t = s.strip()
                    for m in re.finditer(r'[Cc]onfiguration\["(\w+)"\]', t):
                        d.fact(f"Reads configuration key `{m.group(1)}`: {code(t)}", f, i)
                    m = re.search(r'static readonly string (\w+)\s*=\s*"([^"]*)"', t)
                    if m:
                        d.fact(f"Constant `{m.group(1)}` = `\"{m.group(2)}\"`", f, i)
                    m = re.match(r'^string (\w+)\s*=\s*"([^"]*)";', t)
                    if m:
                        d.fact(f"Local literal `{m.group(1)}` = `\"{m.group(2)}\"`", f, i)
                    if re.match(r'^(builder\.DataSource|connectionString)\s*=', t):
                        e = next(k for k in range(i, len(lines_of(f)) + 1) if lines_of(f)[k - 1].rstrip().endswith(";"))
                        d.quote(f, i, e)
                    if re.search(r'new\s+SecretVersionName\(|RunWithRetriableTransactionAsync|NpgsqlDataSource\.Create|SpannerConnection\s+\w+\s*=\s*new|IDistributedCache', t):
                        d.fact(f"Uses {code(t)}", f, i)
    # manifests
    d.section("Redis deployment manifests")
    for mf in ("kubernetes-manifests/redis.yaml", "kustomize/base/redis.yaml"):
        if not (REPO / mf).exists():
            d.omit(mf, "file not present")
            continue
        d.section(f"`{mf}`", 3)
        d.table(["Key path", "Value"], [(code(k), code(v), (mf, ln)) for k, v, ln in yaml_leaves(mf)])
    a, b = (REPO / "kubernetes-manifests/redis.yaml").read_bytes(), (REPO / "kustomize/base/redis.yaml").read_bytes()
    d.fact("`kubernetes-manifests/redis.yaml` and `kustomize/base/redis.yaml` are byte-identical" if a == b else
           "`kubernetes-manifests/redis.yaml` and `kustomize/base/redis.yaml` differ", "kustomize/base/redis.yaml",
           1, len(lines_of("kustomize/base/redis.yaml")))
    d.section("`REDIS_ADDR` settings in deployment files")
    rows = []
    for top in ("kubernetes-manifests", "kustomize", "helm-chart", "release"):
        for p in sorted((REPO / top).rglob("*.yaml")):
            r = rel(p)
            ls = lines_of(r)
            for i, s in enumerate(ls, 1):
                if re.search(r'name:\s*REDIS_ADDR\b', s):
                    nxt = ls[i].strip() if i < len(ls) else ""
                    rows.append((code(r), code(s), code(nxt), (r, i, i + 1)))
    d.table(["File", "Line", "Next line"], rows)
    d.section("Kustomize components changing cart storage")
    for comp in sorted((REPO / "kustomize/components").iterdir()):
        k = comp / "kustomization.yaml"
        if not k.exists() or "REDIS_ADDR" not in k.read_text(encoding="utf-8"):
            continue
        r = rel(k)
        d.section(f"`{comp.name}`", 3)
        d.table(["Key path", "Value"], [(code(kp), code(v), (r, ln)) for kp, v, ln in yaml_leaves(r)])
    d.section("Helm chart cart database values")
    hv = "helm-chart/values.yaml"
    hl = lines_of(hv)
    st_i = next((i for i, s in enumerate(hl, 1) if re.match(r'^cartDatabase:', s)), None)
    if st_i:
        en = next((i - 1 for i in range(st_i + 1, len(hl) + 1) if re.match(r'^\w', hl[i - 1])), len(hl))
        d.table(["Key path", "Value"], [(code(kp), code(v), (hv, ln)) for kp, v, ln in yaml_leaves(hv, st_i, en)])
    ht = "helm-chart/templates/cartservice.yaml"
    tl = lines_of(ht)
    a = next((i for i, s in enumerate(tl, 1) if ".Values.cartDatabase.type" in s), None)
    if a:
        b = next(i for i in range(a, len(tl) + 1) if ".Values.cartDatabase.connectionString" in tl[i - 1])
        d.quote(ht, a, b)
    d.section("Terraform Memorystore (Redis) instance")
    tf = "terraform/memorystore.tf"
    if (REPO / tf).exists():
        tfl = lines_of(tf)
        for i, s in enumerate(tfl, 1):
            m = re.match(r'^resource\s+"(google_redis_instance)"\s+"([^"]+)"', s)
            if m:
                e = brace_end(tf, i)
                d.fact(f"Resource `{m.group(1)}` named `{m.group(2)}`", tf, i, e)
                d.table(["Attribute", "Value"], [(code(km.group(1)), code(km.group(2)), (tf, k))
                                                  for k in range(i + 1, e) for km in [re.match(r'^\s*(\w+)\s*=\s*(.+?)\s*$', tfl[k - 1])] if km])
            if "REDIS_CONNECTION_STRING" in s:
                d.fact(f"Kustomization rewrite: {code(s)}", tf, i)
    else:
        d.omit("Terraform Memorystore", "terraform/memorystore.tf not present")
    d.section("In-process data caches")
    for svc, f, lang, i, s in scan_lines(["productcatalogservice", "frontend"]):
        if re.search(r'reloadCatalog\s*(=|\|\|)|signal\.Notify\(|catalogMutex\.(Lock|Unlock)\(|syscall\.SIGUSR|deploymentDetailsMap\s*=\s*make', s):
            d.fact(f"{code(s)} in `{encl_name(f, i)}`", f, i)
    d.omit("Session store", "the frontend session ID is an HTTP cookie set in `ensureSessionID` (`src/frontend/middleware.go`); no session store is referenced in frontend code")
    return d


# ============================================================================= 15

def doc15():
    d = Doc(15, "Data access sites are lines matching a fixed list of read/write call patterns (cart cache `GetAsync`/"
                "`SetAsync`, Spanner `CreateSelectCommand`/`CreateInsertOrUpdateCommand`/`CreateDmlCommand`, Npgsql "
                "`dataSource.CreateCommand(sql)` with the SQL text of the assigned variable, Secret Manager "
                "`AccessSecretVersion`, `os.ReadFile`, `require('./data/...')`, Jinja2 `get_template`/`render`, Go "
                "template execution, HTTP cookies, GCE metadata reads, in-memory maps). Operation is read/write from the "
                "call name or the SQL verb (SELECT = read; INSERT/UPDATE/DELETE = write). The handler mapping reuses the "
                "document 10 call scan: each handler body and the same-service functions it calls (by name) are scanned "
                "for those patterns; for cartservice the `ICartStore` method name resolves to every implementation. "
                + GEN_NOTE + " Test files are not scanned.")
    d.section("All data access sites")
    rows = []
    for svc, f, lang, i, s in scan_lines():
        for h in data_hits(f, i):
            sql = f"{code(h['sql'][0])} (L{h['sql'][1]})" if h["sql"] else "-"
            rows.append((svc, code(encl_name(f, i)), h["label"], h["op"], sql, (f, i)))
    d.table(["Service", "Function", "Data source", "Operation", "SQL"], rows)
    d.section("Counts by service and operation (counts of the rows above)")
    d.body += ["| Service | Operation | Sites |", "|---|---|---|"]
    d.body += [f"| {s} | {o} | {n} |" for (s, o), n in sorted(Counter((r[0], r[3]) for r in rows).items())] + [""]
    d.section("Handler x data source x operation")
    for svc in services():
        hs = handlers(svc)
        out, idx = [], {}
        for label, y, reg in hs:
            for e in scan(svc, y):
                if e["kind"] != "data":
                    continue
                key = (label, e["path"], e["line"], e["label"])
                if key in idx:
                    idx[key][4] += 1
                    continue
                idx[key] = [code(label), e["label"], e["op"], fmt_chain(e), 1, (e["path"], e["line"])]
                out.append(idx[key])
        if out:
            d.section(svc, 3)
            d.table(["Handler", "Data source", "Operation", "Via (first call path)", "Call paths reaching it"], [tuple(r) for r in out])
    d.section("Module-level data loads (outside handlers)")
    for r in rows:
        if r[1] == "`(top level)`":
            d.fact(f"{r[0]}: {r[2]} ({r[3]})", *r[5])
    for svc in services():
        if svc != "loadgenerator" and not any(r[0] == svc for r in rows):
            d.omit(f"{svc} data access", "no line matched the data access patterns")
    return d


def build():
    return [doc09(), doc10(), doc11(), doc12(), doc13(), doc14(), doc15()]
