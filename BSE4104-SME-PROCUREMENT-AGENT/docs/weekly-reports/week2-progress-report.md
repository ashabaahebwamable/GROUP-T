# Week 2 Progress Report — Foundation Model Engineering and Prompting

## Objective

The Week 2 task focused on delivering the smallest useful model-backed capability: a quotation-extraction baseline that can convert supplier quotation text into a structured JSON object without turning the system into an autonomous purchasing agent. This work established the first evidence-backed model interaction pattern for the ProcurePrep workflow, before later stages add retrieval, tools, and agency.

## Model selection

The repository adopts Google Gemini 3.6 Flash as the baseline model for this phase. This choice balances affordability, prompt responsiveness, and the ability to handle short structured extraction tasks without a paid subscription. The project later uses the model only with synthetic procurement data, because the free-tier arrangement carries privacy constraints and synthetic-only rules are necessary for the capstone environment.

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

The repository includes both a deterministic extractor baseline and a live Gemini validation path. The live path was successfully exercised with a valid API key using the supported model name `gemini-3.6-flash`.

The real model-run output was saved to:

`evidence/live-evaluation/gemini-week2-live-results.json`

The live run covered the same 10-case quotation matrix and produced actual model outputs, including uncertainty notes for ambiguous delivery, unsupported values, prompt-injection content, and conflicting totals.

The repository also includes a parser-only unit test suite:

`python -m unittest discover -s tests -v`

Result: 4 tests ran and all passed.

This confirms two things: the deterministic code still behaves as expected, and the live Gemini interaction also works when the API is configured and the supported model name is used.

## Conclusion

Week 2 delivered the required foundation-model engineering baseline: model selection, prompt versioning, real model interaction, and live evaluation evidence. The project now has a working model-backed quotation-extraction path using Gemini 3.6 Flash, with detailed output captured for the same 10-case evaluation matrix.
