"""Section 05 Infrastructure (documents 16-20) of the Online Boutique team wiki.

Deterministic static extraction from the pinned repository: Kubernetes manifests,
kustomize components, helm chart templates (Istio kinds only), Istio manifests, and
environment-variable reads in service source code. Every fact carries file:line.
"""
import re

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

from task070_ob_wiki_common import REPO, Doc, grep, read_lines, rel

K8S = "kubernetes-manifests"
COMP = "kustomize/components"
ISTIO = "istio-manifests"
HELM = "helm-chart/templates"
WORKLOAD_KINDS = ("Deployment", "StatefulSet", "DaemonSet")


# ---------------------------------------------------------------- YAML helpers
def _shift(node, off, seen):
    for m in (node.start_mark, node.end_mark):
        if id(m) not in seen:
            seen.add(id(m))
            m.line += off
    if isinstance(node, MappingNode):
        for k, v in node.value:
            _shift(k, off, seen)
            _shift(v, off, seen)
    elif isinstance(node, SequenceNode):
        for v in node.value:
            _shift(v, off, seen)


def compose(text, off=0):
    docs = [d for d in yaml.compose_all(text) if d is not None]
    if off:
        seen = set()
        for d in docs:
            _shift(d, off, seen)
    return docs


def load(path):
    return compose((REPO / path).read_text(encoding="utf-8"))


def ln(node):
    return node.start_mark.line + 1


def last(node):
    """1-based last line of a node's own content (trailing comments/next tokens excluded)."""
    if isinstance(node, MappingNode) and node.value:
        return last(node.value[-1][1])
    if isinstance(node, SequenceNode) and node.value:
        return last(node.value[-1])
    m = node.end_mark
    if isinstance(node, ScalarNode) and node.style in ("|", ">"):
        return m.line if m.column == 0 else m.line + 1
    return m.line + 1


def kspan(parent, key):
    """(key line, last line) of `key: value` inside mapping `parent`."""
    for kn, v in parent.value:
        if kn.value == key:
            return ln(kn), last(v)
    return None


def g(node, *keys):
    for k in keys:
        if node is None:
            return None
        if isinstance(k, int):
            node = node.value[k] if isinstance(node, SequenceNode) and k < len(node.value) else None
        elif isinstance(node, MappingNode):
            node = next((v for kn, v in node.value if kn.value == k), None)
        else:
            return None
    return node


def sv(node):
    """Scalar value as written, or None."""
    return node.value if isinstance(node, ScalarNode) else None


def items(node):
    return node.value if isinstance(node, SequenceNode) else []


def flat(node, prefix=""):
    """[(dotted path, scalar text, line)] for every scalar leaf; empty mappings/sequences as {} / []."""
    out = []
    if isinstance(node, MappingNode):
        if not node.value:
            out.append((prefix or ".", "{}", ln(node)))
        for k, v in node.value:
            out += flat(v, f"{prefix}.{k.value}" if prefix else k.value)
    elif isinstance(node, SequenceNode):
        if not node.value:
            out.append((prefix or ".", "[]", ln(node)))
        for i, v in enumerate(node.value):
            out += flat(v, f"{prefix}[{i}]")
    else:
        out.append((prefix or ".", node.value, ln(node)))
    return out


def flat_str(node):
    if node is None:
        return "not set"
    return "; ".join(v if p == "." else f"{p}={v}" for p, v, _ in flat(node)) or "not set"


def yaml_files(*dirs):
    files = []
    for d in dirs:
        files += [p for p in (REPO / d).rglob("*.yaml") if p.is_file()]
    return sorted(rel(p) for p in files)


def manifest_files():
    return [f for f in yaml_files(K8S) if not f.endswith("kustomization.yaml")]


def component_files():
    return [f for f in yaml_files(COMP) if not f.endswith("kustomization.yaml")]


def resources(paths, kinds):
    """[(path, doc node)] for documents whose kind is in kinds (and not a `$patch: delete`)."""
    out = []
    for p in paths:
        for d in load(p):
            if sv(g(d, "kind")) in kinds and g(d, "$patch") is None:
                out.append((p, d))
    return out


def workloads():
    return [(p, d) for p, d in resources(manifest_files() + component_files(), WORKLOAD_KINDS)
            if g(d, "spec", "template") is not None]


def containers(d):
    """[(kind 'container'|'initContainer', node)]"""
    spec = g(d, "spec", "template", "spec")
    out = [("initContainer", c) for c in items(g(spec, "initContainers"))]
    out += [("container", c) for c in items(g(spec, "containers"))]
    return out


def name(d):
    return sv(g(d, "metadata", "name"))


def embedded_patches():
    """[(component kustomization path, patch doc node)] for inline `patch: |-` strings (lines shifted to file lines)."""
    out = []
    for p in yaml_files(COMP):
        if not p.endswith("kustomization.yaml"):
            continue
        for d in load(p):
            for item in items(g(d, "patches")):
                v = g(item, "patch")
                if isinstance(v, ScalarNode) and v.style in ("|", ">"):
                    for pd in compose(v.value, off=v.start_mark.line + 1):
                        out.append((p, item, pd))
    return out


def component_of(path):
    return path.split("/")[2] if path.startswith(COMP + "/") else "-"


# ---------------------------------------------------------------- 16
def doc16():
    doc = Doc(16, "PyYAML node composition of every YAML document under `kubernetes-manifests/` and "
                  "`kustomize/components/`; workload kinds Deployment/StatefulSet/DaemonSet with a pod template are "
                  "tabulated; line numbers come from YAML node marks. Inline kustomize patches are parsed from their "
                  "block-scalar text with line offsets. `not set` means the key is absent from the manifest.")
    doc.section("Default deployment resource list (kustomization)")
    kpath = f"{K8S}/kustomization.yaml"
    for i, line in enumerate(read_lines(kpath), 1):
        m = re.match(r"^(#?)\s*- (\S+\.yaml)", line)
        if m:
            state = "commented out (not included)" if m.group(1) else "included"
            doc.fact(f"`{m.group(2)}`: {state} in `resources:`", kpath, i)
    doc.section("Workloads")
    rows = []
    for p, d in workloads():
        spec = g(d, "spec", "template", "spec")
        rows.append((sv(g(d, "kind")), name(d), component_of(p), sv(g(d, "spec", "replicas")) or "not set",
                     flat_str(g(d, "spec", "selector", "matchLabels")),
                     flat_str(g(d, "spec", "template", "metadata", "labels")),
                     flat_str(g(d, "spec", "template", "metadata", "annotations")),
                     sv(g(spec, "serviceAccountName")) or "not set",
                     sv(g(spec, "terminationGracePeriodSeconds")) or "not set",
                     flat_str(g(spec, "securityContext")), (p, ln(d), last(d))))
    doc.table(["Kind", "Name", "Kustomize component", "replicas", "selector.matchLabels", "Pod labels",
               "Pod annotations", "serviceAccountName", "terminationGracePeriodSeconds", "Pod securityContext"], rows)
    doc.section("Containers (image and securityContext)")
    rows = []
    for p, d in workloads():
        for kind, c in containers(d):
            rows.append((name(d), kind, sv(g(c, "name")), sv(g(c, "image")), flat_str(g(c, "securityContext")),
                         (p, ln(c), last(c))))
    doc.table(["Workload", "Type", "Container", "image", "Container securityContext"], rows)

    kinds = {sv(g(d, "kind")) for f in manifest_files() + component_files() for d in load(f)}
    for k in ("StatefulSet", "DaemonSet"):
        if k not in kinds:
            doc.omit(k, f"no `kind: {k}` document under `{K8S}/` or `{COMP}/`")

    doc.section("ServiceAccounts (kustomize component `service-accounts`)")
    rows = [(name(d), component_of(p), (p, ln(d), last(d)))
            for p, d in resources(component_files(), ("ServiceAccount",))]
    doc.table(["ServiceAccount", "Kustomize component"], rows)
    doc.section("Kustomize JSON patches on Deployment fields")
    rows = []
    for p in yaml_files(COMP):
        if not p.endswith("kustomization.yaml"):
            continue
        for d in load(p):
            for item in items(g(d, "patches")):
                tgt, v = g(item, "target"), g(item, "patch")
                if tgt is None or not isinstance(v, ScalarNode):
                    continue
                for pd in compose(v.value, off=v.start_mark.line + 1):
                    for op in items(pd):
                        rows.append((component_of(p), sv(g(tgt, "kind")), sv(g(tgt, "name")), sv(g(op, "op")),
                                     sv(g(op, "path")), sv(g(op, "value")), (p, ln(op), last(op))))
    doc.table(["Kustomize component", "Target kind", "Target name", "op", "path", "value"], rows)
    doc.section("Kustomize image transformers")
    rows = []
    for p in yaml_files(COMP):
        if not p.endswith("kustomization.yaml"):
            continue
        for d in load(p):
            for im in items(g(d, "images")):
                fields = "; ".join(f"{k.value}={v.value}" for k, v in im.value if k.value != "name")
                rows.append((component_of(p), sv(g(im, "name")), fields, (p, ln(im), last(im))))
    doc.table(["Kustomize component", "Image name", "Transform"], rows)
    doc.omit("Helm chart workload values", f"`{HELM}/` workloads are Go templates over `helm-chart/values.yaml`; "
                                           "only the plain manifests and kustomize components are tabulated")
    return doc


# ---------------------------------------------------------------- 17
def doc17():
    doc = Doc(17, "PyYAML node composition of `kind: Service` and `kind: NetworkPolicy` documents under "
                  "`kubernetes-manifests/` and `kustomize/components/`, plus `$patch: delete` patches in kustomize "
                  "components (inline and file patches). One row per Service port. `not set` means the key is absent.")
    doc.section("Services")
    rows = []
    for p, d in resources(manifest_files() + component_files(), ("Service",)):
        spec = g(d, "spec")
        for port in items(g(spec, "ports")):
            rows.append((name(d), component_of(p), sv(g(spec, "type")) or "not set", sv(g(port, "name")) or "not set",
                         sv(g(port, "port")), sv(g(port, "targetPort")) or "not set",
                         sv(g(port, "protocol")) or "not set", flat_str(g(spec, "selector")), (p, ln(port), last(port))))
    doc.table(["Service", "Kustomize component", "type", "port name", "port", "targetPort", "protocol", "selector"], rows)

    doc.section("NetworkPolicies (kustomize component `network-policies`)")
    rows = []
    for p, d in resources(component_files(), ("NetworkPolicy",)):
        spec = g(d, "spec")
        pts = ", ".join(sv(t) for t in items(g(spec, "policyTypes")))

        def rules(key, peer_key):
            out = []
            for r in items(g(spec, key)):
                peers = [flat_str(g(x, "podSelector", "matchLabels")) if g(x, "podSelector") is not None
                         else flat_str(x) for x in items(g(r, peer_key))]
                ports = [f"{sv(g(x, 'port'))}/{sv(g(x, 'protocol')) or 'not set'}" for x in items(g(r, "ports"))]
                if not peers and not ports:
                    out.append("{} (empty rule)")
                else:
                    out.append(f"{peer_key}: {' , '.join(peers) or 'not set'}; ports: {', '.join(ports) or 'not set'}")
            return " / ".join(out) or "not set"
        rows.append((name(d), flat_str(g(spec, "podSelector", "matchLabels")) if g(spec, "podSelector", "matchLabels")
                     is not None else flat_str(g(spec, "podSelector")), pts, rules("ingress", "from"),
                     rules("egress", "to"), (p, ln(d), last(d))))
    doc.table(["NetworkPolicy", "podSelector", "policyTypes", "ingress", "egress"], rows)

    doc.section("Resource deletions by kustomize components")
    rows = []
    for p, item, pd in embedded_patches():
        if g(pd, "$patch") is not None:
            rows.append((component_of(p), sv(g(pd, "kind")), name(pd), (p, ln(pd), last(pd))))
    for p in component_files():
        for d in load(p):
            if g(d, "$patch") is not None:
                rows.append((component_of(p), sv(g(d, "kind")), name(d), (p, ln(d), last(d))))
    doc.table(["Kustomize component", "Deleted kind", "Deleted name"], sorted(rows, key=lambda r: (r[0], r[3])))
    if not resources(manifest_files(), ("NetworkPolicy",)):
        doc.omit("NetworkPolicy in default deployment", f"no `kind: NetworkPolicy` document under `{K8S}/`")
    if not resources(manifest_files() + component_files(), ("Ingress",)):
        doc.omit("Kubernetes Ingress", f"no `kind: Ingress` document under `{K8S}/` or `{COMP}/`")
    return doc


# ---------------------------------------------------------------- 18
def probe(node):
    if node is None:
        return "not set"
    return flat_str(node)


def doc18():
    doc = Doc(18, "PyYAML node composition of every container and initContainer of the workloads under "
                  "`kubernetes-manifests/` and `kustomize/components/`; resources, probes, ports and volume mounts are "
                  "flattened as dotted key=value pairs. `not set` means the key is absent from the manifest.")
    doc.section("Resources")
    rows = []
    for p, d in workloads():
        for kind, c in containers(d):
            r = g(c, "resources")
            rows.append((name(d), kind, sv(g(c, "name")),
                         sv(g(r, "requests", "cpu")) or "not set", sv(g(r, "requests", "memory")) or "not set",
                         sv(g(r, "limits", "cpu")) or "not set", sv(g(r, "limits", "memory")) or "not set",
                         (p, *kspan(c, "resources")) if r is not None else (p, ln(c), last(c))))
    doc.table(["Workload", "Type", "Container", "requests.cpu", "requests.memory", "limits.cpu", "limits.memory"], rows)
    doc.section("Probes")
    rows = []
    for p, d in workloads():
        for kind, c in containers(d):
            for key in ("readinessProbe", "livenessProbe", "startupProbe"):
                pr = g(c, key)
                if pr is not None:
                    rows.append((name(d), sv(g(c, "name")), key, probe(pr), (p, *kspan(c, key))))
    doc.table(["Workload", "Container", "Probe", "Definition"], rows)
    doc.section("Containers without probes")
    rows = []
    for p, d in workloads():
        for kind, c in containers(d):
            missing = [k for k in ("readinessProbe", "livenessProbe") if g(c, k) is None]
            if missing:
                rows.append((name(d), kind, sv(g(c, "name")), ", ".join(missing), (p, ln(c), last(c))))
    doc.table(["Workload", "Type", "Container", "Absent keys"], rows)
    doc.section("Container ports")
    rows = []
    for p, d in workloads():
        for kind, c in containers(d):
            for port in items(g(c, "ports")):
                rows.append((name(d), sv(g(c, "name")), sv(g(port, "containerPort")), sv(g(port, "name")) or "not set",
                             (p, ln(port), last(port))))
    doc.table(["Workload", "Container", "containerPort", "port name"], rows)
    doc.section("Volume mounts, volumes, command and args")
    rows = []
    for p, d in workloads():
        for kind, c in containers(d):
            for key in ("volumeMounts", "command", "args"):
                n = g(c, key)
                if n is not None:
                    rows.append((name(d), sv(g(c, "name")), key, flat_str(n), (p, *kspan(c, key))))
        vols = g(d, "spec", "template", "spec", "volumes")
        if vols is not None:
            rows.append((name(d), "(pod)", "volumes", flat_str(vols),
                         (p, *kspan(g(d, "spec", "template", "spec"), "volumes"))))
    doc.table(["Workload", "Container", "Key", "Value"], rows)
    doc.omit("Helm chart resources and probes", f"`{HELM}/` container specs are Go templates over "
                                              "`helm-chart/values.yaml`; only the plain manifests and kustomize "
                                              "components are tabulated")
    if not any(g(c, "startupProbe") is not None for _, d in workloads() for _, c in containers(d)):
        doc.omit("startupProbe", "no container declares `startupProbe`")
    return doc


# ---------------------------------------------------------------- 19
CODE_PATTERNS = [
    ("os.Getenv", r'os\.Getenv\("([A-Za-z0-9_]+)"\)'),
    ("os.LookupEnv", r'os\.LookupEnv\("([A-Za-z0-9_]+)"\)'),
    ("mustMapEnv", r'mustMapEnv\([^,]+,\s*"([A-Za-z0-9_]+)"\)'),
    ("process.env", r"process\.env\.([A-Za-z0-9_]+)"),
    ("process.env[...]", r"process\.env\[['\"]([A-Za-z0-9_]+)['\"]\]"),
    ("os.environ.get", r"os\.environ\.get\(['\"]([A-Za-z0-9_]+)['\"]"),
    ("os.environ[...]", r"os\.environ\[['\"]([A-Za-z0-9_]+)['\"]\]"),
    ("in os.environ", r"['\"]([A-Za-z0-9_]+)['\"] in os\.environ"),
    ("os.getenv", r"os\.getenv\(['\"]([A-Za-z0-9_]+)['\"]"),
    ("System.getenv", r'System\.getenv\("([A-Za-z0-9_]+)"\)'),
    ("System.getenv().getOrDefault", r'System\.getenv\(\)\.getOrDefault\("([A-Za-z0-9_]+)"'),
    ("Environment.GetEnvironmentVariable", r'Environment\.GetEnvironmentVariable\("([A-Za-z0-9_]+)"\)'),
]
CODE_EXT = (".go", ".js", ".py", ".java", ".cs")
SKIP = ("/genproto/", "_pb2", "/node_modules/")


_CODE_READS = []


def code_reads():
    if not _CODE_READS:
        _CODE_READS.append(_code_reads())
    return _CODE_READS[0]


def _code_reads():
    rows = []
    files = sorted(rel(f) for ext in CODE_EXT for f in (REPO / "src").rglob("*" + ext) if f.is_file())
    for path in files:
        if any(x in "/" + path for x in SKIP):
            continue
        for line, text in enumerate(read_lines(path), 1):
            for label, rx in CODE_PATTERNS:
                for m in re.finditer(rx, text):
                    rows.append((path.split("/")[1], m.group(1), label, f"`{text.strip()}`", (path, line)))
    return sorted(set(rows), key=lambda r: (r[0], r[4][0], r[4][1], r[1], r[2]))


def env_rows(d, p):
    rows = []
    for kind, c in containers(d):
        for e in items(g(c, "env")):
            vf = g(e, "valueFrom")
            val = f"value: {sv(g(e, 'value'))}" if g(e, "value") is not None else \
                f"valueFrom: {flat_str(vf)}" if vf is not None else \
                "$patch: delete" if g(e, "$patch") is not None else "not set"
            rows.append((name(d), sv(g(c, "name")), sv(g(e, "name")), val, (p, ln(e), last(e))))
    return rows


def doc19():
    doc = Doc(19, "Container `env` entries are read by PyYAML node composition from the workloads under "
                  "`kubernetes-manifests/` and `kustomize/components/`, and from inline Deployment patches in "
                  "kustomize component kustomization files (lines offset into the file). Code reads are regex matches "
                  "over `src/**/*.{go,js,py,java,cs}` (generated protobuf code excluded) for os.Getenv, os.LookupEnv, "
                  "mustMapEnv, process.env, os.environ, os.getenv, System.getenv, "
                  "Environment.GetEnvironmentVariable; the C# `Configuration[\"...\"]` lookups are listed separately. "
                  "Dockerfile `ENV` instructions are listed from `src/*/Dockerfile`.")
    doc.section("Environment variables in workload manifests")
    rows = []
    for p, d in workloads():
        rows += [(r[0], component_of(p), *r[1:]) for r in env_rows(d, p)]
    doc.table(["Workload", "Kustomize component", "Container", "Name", "Value / valueFrom"], rows)
    doc.section("Commented-out env entries in workload manifests")
    rows = []
    for p in manifest_files():
        for i, line in enumerate(read_lines(p), 1):
            m = re.match(r"^\s*#\s*-\s*name:\s*(\S+)", line)
            if m:
                rows.append((p.split("/")[-1], m.group(1), f"`{line.strip()}`", (p, i)))
    doc.table(["Manifest", "Name", "Line text"], rows)
    doc.section("Environment variables set by kustomize component patches")
    rows = []
    for p, item, pd in embedded_patches():
        if sv(g(pd, "kind")) in WORKLOAD_KINDS and g(pd, "$patch") is None:
            rows += [(component_of(p), *r) for r in env_rows(pd, p)]
    doc.table(["Kustomize component", "Deployment", "Container", "Name", "Value / patch"], rows)
    doc.section("Environment variables read in source code")
    doc.table(["Service", "Variable", "Access", "Code"], code_reads())
    doc.section("Helper `mustMapEnv` definitions")
    for p, l, t in grep(r"^func mustMapEnv\(", "src/**/*.go"):
        doc.quote(p, l, l + 6)
    doc.section("Configuration keys read via C# `Configuration[...]`")
    rows = [(p.split("/")[1], m.group(1), f"`{t}`", (p, l))
            for p, l, t in grep(r'Configuration\["([A-Za-z0-9_]+)"\]', "src/**/*.cs")
            for m in re.finditer(r'Configuration\["([A-Za-z0-9_]+)"\]', t)]
    doc.table(["Service", "Key", "Code"], rows)
    doc.section("Dockerfile ENV instructions")
    rows = [(p.split("/")[1], f"`{t}`", (p, l)) for p, l, t in grep(r"^ENV\s", "src/*/Dockerfile")]
    doc.table(["Service", "Instruction"], rows)
    if not any("valueFrom" in r[4] for p, d in workloads() for r in env_rows(d, p)):
        doc.omit("valueFrom (Secret/ConfigMap references)", f"no `valueFrom` in workload env under `{K8S}/` or `{COMP}/`")
    for label, _ in CODE_PATTERNS:
        if not any(r[2] == label for r in code_reads()):
            doc.omit(f"Code reads via `{label}`", "no match in `src/**/*.{go,js,py,java,cs}`")
    doc.omit("Helm chart env values", f"`{HELM}/` env entries are Go templates over `helm-chart/values.yaml`; "
                                     "only the plain manifests and kustomize patches are tabulated")
    return doc


# ---------------------------------------------------------------- 20
def doc20():
    doc = Doc(20, "PyYAML node composition of every resource in `istio-manifests/` and "
                  "`kustomize/components/service-mesh-istio/`; each resource's `spec` is flattened to dotted field "
                  "paths with the line of each scalar. Helm chart Istio resources are located by regex on "
                  "`apiVersion: (networking|security).istio.io` lines in `helm-chart/templates/*.yaml`; their bodies "
                  "are Go templates and are listed by kind, name expression and the nearest preceding `{{- if ...}}` "
                  "guard line.")
    for d_ in (ISTIO, f"{COMP}/service-mesh-istio"):
        doc.section(f"Resources in `{d_}/`")
        for p in yaml_files(d_):
            if p.endswith("kustomization.yaml"):
                continue
            for d in load(p):
                doc.section(f"{sv(g(d, 'kind'))} `{name(d)}`", 3)
                doc.fact(f"apiVersion `{sv(g(d, 'apiVersion'))}`, kind `{sv(g(d, 'kind'))}`, name `{name(d)}`",
                         p, ln(d), last(d))
                doc.body.append("")
                doc.table(["Field", "Value"], [(f"spec.{fp}", v, (p, l)) for fp, v, l in flat(g(d, "spec"))])
    doc.section("kustomize component `service-mesh-istio` composition")
    kp = f"{COMP}/service-mesh-istio/kustomization.yaml"
    for d in load(kp):
        for r in items(g(d, "resources")):
            doc.fact(f"resource `{sv(r)}`", kp, ln(r))
    for p, item, pd in embedded_patches():
        if p == kp:
            doc.fact(f"patch deletes {sv(g(pd, 'kind'))} `{name(pd)}`" if g(pd, "$patch") is not None
                     else f"patch on {sv(g(pd, 'kind'))} `{name(pd)}`", p, ln(pd), last(pd))
    doc.section("Annotations referencing Istio in workload manifests")
    rows = [(p.split("/")[-1], f"`{t}`", (p, l)) for p, l, t in grep(r"istio\.io", f"{K8S}/*.yaml")]
    doc.table(["Manifest", "Line text"], rows)
    doc.section("Istio resources in the Helm chart templates")
    rows = []
    for p in sorted(rel(x) for x in (REPO / HELM).glob("*.yaml")):
        lines = read_lines(p)
        for i, line in enumerate(lines, 1):
            m = re.match(r"^apiVersion:\s*((networking|security)\.istio\.io/\S+)", line)
            if not m:
                continue
            kind = next((re.sub(r"^kind:\s*", "", x) for x in lines[i:i + 3] if x.startswith("kind:")), "not set")
            nm = next((x.strip() for x in lines[i:i + 6] if x.strip().startswith("name:")), "not set")
            guard = next(((j + 1, lines[j].strip()) for j in range(i - 2, -1, -1)
                          if re.match(r"\s*\{\{-?\s*if\s", lines[j])), None)
            rows.append((p.split("/")[-1], m.group(1), kind, f"`{nm}`",
                         f"`{guard[1]}` (L{guard[0]})" if guard else "none", (p, i)))
    doc.table(["Template", "apiVersion", "Kind", "Name expression", "Nearest preceding if-guard"], rows)
    doc.section("Helm chart values that gate or parameterise these templates")
    vp = "helm-chart/values.yaml"
    vals = load(vp)[0]
    rows = []
    for path in (("sidecars",), ("authorizationPolicies",), ("frontend", "virtualService"),
                 ("cartDatabase", "externalRedisTlsOrigination")):
        n = g(vals, *path)
        if n is None:
            doc.omit(f"`{'.'.join(path)}` in `{vp}`", "key absent")
            continue
        rows += [(".".join(path) + "." + fp, v, (vp, l)) for fp, v, l in flat(n)]
    doc.table(["Values key", "Default value"], rows)
    doc.omit("Helm Istio resource bodies (Sidecar egress hosts, AuthorizationPolicy rules, DestinationRule, "
             "ServiceEntry fields)", "Go-template bodies are not rendered by this extractor; kind, name expression "
             "and guard line are listed")
    present = {sv(g(d, "kind")) for d_ in (ISTIO, f"{COMP}/service-mesh-istio") for p in yaml_files(d_)
               for d in load(p)}
    for k in ("DestinationRule", "PeerAuthentication", "AuthorizationPolicy", "Sidecar"):
        if k not in present:
            doc.omit(f"{k} in `{ISTIO}/` and `{COMP}/service-mesh-istio/`",
                     "no document of this kind in these directories (Helm templates listed above where present)")
    return doc


def build():
    return [doc16(), doc17(), doc18(), doc19(), doc20()]
