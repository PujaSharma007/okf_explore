#!/usr/bin/env python3
"""Score the bundle against references/test_questions.md.

    python tools/evaluate_okf.py                 run all 15 questions with Ollama and score the answers
    python tools/evaluate_okf.py --no-llm        check ONLY the retrieval step (fast, no model needed)
    python tools/evaluate_okf.py --depth 1       try a smaller walk (1 link-step instead of 2)

For every question there are two separate checks, so you can tell WHO made a mistake:
  RETRIEVAL : did the walk over the links reach every concept that the expected answer needs?
              (if not, the bundle or the walk is at fault)
  ANSWER    : did the model's answer contain every expected ID, and nothing extra?
              (if retrieval was fine but this fails, the model is at fault)

IDs that already appear in the question itself are ignored when scoring, because repeating them
is not an answer.  Full details are written to eval_results.md.
"""
import argparse
import re
from pathlib import Path

from okf_lib import PROMPT, ROOT, ask_ollama, find_concepts, load_bundle, retrieve


def parse_questions(path, concepts):
    text = path.read_text(encoding="utf-8")
    known = {c.slug for c in concepts.values()}
    out = []
    parts = re.split(r"^### Question (\d+)\s*$", text, flags=re.M)
    for num, body in zip(parts[1::2], parts[2::2]):
        lines = [l for l in body.strip().splitlines()]
        question = next(l.strip() for l in lines if l.strip())
        expected_text, grab = [], False
        for l in lines:
            if l.strip().startswith("Expected answer"):
                grab = True
                continue
            if grab:
                if not l.strip():
                    break
                expected_text.append(l)
        expected = {s for s in re.findall(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", "\n".join(expected_text)) if s in known}
        out.append({"n": int(num), "question": question, "expected": expected})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--questions", default=str(ROOT / "references" / "test_questions.md"))
    a = ap.parse_args()

    concepts = load_bundle()
    questions = parse_questions(Path(a.questions), concepts)
    report = [f"# Evaluation results\n\nmodel: {'(none, retrieval only)' if a.no_llm else a.model} · walk depth: {a.depth}\n"]
    retr_ok = complete = exact = 0

    print(f"{'Q':>3}  {'RETRIEVAL':<10} {'ANSWER':<10} notes")
    for q in questions:
        in_question = set(find_concepts(q["question"], concepts))
        want = q["expected"] - in_question
        entries, visited, context = retrieve(q["question"], concepts, depth=a.depth)
        seen_in_context = {c.slug for c, _ in visited}
        # only count what actually fit into the context text
        in_ctx = {s for s in seen_in_context if f"## {s}  [" in context}
        r_missing = want - in_ctx
        r_ok = not r_missing
        retr_ok += r_ok

        answer, missing, extra, verdict, notes = "", set(), set(), "-", ""
        if not a.no_llm:
            answer = ask_ollama(PROMPT.format(context=context, question=q["question"]), a.model, a.host)
            got = set(find_concepts(answer, concepts)) - in_question
            missing, extra = want - got, got - want
            if "NOT FOUND" in answer.upper() and not got:
                verdict = "NOT FOUND"
            elif not missing and not extra:
                verdict = "EXACT"
            elif not missing:
                verdict = "COMPLETE+"
            else:
                verdict = "MISSING"
            complete += not missing and verdict != "NOT FOUND"
            exact += verdict == "EXACT"
            notes = (f"missing: {', '.join(sorted(missing))}  " if missing else "") + \
                    (f"extra: {', '.join(sorted(extra))}" if extra else "")
        if not r_ok:
            notes = f"not retrieved: {', '.join(sorted(r_missing))}  " + notes
        print(f"{q['n']:>3}  {'OK' if r_ok else 'MISS':<10} {verdict:<10} {notes}")

        report.append(f"## Q{q['n']}. {q['question']}\n")
        report.append(f"* Expected IDs (minus ones in the question): {', '.join(sorted(want))}")
        report.append(f"* Entry concepts: {', '.join(concepts[e].slug for e in entries)}")
        report.append(f"* Retrieval: {'OK' if r_ok else 'MISSING ' + ', '.join(sorted(r_missing))} "
                      f"({len(visited)} concepts, ~{len(context) // 4} tokens)")
        if not a.no_llm:
            report.append(f"* Verdict: **{verdict}**  {notes}")
            report.append(f"* Model answer:\n\n```\n{answer}\n```")
        report.append("")

    n = len(questions)
    print(f"\nRetrieval reached every needed concept : {retr_ok}/{n}")
    if not a.no_llm:
        print(f"Answers with nothing missing           : {complete}/{n}")
        print(f"Answers exactly right (no extras)      : {exact}/{n}")
    summary = f"\n**Retrieval {retr_ok}/{n}**" + ("" if a.no_llm else f" · complete {complete}/{n} · exact {exact}/{n}")
    (ROOT / "eval_results.md").write_text("\n".join(report) + summary + "\n", encoding="utf-8")
    print("Details written to eval_results.md")


if __name__ == "__main__":
    main()
