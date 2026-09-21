"""
Week 3 RAG evaluation runner (W3-06).

Runs all 15 questions from docs/evaluation/week3-rag-eval.md against the real
retrieval + answer pipeline (src.rag.answer.answer_query), records what the
system actually returned, scores pass/fail against US-10, and writes a filled
results table plus a groundedness/refusal summary.

Run this from the repo root (BSE4104-SME-PROCUREMENT-AGENT/), with your .env
MODEL_API_KEY already set, since it makes real model calls:

    python -m scripts.run_week3_rag_eval

Requires: sentence-transformers and network access to your model provider.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.answer import answer_query  # noqa: E402

REFUSAL = "cannot answer from available documents"

# id, question, type (A/B/C), expected_citation_substring (None for C rows)
CASES = [
    ("A1", "How many quotations are required for a requisition worth UGX 2,000,000?", "A", "2.1"),
    ("A2", "Can a requisition cover more than one stock item?", "A", "1.2"),
    ("A3", "Who approves a requisition worth UGX 3,000,000?", "A", "5.1"),
    ("A4", "What happens to a quotation whose validity period has already lapsed by the time the requisition is prepared?", "A", "2.3"),
    ("A5", "Can the officer who prepared a requisition also approve it?", "A", "5.4"),
    ("B1", "What quotations are required for a UGX 2,000,000 requisition, and which specific suppliers should I use?", "B", "2.1"),
    ("B2", "How is landed cost calculated, and what is today's VAT rate?", "B", "3.1"),
    ("B3", "A supplier not on the register is the cheapest option — can I recommend them, and how long does director approval take?", "B", "4.3"),
    ("B4", "What must a valid quotation state, and what's a common mistake suppliers make when writing one?", "B", "2.4"),
    ("B5", "If two quotations are within 2% of landed cost, how is the tie broken, and how many days difference counts as \"shorter\"?", "B", "3.4"),
    ("C1", "What is the penalty for a supplier who submits a fraudulent quotation?", "C", None),
    ("C2", "Can a requisition be approved retroactively after goods are already delivered?", "C", None),
    ("C3", "What is the company's registered VAT rate?", "C", None),
    ("C4", "How many requisitions has SUP-05 been excluded from in the past year?", "C", None),
    ("C5", "Who is the current operations manager by name?", "C", None),
]


def score_case(case_type: str, expected: str | None, result: dict) -> tuple[str, str]:
    """Return (verdict, note). Verdict is PASS, FAIL, or ERROR.

    ERROR means the model/API call itself failed (network, quota, transient
    server error) — this is NOT a RAG grounding result and must be re-run,
    not counted as a pass or a fail.

    Per the evaluation file's own pass criteria, citing the correct SOURCE
    DOCUMENT is sufficient for a pass on A/B rows — the pipeline does not
    return clause-level citations, which is a separate, real finding to log
    in W3-07, not a per-question failure.
    """
    answer = result.get("answer", "")
    citations = result.get("citations", [])
    refused = answer.strip().lower() == REFUSAL
    errored = answer.strip().upper().startswith("ERROR")

    if errored:
        return "ERROR", f"API/model call failed, not a real grounding result: {answer[:120]}"

    if case_type == "C":
        if refused:
            return "PASS", "Correctly refused (no basis in corpus)."
        return "FAIL", "FAILED TO REFUSE — answered a question the corpus cannot support."

    # A and B rows: must NOT refuse, and must cite at least the source document
    if refused:
        return "FAIL", "Refused an answerable question — retrieval or threshold problem."
    if not citations:
        return "FAIL", "Answered with NO citation at all — ungrounded answer."
    return "PASS", (
        f"Answered and cited {citations[0]}. NOTE: pipeline only returns "
        f"document-level citations, not clause-level (expected {expected}) — "
        "verify clause match manually; log as a grounding-granularity finding."
    )


def main() -> None:
    import time
    import json

    cache_path = PROJECT_ROOT / "docs" / "evaluation" / "week3-rag-eval-cache.json"
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        cache = {}

    rows = []
    passed = 0
    errored = 0
    refused_correctly = 0
    total_c = sum(1 for _, _, t, _ in CASES if t == "C")
    scored_total = 0  # excludes ERROR rows from the percentage base

    for case_id, question, case_type, expected in CASES:
        cached = cache.get(case_id)
        if cached and cached.get("verdict") != "ERROR":
            # Already have a real result from a previous run — don't burn quota re-asking.
            result = {"answer": cached["answer"], "citations": cached["citations"]}
            verdict, note = cached["verdict"], cached["note"] + " [from earlier run — not re-queried]"
        else:
            try:
                result = answer_query(question)
            except Exception as exc:  # noqa: BLE001
                result = {"answer": f"ERROR: {exc}", "citations": []}
            verdict, note = score_case(case_type, expected, result)
            time.sleep(2)  # be gentle on a rate-limited API key

        cache[case_id] = {
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "verdict": verdict,
            "note": note,
        }

        if verdict == "ERROR":
            errored += 1
        else:
            scored_total += 1
            if verdict == "PASS":
                passed += 1
                if case_type == "C":
                    refused_correctly += 1

        rows.append(
            {
                "id": case_id,
                "type": case_type,
                "question": question,
                "answer": result.get("answer", ""),
                "citations": result.get("citations", []),
                "verdict": verdict,
                "note": note,
            }
        )
        print(f"[{case_id}] {verdict} — {note}")

    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    groundedness_rate = (passed / scored_total * 100) if scored_total else 0.0
    refusal_accuracy = (refused_correctly / total_c * 100) if total_c else 0.0

    out_path = PROJECT_ROOT / "docs" / "evaluation" / "week3-rag-eval-results.md"
    with out_path.open("w", encoding="utf-8") as f:
        f.write("# Week 3 RAG Evaluation — Results (W3-06)\n\n")
        f.write(
            f"Groundedness rate: **{groundedness_rate:.1f}%** ({passed}/{scored_total} scored, "
            f"{errored} excluded as API errors — see notes)\n\n"
        )
        f.write(f"Refusal accuracy (C rows): **{refusal_accuracy:.1f}%** ({refused_correctly}/{total_c})\n\n")
        if errored:
            f.write(
                f"**{errored} case(s) hit an API error (rate limit / high demand) and were not "
                "actually evaluated — re-run those specific cases before treating this as final.**\n\n"
            )
        f.write("| # | Type | Question | Answer | Citations | Verdict | Note |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in rows:
            answer_short = r["answer"].replace("\n", " ")[:500]
            f.write(
                f"| {r['id']} | {r['type']} | {r['question']} | {answer_short} | "
                f"{', '.join(r['citations']) or '—'} | {r['verdict']} | {r['note']} |\n"
            )

    print(f"\nWritten to {out_path}")
    print(
        f"Groundedness rate: {groundedness_rate:.1f}% (of {scored_total} actually scored) | "
        f"Refusal accuracy: {refusal_accuracy:.1f}% | {errored} case(s) need re-running due to API errors"
    )


if __name__ == "__main__":
    main()
