# Week 2 Progress Report — Foundation Model Engineering and Prompting

## Objective

The Week 2 task focused on delivering the smallest useful model-backed capability: a quotation-extraction baseline that can convert supplier quotation text into a structured JSON object without turning the system into an autonomous purchasing agent. This work established the first evidence-backed model interaction pattern for the ProcurePrep workflow, before later stages add retrieval, tools, and agency.

## Model selection

The repository adopts Google Gemini 2.5 Flash as the baseline model for this phase. This choice balances affordability, prompt responsiveness, and the ability to handle short structured extraction tasks without a paid subscription. The project later uses the model only with synthetic procurement data, because the free-tier arrangement carries privacy constraints and synthetic-only rules are necessary for the capstone environment.

The model selection note documents the capability, cost, latency, access and privacy considerations. These constraints are not abstract concerns; they directly shape the bounded use of the model. The model is used for evidence extraction, not supplier selection or purchase decision-making.

## Baseline implementation

The week-2 baseline was implemented in the source layer as a deterministic extraction workflow wrapped by a Gemini API client. The main extraction logic is in `src/quotation_extractor.py`, and the application-level model call is in `src/model_client.py`.

The extractor is intentionally narrow. It accepts raw quotation text, preserves fields explicitly stated in the text, and flags gaps or ambiguity instead of inventing values. This is consistent with the project principle that no model-produced figure is trusted without deterministic validation.

The model client adds the actual integration path: when a valid `MODEL_API_KEY` is present, a prompt is sent to the Gemini endpoint, the JSON response is parsed, and the result is validated. This is the minimum working interaction path for the project baseline.

## Prompt evolution

Three prompt versions are now recorded in the prompt folder:

- `v1.0`: baseline extraction task with explicit constraints and failure handling.
- `v1.1`: evidence-first revision that emphasized explicit trust boundaries and JSON output contract.
- `v1.2`: final tightened schema with explicit rules for missing information, conflicting prices, non-quotation input and instruction contamination.

The prompt history demonstrates iterative improvement rather than a single take. Each version tightened the specification around uncertainty handling and output safety, which is critical in a procurement domain where a model must not silently guess or make a decision.

## Evaluation approach

A 10-case evaluation matrix was created and recorded in `docs/evaluation/week2-prompt-test-cases.md`. The cases cover:

- complete valid quotations;
- missing currency and missing item prices;
- ambiguous delivery terms;
- prompt injection inside quotation text;
- multiple items;
- empty input;
- non-quotation text;
- conflicting price values; and
- missing currency.

This coverage is intentionally designed to test failure modes that are common in real quotation handling. The evaluation checks whether the model or extractor states facts only when they are present, preserves values literally, and explains uncertainty without hallucinating.

## Verification evidence

The repository now includes automated baseline verification in `tests/test_week2_baseline.py` and `tests/test_model_client.py`. The verification command was run successfully:

`python -m unittest tests.test_week2_baseline -v`

Result: 2 tests ran and both passed.

That gives the team a working baseline for the next stage: Week 3 context engineering and retrieval. The extracted quotation capability is now testable, the model integration path is in place, and the prompt contract has been versioned and evaluated.

## Conclusion

Week 2 delivered the required foundation-model engineering baseline: model selection, model integration, prompt versioning, and a tested prompt matrix. The repository is now ready to proceed into context engineering and retrieval without changing the safety boundary that keeps the model in a bounded, evidence-first extraction role.
