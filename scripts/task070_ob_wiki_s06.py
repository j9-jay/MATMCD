"""Online Boutique team wiki, sections 06 Build & Test and 07 Observability (documents 21-25).

Deterministic static extraction from the pinned repository (see task070_ob_wiki_common).
Every table row / fact carries the repository path and line it was read from; only
template wording is fixed text. Generated code (genproto, *_pb2*.py), node_modules and
lock files' transitive entries (go.sum, package-lock.json, indirect go.mod requires,
pip-compile pins not listed in requirements.in) are not listed.
"""
import json
import re
from pathlib import Path

from task070_ob_wiki_common import REPO, Doc, grep, read_lines, rel, services

GENERATED = re.compile(r"(^|/)(genproto|node_modules)(/|$)|_pb2(_grpc)?\.py$")
CODE_EXT = {".go", ".java", ".js", ".py", ".cs"}


def T(doc, headers, rows):
    """doc.table preceded by a blank line; nothing is written for an empty row list."""
    if not rows:
        return
    if doc.body and doc.body[-1] != "":
        doc.body.append("")
    doc.table(headers, rows)


def _files(root, pattern):
    return [rel(p) for p in sorted((REPO / root).glob(pattern))
            if p.is_file() and not GENERATED.search(rel(p))]


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _is_comment_or_blank(line):
    s = line.strip()
    return not s or s.startswith("#")


def _block_end(lines, start, base_indent):
    """Last 1-based line of the YAML block that starts at 1-based `start` (indent base_indent)."""
    end = start
    for j in range(start, len(lines)):
        line = lines[j]
        if _is_comment_or_blank(line):
            continue
        if line.strip() == "---" or _indent(line) <= base_indent:
            break
        end = j + 1
    return end


def _source_files(svc):
    out = []
    for p in sorted((REPO / "src" / svc).rglob("*")):
        r = rel(p)
        if p.is_file() and p.suffix in CODE_EXT and not GENERATED.search(r):
            out.append(r)
    return out


def _is_test_file(path):
    return path.endswith("_test.go") or "/tests/" in path or re.search(r"(^|/)test_[^/]*\.py$|\.(test|spec)\.js$", path)


# --------------------------------------------------------------------------- 21

def _dockerfile_rows(path):
    lines = read_lines(path)
    rows, stage, i = [], 0, 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\s*([A-Za-z]+)\s+(.*)$", line)
        if _is_comment_or_blank(line) or not m:
            i += 1
            continue
        start, parts = i + 1, [m.group(2).rstrip("\\").strip()]
        while lines[i].rstrip().endswith("\\") and i + 1 < len(lines):
            i += 1
            if not _is_comment_or_blank(lines[i]):
                parts.append(lines[i].strip().rstrip("\\").strip())
        instr = m.group(1).upper()
        if instr == "FROM":
            stage += 1
        rows.append((stage, instr, " ".join(p for p in parts if p), (path, start, i + 1)))
        i += 1
    return rows


def _stage_rows(path):
    out = []
    for stage, instr, args, ref in _dockerfile_rows(path):
        if instr != "FROM":
            continue
        m = re.match(r"(\S+?)(?:@(sha256:[0-9a-f]+))?(?:\s+(?:as|AS)\s+(\S+))?$", args)
        out.append((stage, m.group(1), m.group(2) or "-", m.group(3) or "-", ref))
    return out


def _gomod_rows(path):
    lines, rows, facts, inblock = read_lines(path), [], [], False
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if m := re.match(r"^(module|go)\s+(\S+)$", s):
            facts.append((m.group(1), m.group(2), i))
        if s == "require (":
            inblock = True
            continue
        if inblock and s == ")":
            inblock = False
            continue
        m = re.match(r"^(?:require\s+)?(\S+)\s+(v\S+)(\s*//\s*indirect)?$", s) if (inblock or s.startswith("require ")) else None
        if m and not m.group(3):
            rows.append((m.group(1), m.group(2), (path, i)))
    return facts, rows


def _json_block_rows(path, key):
    """Entries "name": "value" inside the top-level JSON object `key` (line based)."""
    lines, rows, inside = read_lines(path), [], False
    for i, line in enumerate(lines, 1):
        if re.match(rf'^\s*"{re.escape(key)}"\s*:\s*\{{', line):
            inside = True
            continue
        if inside:
            if line.strip().startswith("}"):
                inside = False
                continue
            if m := re.match(r'^\s*"([^"]+)"\s*:\s*("(?:[^"\\]|\\.)*")', line):
                rows.append((m.group(1), json.loads(m.group(2)), (path, i)))
    return rows


def _requirements_in(path):
    rows = []
    for i, line in enumerate(read_lines(path), 1):
        s = line.split("#", 1)[0].strip()
        if m := re.match(r"^([A-Za-z0-9_.\-\[\]]+)\s*(.*)$", s):
            rows.append((m.group(1), m.group(2) or "-", (path, i)))
    return rows


def _requirements_txt_pin(path, name):
    norm = re.sub(r"[-_.]+", "-", name.lower())
    for i, line in enumerate(read_lines(path), 1):
        if m := re.match(r"^([A-Za-z0-9_.\-]+)(\[[^\]]*\])?==(\S+)", line):
            if re.sub(r"[-_.]+", "-", m.group(1).lower()) == norm:
                return m.group(3), i, m.group(1) + (m.group(2) or "")
    return None


def _gradle(path):
    lines = read_lines(path)
    defs = {}
    for i, line in enumerate(lines, 1):
        if m := re.match(r'^\s*def\s+(\w+)\s*=\s*"([^"]*)"', line):
            defs[m.group(1)] = (m.group(2), i)
    plugins, deps, settings = [], [], []
    block, conf, depth = None, None, 0
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if block is None and (m := re.match(r"^(plugins|dependencies)\s*\{", s)):
            block, depth = m.group(1), 1
            continue
        if block:
            depth += s.count("{") - s.count("}")
            if depth <= 0:
                block = None
                continue
            if block == "plugins" and (m := re.match(r"^id\s+'([^']+)'(?:\s+version\s+'([^']+)')?", s)):
                plugins.append((m.group(1), m.group(2) or "-", (path, i)))
            if block == "dependencies":
                if m := re.match(r"^(implementation|runtimeOnly|compileOnly|testImplementation|annotationProcessor|api)\b", s):
                    conf = m.group(1)
                for coord in re.findall(r'"([^"]+:[^"]+)"', s):
                    resolved = re.sub(r"\$\{(\w+)\}", lambda mm: defs.get(mm.group(1), (mm.group(0),))[0], coord)
                    deps.append((conf, coord, resolved, (path, i)))
        elif re.search(r"(sourceCompatibility|targetCompatibility|toolVersion|mainClass\.set|defaultJvmOpts)", s) or \
                (re.match(r'^\s*\["', line) and "agentpath" in line):
            settings.append((s, (path, i)))
    return plugins, defs, deps, settings


def _csproj(path):
    rows = []
    for i, line in enumerate(read_lines(path), 1):
        if m := re.search(r'<Project Sdk="([^"]+)"', line):
            rows.append(("Project SDK", m.group(1), "-", (path, i)))
        if m := re.search(r"<TargetFramework>([^<]+)</TargetFramework>", line):
            rows.append(("TargetFramework", m.group(1), "-", (path, i)))
        if m := re.search(r'<PackageReference Include="([^"]+)" Version="([^"]+)"', line):
            rows.append(("PackageReference", m.group(1), m.group(2), (path, i)))
        if m := re.search(r'<ProjectReference Include="([^"]+)"', line):
            rows.append(("ProjectReference", m.group(1), "-", (path, i)))
        if m := re.search(r'<Protobuf Include="([^"]+)"', line):
            rows.append(("Protobuf", m.group(1), "-", (path, i)))
    return rows


def _skaffold_docs(path="skaffold.yaml"):
    """[(config name, name line, [(1-based line, text)])] per YAML document."""
    lines, docs, cur = read_lines(path), [], []
    for i, line in enumerate(lines, 1):
        if line.strip() == "---":
            docs.append(cur)
            cur = []
        else:
            cur.append((i, line))
    docs.append(cur)
    out = []
    for d in docs:
        name, nline = None, None
        for k, (i, line) in enumerate(d):
            if line.startswith("metadata:"):
                for i2, l2 in d[k + 1:]:
                    if m := re.match(r"^\s+name:\s*(\S+)", l2):
                        name, nline = m.group(1), i2
                        break
                break
        out.append((name, nline, d))
    return out


def _skaffold_artifacts(path="skaffold.yaml"):
    rows = []
    for cfg, _, d in _skaffold_docs(path):
        section, cur = None, None
        for i, line in enumerate(l for _, l in d):
            ln = d[i][0]
            if not line.startswith(" ") and not line.startswith("-") and line.strip() and not line.startswith("#"):
                section = line.split(":")[0]
            if section != "build":
                continue
            if m := re.match(r"^\s*-\s+image:\s*(\S+)", line):
                cur = [cfg, m.group(1), "-", "-", ln]
                rows.append(cur)
            elif cur and (m := re.match(r"^\s+context:\s*(\S+)", line)):
                cur[2] = m.group(1)
            elif cur and (m := re.match(r"^\s+dockerfile:\s*(\S+)", line)):
                cur[3] = m.group(1)
            elif re.match(r"^  \w", line):
                cur = None
    return [(c, img, ctx, df, (path, ln)) for c, img, ctx, df, ln in rows]


def _skaffold_build_settings(path="skaffold.yaml"):
    out = []
    for cfg, _, d in _skaffold_docs(path):
        section, sub = None, None
        for ln, line in d:
            if _is_comment_or_blank(line):
                continue
            if not line.startswith(" ") and not line.startswith("-"):
                section = line.split(":")[0]
                continue
            if section != "build":
                continue
            if re.match(r"^  \w", line):
                sub = line.strip().split(":")[0]
            if sub != "artifacts":
                out.append((cfg, line.strip(), (path, ln)))
    return out


def doc21():
    doc = Doc(21, "Dockerfiles under `src/` parsed instruction by instruction (FROM starts a new stage; continuation lines joined); "
                  "build files parsed line by line: `go.mod` (module, go directive, direct `require` entries without `// indirect`), "
                  "`package.json` (`dependencies`/`devDependencies`/`scripts`), `requirements.in` (direct dependencies) with the matching pin "
                  "in the pip-compiled `requirements.txt`, `build.gradle` (plugins, `def` version variables, `dependencies` block with "
                  "`${var}` resolved from the same file), `gradle-wrapper.properties`, `*.csproj` (SDK, target framework, package/project "
                  "references); `skaffold.yaml` build artifacts and build settings. Only direct dependencies are listed; transitive entries "
                  "of lock files (`go.sum`, `package-lock.json`, indirect `go.mod` requires, other `requirements.txt` pins) are not listed.")
    doc.section("Skaffold build artifacts")
    T(doc, ["Skaffold config", "Image", "Context", "Dockerfile"], _skaffold_artifacts())
    doc.section("Skaffold build settings (non-artifact keys)", 3)
    T(doc, ["Skaffold config", "Setting line"], _skaffold_build_settings())

    for svc in services():
        doc.section(f"Service `{svc}`")
        dockerfiles = _files(f"src/{svc}", "**/Dockerfile*")
        for df in dockerfiles:
            doc.section(f"Dockerfile `{df}` stages", 3)
            T(doc, ["Stage", "Base image", "Digest", "Stage alias"], _stage_rows(df))
            doc.section(f"Dockerfile `{df}` instructions", 4)
            T(doc, ["Stage", "Instruction", "Arguments"], _dockerfile_rows(df))
        if not dockerfiles:
            doc.omit(f"{svc} Dockerfile", "no Dockerfile under the service directory")
        found = False
        for gm in _files(f"src/{svc}", "**/go.mod"):
            found = True
            facts, rows = _gomod_rows(gm)
            doc.section(f"`{gm}`", 3)
            for key, val, ln in facts:
                doc.fact(f"`{key}` directive: `{val}`", gm, ln)
            T(doc, ["Direct module", "Version"], rows)
        for pj in _files(f"src/{svc}", "**/package.json"):
            found = True
            doc.section(f"`{pj}`", 3)
            for key in ("dependencies", "devDependencies"):
                rows = _json_block_rows(pj, key)
                if rows:
                    T(doc, [f"{key} package", "Version spec"], rows)
            scripts = _json_block_rows(pj, "scripts")
            if scripts:
                T(doc, ["npm script", "Command"], scripts)
        for rin in _files(f"src/{svc}", "**/requirements.in"):
            found = True
            doc.section(f"`{rin}`", 3)
            rows = _requirements_in(rin)
            T(doc, ["Direct dependency", "Specifier"], rows)
            rtxt = str(Path(rin).with_name("requirements.txt").as_posix())
            if (REPO / rtxt).is_file():
                pins = []
                for name, _, _ in rows:
                    base = re.sub(r"\[.*\]", "", name)
                    if p := _requirements_txt_pin(rtxt, base):
                        pins.append((p[2], p[0], (rtxt, p[1])))
                    else:
                        doc.omit(f"{svc} pin for {name} in requirements.txt", "no `name==version` line for it in requirements.txt")
                for i, line in enumerate(read_lines(rtxt), 1):
                    if re.match(r"^#\s+pip-compile", line):
                        doc.fact(f"`requirements.txt` header: `{line.lstrip('#').strip()}`", rtxt, i)
                T(doc, ["Direct dependency as written in requirements.txt", "Pinned version in requirements.txt"], pins)
        for bg in _files(f"src/{svc}", "build.gradle"):
            found = True
            plugins, defs, deps, settings = _gradle(bg)
            doc.section(f"`{bg}`", 3)
            T(doc, ["Gradle plugin", "Version"], plugins)
            T(doc, ["Version variable", "Value"], [(k, v, (bg, ln)) for k, (v, ln) in sorted(defs.items(), key=lambda x: x[1][1])])
            T(doc, ["Configuration", "Declared coordinate", "Resolved coordinate"], deps)
            T(doc, ["Build setting line"], settings)
            for wp in _files(f"src/{svc}", "gradle/wrapper/gradle-wrapper.properties"):
                for i, line in enumerate(read_lines(wp), 1):
                    if line.startswith("distributionUrl="):
                        doc.fact(f"Gradle wrapper `{line.strip()}`", wp, i)
        for cp in _files(f"src/{svc}", "**/*.csproj"):
            found = True
            doc.section(f"`{cp}`", 3)
            T(doc, ["Element", "Name / value", "Version"], _csproj(cp))
        if not found:
            doc.omit(f"{svc} build/dependency file", "no go.mod, package.json, requirements.in, build.gradle or *.csproj in the service directory")
    return doc


# --------------------------------------------------------------------------- 22

def _parse_workflow(path):
    lines = read_lines(path)
    wf = {"name": None, "triggers": [], "permissions": [], "jobs": []}
    top = None
    event = None
    job = None
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        ln = i + 1
        if _is_comment_or_blank(line):
            i += 1
            continue
        ind = _indent(line)
        s = line.strip()
        if ind == 0:
            top = s.split(":")[0]
            if top == "name":
                wf["name"] = (s.split(":", 1)[1].strip().strip('"'), ln)
            i += 1
            continue
        if top == "on":
            if ind == 2:
                event = s.rstrip(":").split(":")[0]
                wf["triggers"].append((event, "(event)", "-", (path, ln)))
            elif ind >= 4 and (m := re.match(r"^([\w-]+):\s*(.*)$", s)):
                key, val = m.group(1), m.group(2)
                vals, end = [], ln
                if val:
                    vals.append(val)
                else:
                    j = i + 1
                    while j < n and (_is_comment_or_blank(lines[j]) or (_indent(lines[j]) > ind or lines[j].strip().startswith("- ")) and _indent(lines[j]) >= ind):
                        if lines[j].strip().startswith("- "):
                            vals.append(lines[j].strip()[2:].strip())
                            end = j + 1
                        elif not _is_comment_or_blank(lines[j]):
                            break
                        j += 1
                wf["triggers"].append((event, key, ", ".join(vals), (path, ln, end)))
        elif top == "permissions":
            wf["permissions"].append((s, (path, ln)))
        elif top == "jobs":
            if ind == 2:
                job = {"id": s.rstrip(":"), "line": ln, "keys": [], "steps": []}
                wf["jobs"].append(job)
            elif ind == 4 and s.startswith("steps:"):
                j = i + 1
                while j < n and _is_comment_or_blank(lines[j]):
                    j += 1
                dash = _indent(lines[j])
                k = j
                while k < n:
                    l2 = lines[k]
                    if _is_comment_or_blank(l2):
                        k += 1
                        continue
                    if _indent(l2) < dash or (_indent(l2) == dash and not l2.strip().startswith("-")):
                        break
                    if _indent(l2) == dash and l2.strip().startswith("- "):
                        start = k + 1
                        end = _block_end(lines, start, dash)
                        body = [lines[x] for x in range(start - 1, end)]
                        body[0] = " " * (dash + 2) + body[0].strip()[2:]
                        step = {"start": start, "end": end, "name": "-", "uses": "-", "id": "-", "timeout": "-", "run": False}
                        for b in body:
                            if _indent(b) != dash + 2:
                                continue
                            if m := re.match(r"^\s*(name|uses|id|timeout-minutes|run):\s*(.*)$", b):
                                key = {"timeout-minutes": "timeout"}.get(m.group(1), m.group(1))
                                step[key] = True if key == "run" else m.group(2).strip().strip('"')
                        job["steps"].append(step)
                        k = end
                        continue
                    k += 1
                i = k
                continue
            elif ind == 4 and (m := re.match(r"^([\w-]+):\s*(.*)$", s)):
                end = _block_end(lines, ln, 4)
                text = " ".join(lines[x].strip() for x in range(ln - 1, end) if not _is_comment_or_blank(lines[x]))
                job["keys"].append((text, (path, ln, end)))
                i = end
                continue
        i += 1
    return wf


def _parse_cloudbuild(path):
    lines = read_lines(path)
    steps, settings, top = [], [], None
    i = 0
    while i < len(lines):
        line, ln = lines[i], i + 1
        if _is_comment_or_blank(line):
            i += 1
            continue
        if _indent(line) == 0 and not line.startswith("-"):
            top = line.split(":")[0]
            if top != "steps":
                end = _block_end(lines, ln, 0)
                settings.append((" ".join(lines[x].strip() for x in range(ln - 1, end) if not _is_comment_or_blank(lines[x])), (path, ln, end)))
                i = end
                continue
            i += 1
            continue
        if top == "steps" and line.strip().startswith("- "):
            dash = _indent(line)
            end = _block_end(lines, ln, dash)
            fields = {}
            for x in range(ln - 1, end):
                body = lines[x].strip()[2:] if x == ln - 1 else lines[x].strip()
                if m := re.match(r"^(id|name|entrypoint):\s*(.*)$", body):
                    if (_indent(lines[x]) == dash + 2) or x == ln - 1:
                        fields[m.group(1)] = m.group(2).strip().strip("'\"")
            steps.append((fields.get("id", "-"), fields.get("name", "-"), fields.get("entrypoint", "-"), (path, ln, end)))
            i = end
            continue
        i += 1
    return steps, settings


def _skaffold_profiles(path="skaffold.yaml"):
    out = []
    for cfg, _, d in _skaffold_docs(path):
        section = None
        for idx, (ln, line) in enumerate(d):
            if _is_comment_or_blank(line):
                continue
            if not line.startswith(" ") and not line.startswith("-"):
                section = line.split(":")[0]
                continue
            if section == "profiles" and (m := re.match(r"^-\s+name:\s*(\S+)", line)):
                end = ln
                for ln2, l2 in d[idx + 1:]:
                    if _is_comment_or_blank(l2):
                        continue
                    if not l2.startswith(" "):
                        break
                    end = ln2
                out.append((cfg, m.group(1), ln, end))
    return out


def doc22():
    doc = Doc(22, "GitHub Actions workflow files in `.github/workflows/` parsed by YAML indentation (workflow `name`, `on` events with their "
                  "branch/path/type filters, `permissions`, jobs with job-level keys and steps); each step is listed with name/uses/id/timeout "
                  "and its full text is quoted verbatim. Cloud Build files (YAML files with a top-level `steps:` key outside `src/`, "
                  "`helm-chart/`, `kustomize/`, `kubernetes-manifests/`, `release/`, `istio-manifests/`, `terraform/`) parsed into steps "
                  "and top-level settings. `skaffold.yaml` profiles quoted verbatim. Release scripts in `docs/releasing/*.sh` scanned for "
                  "required environment variables (`${VAR:?...}`) and command lines invoking gcloud/helm/git/skaffold/docker/kubectl or sibling "
                  "scripts. `.github/workflows/*.sh` helper scripts listed command line by command line.")
    wfs = _files(".github/workflows", "*.yaml") + _files(".github/workflows", "*.yml")
    doc.section("GitHub Actions workflows")
    summary = []
    parsed = {}
    for wf in sorted(wfs):
        p = _parse_workflow(wf)
        parsed[wf] = p
        events = sorted({t[0] for t in p["triggers"]})
        name, nl = p["name"] if p["name"] else ("-", 1)
        summary.append((name, wf, ", ".join(events), ", ".join(j["id"] for j in p["jobs"]), (wf, nl)))
    T(doc, ["Workflow name", "File", "Trigger events", "Jobs"], summary)
    for wf in sorted(wfs):
        p = parsed[wf]
        name = p["name"][0] if p["name"] else wf
        doc.section(f"Workflow \"{name}\" (`{wf}`)", 3)
        T(doc, ["Event", "Filter", "Values"], p["triggers"])
        if p["permissions"]:
            T(doc, ["Permission line"], p["permissions"])
        for job in p["jobs"]:
            doc.section(f"Job `{job['id']}`", 4)
            doc.fact(f"Job id `{job['id']}`", wf, job["line"])
            if job["keys"]:
                T(doc, ["Job setting"], job["keys"])
            T(doc, ["#", "Step name", "uses", "id", "timeout-minutes", "has run"],
                      [(k, s["name"], s["uses"], s["id"], s["timeout"], "yes" if s["run"] else "no", (wf, s["start"], s["end"]))
                       for k, s in enumerate(job["steps"], 1)])
            for k, s in enumerate(job["steps"], 1):
                if s["end"] > s["start"]:
                    doc.body.append(f"Step {k} (`{s['name'] if s['name'] != '-' else s['uses']}`) full text:")
                    doc.quote(wf, s["start"], s["end"])
    for sh in _files(".github/workflows", "*.sh"):
        doc.section(f"Workflow helper script `{sh}`", 3)
        T(doc, ["Command line"], [(line.strip(), (sh, i)) for i, line in enumerate(read_lines(sh), 1)
                                     if not _is_comment_or_blank(line)])

    doc.section("Cloud Build configurations")
    skip = ("src/", "helm-chart/", "kustomize/", "kubernetes-manifests/", "release/", "istio-manifests/", "terraform/", ".github/workflows/")
    cb_files = sorted({r for r in (rel(p) for p in REPO.rglob("*.yaml") if p.is_file())
                       if not r.startswith(skip) and any(l.startswith("steps:") for l in read_lines(r))})
    for cb in cb_files:
        steps, settings = _parse_cloudbuild(cb)
        doc.section(f"`{cb}`", 3)
        T(doc, ["Step id", "Builder image (name)", "entrypoint"], steps)
        for *_, ref in steps:
            doc.quote(*ref)
        T(doc, ["Top-level setting"], settings)
    if not cb_files:
        doc.omit("Cloud Build configuration", "no YAML file with a top-level `steps:` key")

    doc.section("Skaffold profiles")
    profs = _skaffold_profiles()
    T(doc, ["Skaffold config", "Profile"], [(c, n, ("skaffold.yaml", s, e)) for c, n, s, e in profs])
    for c, n, s, e in profs:
        doc.body.append(f"Profile `{n}` of config `{c}`:")
        doc.quote("skaffold.yaml", s, e)
    for cfg, _, d in _skaffold_docs():
        for ln, line in d:
            if line.startswith("requires:"):
                sk = read_lines("skaffold.yaml")
                end = ln
                while end < len(sk) and (sk[end].startswith(" ") or sk[end].startswith("-")):
                    end += 1
                doc.fact(f"Config `{cfg}` declares `requires`: " + " ".join(sk[x].strip() for x in range(ln, end)),
                         "skaffold.yaml", ln, end)

    doc.section("Release scripts")
    scripts = _files("docs/releasing", "*.sh")
    for sc in scripts:
        doc.section(f"`{sc}`", 3)
        lines = read_lines(sc)
        env = [(m.group(1), (sc, i)) for i, line in enumerate(lines, 1) for m in re.finditer(r"\$\{(\w+):[?-]", line)]
        if env:
            T(doc, ["Environment variable read with default/required expansion"], env)
        cmds = [(line.strip(), (sc, i)) for i, line in enumerate(lines, 1)
                if not _is_comment_or_blank(line) and re.search(r"(^|[\s(])(gcloud|helm|git|skaffold|docker|kubectl|gsed|cp)\s|\$\{SCRIPT_DIR\}\"?/[\w.-]+\.sh", line)]
        T(doc, ["Command line"], cmds)
        first = next((i for i, line in enumerate(lines, 1) if not _is_comment_or_blank(line) and not line.startswith("#!")), None)
        if first:
            doc.body.append(f"Script body of `{sc}` (license header omitted):")
            doc.quote(sc, first, len(lines))
    if not scripts:
        doc.omit("Release scripts", "no docs/releasing/*.sh")
    return doc


# --------------------------------------------------------------------------- 23

def _go_tests(path):
    lines = read_lines(path)
    funcs = []
    for i, line in enumerate(lines, 1):
        if m := re.match(r"^func\s+((?:Test|Benchmark|Example|Fuzz)\w*)\(", line):
            end = i
            for j in range(i, len(lines)):
                if lines[j].startswith("}"):
                    end = j + 1
                    break
            body = lines[i - 1:end]
            cases = []
            if any("t.Run(" in b for b in body):
                for k, b in enumerate(body):
                    if c := re.match(r'^\s*\{"((?:[^"\\]|\\.)*)",', b):
                        cases.append((c.group(1), i + k))
            funcs.append((m.group(1), i, end, cases))
    return funcs


def doc23():
    doc = Doc(23, "Test files located by name (`*_test.go`, files under `tests/` directories, `test_*.py`, `*.test.js`, `*.spec.js`, "
                  "Java `src/test`), skipping generated code. Go: top-level `func Test*/Benchmark*/Example*/Fuzz*` and, for functions "
                  "that call `t.Run`, the case names of table entries written as `{\"name\", ...}`. C#: methods following `[Fact]`/`[Theory]` "
                  "attributes. npm `test` scripts from `package.json`. CI usage: lines in `.github/workflows/*` that invoke a test runner, "
                  "the `for SERVICE in` loop around it, and the kustomize build test folders (`kustomize/tests/*/kustomization.yaml`).")
    any_tests = False
    doc.section("Go tests")
    for svc in services():
        for tf in _files(f"src/{svc}", "**/*_test.go"):
            any_tests = True
            funcs = _go_tests(tf)
            doc.section(f"`{tf}`", 3)
            for i, line in enumerate(read_lines(tf), 1):
                if m := re.match(r"^package\s+(\w+)", line):
                    doc.fact(f"Go package `{m.group(1)}`", tf, i)
                    break
            T(doc, ["Test function", "Table cases (count)"], [(f, len(c), (tf, s, e)) for f, s, e, c in funcs])
            rows = [(f, name, (tf, ln)) for f, _, _, c in funcs for name, ln in c]
            if rows:
                T(doc, ["Test function", "Case name"], rows)
    doc.section("C# tests")
    cs_found = False
    for svc in services():
        for tf in _files(f"src/{svc}", "tests/**/*.cs"):
            lines = read_lines(tf)
            rows = []
            for i, line in enumerate(lines, 1):
                if m := re.match(r"^\s*\[(Fact|Theory)\b", line):
                    for j in range(i, min(i + 5, len(lines))):
                        if mm := re.search(r"\b(?:public|private|internal)\s+(?:async\s+)?[\w<>]+\s+(\w+)\s*\(", lines[j]):
                            rows.append((m.group(1), mm.group(1), (tf, i, j + 1)))
                            break
            if rows:
                cs_found = any_tests = True
                doc.section(f"`{tf}`", 3)
                for i, line in enumerate(lines, 1):
                    if m := re.search(r"\b(?:public\s+)?class\s+(\w+)", line):
                        doc.fact(f"Test class `{m.group(1)}`", tf, i)
                T(doc, ["Attribute", "Test method"], rows)
        for cp in _files(f"src/{svc}", "tests/**/*.csproj"):
            pk = [(n, v, ref) for kind, n, v, ref in _csproj(cp) if kind == "PackageReference"]
            doc.fact(f"Test project file `{cp}`", cp, 1)
            T(doc, ["Test project package", "Version"], pk)
    if not cs_found:
        doc.omit("C# tests", "no [Fact]/[Theory] methods found")

    other = {"Python": [r for r in _files("src", "**/*.py") if re.search(r"(^|/)test_[^/]*\.py$|_test\.py$", r)],
             "JavaScript": [r for r in _files("src", "**/*.js") if re.search(r"\.(test|spec)\.js$", r)],
             "Java": _files("src", "**/src/test/**/*.java")}
    for lang, files in other.items():
        if files:
            any_tests = True
            doc.section(f"{lang} test files")
            T(doc, ["File"], [(f, (f, 1)) for f in files])
        else:
            doc.omit(f"{lang} tests", "no test files of this language in the repository")
    doc.section("npm test scripts")
    rows = []
    for pj in _files("src", "*/package.json"):
        rows += [(pj, cmd, ref) for name, cmd, ref in _json_block_rows(pj, "scripts") if name == "test"]
    T(doc, ["package.json", "`test` script"], rows)

    doc.section("How CI runs tests")
    rows = []
    for f in _files(".github/workflows", "*.y*ml"):
        for i, line in enumerate(read_lines(f), 1):
            if re.search(r"\b(go test|dotnet test|pytest|npm test|gradlew test|mvn test)\b|for SERVICE in", line):
                rows.append((f, line.strip(), (f, i)))
    T(doc, ["Workflow", "Line"], rows)
    loop = [(f, re.findall(r'"(\w+)"', t), ref) for f, t, ref in rows if "for SERVICE in" in t]
    if loop:
        listed = sorted({s for _, svcs, _ in loop for s in svcs})
        go_files = [tf for svc in services() for tf in _files(f"src/{svc}", "**/*_test.go")]
        T(doc, ["Go test file", "Directory of the file", "Directory equals `src/$SERVICE` for a listed SERVICE"],
                  [(tf, str(Path(tf).parent.as_posix()), "yes" if str(Path(tf).parent.as_posix()) in {f"src/{s}" for s in listed} else "no",
                    loop[0][2]) for tf in go_files])
    doc.section("Kustomize build tests", 3)
    for k in _files("kustomize/tests", "*/kustomization.yaml"):
        comps = [(Path(k).parent.name, line.strip()[2:], (k, i)) for i, line in enumerate(read_lines(k), 1)
                 if line.startswith("- ../../components/")]
        T(doc, ["Test folder", "Component"], comps)
    for f in _files(".deploystack", "test"):
        for i, line in enumerate(read_lines(f), 1):
            if line.startswith("# DEPLOYSTACK"):
                end = i
                while end < len(read_lines(f)) and read_lines(f)[end].startswith("# ") and read_lines(f)[end].strip() != "#":
                    end += 1
                doc.section("DeployStack test script", 3)
                doc.quote(f, i, end)
                break
    if not any_tests:
        doc.omit("Test files", "none found")
    return doc


# --------------------------------------------------------------------------- 24

LOG_RX = {
    ".go": [(re.compile(r"(?:(?<![\w.])(log|fmt)|(\}\)|\)))\.(Info|Infof|Warn|Warnf|Warning|Warningf|Error|Errorf|Debug|Debugf|Fatal|Fatalf|Panic|Panicf|Print|Printf|Println|Trace|Tracef)\("), "go")],
    ".java": [(re.compile(r"\blogger\.(info|warn|error|debug|trace|fatal)\("), "java"),
              (re.compile(r"\blogger\.log\(Level\.(\w+),"), "javalevel")],
    ".js": [(re.compile(r"\b(logger|console)\.(info|warn|error|debug|log|trace|fatal)\("), "js")],
    ".py": [(re.compile(r"\blogger\.(info|warn|warning|error|debug|critical|exception)\("), "py"),
            (re.compile(r"(?<![\w.])print\("), "pyprint")],
    ".cs": [(re.compile(r"\bConsole\.Write(?:Line)?\s*\("), "cs"),
            (re.compile(r"\b_?logger\.Log(Information|Warning|Error|Debug|Critical|Trace)\("), "cslog")],
}


def _first_literal(lines, li, col):
    """Scan from the '(' at lines[li][col]; return (first string literal inside the call or None, end line index)."""
    depth, quote, lit, cur, prefix = 0, None, None, [], ""
    i, j = li, col
    while i < len(lines) and i < li + 12:
        s = lines[i]
        while j < len(s):
            c = s[j]
            if quote:
                cur.append(c)
                if c == "\\" and j + 1 < len(s):
                    cur.append(s[j + 1])
                    j += 2
                    continue
                if c == quote:
                    if lit is None and depth >= 1:
                        lit = prefix + "".join(cur)
                    quote, cur = None, []
            elif c in "\"'`":
                quote, cur = c, [c]
                prefix = s[j - 1] if j > 0 and s[j - 1] in "$f" and (j < 2 or not s[j - 2].isalnum()) else ""
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return lit, i
            j += 1
        if quote:
            cur.append("\n")
        i, j = i + 1, 0
    return lit, i - 1


def _log_statements(path):
    lines = read_lines(path)
    rx = LOG_RX.get(Path(path).suffix, [])
    rows = []
    for li, line in enumerate(lines):
        if line.strip().startswith(("//", "#", "*")):
            continue
        if path.endswith(".go") and li > 0 and lines[li - 1].rstrip().endswith(".") and                 (m := re.match(r"^\s*(Info|Infof|Warn|Warnf|Error|Errorf|Debug|Debugf|Fatal|Fatalf|Print|Printf|Println)\(", line)):
            meth = m.group(1)
            level = "-" if meth.startswith("Print") else meth.rstrip("f")
            lit, end = _first_literal(lines, li, line.index("("))
            rows.append((level, lines[li - 1].strip() + meth, lit if lit is not None else "(no string literal)", (path, li, end + 1)))
            continue
        for r, kind in rx:
            for m in r.finditer(line):
                start = li
                if kind == "go":
                    recv, meth = m.group(1) or m.group(2), m.group(3)
                    if recv == "fmt" and not meth.startswith("Print"):
                        continue
                    call, start = f"{recv}.{meth}", li
                    if recv in (")", "})"):
                        head = line[:m.start()].strip()
                        k = li
                        while recv == "})" and k > max(0, li - 15) and "WithFields(" not in lines[k]:
                            k -= 1
                        if recv == "})":
                            head = lines[k].strip()
                            head = head[:head.index("WithFields(")] + "WithFields(...)" if "WithFields(" in head else head
                            start = k
                        else:
                            head = head + ")"
                        call = f"{head}.{meth}"
                    level = "-" if meth.startswith("Print") else re.sub(r"(f|ing|ingf)$", "", meth) if meth not in ("Warning", "Warningf") else "Warning"
                    if meth in ("Warn", "Warnf"):
                        level = "Warn"
                elif kind == "java":
                    call, level = f"logger.{m.group(1)}", m.group(1).upper()
                elif kind == "javalevel":
                    call, level = "logger.log", m.group(1)
                elif kind == "js":
                    call, level = f"{m.group(1)}.{m.group(2)}", m.group(2)
                elif kind == "py":
                    call, level = f"logger.{m.group(1)}", m.group(1)
                elif kind == "pyprint":
                    call, level = "print", "-"
                elif kind == "cs":
                    call, level = "Console.WriteLine" if "Line" in m.group(0) else "Console.Write", "-"
                else:
                    call, level = f"logger.Log{m.group(1)}", m.group(1)
                paren = line.find("(", m.start() + len(m.group(0)) - 1 if kind != "javalevel" else m.start())
                lit, end = _first_literal(lines, li, paren)
                rows.append((level, call, lit if lit is not None else "(no string literal)", (path, start + 1, end + 1)))
    return rows


LOG_LIBS = re.compile(r"(logrus|pino|python-json-logger|log4j|Microsoft\.Extensions\.Logging|winston|bunyan|zap|serilog)", re.I)
LOG_CFG = {
    ".go": re.compile(r"logrus\.New\(\)|\blog\.(Level|Formatter|Out)\s*=|FieldKey\w+:|JSONFormatter|TimestampFormat|ctxKeyLog\{\}\)\.\(logrus|lh\.log\.WithFields|WithFields\(logrus\.Fields\{"),
    ".js": re.compile(r"pino\(|name:\s*'|messageKey:|severity:|formatters:"),
    ".py": re.compile(r"getJSONLogger\(|getLogger\(|StreamHandler\(|JsonFormatter\(|setLevel\(|propagate\s*=|setFormatter\(|addHandler\(|log_record\["),
    ".java": re.compile(r"LogManager\.getLogger\("),
}


def _go_fields(path):
    out = []
    for i, line in enumerate(read_lines(path), 1):
        if line.strip().startswith("//"):
            continue
        for m in re.finditer(r'WithField\("([^"]+)"', line):
            out.append((m.group(1), "WithField", (path, i)))
    lines = read_lines(path)
    depth = 0
    for i, line in enumerate(lines, 1):
        if depth == 0 and "logrus.Fields{" in line:
            depth = line[line.index("logrus.Fields{"):].count("{") - line[line.index("logrus.Fields{"):].count("}")
            seg = line[line.index("logrus.Fields{"):]
            for m in re.finditer(r'"([^"]+)":', seg):
                out.append((m.group(1), "logrus.Fields key", (path, i)))
            continue
        if depth > 0:
            if m := re.match(r'^\s*"([^"]+)":', line):
                out.append((m.group(1), "logrus.Fields key", (path, i)))
            depth += line.count("{") - line.count("}")
    out.sort(key=lambda r: r[2][1])
    return out


def doc24():
    doc = Doc(24, "Per service: logging library taken from the service's direct dependency declarations (go.mod, package.json, "
                  "requirements.in, build.gradle, *.csproj) matched against known logging package names; logging configuration lines "
                  "matched per language (logrus logger construction/level/formatter/output, pino options, Python logging handler/formatter "
                  "setup, log4j2 XML configuration, ASP.NET `appsettings.json` `Logging` section); log statements located by call pattern "
                  "(Go `log.*`/`fmt.Print*`, logrus chained `.Info(` etc.; Java `logger.*`; JS `logger.*`/`console.*`; Python "
                  "`logger.*`/`print`; C# `Console.Write*`). For each statement the level is the method name (Go `f` suffix removed; `-` for "
                  "print-style calls that carry no level) and the template is the first string literal inside the call parentheses as written in the source (chained logrus calls are shown with their chain head), "
                  "read across continuation lines. Test files and generated code are excluded. Go structured field keys from `WithField` "
                  "and `logrus.Fields{}` literals are listed separately.")
    for svc in services():
        doc.section(f"Service `{svc}`")
        files = [f for f in _source_files(svc) if not _is_test_file(f)]
        libs = []
        for bf in _files(f"src/{svc}", "**/go.mod"):
            libs += [(n, v, ref) for n, v, ref in _gomod_rows(bf)[1] if LOG_LIBS.search(n)]
        for bf in _files(f"src/{svc}", "**/package.json"):
            libs += [(n, v, ref) for n, v, ref in _json_block_rows(bf, "dependencies") if LOG_LIBS.search(n)]
        for bf in _files(f"src/{svc}", "**/requirements.in"):
            libs += [(n, v, ref) for n, v, ref in _requirements_in(bf) if LOG_LIBS.search(n)]
        for bf in _files(f"src/{svc}", "build.gradle"):
            libs += [(":".join(r.split(":")[:2]), (r.split(":") + ["-"])[2], ref) for _, c, r, ref in _gradle(bf)[2] if LOG_LIBS.search(c)]
        for bf in _files(f"src/{svc}", "**/*.csproj"):
            if "/tests/" in bf:
                continue
            libs += [(n, v, ref) for k, n, v, ref in _csproj(bf) if k == "PackageReference" and LOG_LIBS.search(n)]
        doc.section("Logging library", 3)
        if libs:
            T(doc, ["Dependency", "Version"], libs)
        else:
            doc.omit(f"{svc} logging library", "no logging package among the service's direct dependencies")
        cfg = []
        for f in files:
            rx = LOG_CFG.get(Path(f).suffix)
            if rx:
                cfg += [(line.strip(), (f, i)) for i, line in enumerate(read_lines(f), 1) if rx.search(line)]
        for f in _files(f"src/{svc}", "**/log4j2*.xml"):
            cfg += [(line.strip(), (f, i)) for i, line in enumerate(read_lines(f), 1)
                    if re.search(r"<(Configuration|Console|JsonLayout|KeyValuePair|Logger|Root|AppenderRef|PatternLayout)\b", line)]
        for f in _files(f"src/{svc}", "**/appsettings*.json"):
            lines = read_lines(f)
            for i, line in enumerate(lines, 1):
                if re.match(r'^\s*"Logging"\s*:', line):
                    depth = 0
                    for j in range(i - 1, len(lines)):
                        depth += lines[j].count("{") - lines[j].count("}")
                        cfg.append((lines[j].strip(), (f, j + 1)))
                        if depth <= 0 and j > i - 1:
                            break
        doc.section("Logging configuration", 3)
        if cfg:
            T(doc, ["Configuration line"], cfg)
        else:
            doc.omit(f"{svc} logging configuration", "no logger construction or logging configuration file found")
        stmts = []
        for f in files:
            stmts += _log_statements(f)
        doc.section("Log statements", 3)
        if stmts:
            T(doc, ["Level", "Call", "Message template (first string literal in the call)"], stmts)
        else:
            doc.omit(f"{svc} log statements", "no logging or print call found in the service's non-test source files")
        fields = []
        for f in files:
            if f.endswith(".go"):
                fields += _go_fields(f)
        if fields:
            doc.section("Structured log field keys (Go)", 3)
            T(doc, ["Field key", "Attached via"], fields)
    return doc


# --------------------------------------------------------------------------- 25

OBS_CATS = [
    ("Env flag / collector address", re.compile(r"(Getenv|getenv|environ|process\.env|System\.getenv|mustMapEnv)\W.*\b\w*(TRACING|PROFILER|STATS|COLLECTOR|OTEL_)\w*|\w*(TRACING|PROFILER|STATS|COLLECTOR)\w*\W\s+in\s+os\.environ")),
    ("Import / require", re.compile(r'^\s*(import\s|from\s|\w*\s*"[^"]*(opentelemetry|otel|profiler|opencensus)[^"]*"\s*$)|require\([\'"][^\'"]*(opentelemetry|profiler|trace-agent)')),
    ("Setup function", re.compile(r"\bfunc\s+init(Tracing|Profiling|Stats)\b|\bdef\s+initStackdriverProfiling\b|\b(go\s+)?init(Tracing|Profiling|Stats)\(|\binitStackdriverProfiling\(|private static void init(Stats|Tracing)\b")),
    ("Tracer provider / exporter / propagation", re.compile(r"NewTracerProvider|WithBatcher|WithSampler|SetTracerProvider|SetTextMapPropagator|NewCompositeTextMapPropagator|propagation\.\w+\{\}|otlptracegrpc\.|mustConnGRPC\(ctx, &collectorConn|NodeTracerProvider\(|addSpanProcessor|provider\.register\(|SERVICE_NAME|set_tracer_provider|add_span_processor|BatchSpanProcessor\(|OTLPSpanExporter\(|endpoint\s*=|insecure\s*=")),
    ("gRPC / HTTP instrumentation", re.compile(r"otelgrpc\.\w+|otelhttp\.\w+|new GrpcInstrumentation\(|registerInstrumentations\(|GrpcInstrumentor\w+\(\)|_instrumentor\.instrument\(")),
    ("Profiler", re.compile(r"profiler\.Start\(|profiler\.Config\{|Service(Version)?:\s+\w|googlecloudprofiler\.start\(|@google-cloud/profiler'\)\.start|serviceContext|^\s*(service|version):\s*'|profiler_java_agent|/opt/cprof")),
    ("Not implemented / TODO", re.compile(r"TODO.*(OpenTele|stats|tracing)|temporarily unavailable|not yet implemented", re.I)),
]
OBS_DEPS = re.compile(r"(opentelemetry|otel|profiler|trace|opencensus|census)", re.I)


def doc25():
    doc = Doc(25, "Per service, non-test non-generated source lines classified by fixed patterns into: environment flags / collector "
                  "address reads, observability imports, setup functions and their calls, tracer provider/exporter/propagation calls, "
                  "gRPC/HTTP instrumentation, profiler start/config, and TODO/not-implemented markers (first matching class wins; lines "
                  "quoted verbatim). Dockerfile and build.gradle lines referencing the Cloud Profiler agent or profiler/tracing variables; "
                  "direct dependencies whose name contains opentelemetry/otel/profiler/trace/opencensus/census. Deployment configuration: "
                  "observability-named env vars in `kubernetes-manifests/*.yaml`, patches in "
                  "`kustomize/components/google-cloud-operations/kustomization.yaml` (deployment, env name, value or `$patch: delete`), the "
                  "collector Deployment/Service and the collector config template quoted verbatim from `otel-collector.yaml`, and the "
                  "`opentelemetryCollector`/`googleCloudOperations` blocks of `helm-chart/values.yaml` quoted verbatim.")
    any_metrics = []
    for svc in services():
        doc.section(f"Service `{svc}`")
        deps = []
        for bf in _files(f"src/{svc}", "**/go.mod"):
            deps += [(n, v, ref) for n, v, ref in _gomod_rows(bf)[1] if OBS_DEPS.search(n)]
        for bf in _files(f"src/{svc}", "**/package.json"):
            deps += [(n, v, ref) for n, v, ref in _json_block_rows(bf, "dependencies") if OBS_DEPS.search(n)]
        for bf in _files(f"src/{svc}", "**/requirements.in"):
            deps += [(n, v, ref) for n, v, ref in _requirements_in(bf) if OBS_DEPS.search(n)]
        for bf in _files(f"src/{svc}", "build.gradle"):
            deps += [(":".join(r.split(":")[:2]), (r.split(":") + ["-"])[2], ref) for _, c, r, ref in _gradle(bf)[2] if OBS_DEPS.search(c)]
        for bf in _files(f"src/{svc}", "**/*.csproj"):
            deps += [(n, v, ref) for k, n, v, ref in _csproj(bf) if k == "PackageReference" and OBS_DEPS.search(n)]
        if deps:
            T(doc, ["Observability dependency", "Version"], deps)
        rows = []
        for f in [f for f in _source_files(svc) if not _is_test_file(f)]:
            for i, line in enumerate(read_lines(f), 1):
                for cat, rx in OBS_CATS:
                    if rx.search(line) and (cat != "Import / require" or re.search(r"opentelemetry|otel|profiler|opencensus|trace-agent", line)):
                        rows.append((cat, line.strip(), (f, i)))
                        break
                if re.search(r"MeterProvider|\bmetric\.|NewMeter|meter\.|prometheus", line):
                    any_metrics.append((f, i))
        for f in _files(f"src/{svc}", "**/Dockerfile*") + _files(f"src/{svc}", "build.gradle"):
            for i, line in enumerate(read_lines(f), 1):
                if re.search(r"cprof|cloud-profiler|Profiler|ENABLE_PROFILER|DISABLE_PROFILER|ENABLE_TRACING|COLLECTOR", line):
                    rows.append(("Build / image", line.strip(), (f, i)))
        if rows:
            T(doc, ["Class", "Line"], rows)
        else:
            doc.omit(f"{svc} tracing/metrics/profiling instrumentation", "no matching line in the service's source, Dockerfile or build files")
    if not any_metrics:
        stats = [(f, i) for f, i, t in grep(r"TODO.*OpenTele\w* stats", "src/**/*") if not GENERATED.search(f)]
        doc.omit("Application metrics instrumentation in service code",
                 "no metrics SDK calls (MeterProvider, meter, metric., prometheus) in service sources; stats TODO markers at "
                 + ", ".join(f"`{f}:L{i}`" for f, i in stats))

    doc.section("Deployment configuration")
    doc.section("Observability env vars in base Kubernetes manifests", 3)
    rows = []
    for f in _files("kubernetes-manifests", "*.yaml"):
        lines = read_lines(f)
        for i, line in enumerate(lines, 1):
            if m := re.match(r"^\s*-\s+name:\s*(\w*(TRACING|PROFILER|STATS|COLLECTOR|OTEL)\w*)\s*$", line):
                val = re.match(r"^\s*value:\s*(.*)$", lines[i]) if i < len(lines) else None
                rows.append((f, m.group(1), val.group(1) if val else "-", (f, i, i + 1 if val else i)))
    T(doc, ["Manifest", "Env var", "Value"], rows)

    comp = "kustomize/components/google-cloud-operations"
    kz = f"{comp}/kustomization.yaml"
    if (REPO / kz).is_file():
        doc.section("Kustomize component `google-cloud-operations`", 3)
        lines = read_lines(kz)
        for i, line in enumerate(lines, 1):
            if re.match(r"^resources:", line):
                for j in range(i, len(lines)):
                    if not lines[j].startswith("  - "):
                        break
                    doc.fact(f"Resource `{lines[j].strip()[2:]}`", kz, j + 1)
        rows, dep, pending = [], None, None
        body_start = next(i for i, line in enumerate(lines, 1) if not _is_comment_or_blank(line))
        for i, line in enumerate(lines, 1):
            if i > body_start and line.startswith("#") and line.strip() != "#":
                rows.append(("(comment)", line.lstrip("# ").strip(), "-", (kz, i)))
            if re.match(r"^- patch:", line):
                dep = None
            if dep is None and (m := re.match(r"^\s+name:\s*(\S+)", line)) and "metadata" in lines[i - 2]:
                dep = m.group(1)
            if m := re.match(r"^\s+- name:\s*(\w+)\s*$", line):
                pending = (m.group(1), i)
            elif pending and (m := re.match(r"^\s+(value|\$patch):\s*(.*)$", line)):
                rows.append((dep, pending[0], f"{m.group(1)}: {m.group(2)}", (kz, pending[1], i)))
                pending = None
        T(doc, ["Deployment", "Env var", "Patch"], rows)
        oc = f"{comp}/otel-collector.yaml"
        if (REPO / oc).is_file():
            ol = read_lines(oc)
            kind, ctr, await_name = None, None, False
            for i, line in enumerate(ol, 1):
                if m := re.match(r"^kind:\s*(\w+)", line):
                    kind, ctr = m.group(1), None
                if m := re.match(r"^\s+(initContainers|containers):\s*$", line):
                    ctr = {"initContainers": "init container", "containers": "container"}[m.group(1)]
                    await_name = True
                if ctr and await_name and (m := re.match(r"^\s+- name:\s*(\S+)", line)):
                    doc.fact(f"{kind} {ctr} `{m.group(1)}`", oc, i)
                    ctr, await_name = f"{ctr} `{m.group(1)}`", False
                if m := re.match(r"^  name:\s*(\S+)", line):
                    doc.fact(f"{kind} `{m.group(1)}`", oc, i)
                if m := re.match(r"^\s+(?:- )?(image|port|targetPort|protocol|type|replicas):\s*(.*)$", line):
                    where = f" {ctr}" if ctr and m.group(1) == "image" else ""
                    doc.fact(f"{kind}{where} `{m.group(1)}`: `{m.group(2)}`", oc, i)
                if re.match(r"^\s+- --config=", line):
                    doc.fact(f"{kind} {ctr} arg `{line.strip()[2:]}`", oc, i)
            for i, line in enumerate(ol, 1):
                if re.match(r"^\s+collector-gateway-config-template\.yaml:\s*\|", line):
                    end = len(ol)
                    while end > i and not ol[end - 1].strip():
                        end -= 1
                    doc.body.append("Collector configuration template (ConfigMap data):")
                    doc.quote(oc, i, end)
                    break
    else:
        doc.omit("google-cloud-operations kustomize component", "directory not present")

    hv = "helm-chart/values.yaml"
    if (REPO / hv).is_file():
        lines = read_lines(hv)
        blocks = []
        for i, line in enumerate(lines, 1):
            if re.match(r"^(opentelemetryCollector|googleCloudOperations):", line):
                blocks.append((i, _block_end(lines, i, 0)))
        if blocks:
            doc.section("Helm chart values", 3)
            for s, e in blocks:
                doc.quote(hv, s, e)
    return doc


def build():
    return [doc21(), doc22(), doc23(), doc24(), doc25()]
