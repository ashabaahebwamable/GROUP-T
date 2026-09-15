# Handoff to Azibo — Working Quotation Extraction Prompt

**From:** Tendo Caisey, AI Engineering Lead  
**To:** Azibo  
**Task:** Wire the quotation-extraction prompt into the ProcurePrep backend.

Use `prompts/quotation_extraction_v1.1.txt` as the current candidate prompt.

## Integration contract

Input:

- raw quotation text

Model:

- `gemini-3.6-flash`

Expected output:

- JSON object matching the prompt's schema

The backend should:

1. Load the prompt from the versioned prompt file rather than hard-coding it inside application logic.
2. Insert the quotation text into the `<QUOTATION>` section.
3. Call the Gemini API.
4. Parse the returned JSON.
5. Validate the JSON against the expected schema.
6. Reject/flag malformed output rather than silently accepting it.
7. Log prompt version, model name, latency, success/failure, and validation result.
8. Never send confidential or real procurement data while using the free tier.
9. Keep the API key in an environment variable.

Do not allow this extraction step to approve suppliers, create real purchases, or make financial commitments.

The prompt was deliberately designed to treat instructions embedded inside quotation text as untrusted data.
