"""Shared helpers for asking questions of the bundle.

The idea ("how OKF retrieval works"), in plain words:
  1. Find which concepts the question is about          -> the "entry points"
  2. Walk the links outwards from them (1-2 steps)       -> the "neighbourhood"
  3. Hand ONLY that neighbourhood to the language model  -> the "context"
So the model reads a few linked files instead of the whole bundle.
"""
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"tools", "references", "__pycache__", ".git", ".venv"}
LINK_RE = re.compile(r"\[([^\]]*)\]\((/[^)\s]+?)\.md\)")

# Sections that are prose (long text). We keep them for the concepts closest to the question
# and drop them for concepts further away, so the model is not flooded with detail.
PROSE_SECTIONS = {"Typical tasks", "Typical injuries", "Limitations", "Inspection",
                  "Controls summary", "Official citation", "Applies to", "Hierarchy of controls"}
STOPWORDS = set("which what that this with from have need needs required require applies apply "
                "about does into their them they when where whose should would could".split())


# ---------------------------------------------------------------- loading the bundle
class Concept:
    def __init__(self, path):
        text = path.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
        meta = yaml.safe_load(m.group(1)) if m else {}
        body = text[m.end():] if m else text
        self.id = path.relative_to(ROOT).with_suffix("").as_posix()      # e.g. hazards/welding-fumes
        self.slug = path.stem                                            # e.g. welding-fumes
        self.type = meta.get("type", "Unknown")
        self.title = meta.get("title", self.slug)
        self.description = meta.get("description", "")
        self.links = sorted({t.lstrip("/") for _, t in LINK_RE.findall(body)})
        self.sections = self._clean_sections(body)

    @staticmethod
    def _clean_sections(body):
        body = re.sub(r"^\[\^[^\]]+\]:.*$", "", body, flags=re.M)        # footnote definitions
        body = re.sub(r"\[\^[^\]]+\]", "", body)                         # footnote marks
        body = re.sub(r"^_Source_\s*$", "", body, flags=re.M)
        body = LINK_RE.sub(lambda m: m.group(2).split("/")[-1], body)    # [Text](/x/y.md) -> y
        body = body.replace("**", "")
        sections, name, buf = {}, "Summary", []
        for line in body.splitlines():
            if line.startswith("# "):
                sections[name] = "\n".join(buf).strip()
                name, buf = line[2:].strip(), []
            else:
                buf.append(line)
        sections[name] = "\n".join(buf).strip()
        sections.pop("Official references", None)
        return {k: v for k, v in sections.items() if v}

    def render(self, full=True):
        out = [f"## {self.slug}  [{self.type}]", self.description]
        for name, text in self.sections.items():
            if name == "Summary":
                continue
            if not full and name in PROSE_SECTIONS:
                continue
            out.append(f"{name}:\n{text}")
        return "\n".join(out)


def load_bundle():
    concepts = {}
    for p in sorted(ROOT.rglob("*.md")):
        parts = p.relative_to(ROOT).parts
        if p.name in ("index.md", "log.md") or any(x in SKIP_DIRS or x.startswith(".") for x in parts):
            continue
        c = Concept(p)
        concepts[c.id] = c
    slugs = [c.slug for c in concepts.values()]
    dupes = {s for s in slugs if slugs.count(s) > 1}
    assert not dupes, f"Concept names must be unique across folders: {dupes}"
    return concepts


# ---------------------------------------------------------------- finding concepts in text
def _norm(text):
    return re.sub(r"[-_]", " ", text.lower())


def find_concepts(text, concepts):
    """Return slugs of concepts mentioned in `text` (by id, hyphenated or plain words, or title).
    Longest names are matched first and then 'used up', so 'welding fumes' is not also read as 'welding'."""
    names = []
    for c in concepts.values():
        for n in {_norm(c.slug), _norm(c.title)}:
            names.append((n, c.slug))
    names.sort(key=lambda x: -len(x[0]))
    work, hits = _norm(text), []
    for name, slug in names:
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", work):
            hits.append((m.start(), slug))
            work = work[:m.start()] + " " * len(name) + work[m.end():]
    seen, ordered = set(), []
    for _, slug in sorted(hits):
        if slug not in seen:
            seen.add(slug)
            ordered.append(slug)
    return ordered


# ---------------------------------------------------------------- retrieval by walking links
def _fallback_entries(question, concepts, top=3):
    words = {w for w in re.findall(r"[a-z]{4,}", _norm(question)) if w not in STOPWORDS}
    scored = []
    for c in concepts.values():
        hay = set(re.findall(r"[a-z]{4,}", _norm(f"{c.slug} {c.title} {c.description}")))
        score = len(words & hay)
        if score:
            scored.append((-score, c.id))
    return [cid for _, cid in sorted(scored)[:top]]


def retrieve(question, concepts, depth=2, max_chars=12000):
    """Returns (entry_ids, visited, context_text). visited = [(concept, distance)]."""
    by_slug = {c.slug: c.id for c in concepts.values()}
    entries = [by_slug[s] for s in find_concepts(question, concepts)] or _fallback_entries(question, concepts)

    # backlinks, so we can walk a link in both directions
    neighbours = {cid: set(c.links) for cid, c in concepts.items()}
    for cid, c in concepts.items():
        for t in c.links:
            if t in neighbours:
                neighbours[t].add(cid)

    dist, frontier = {e: 0 for e in entries}, list(entries)
    for d in range(1, depth + 1):
        nxt = []
        for cid in frontier:
            for n in sorted(neighbours.get(cid, ())):
                if n in concepts and n not in dist:
                    dist[n] = d
                    nxt.append(n)
        frontier = nxt

    visited = sorted(((concepts[i], d) for i, d in dist.items()), key=lambda x: (x[1], x[0].id))
    blocks, used = [], 0
    for c, d in visited:
        block = c.render(full=(d <= 1))
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return entries, visited, "\n\n".join(blocks)


# ---------------------------------------------------------------- talking to the model (Ollama)
PROMPT = """You answer questions about workplace safety using ONLY the facts below.
The facts come from a linked knowledge bundle. Each block is named by its ID.

Rules:
- Use only the facts. Do not use outside knowledge.
- Answer as a short bullet list of IDs, written exactly as in the facts (lowercase with hyphens).
- If the facts do not contain the answer, write: NOT FOUND

FACTS:
{context}

QUESTION: {question}

ANSWER:"""


def ask_ollama(prompt, model="qwen2.5:3b", host="http://localhost:11434", num_ctx=8192):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0, "num_ctx": num_ctx}}).encode()
    req = urllib.request.Request(f"{host}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read())["response"].strip()
    except urllib.error.URLError as e:
        raise SystemExit(f"Could not reach Ollama at {host} ({e.reason}).\n"
                         f"Start it, and check the model exists with:  ollama list")
