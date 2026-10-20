#!/usr/bin/env python3
"""Check that the bundle follows OKF v0.2.   Run:  python tools/validate_bundle.py

Checks (from the spec's conformance section, plus link and footnote checks):
  1. Every concept .md file has a YAML header with a non-empty `type`.
  2. index.md has no header (except the root one) and log.md has ISO date headings.
  3. Every markdown link between concepts points at a file that exists.
  4. Every `sources` entry that is a bundle path exists.
  5. Every footnote used in a file is defined in that file.
"""
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"tools", "__pycache__", ".git", ".venv"}
errors, warnings = [], []
types = Counter()
link_count = 0


def rel(p):
    return p.relative_to(ROOT).as_posix()


def md_files():
    for p in sorted(ROOT.rglob("*.md")):
        if any(part in SKIP_DIRS or part.startswith(".") for part in p.relative_to(ROOT).parts):
            continue
        yield p


def split_header(text):
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    return (m.group(1), text[m.end():]) if m else (None, text)


for path in md_files():
    name = path.name
    text = path.read_text(encoding="utf-8")
    header, body = split_header(text)

    if name == "index.md":
        if header is not None and path.parent != ROOT:
            errors.append(f"{rel(path)}: only the root index.md may have a header")
        if header is not None:
            try:
                meta = yaml.safe_load(header) or {}
                if set(meta) - {"okf_version"}:
                    errors.append(f"{rel(path)}: root index.md header may only hold okf_version")
            except yaml.YAMLError as e:
                errors.append(f"{rel(path)}: bad YAML ({e})")
    elif name == "log.md":
        if not re.search(r"^## \d{4}-\d{2}-\d{2}$", body, re.M):
            errors.append(f"{rel(path)}: log.md needs '## YYYY-MM-DD' headings")
    else:
        if header is None:
            errors.append(f"{rel(path)}: no YAML header")
            continue
        try:
            meta = yaml.safe_load(header)
        except yaml.YAMLError as e:
            errors.append(f"{rel(path)}: bad YAML ({e})")
            continue
        if not isinstance(meta, dict) or not str(meta.get("type", "")).strip():
            errors.append(f"{rel(path)}: missing or empty `type`")
            continue
        types[meta["type"]] += 1
        for s in meta.get("sources", []) or []:
            res = str(s.get("resource", ""))
            if not res:
                errors.append(f"{rel(path)}: a source has no `resource`")
            elif res.startswith("/") and not (ROOT / res.lstrip("/")).exists():
                errors.append(f"{rel(path)}: source path not found: {res}")
        used = set(re.findall(r"\[\^([^\]]+)\](?!:)", body))
        defined = set(re.findall(r"^\[\^([^\]]+)\]:", body, re.M))
        for f in sorted(used - defined):
            errors.append(f"{rel(path)}: footnote [^{f}] used but not defined")
        for f in sorted(defined - used):
            warnings.append(f"{rel(path)}: footnote [^{f}] defined but never used")

    for target in re.findall(r"\[[^\]]*\]\(([^)\s]+)\)", body):
        if re.match(r"[a-z]+://", target) or target.startswith("#"):
            continue
        link_count += 1
        target = target.split("#")[0]
        dest = (ROOT / target.lstrip("/")) if target.startswith("/") else (path.parent / target)
        if not dest.exists():
            errors.append(f"{rel(path)}: broken link -> {target}")

print("Concept types found:", dict(types))
print(f"Links checked: {link_count}")
for w in warnings:
    print("warning:", w)
for e in errors:
    print("ERROR:", e)
print("RESULT:", "FAILED" if errors else "OK - bundle is conformant with OKF v0.2")
sys.exit(1 if errors else 0)
