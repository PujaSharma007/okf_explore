# Workplace Safety Knowledge Base (an OKF learning project)

> **Please read first:** this is a **learning project**. It is **not** real safety advice.
> The safety facts were written with the help of an AI chatbot, and they have not been checked by a safety expert.
> Never use this project to decide what protection a real workplace needs.

---

## 1. What is OKF?

**OKF** stands for **Open Knowledge Format**. It is a very simple way to write down knowledge.

Here is the whole idea:

* Knowledge is saved as **plain text files** (markdown, `.md`). Anyone can open them in Notepad.
* Each file is about **one thing** (one hazard, one rule, one piece of equipment).
* At the top of each file there is a small **label** that says what kind of thing it is.
* Files **link to each other**, like links on a website. This is how you show that things are related.
* All the files sit together in a **folder**. That folder is called a **bundle**.

That is all. No database, no special program.

### A tiny example

This is a real file from this project (shortened: some labels and sections are left out):

```markdown
---
type: PPE
title: "Respirator"
description: "Reduces inhalation exposure when correctly selected for the identified airborne hazard."
---

# Protects against

* [Welding fumes](/hazards/welding-fumes.md)
* [Chemical exposure](/hazards/chemical-exposure.md)
```

* The part between the two `---` lines is the **label**. The only label OKF *requires* is `type`.
* The line `[Welding fumes](/hazards/welding-fumes.md)` is a **link** to another file.

### Why use it?

* **Easy to read** for people and for AI models.
* **Easy to track changes** (put the folder on GitHub and you can see who changed what).
* **Shows how things connect**, not just a list of facts.
* **Can show where a fact came from** (a `sources` label points to the original document).
* **An AI can read just a few linked files** instead of everything, which is faster and cheaper.

OKF was published by Google Cloud Platform on GitHub:
<https://github.com/GoogleCloudPlatform/open-knowledge-format> (this project follows version 0.2 of its specification).

---

## 2. What is this project?

A small OKF bundle about **workplace safety**. It connects four kinds of things:

```
Work type  ->  Hazard  ->  Protective equipment (PPE)
                  |  \
                  |   -> Safety rule
                  -> Preventive measure
```

For example:

> **Welding** involves the hazard **welding fumes**.
> Welding fumes need a **respirator**, are covered by the rule **respiratory protection**,
> and are reduced by **local exhaust ventilation**.

It can answer questions like *"What PPE is required for welding?"* by **following the links**.

### What is inside the bundle

| Kind | How many | Examples |
|---|---|---|
| Work types | 5 | welding, grinding, roof-work, excavation, chemical-handling |
| Hazards | 8 | welding-fumes, high-noise, fall-from-height, burns |
| PPE (protective equipment) | 8 | respirator, hard-hat, safety-harness |
| Safety rules | 6 | fall-protection, hearing-conservation (each cites an OSHA standard) |
| Preventive measures | 15 | local exhaust ventilation, guardrails, training |
| **Total concept files** | **42** | |

---

## 3. What is the purpose?

1. **To learn how OKF works** by building a small, complete example from start to finish.
2. **To test an idea:** can a language model answer questions correctly when it only reads the few linked files it needs, not the whole knowledge base?
3. **To practise checking answers**, using 15 test questions that have known correct answers.

---

## 4. How does it work?

```
 references/            tools/build_bundle.py            the OKF bundle
 (7 raw notes    --->   reads the notes, checks     --->  42 small linked files
  written with AI)      they agree, writes files         (in 5 folders)
                                                              |
              +-----------------------+-----------------------+
              |                       |                       |
     validate_bundle.py      visualize_bundle.py       ask_okf.py / evaluate_okf.py
     "is it valid OKF?"      "draw it as a network"    "answer questions and score them"
```

### Step by step

1. **`references/`** holds 7 raw notes (about work activities, hazards, PPE, rules, measures, a table, and test questions). They are the *source material*.
2. **`build_bundle.py`** reads those notes, checks that they do not contradict each other, and writes the 42 small linked concept files. All links are worked out by the script, not typed by hand.
3. **`validate_bundle.py`** checks that every file has a valid label and every link points to a file that exists.
4. **`visualize_bundle.py`** draws the bundle as a clickable network (`viz.html`), like a map of connected ideas.
5. **`ask_okf.py`** takes a question, finds the files it is about, follows their links 2 steps, and gives only those files to a small AI model that runs on your own computer (Ollama).
6. **`evaluate_okf.py`** asks all 15 test questions and compares the answers with the correct ones.

### How the testing separates two kinds of mistakes

Every question gets two checks:

* **RETRIEVAL:** did following the links reach all the files that the answer needs? If not, the *bundle* is at fault.
* **ANSWER:** did the AI model then name the right things? If not, the *model* is at fault.

---

## 5. What is in each folder?

```
okf_project/
├── README.md              this file
├── index.md               the front page of the bundle (a table of contents)
├── log.md                 a history of changes
├── work-types/            5 files, one per kind of work
├── hazards/               8 files, one per hazard
├── ppe/                   8 files, one per piece of protective equipment
├── rules/                 6 files, one per safety rule
├── controls/              15 files, one per preventive measure
├── references/            the 7 raw source files (one of them holds the 15 test questions)
└── tools/                 the Python scripts (not part of the bundle itself)
```

Each of the five bundle folders also has its own `index.md`.

---

## 6. How to run it

You need **Python 3** and one small package:

```powershell
pip install pyyaml
```

Run these from the project folder (Windows PowerShell):

```powershell
# Check the bundle is valid OKF
python tools\validate_bundle.py

# Draw the network, then double-click viz.html
python tools\visualize_bundle.py

# Test only the link-following part (no AI model needed)
python tools\evaluate_okf.py --no-llm
```

To ask questions with an AI model, install [Ollama](https://ollama.com), download a model (this project used `qwen2.5:3b`), and run:

```powershell
python tools\ask_okf.py "What PPE is required for welding?"
python tools\evaluate_okf.py
```

The full test writes its details to `eval_results.md`.

---

## 7. Results so far

* **Link-following (retrieval): 15 of 15** questions reached every file they needed.
* **Model answers (`qwen2.5:3b`, first run):** 9 of 15 had nothing missing, and 8 of 15 were exactly right.
  Some of the "missing" items were middle steps that the question did not really ask for,
  so the scoring is a little too strict. This is still being looked at.

---

## 8. Is it safe to run?

Yes. In plain terms:

* The scripts **only read and write files inside this folder**. They do not delete anything.
* They **do not send your data anywhere**. The only network call is to Ollama **on your own computer** (`localhost`).
* `viz.html` works **offline**. All it needs is already inside the file.
* There are **no passwords, keys or personal data** in this project.

Two things to be careful about:

* **`build_bundle.py` overwrites the 42 concept files.** If you edit one by hand and then run the script again, your edit is lost. Change the files in `references/` instead, then re-run the script.
* **Do not trust the content as real safety guidance.** The OSHA links and numbers were suggested by an AI and only spot-checked. Every concept is marked `status: draft`.

---

## 9. Small glossary

| Word | Meaning |
|---|---|
| **OKF** | Open Knowledge Format: knowledge saved as linked markdown files |
| **Bundle** | The folder that holds all the files |
| **Concept** | One file about one thing |
| **Frontmatter** | The small label between the `---` lines at the top of a file |
| **Link** | A pointer from one file to another |
| **PPE** | Personal protective equipment (helmet, gloves, respirator...) |
| **Hazard** | Something that can hurt a person |
| **Retrieval** | Finding the right files for a question |
| **Ollama** | A free program that runs AI models on your own computer |

---

## 10. Ideas for next steps

* Fix the scoring so "middle step" items do not count against the model.
* Try a bigger model and compare it with the small one.
* Compare this approach with a normal "search the text" approach on the same 15 questions.
* Have an expert check the safety facts and mark verified concepts with `verified`.
