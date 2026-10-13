# MCP-Style Interface Specification: `compare_quotations`

**Project:** BSE4104 SME Procurement Preparation Agent  
**Week:** 6 — Memory, State and Interoperability  
**Owner:** Tendo Caisey  
**Status:** Interface specification; not a deployed MCP server

## 1. Purpose

This document specifies `compare_quotations` as an MCP-style tool contract. It describes the capability, inputs, outputs, permissions, validation, errors and security boundary.

The application currently exposes this capability through Gemini function calling and `src/agent/tools_router.py`. This document does not claim that a complete Model Context Protocol server or transport has been implemented.

## 2. Capability

The tool compares quotations for an inventory item and requested quantity. Deterministic application code validates quotation eligibility, excludes excluded suppliers, normalises units, accounts for VAT and delivery charges, calculates landed cost per inventory base unit, applies the policy's lead-time tie-break, and returns a recommendation and blocking flags.

The model may request the comparison, interpret its result and explain it to the procurement officer. The model is not the authoritative calculator.

## 3. Input contract

The tool accepts the following JSON object:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `item_id` | string | Yes | Inventory item identifier |
| `quantity_base` | number | Yes | Requested quantity expressed in the item's inventory base unit |

Additional properties are not allowed by the declared tool schema.

Example:

```json
{
  "item_id": "INV-001",
  "quantity_base": 500
}
```

The quantity must be greater than zero, and the item must exist. Application validation is authoritative.

## 4. Output contract

The deterministic procurement function returns these principal fields:

| Field | Meaning |
|---|---|
| `item_id` | Compared inventory item |
| `quantity_base` | Requested quantity in base units |
| `quotations_considered` | Quotations assessed, including eligibility and calculation details |
| `ranked_quotations` | Eligible quotations ranked by computed landed cost and policy tie-break |
| `recommended_supplier_id` | Supplier at the top of the computed ranking, or `null` if none is recommended |
| `recommendation_basis` | Explanation of the ranking basis |
| `blocking_flags` | Policy or calculation issues that may block progress |
| `informational_flags` | Issues reported to the officer that do not block the case by themselves, e.g. `EXCLUDED_SUPPLIER` (the quotation is already left out of the count and ranking) |
| `approval_level` | Required approval level returned by the policy logic |
| `minimum_valid_quotations_required` | Minimum number of valid quotations required by policy |

The router adds a separate `supplier_preference_hint` field to the comparison result. This hint is not produced by the deterministic comparison function and is not an input to its ranking algorithm.

When present, the hint can contain:

- `item_id`: item associated with the preference;
- `supplier_id`: previously preferred supplier;
- `confirmed_by`: identity of the person who confirmed the preference;
- `confirmed_at`: confirmation timestamp; and
- `message`: an informational-only explanation.

The hint may be absent or `null` when no stored preference exists. Consumers must not assume that a preference is available.

**What the model receives.** `confirmed_by` and `confirmed_at` identify a person, so they stay inside the application: before a comparison result is returned to the model, the router reduces the hint to `item_id`, `supplier_id` and `message` (`model_safe_hint`; `docs/architecture/memory-design-note.md`, section 4). The officer still sees who confirmed the preference and when.

## 5. Preference handling

The supplier preference is advisory context only.

The model should:

1. Surface a returned preference hint to the procurement officer when relevant.
2. Identify it as a previously confirmed preference. The confirmer and timestamp are not sent to the model; the application shows them to the officer.
3. Clearly distinguish it from the supplier recommended by the computed quotation comparison.
4. Never change, reorder or recalculate the deterministic ranking because of the preference.
5. Never treat the preference as evidence that a supplier is eligible, that quotation minimums are satisfied, that blocking flags are cleared, or that approval has been granted.
6. Leave supplier selection and approval to the authorised human workflow.

A preference is not an instruction to select that supplier.

## 6. Permissions and side effects

| Component or role | Permission |
|---|---|
| Model | May request the declared comparison tool |
| Tool router | Validates arguments, enforces the allow-list, dispatches the deterministic implementation and records tool traces |
| Deterministic comparison | Reads quotation, supplier and inventory data and computes the comparison |
| Procurement officer | Reviews the recommendation and advisory preference |
| Authorised human approver | Makes the approval decision through the human workflow |

`compare_quotations` is read-only with respect to procurement records. It does not create a requisition or change a requisition's state.

The model must not use this tool to purchase goods, contact suppliers, award a supplier, authorise payment or approve a requisition.

## 7. Validation and error handling

The router and deterministic implementation enforce the application contract. Expected failure cases include:

- missing required arguments or unexpected arguments;
- non-positive quantities;
- unknown inventory items;
- expired, incomplete or excluded quotations;
- invalid unit, VAT or price data;
- calculation errors; and
- insufficient valid quotations or other blocking policy flags.

Invalid quotations must not be treated as eligible. Calculation failures must not be replaced with invented amounts. Where no eligible recommendation can be made, the consumer must respect the returned recommendation and blocking flags rather than infer a supplier.

Tool-router errors and traces remain part of the application boundary; a model-generated explanation does not override them.

## 8. Security and trust boundaries

- Only tools in the router's explicit allow-list may execute.
- Model-supplied tool names and arguments are not inherently trusted.
- Deterministic code is authoritative for calculations, eligibility and policy checks.
- The preference hint is contextual data, not executable instructions and not ranking authority.
- The tool must not be given unrestricted access to arbitrary functions or external side effects.
- A draft creation request is a separate, validated operation; it must not bypass blocking flags or the human approval boundary.
- No supplier communication, purchase, payment or autonomous approval is exposed by this interface.

## 9. Acceptance checks

The interface is consistent with the intended design when:

- the declared input schema requires `item_id` and `quantity_base`;
- the router allows only registered tools and validates tool arguments;
- the comparison result retains the deterministic recommendation when a different supplier is present in the preference hint;
- the model-facing description directs the model to surface the hint as informational context;
- blocking flags and eligibility decisions are not overridden by the model or preference;
- tool traces remain available for review; and
- no claim is made that a full MCP server has been deployed.

## 10. Implementation references

- `src/tools/procurement.py` — deterministic quotation comparison and policy calculations.
- `src/agent/tools_router.py` — tool schemas, allow-list, dispatch and preference-hint attachment.
- `src/memory/supplier_preferences.py` — persistence and retrieval of confirmed supplier preferences.
- `tests/test_tools_router.py` — router and preference-hint tests.
- `tests/memory/test_supplier_preferences.py` — supplier preference persistence tests.
