#!/usr/bin/env python3
"""Draw the bundle as a network.   Run:  python tools/visualize_bundle.py

Writes viz.html in the bundle root. Open it by double-clicking; it needs no internet and no server.
  * every concept file is a dot (a "node"), coloured by its `type`
  * every markdown link between two concepts is a line (an "edge")
  * click a dot to see its details and to jump along its links
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"tools", "references", "__pycache__", ".git", ".venv"}
OUT = ROOT / "viz.html"
CYTOSCAPE = (ROOT / "tools" / "vendor" / "cytoscape.min.js").read_text(encoding="utf-8")


def concept_files():
    for p in sorted(ROOT.rglob("*.md")):
        parts = p.relative_to(ROOT).parts
        if p.name in ("index.md", "log.md") or any(x in SKIP_DIRS or x.startswith(".") for x in parts):
            continue
        yield p


nodes, bodies = {}, {}
for p in concept_files():
    text = p.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    meta = yaml.safe_load(m.group(1)) if m else {}
    cid = p.relative_to(ROOT).with_suffix("").as_posix()
    body = text[m.end():] if m else text
    nodes[cid] = {
        "id": cid,
        "label": meta.get("title", cid.split("/")[-1]),
        "type": meta.get("type", "Unknown"),
        "description": meta.get("description", ""),
        "status": meta.get("status", "stable"),
        "folder": cid.split("/")[0],
    }
    bodies[cid] = body

directed = set()
for cid, body in bodies.items():
    for target in re.findall(r"\[[^\]]*\]\((/[^)\s]+?)\.md\)", body):
        t = target.lstrip("/")
        if t in nodes and t != cid:
            directed.add((cid, t))

edges, seen = [], set()
for a, b in sorted(directed):
    key = tuple(sorted((a, b)))
    if key in seen:
        continue
    seen.add(key)
    edges.append({"source": a, "target": b, "both": (b, a) in directed})

for n in nodes.values():
    n["out"] = sorted(t for s, t in directed if s == n["id"])
    n["in"] = sorted(s for s, t in directed if t == n["id"])
    n["degree"] = len(set(n["out"]) | set(n["in"]))

data = {"nodes": list(nodes.values()), "edges": edges}
html = (ROOT / "tools" / "viz_template.html").read_text(encoding="utf-8")
html = html.replace("/*CYTOSCAPE*/", CYTOSCAPE)
html = html.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
OUT.write_text(html, encoding="utf-8", newline="\n")
print(f"Wrote {OUT.name}: {len(nodes)} nodes, {len(edges)} connections")
print("Open it by double-clicking viz.html")
