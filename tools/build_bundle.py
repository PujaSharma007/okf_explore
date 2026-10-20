#!/usr/bin/env python3
"""Build the safety OKF bundle from the files in references/.

Run from anywhere:   python tools/build_bundle.py

What it does (in plain words):
  1. Reads the 6 reference files plus ppe_matrix.csv.
  2. Checks that the files agree with each other (hazard <-> PPE <-> rule <-> work type).
  3. Writes one small OKF concept file per work type, hazard, PPE item, rule and control.
  4. Writes index.md (root and per folder) and log.md.
  5. Adds an OKF header to each reference file so the whole folder is a valid bundle.

Every link between concepts is computed from the reference files, nothing is typed by hand.
"""
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "references"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = NOW[:10]

# --- the reference files, as sources a concept can cite -----------------------------------
REF_SOURCES = {
    "work-activities": ("/references/work_activities.md", "Work activities reference"),
    "hazards-catalog": ("/references/hazards_catalog.md", "Hazards catalog reference"),
    "ppe-catalog": ("/references/ppe_catalog.md", "PPE catalog reference"),
    "safety-rules": ("/references/safety_rules.md", "Safety rules reference"),
    "preventive-measures": ("/references/preventive_measures.md", "Preventive measures reference"),
    "ppe-matrix": ("/references/ppe_matrix.csv", "PPE matrix (work type x hazard x PPE)"),
}

SKIP_HEADINGS = {"PPE selection note", "Scope note", "Implementation note"}


# --- reading the reference files ------------------------------------------------------------
def split_ids(value):
    return [x.strip(" .") for x in value.split(",") if x.strip(" .")]


def find_urls(line):
    return re.findall(r"https?://[^\s)]+", line)


def parse_id_file(path):
    """Sections that start with '## some-id' and contain '- Key: value' lines."""
    entries, cur, key = {}, None, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            if name in SKIP_HEADINGS or not re.fullmatch(r"[a-z0-9-]+", name):
                cur = None
                continue
            cur, key = name, None
            entries[cur] = {"_urls": []}
            continue
        if cur is None:
            continue
        m = re.match(r"- ([A-Za-z ]+):\s*(.*)$", line)
        if m:
            key = m.group(1).strip()
            entries[cur][key] = m.group(2).strip()
        for u in find_urls(line):
            if u not in entries[cur]["_urls"]:
                entries[cur]["_urls"].append(u)
    return entries


def parse_measures(path):
    """Preventive measures: '## Level' then '### Title' then '- Key: value' lines."""
    items, level, cur, key = [], None, None, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            level = None if name in SKIP_HEADINGS else name
            cur = None
        elif line.startswith("### ") and level:
            cur = {"title": line[4:].strip(), "level": level, "_urls": []}
            items.append(cur)
            key = None
        elif cur is not None:
            m = re.match(r"- ([A-Za-z ]+):\s*(.*)$", line)
            if m:
                key = m.group(1).strip()
                cur[key] = m.group(2).strip()
            for u in find_urls(line):
                if u not in cur["_urls"]:
                    cur["_urls"].append(u)
    for c in items:
        c["id"] = re.sub(r"[^a-z0-9]+", "-", c["title"].lower()).strip("-")
    return items


def read_matrix(path):
    matrix = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            matrix[(row["work_type"], row["hazard"])] = row["required_ppe"].split("|")
    return matrix


# --- small helpers for writing --------------------------------------------------------------
def q(s):
    return json.dumps(s, ensure_ascii=False)  # a double-quoted string is valid YAML


TITLE_OVERRIDES = {"eye-face-protection": "Eye and face protection"}


def title_of(i):
    return TITLE_OVERRIDES.get(i, i.replace("-", " ").capitalize())


def link(folder, i, title=None):
    return f"[{title or title_of(i)}](/{folder}/{i}.md)"


def bullets(items):
    return "\n".join(f"* {x}" for x in items) if items else "_None listed in the reference files._"


def osha(url):
    m = re.search(r"standardnumber/\d+/(\d+\.\d+)$", url)
    if not m:
        raise ValueError(f"Unexpected URL shape: {url}")
    num = m.group(1)
    return f"osha-{num.replace('.', '-')}", f"OSHA 29 CFR {num}"


def uniq(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def frontmatter(type_, title, desc, tags, source_ids, urls):
    lines = [
        "---",
        f"type: {type_}",
        f"title: {q(title)}",
        f"description: {q(desc)}",
        "tags: [" + ", ".join(tags) + "]",
        "status: draft",
        f"generated: {{ by: process:build-bundle, at: {NOW} }}",
        "sources:",
    ]
    for sid in source_ids:
        res, t = REF_SOURCES[sid]
        lines += [f"  - id: {sid}", f"    resource: {res}", f"    title: {q(t)}"]
    for url in uniq(urls):
        oid, ot = osha(url)
        lines += [f"  - id: {oid}", f"    resource: {url}", f"    title: {q(ot)}"]
    lines.append("---")
    return "\n".join(lines)


def footnote_defs(source_ids, urls):
    out = [f"[^{sid}]: {REF_SOURCES[sid][1]}" for sid in source_ids]
    for url in uniq(urls):
        oid, ot = osha(url)
        out.append(f"[^{oid}]: {ot}, {url}")
    return "\n".join(out)


def official_refs(urls):
    items = []
    for url in uniq(urls):
        oid, ot = osha(url)
        items.append(f"{ot}[^{oid}]")
    return items


def section(title, body, note=None):
    text = body + (f"\n\n_Source_[^{note}]" if note else "")
    return f"# {title}\n\n{text}"


def write(folder, cid, content):
    d = ROOT / folder
    d.mkdir(exist_ok=True)
    (d / f"{cid}.md").write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def first_sentence(text):
    return text if text.endswith(".") else text + "."


# --- load everything ------------------------------------------------------------------------
work = parse_id_file(REF / "work_activities.md")
haz = parse_id_file(REF / "hazards_catalog.md")
ppe = parse_id_file(REF / "ppe_catalog.md")
rules = parse_id_file(REF / "safety_rules.md")
controls = parse_measures(REF / "preventive_measures.md")
matrix = read_matrix(REF / "ppe_matrix.csv")

# --- consistency checks (this is what caught the 3 mismatches earlier) ----------------------
problems = []


def check(label, a, b):
    if set(a) != set(b):
        problems.append(f"{label}: {sorted(a)} != {sorted(b)}")


for w, e in work.items():
    check(f"work '{w}' hazards vs hazards_catalog",
          ids := split_ids(e["Hazards"]), [h for h, he in haz.items() if w in split_ids(he["Work types"])])
    check(f"work '{w}' hazards vs matrix", ids, [h for (ww, h) in matrix if ww == w])
for h, e in haz.items():
    p = split_ids(e["PPE"])
    mp = {x for (w, hh), v in matrix.items() if hh == h for x in v}
    check(f"hazard '{h}' PPE vs matrix", p, mp)
    check(f"hazard '{h}' PPE vs ppe_catalog", p, [x for x, pe in ppe.items() if h in split_ids(pe["Hazards"])])
    check(f"hazard '{h}' rules vs safety_rules", split_ids(e["Rules"]),
          [r for r, re_ in rules.items() if h in split_ids(re_["Hazards"])])
    for pid in p:
        if pid not in ppe:
            problems.append(f"hazard '{h}' lists unknown PPE '{pid}'")
    for rid in split_ids(e["Rules"]):
        if rid not in rules:
            problems.append(f"hazard '{h}' lists unknown rule '{rid}'")
for c in controls:
    for h in split_ids(c["Hazards reduced"]):
        if h not in haz:
            problems.append(f"control '{c['id']}' reduces unknown hazard '{h}'")

if problems:
    print("The reference files disagree with each other:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("Reference files agree with each other.")

# --- derived relationships ------------------------------------------------------------------
def hazards_of(w):
    return split_ids(work[w]["Hazards"])


def controls_for(hazard_ids):
    return [c for c in controls if set(split_ids(c["Hazards reduced"])) & set(hazard_ids)]


def work_types_of_ppe(pid):
    return uniq([w for (w, h), v in matrix.items() if pid in v])


# --- 1. work types --------------------------------------------------------------------------
for w, e in work.items():
    hs = hazards_of(w)
    ppe_lines = [f"{link('hazards', h, '**' + title_of(h) + '**')}: "
                 + ", ".join(link("ppe", x) for x in matrix[(w, h)]) for h in hs]
    rule_ids = uniq([r for h in hs for r in split_ids(haz[h]["Rules"])])
    # Controls are deliberately NOT listed on work types: a hazard such as 'burns' is shared by
    # welding and chemical handling, so linking controls here would suggest e.g. chemical
    # substitution for welders. Follow the hazard link instead.
    sids = ["work-activities", "ppe-matrix", "hazards-catalog"]
    body = "\n\n".join([
        first_sentence(e["Description"]) + "[^work-activities]",
        section("Typical tasks", e["Typical tasks"]),
        section("Hazards", bullets([link("hazards", h) for h in hs]), "work-activities"),
        section("Required PPE", bullets(ppe_lines), "ppe-matrix"),
        section("Applicable rules", bullets([link("rules", r) for r in rule_ids]), "hazards-catalog"),
        section("Official references", bullets(official_refs(e["_urls"]))),
        footnote_defs(sids, e["_urls"]),
    ])
    write("work-types", w, frontmatter("Work Type", title_of(w), first_sentence(e["Description"]),
                                       ["safety", "work-type"], sids, e["_urls"]) + "\n\n" + body)

# --- 2. hazards -----------------------------------------------------------------------------
for h, e in haz.items():
    ctrl = controls_for([h])
    sids = ["hazards-catalog", "ppe-matrix", "preventive-measures"]
    body = "\n\n".join([
        first_sentence(e["Harm"]) + "[^hazards-catalog]",
        section("Typical injuries", e["Typical injuries"]),
        section("Work types", bullets([link("work-types", w) for w in split_ids(e["Work types"])]),
                "hazards-catalog"),
        section("Required PPE", bullets([link("ppe", x) for x in split_ids(e["PPE"])]), "ppe-matrix"),
        section("Rules", bullets([link("rules", r) for r in split_ids(e["Rules"])]), "hazards-catalog"),
        section("Preventive measures", bullets([link("controls", c["id"], c["title"]) for c in ctrl]),
                "preventive-measures"),
        section("Controls summary", e["Controls"]),
        section("Official references", bullets(official_refs(e["_urls"]))),
        footnote_defs(sids, e["_urls"]),
    ])
    write("hazards", h, frontmatter("Hazard", title_of(h), first_sentence(e["Harm"]),
                                    ["safety", "hazard"], sids, e["_urls"]) + "\n\n" + body)

# --- 3. PPE ---------------------------------------------------------------------------------
for p, e in ppe.items():
    rule_ids = [r for r, re_ in rules.items() if p in split_ids(re_["PPE"])]
    sids = ["ppe-catalog", "safety-rules", "ppe-matrix"]
    body = "\n\n".join([
        first_sentence(e["Purpose"]) + "[^ppe-catalog]",
        section("Protects against", bullets([link("hazards", h) for h in split_ids(e["Hazards"])]),
                "ppe-catalog"),
        section("Used in work types", bullets([link("work-types", w) for w in work_types_of_ppe(p)]),
                "ppe-matrix"),
        section("Rules", bullets([link("rules", r) for r in rule_ids]), "safety-rules"),
        section("Limitations", e["Limitations"]),
        section("Inspection", e["Inspection"]),
        section("Official references", bullets(official_refs(e["_urls"]))),
        footnote_defs(sids, e["_urls"]),
    ])
    write("ppe", p, frontmatter("PPE", title_of(p), first_sentence(e["Purpose"]),
                                ["safety", "ppe"], sids, e["_urls"]) + "\n\n" + body)

# --- 4. rules -------------------------------------------------------------------------------
for r, e in rules.items():
    sids = ["safety-rules"]
    body = "\n\n".join([
        first_sentence(e["Summary"]) + "[^safety-rules]",
        section("Official citation", e["Official citation"]),
        section("Applies to", e["Applies to"]),
        section("Required PPE", bullets([link("ppe", x) for x in split_ids(e["PPE"])]), "safety-rules"),
        section("Hazards covered", bullets([link("hazards", h) for h in split_ids(e["Hazards"])]),
                "safety-rules"),
        section("Official references", bullets(official_refs(e["_urls"]))),
        footnote_defs(sids, e["_urls"]),
    ])
    write("rules", r, frontmatter("Safety Rule", title_of(r), first_sentence(e["Summary"]),
                                  ["safety", "rule", "osha"], sids, e["_urls"]) + "\n\n" + body)

# --- 5. preventive measures (controls) ------------------------------------------------------
for c in controls:
    sids = ["preventive-measures"]
    body = "\n\n".join([
        first_sentence(c["Measure"]) + "[^preventive-measures]",
        section("Hierarchy of controls", c["level"], "preventive-measures"),
        section("Hazards reduced", bullets([link("hazards", h) for h in split_ids(c["Hazards reduced"])]),
                "preventive-measures"),
        section("Official references", bullets(official_refs(c["_urls"]))),
        footnote_defs(sids, c["_urls"]),
    ])
    write("controls", c["id"], frontmatter("Preventive Measure", c["title"], first_sentence(c["Measure"]),
                                           ["safety", "control", c["level"].lower()], sids, c["_urls"])
          + "\n\n" + body)

# --- 6. index files and log -----------------------------------------------------------------
FOLDERS = [
    ("work-types", "Work Types", "Jobs and tasks, with their hazards, required PPE, rules and controls."),
    ("hazards", "Hazards", "What can hurt people, linked to work types, PPE, rules and controls."),
    ("ppe", "PPE", "Protective equipment, what it protects against, and its limits."),
    ("rules", "Rules", "OSHA requirements, with citations and the PPE and hazards they cover."),
    ("controls", "Preventive Measures", "Non-PPE controls, grouped by the hierarchy of controls."),
]


def read_fm(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = {}
    for line in m.group(1).splitlines():
        for k in ("title", "description"):
            if line.startswith(k + ":"):
                meta[k] = json.loads(line.split(":", 1)[1].strip())
    return meta


for folder, heading, _ in FOLDERS:
    lines = [f"# {heading}", ""]
    for f in sorted((ROOT / folder).glob("*.md")):
        if f.name in ("index.md", "log.md"):
            continue
        meta = read_fm(f)
        lines.append(f"* [{meta['title']}]({f.name}) - {meta['description']}")
    (ROOT / folder / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

root_lines = ['---', 'okf_version: "0.2"', '---', "", "# Workplace Safety Knowledge Bundle", ""]
root_lines += [f"* [{h}]({f}/) - {d}" for f, h, d in FOLDERS]
root_lines += ["", "# Source material", "",
               "* [References](references/) - Raw reference files the concepts were written from."]
(ROOT / "index.md").write_text("\n".join(root_lines) + "\n", encoding="utf-8", newline="\n")

counts = {f: len(list((ROOT / f).glob("*.md"))) - 1 for f, _, _ in FOLDERS}  # minus index.md
total = sum(counts.values())
(ROOT / "log.md").write_text(
    f"# Directory Update Log\n\n## {TODAY}\n"
    f"* **Creation**: Generated {total} concept files from the reference files "
    f"({', '.join(f'{n} {f}' for f, n in counts.items())}).\n"
    f"* **Update**: Added OKF headers to the reference files so the whole folder is a valid bundle.\n",
    encoding="utf-8", newline="\n")

# --- 7. give each reference .md file an OKF header (only if it has none) -----------------------
REF_META = {
    "work_activities.md": ("Work activities reference", "Source list of work types, tasks and hazards."),
    "hazards_catalog.md": ("Hazards catalog reference", "Source list of hazards, injuries, PPE, rules and controls."),
    "ppe_catalog.md": ("PPE catalog reference", "Source list of PPE items, limits and inspection guidance."),
    "safety_rules.md": ("Safety rules reference", "Source list of OSHA rules with citations."),
    "preventive_measures.md": ("Preventive measures reference", "Source list of non-PPE controls by hierarchy."),
    "test_questions.md": ("Test questions", "15 questions with expected answers for testing the bundle."),
}
for name, (t, d) in REF_META.items():
    p = REF / name
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        header = f"---\ntype: Reference\ntitle: {q(t)}\ndescription: {q(d)}\ntags: [safety, reference]\nstatus: draft\n---\n\n"
        p.write_text(header + text, encoding="utf-8", newline="\n")

print(f"Wrote {total} concept files: " + ", ".join(f"{n} {f}" for f, n in counts.items()))
