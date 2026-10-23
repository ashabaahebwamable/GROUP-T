# Week 7 Progress Report — Evaluation, Observability and Guardrails

## Objective

Week 7 set out to show, with evidence, that ReqPrep is reliable, grounded, inspectable and safe: a fixed scenario set judged against thresholds agreed before running, structured traces for every request, guardrails proven in code, and a catalogue of real failures with their fixes.

## What was delivered

| Task | Evidence | Status |
|---|---|---|
| W7-01 Scenario set | `docs/evaluation/final-scenarios.md`: 40 scenarios (10 normal, 6 edge, 4 incorrect information, 4 adversarial, 3 tool failure, 3 unauthorized, 10 for full user-story coverage), each with input, expected outcome, pass criteria and user story; 4 synthetic test letters outside the knowledge corpus | Done |
| W7-02 Criteria | `docs/evaluation/criteria.md`: task completion, groundedness, tool-selection accuracy, instruction following, latency, safety violations (target 0); signed by Mable (19 Oct) and Tendo (21 Oct) **before** the first run | Done |
| W7-03 Runner and results | `scripts/eval_runner.py` (also `python -m src.eval.run`); run `20261023T020535Z` in `evidence/eval/`; `docs/evaluation/final-results.md` | **Partly done** (see below) |
| W7-04 Observability | `src/observability/`: one structured record per request (model, prompt version, retrieved chunks, tool calls and results, latency, errors, outcome); `python -m src.observability export <run-id>`; 5 traces in `evidence/traces/week7/` | Done |
| W7-05 Guardrails | `docs/evaluation/guardrails-evidence.md`: 10 guardrails with code references, tests and status | Done, except G10 (prompt injection) awaiting live evidence |
| W7-06 Failure Catalogue | `docs/evaluation/failure-catalogue.md`: 8 genuine failures since Week 3 with symptom, root cause, fix and re-test | Done (5 fixed, 3 open) |
| W7-07 Evidence | `evidence/screenshots/week7/`: evaluation run, trace viewer, CI (including a green run after the FC-02 fix), PR list, ClickUp | Done |

## Evaluation results so far

The runner executed the 26 scenarios that need no model call; the 14 others are not yet automated.

| Measure | Result | Threshold |
|---|---|---|
| Safety violations | **0** | 0 |
| Task completion (automated) | **25 / 26** | ≥ 90% overall |
| — normal / edge / unauthorized / additional | 7/7, 5/5, 3/3, 7/7 | — |
| — tool failure | 2/3 (T02, see below) | — |
| Tool selection, rule-based agent | **8 / 8** exact | 100% |
| Latency p50 / p95, no model call | 0.04 s / 0.11 s | p95 ≤ 5 s |

**T02 is a scenario error, not a system failure.** The scenario did not state a date, so the runner used 1 Sep, when INV-003's quotation QUO-1005 has lapsed. The trace shows the retry worked (failure, successful retry, case continued) and the case then stopped correctly at S4. The scenario should use 27 Aug, as N02 does. Because results have been seen, the correction will be recorded in `criteria.md` section 7 before T02 is re-run.

**Not yet evaluated.** The 13 Gemini-backed scenarios (policy Q&A, extraction, model agent), including **all four adversarial scenarios A01–A04**, and X07. The criteria require 100% in the adversarial category and full groundedness, so **the evaluation cannot be declared passed yet**. The automatic outcomes also still need the reviewer's verdict in `final-results.md`, which the criteria make the deciding judgement.

## Failures found and fixed this week

| # | Failure | Fix |
|---|---|---|
| FC-01 | A zero, negative or non-numeric quantity ran five tool calls before stopping (US-02 AC3, scenario E05) | `src/validation.py` rejects it before any tool runs (`INVALID_QUANTITY`, S5), on new and resumed cases; PR #16; E05 now passes |
| FC-02 | The evaluation runner, inside `src/`, confirmed suppliers on the officer's behalf and broke the guard test | Runner moved to `scripts/`; the guard test is unchanged and passes |
| FC-03 | An evaluation smoke run wrote into the real trace log | Runner traces isolated in a temporary folder; PR #17 |

Still open from Week 3: citations name the file, not the clause (FC-04); the similarity threshold does not separate answerable from unanswerable questions (FC-05); structured lookups bypass the threshold (FC-06).

## Known gaps

- **Prompt injection (G10)** is mitigated by code — no approval tool, allow-listed tools, H1 confirmation before any draft — but not yet shown to hold at the model. A01 and A02 provide that evidence.
- `item_id` has no format check (unknown codes are caught by lookup only); submit has no role check; a refused approval on the case-store path is not logged; tool argument types are not validated against the schema.

## Testing

`python -m pytest`: **203 tests and 173 subtests pass** (23 Oct), including the new quantity-guardrail and observability tests; CI is green on `main`.

## Contributions (from repository history)

| Member | Week 7 |
|---|---|
| Tendo Caisey | Evaluation runner and its second batch of scenarios; recorded the run; signed the criteria |
| Akisa Maria Ashley | Observability and trace export (W7-04); quantity guardrail (FC-01); moved the runner out of `src/` (FC-02); guardrails evidence (W7-05); Failure Catalogue (W7-06) |
| Azibo Isaac Alinda | Reviewed and merged the quantity-guardrail and evidence pull requests (#16, #19) |
| Wakinya Esau John | Week 7 screenshots, including the evaluation run, trace viewer and green CI (W7-07) |
| Ashaba Ahebwa Mable | Scenario set and test letters (W7-01); criteria and thresholds (W7-02); this report |

## Next steps

1. Correct T02's date (recorded in `criteria.md` §7) and re-run it.
2. Run the 13 Gemini-backed scenarios over two days (about 17 requests; free-tier limit 20 a day), adversarial first, and paste A01/A02 into guardrail G10.
3. Automate or run X07 by hand.
4. Reviewer verdicts for all 40 scenarios in `final-results.md`, then a final pass/fail against the thresholds.
