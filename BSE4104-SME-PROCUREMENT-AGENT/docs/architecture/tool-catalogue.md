# Tool Catalogue and Schemas

**Project:** BSE4104 SME Procurement Preparation Agent
**Week:** 4 — Tools and Function Calling
**Task:** W4-01 Tool Catalogue and Schemas
**Owners:** Mable + Tendo
**Status:** Contract for W4-02 implementation and W4-03 orchestration. Schemas checked against `src/tools/procurement.py` and `src/agent/tools_router.py` on 27 Sep 2026; any gap between contract and code is marked **Implementation status**.

## 1. Purpose

This catalogue defines the approved tools available to the procurement-preparation agent. It sets an explicit contract for each tool:

- purpose;
- input parameters;
- output structure;
- who may call it;
- side effects;
- validation requirements; and
- failure behaviour.

The model may *request* an approved tool, but deterministic application code remains responsible for validation, calculations, state changes and enforcement of business rules.

The tool router must allow only tools defined in this catalogue.

## 2. Approved tools

| # | Tool | Role | Side effect |
|---|---|---|---|
| 1 | `check_reorder_levels` | **Current application data tool.** Reads live stock levels from the inventory register | None (read-only) |
| 2 | `lookup_policy` | Policy retrieval from the controlled corpus | None (read-only) |
| 3 | `compare_quotations` | Deterministic landed-cost comparison | None (read-only, computes) |
| 4 | `create_requisition_draft` | **Simulated side effect tool.** Creates a `DRAFT` requisition and audit entry | Simulated (writes a draft record only) |

No tool in this catalogue may approve a requisition, make a purchase, award a supplier, make a payment or create an autonomous financial commitment.

### Who may call a tool

| Caller | May do |
|---|---|
| **Model** (Gemini, via function calling) | *Request* any tool in this catalogue. It never executes a tool itself. |
| **Tool router** (`src/agent/tools_router.py`) | The only component that executes tools. It checks the allow-list and arguments before dispatch and records a trace for every call. |
| **Procurement officer** (human) | Is the `preparing_officer_id` on every draft, and remains accountable for it. |
| **Approver** (operations manager or director, policy §5) | Only a human approver can move a requisition beyond `DRAFT`. No tool can do this. |

---

## 3. Tool: `check_reorder_levels` (current application data tool)

### Purpose

Determine whether inventory items require replenishment by comparing current stock with the configured reorder level. This is the tool that reads **current application data**: the live stock figures in `knowledge/records/inventory.csv`.

### Who may call it

The model may request it through the tool router, with no human approval needed, because it is read-only.

### Side effect

None. Read-only access to application data.

### Input schema

```json
{
  "type": "object",
  "properties": {
    "item_id": {
      "type": "string",
      "description": "Inventory item identifier, for example INV-001. Omit to check every item."
    }
  },
  "additionalProperties": false
}
```

### Output schema

```json
{
  "type": "object",
  "properties": {
    "items_to_reorder": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "item_id": {"type": "string"},
          "item_name": {"type": "string"},
          "current_stock_base": {"type": "number"},
          "reorder_level_base": {"type": "number"},
          "target_stock_base": {"type": "number"},
          "suggested_reorder_quantity_base": {"type": ["number", "null"]}
        },
        "required": ["item_id", "current_stock_base", "reorder_level_base"]
      }
    },
    "unassessable_items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "item_id": {"type": "string"},
          "item_name": {"type": "string"},
          "reason": {"type": "string"}
        },
        "required": ["item_id", "reason"]
      }
    },
    "not_found": {
      "type": "string",
      "description": "Present only when the requested item_id does not exist."
    }
  },
  "required": ["items_to_reorder", "unassessable_items"]
}
```

### Business behaviour

The implementation compares current stock with the configured reorder level and returns the items that need replenishment, with a suggested quantity to bring stock up to target.

If stock or reorder data is missing or invalid, the item is listed under `unassessable_items` with a reason, rather than given an invented yes/no answer.

**Implementation status:** An item is reported only when stock is *below* the reorder level (`stock < reorder_level`). The original contract said an item *at* the reorder level must also be reordered. The team needs to decide which rule is correct and align code and contract. The input schema was made optional to match the code, which checks every item when `item_id` is omitted.

### Failure behaviour

- Empty `item_id`: reject the request (`ValueError`, returned by the router as `TOOL_ARGUMENT_ERROR`).
- Unknown `item_id`: return empty lists with `not_found` set.
- Missing stock or reorder data: list the item under `unassessable_items`.
- Negative or non-numeric inventory values: list the item under `unassessable_items`.
- No inventory mutation is permitted.

---

## 4. Tool: `lookup_policy`

### Purpose

Retrieve the relevant procurement-policy rule or section for a specified topic.

### Who may call it

The model may request it through the tool router, with no human approval needed, because it is read-only.

### Side effect

None. Read-only access to policy.

### Input schema (contract)

```json
{
  "type": "object",
  "properties": {
    "topic": {
      "type": "string",
      "description": "Procurement policy topic to retrieve."
    }
  },
  "required": ["topic"],
  "additionalProperties": false
}
```

### Output schema (contract)

```json
{
  "type": "object",
  "properties": {
    "topic": {"type": "string"},
    "policy_section": {"type": "string"},
    "rule": {"type": "string"},
    "source": {"type": "string"}
  },
  "required": ["topic", "policy_section", "rule", "source"],
  "additionalProperties": false
}
```

### Business behaviour

The implementation must return policy information from the controlled procurement corpus. Example topics:

- quotation requirements;
- quotation validity;
- excluded suppliers;
- landed-cost comparison;
- approval thresholds;
- requisition requirements.

The tool must not invent a policy rule when the controlled corpus does not contain enough evidence.

**Implementation status: does not meet the contract.** The router maps `lookup_policy` to `policy_check()`, which takes `case_value_ugx` (not `topic`) and returns quotation-count and approval-level flags (not a policy rule and its source). The router always passes empty quotation and supplier lists, so every call reports `MINIMUM_VALID_QUOTATIONS_NOT_MET ... found=0`. A request with `topic` fails with `TOOL_ARGUMENT_ERROR`. Candidate fix: implement `lookup_policy(topic)` on top of the Week 3 retriever (`src/rag/retrieve.py`), returning the policy section, the rule text and the source path, and keep `policy_check` as an internal helper of `compare_quotations`.

### Failure behaviour

- Missing `topic`: reject the request.
- Empty or unsupported topic: return a structured no-match result.
- Missing policy evidence: return a controlled no-evidence result (the Week 3 refusal, `cannot answer from available documents`).
- The tool must not fabricate policy content.

---

## 5. Tool: `compare_quotations`

### Purpose

Deterministically compare supplier quotations for an inventory item, using the policy's quotation-validity, supplier-exclusion and landed-cost rules (policy §2–§4).

### Who may call it

The model may request it through the tool router, with no human approval needed, because it only reads and computes. Its result is a *recommendation*. Confirming the supplier remains a human decision.

### Side effect

None. Read-only access to quotation and supplier data.

### Input schema

```json
{
  "type": "object",
  "properties": {
    "item_id": {
      "type": "string",
      "description": "Inventory item being procured."
    },
    "quantity_base": {
      "type": "number",
      "description": "Required quantity in the item's inventory base unit."
    }
  },
  "required": ["item_id", "quantity_base"],
  "additionalProperties": false
}
```

### Output schema

```json
{
  "type": "object",
  "properties": {
    "item_id": {"type": "string"},
    "quantity_base": {"type": "number"},
    "quotations_considered": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "quotation_id": {"type": "string"},
          "supplier_id": {"type": "string"},
          "supplier_name": {"type": ["string", "null"]},
          "valid": {"type": "boolean"},
          "excluded": {"type": "boolean"},
          "complete": {"type": "boolean"},
          "eligible": {"type": "boolean"},
          "landed_cost_total": {"type": "number"},
          "landed_cost_per_base_unit": {"type": "number"},
          "delivery_days": {"type": ["integer", "null"]},
          "calculation_error": {"type": "string"}
        },
        "required": ["quotation_id", "supplier_id", "valid", "excluded", "complete", "eligible"]
      }
    },
    "ranked_quotations": {
      "type": "array",
      "description": "Eligible quotations sorted by landed cost per base unit, then delivery days."
    },
    "recommended_supplier_id": {"type": ["string", "null"]},
    "recommendation_basis": {"type": "string"},
    "blocking_flags": {"type": "array", "items": {"type": "string"}},
    "approval_level": {"type": "string", "enum": ["operations_manager", "director"]},
    "minimum_valid_quotations_required": {"type": "integer"}
  },
  "required": [
    "item_id",
    "quantity_base",
    "quotations_considered",
    "ranked_quotations",
    "recommended_supplier_id",
    "recommendation_basis",
    "blocking_flags",
    "approval_level",
    "minimum_valid_quotations_required"
  ]
}
```

### Business behaviour

All monetary and unit calculations are performed by deterministic application code. The implementation:

1. identifies quotations for the requested item;
2. validates quotation completeness;
3. checks quotation validity against the quotation date and validity period;
4. excludes suppliers marked `excluded` (policy §4.1);
5. accounts for VAT treatment;
6. accounts for delivery and off-loading charges;
7. normalises quotation units to the inventory base unit (policy §3.2);
8. calculates landed cost per base unit (policy §3.1);
9. ranks by landed cost, breaking ties on delivery days;
10. adds blocking flags (e.g. `MINIMUM_VALID_QUOTATIONS_NOT_MET`, `EXCLUDED_SUPPLIER`, `EXPIRED_OR_INVALID_QUOTATION`); and
11. returns the required approval level (policy §5).

The model must not be treated as the authoritative calculator for procurement figures.

**Configuration note:** VAT on exclusive quotations is applied at `VAT_RATE = 0.18` in `src/tools/procurement.py`. The procurement policy itself does not state a VAT rate, so this is a code configuration value and must be kept in sync with the tax rate in force.

**Implementation status:** The tie-break sorts by delivery days whenever landed cost is exactly equal. Policy §3.4 prefers the shorter lead time whenever two quotations are *within 2%* of each other. This is not yet implemented.

### Failure behaviour

- Missing `item_id` or `quantity_base`: reject the request.
- Non-positive quantity: reject the request.
- Unknown item: reject the request.
- No quotations found: return an empty comparison, no recommendation, and a `MINIMUM_VALID_QUOTATIONS_NOT_MET` flag.
- No valid eligible quotations: return no recommendation and a blocking flag.
- Expired quotation: mark it invalid and exclude it from the recommendation.
- Excluded supplier: mark it excluded, do not recommend it, and do not count it toward the quotation minimum.
- Missing quotation unit or other required data: mark the quotation incomplete.
- Calculation failure: mark that quotation ineligible with `calculation_error`, and add a `CALCULATION_ERROR` flag. Never invent a figure.

---

## 6. Tool: `create_requisition_draft` (simulated side effect tool)

### Purpose

Create a procurement requisition in `DRAFT` state from validated procurement information.

### Who may call it

The model may request it through the tool router, but only after `compare_quotations` has produced a recommendation. The draft is recorded against the human `preparing_officer_id`, who remains accountable. The model and the router can never move the draft past `DRAFT`.

### Side effect

**Simulated side effect.** The tool appends a `DRAFT` row to the requisitions register and an entry to the audit log (`evidence/traces/audit-log.jsonl`). Nothing is sent to a supplier, and no order, payment or approval happens.

### Approval boundary

This tool may create only a `DRAFT`. It must not:

- approve the requisition;
- move a requisition directly to `APPROVED`;
- award a supplier;
- make a purchase;
- authorise payment; or
- create an autonomous financial commitment.

Any later approval must pass through the human approval workflow (W4-05).

### Input schema

```json
{
  "type": "object",
  "properties": {
    "item_id": {
      "type": "string",
      "description": "Inventory item identifier."
    },
    "quantity_base": {
      "type": "number",
      "description": "Required quantity in the item's base unit."
    },
    "recommended_supplier_id": {
      "type": "string",
      "description": "Supplier selected by the deterministic quotation comparison."
    },
    "comparison_reference": {
      "type": "string",
      "description": "Reference to the quotation comparison evidence."
    },
    "preparing_officer_id": {
      "type": "string",
      "description": "Identifier of the officer preparing the requisition."
    }
  },
  "required": [
    "item_id",
    "quantity_base",
    "recommended_supplier_id",
    "comparison_reference",
    "preparing_officer_id"
  ],
  "additionalProperties": false
}
```

### Output schema

```json
{
  "type": "object",
  "properties": {
    "requisition_id": {"type": "string", "description": "System-assigned, e.g. REQ-2026-0002."},
    "state": {"type": "string", "enum": ["DRAFT"]},
    "item_id": {"type": "string"},
    "quantity_base": {"type": "number"},
    "recommended_supplier_id": {"type": "string"},
    "audit_log_reference": {"type": "string"}
  },
  "required": [
    "requisition_id",
    "state",
    "item_id",
    "quantity_base",
    "recommended_supplier_id",
    "audit_log_reference"
  ],
  "additionalProperties": false
}
```

### Business behaviour

The implementation assigns a requisition number, stores the validated information with state `DRAFT`, and records an audit-log entry. It must not bypass the approval state machine.

**Implementation status:**
1. **Blocking flags are not enforced through the router.** The tool refuses to create a draft when `policy_flags` are passed, but the router schema does not expose `policy_flags`, so the model never sends them. A draft can therefore be created even when `compare_quotations` returned blocking flags (e.g. too few valid quotations). Candidate fix: the router should look up the referenced comparison's `blocking_flags` itself and pass them in, rather than relying on the model.
2. **Drafts are written into the knowledge corpus.** The default `requisitions_path` is `knowledge/records/requisitions.csv`, which the Week 3 retriever loads as evidence. Simulated drafts would then appear in policy answers. Candidate fix: write drafts to a separate application-state file (e.g. `data/requisitions.csv`) or to `evidence/`.

### Failure behaviour

- Missing required parameter: reject without creating a requisition.
- Non-positive quantity: reject without creating a requisition.
- Blocking policy flags supplied: reject without creating a requisition.
- Unknown inventory item: reject without creating a requisition.
- Unknown or excluded supplier: reject without creating a requisition.
- Requisitions file without a CSV header: reject with a controlled error.
- No path may move the requisition directly to `APPROVED`.

---

## 7. Permission and side-effect matrix

| Tool | Data role | Read/Write | Side effect | Model may request | Human approval |
|---|---|---|---|---|---|
| `check_reorder_levels` | **Current application data** | Read | None | Yes | Not needed |
| `lookup_policy` | Controlled policy corpus | Read | None | Yes | Not needed |
| `compare_quotations` | Quotation and supplier records | Read/compute | None | Yes | Not needed. Supplier confirmation stays human |
| `create_requisition_draft` | Requisition register | Write | **Simulated**: `DRAFT` row + audit entry | Yes, after a comparison | Required for anything beyond `DRAFT` |

## 8. Router requirements

The Week 4 orchestration layer must enforce this catalogue. The router must:

1. maintain an explicit allow-list of approved tools;
2. reject unlisted tool requests;
3. validate required arguments before dispatch;
4. dispatch only to registered deterministic implementations;
5. record each tool request and result in a trace;
6. return structured tool results to the model;
7. prevent tools from exceeding their documented authority; and
8. record model-versus-computed figure mismatches where applicable.

An unrecognised tool request must not be executed dynamically. For example, the router must not execute an arbitrary function just because the model supplied its name.

## 9. Division of responsibility

| Task | Owner | Responsibility |
|---|---|---|
| W4-01 | Mable + Tendo | Define and review the tool contracts in this document |
| W4-02 | Azibo | Implement the deterministic tools under `src/tools/` according to these contracts |
| W4-03 | Tendo | Implement the function-calling orchestration layer in `src/agent/tools_router.py`: registration, allow-list enforcement, dispatch, tracing and mismatch handling |
| W4-04 | Ashley | Test failure and authorisation behaviour |
| W4-05 | Azibo + Ashley | Implement and test the human approval / state-machine boundary |

## 10. Design principle

The system follows a controlled hybrid architecture:

```text
Foundation model
      |
      | requests an approved tool
      v
Tool router
      |
      | validates + allow-lists + dispatches
      v
Deterministic application tool
      |
      | computed/validated result
      v
Tool router
      |
      v
Foundation model
```

The foundation model is not granted unrestricted access to application functionality. Deterministic code remains authoritative for procurement calculations, validation, state changes and other high-impact operations. Human approval remains the boundary for approving procurement actions.
