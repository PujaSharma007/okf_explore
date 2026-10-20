#!/usr/bin/env python3
"""Ask the bundle a question.

    python tools/ask_okf.py "What PPE is required for welding?"
    python tools/ask_okf.py "What PPE is required for welding?" --show-context
    python tools/ask_okf.py "Which work types need hearing-protection?" --no-llm    (no model, just show what is retrieved)
    python tools/ask_okf.py                                                        (type questions one after another)
"""
import argparse

from okf_lib import PROMPT, ask_ollama, load_bundle, retrieve


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?")
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--depth", type=int, default=2, help="how many link-steps to walk from the entry concepts")
    ap.add_argument("--show-context", action="store_true", help="print the text given to the model")
    ap.add_argument("--no-llm", action="store_true", help="only show what was retrieved")
    a = ap.parse_args()

    concepts = load_bundle()

    def run(question):
        entries, visited, context = retrieve(question, concepts, depth=a.depth)
        print(f"\nEntry concepts : {', '.join(concepts[e].slug for e in entries) or '(none)'}")
        print(f"Concepts read  : {len(visited)}  (~{len(context) // 4} tokens of context)")
        print("Walk           : " + ", ".join(f"{c.slug}({d})" for c, d in visited if d <= 1) +
              ("  + more at step 2" if any(d == 2 for _, d in visited) else ""))
        if a.show_context:
            print("\n----- CONTEXT GIVEN TO THE MODEL -----\n" + context + "\n----- END CONTEXT -----")
        if a.no_llm:
            return
        print("\nAsking the model ...")
        print("\nANSWER:\n" + ask_ollama(PROMPT.format(context=context, question=question), a.model, a.host))

    if a.question:
        run(a.question)
    else:
        while True:
            q = input("\nQuestion (blank to quit): ").strip()
            if not q:
                break
            run(q)


if __name__ == "__main__":
    main()
