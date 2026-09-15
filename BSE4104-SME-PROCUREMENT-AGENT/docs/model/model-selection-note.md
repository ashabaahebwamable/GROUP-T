# Model Selection Note — ProcurePrep Agent

**Role:** Tendo Caisey — AI Engineering Lead  
**Week:** 2 — Foundation-Model Engineering & Prompting  
**Date:** 13 September 2026  
**Selected model:** Google Gemini 3.6 Flash (`gemini-3.6-flash`)

## 1. Decision

The ProcurePrep Agent will use **Google Gemini 3.6 Flash** as its foundation model for the Week 2 baseline and, unless evaluation shows a clear reason to change, as the main model for the capstone.

The choice is driven by four requirements: zero project budget, strong general-purpose text reasoning/extraction, sufficiently low latency for an interactive application, and an accessible API that can later support the agent workflow.

## 2. Capability

Gemini 3.6 Flash is a hybrid reasoning model with a large context window and support for fast structured-generation workloads. This is more capability than is required for quotation extraction, but it gives the project headroom for later stages involving procurement-policy context, quotation comparison, and bounded multi-step agent execution.

For the Week 2 task, the model will be used for **structured extraction from supplier quotations**. It should identify fields such as supplier, quotation ID, item, quantity, unit price, currency, delivery time, validity period, and missing/uncertain values.

Importantly, deterministic application code will remain responsible for validation and calculations. The model will not be trusted to perform financial arithmetic or approve suppliers.

## 3. Cost

Gemini 3.6 Flash is currently available on the Gemini API **Free Tier / access tier** subject to the applicable availability and rate limits. This makes it suitable for a student project with no budget.

The free tier has an important trade-off: Google states that content submitted under the free/unpaid service may be used to improve its products. Therefore, the project will use **synthetic procurement data only** during free-tier development and evaluation.

## 4. Latency

The Flash model family is intended for fast, interactive workloads. Exact latency will depend on prompt size, network conditions, API load, and output length, so the project will measure actual response latency during evaluation rather than claiming a fixed number.

For quotation extraction, prompts will be kept focused and outputs constrained to a small JSON schema to reduce unnecessary latency and token usage.

## 5. Privacy

This is the main limitation of the free option. The capstone must therefore avoid confidential institutional procurement records, real supplier information, personal information, credentials, or financial secrets.

The approved development dataset will consist of **synthetic supplier quotations and synthetic inventory records**. API keys will be stored in environment variables and never committed to Git.

If the project later requires confidential data, the model/data-processing arrangement must be reassessed rather than simply sending that data through the free tier.

## 6. Access

The model can be accessed through **Google AI Studio / Gemini API** using an API key. The backend will call the model through the Gemini SDK/API. The key will be stored in `.env` and documented through `.env.example`.

## 7. Why this model fits ProcurePrep

| Criterion        | Assessment                                                                     |
| ---------------- | ------------------------------------------------------------------------------ |
| Capability       | Strong enough for structured quotation extraction and later agent reasoning    |
| Cost             | **Pass** — available on Free Tier                                              |
| Latency          | **Pass** — Flash family is designed for fast workloads; measure actual latency |
| Privacy          | **Conditional pass** — synthetic/non-confidential data only on free tier       |
| Access           | **Pass** — API/AI Studio access                                                |
| Future agent use | **Pass** — suitable foundation for later context, tools and bounded workflow   |

## 8. Final decision

**Selected:** `gemini-3.6-flash`

The decision will be revisited if Week 2 prompt evaluation shows inadequate extraction accuracy, unacceptable latency, or a free-tier limitation that prevents reliable testing.

**Source:** Google Gemini API pricing and billing documentation, checked 13 September 2026.
