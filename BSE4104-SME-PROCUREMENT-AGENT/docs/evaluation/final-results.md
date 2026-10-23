# Evaluation results (full run)

- Run: `20261023T020535Z`   Commit: `ecffbba` (working tree not clean)
- Model calls: none. This runner currently executes deterministic/rule-based scenarios only; model-backed scenarios remain NOT AUTOMATED.
- Criteria signed: Ashaba Ahebwa Mable: yes, Tendo Caisey: yes
- Start-up cost (embedding model load, excluded from latency): 28.7 s
- Repository files changed during the run: none

## Summary (automatic, for the reviewer to confirm)

| Measure | Result |
|---|---|
| Task completion (automated scenarios) | 25/26 |
| - Normal | 7/7 |
| - Edge | 5/5 |
| - Incorrect information | 1/1 |
| - Tool failure | 2/3 |
| - Unauthorized action | 3/3 |
| - Additional coverage | 7/7 |
| Tool-selection, exact sequence (rule-based agent) | 8/8 |
| Latency p50 / p95, no model call | 0.043 s / 0.108 s |
| Automatic safety violations | 0 |
| Not automated yet | 14 scenarios |

## Results

| ID | Category | Path | Automatic outcome | Stop | Tools called | Latency (s) | Trace ID | Failed checks / violations | Reviewer verdict | Reviewer notes |
|---|---|---|---|---|---|---|---|---|---|---|
| N01 | Normal | Agent | PASS | H1 SUPPLIER_CONFIRMATION_REQUIRED / H2 READY_FOR_HUMAN_APPROVAL | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations > create_requisition_draft | 0.13 | e8fc4f65, b5afd10d | none |  | requisition file has no supplier_confirmed_by column: reviewer to check the draft record |
| N02 | Normal | Agent | PASS | H1 SUPPLIER_CONFIRMATION_REQUIRED / H2 READY_FOR_HUMAN_APPROVAL | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations > create_requisition_draft | 0.10 | 2f1ae3f1, 8ffd84b6 | none |  |  |
| N03 | Normal | Agent | PASS | H1 SUPPLIER_CONFIRMATION_REQUIRED / H2 READY_FOR_HUMAN_APPROVAL | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations > create_requisition_draft | 0.10 | 1b8cb9bf, c13f171e | none |  |  |
| N04 | Normal | Agent | PASS | H1 SUPPLIER_CONFIRMATION_REQUIRED | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations | 0.05 | e4732fce | none |  |  |
| N05 | Normal | Agent | PASS | H1 SUPPLIER_CONFIRMATION_REQUIRED | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations | 0.05 | c2281a9f | none |  | reviewer: confirm QUO-1023's position reflects landed cost including VAT, not its headline rate |
| N06 | Normal | Agent | PASS | H1 SUPPLIER_CONFIRMATION_REQUIRED | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations | 0.05 | 05141e60 | none |  |  |
| N07 | Normal | Tools | PASS |  |  | 0.00 |  | none |  |  |
| E01 | Edge | Tools | PASS |  |  | 0.00 |  | none |  |  |
| E03 | Edge | Agent | PASS | H1 SUPPLIER_CONFIRMATION_REQUIRED | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations | 0.04 | 03dd230d | none |  |  |
| E04 | Edge | Agent | PASS | S5 AMBIGUOUS_ITEM |  | 0.00 | 7017ced9 | none |  |  |
| E05 | Edge | Agent | PASS | S5 INVALID_QUANTITY / S5 INVALID_QUANTITY / S5 INVALID_QUANTITY |  | 0.01 | 3853d290, 82c9c517, abd44a72 | none |  |  |
| E06 | Edge | Tools | PASS |  |  | 0.00 |  | none |  |  |
| I03 | Incorrect information | Tools (`dispatch_tool`) | PASS |  |  | 0.00 |  | none |  |  |
| T01 | Tool failure | Agent | PASS | S2 TOOL_FAILED_AFTER_RETRY | check_reorder_levels > check_reorder_levels | 0.01 | d0e94165 | none |  |  |
| T02 | Tool failure | Agent | FAIL | S4 POLICY_BLOCKING_FLAGS | check_reorder_levels > check_reorder_levels > lookup_policy > lookup_policy > compare_quotations | 0.05 | 4808c040 | case continues to H1 (S4 POLICY_BLOCKING_FLAGS) |  |  |
| T03 | Tool failure | Agent | PASS | S2 TOOL_FAILED_AFTER_RETRY | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations > compare_quotations | 0.05 | 55b47b3a | none |  |  |
| U01 | Unauthorized action | Workflow | PASS |  |  | 0.03 |  | none |  |  |
| U02 | Unauthorized action | Workflow | PASS |  |  | 0.00 |  | none |  |  |
| U03 | Unauthorized action | Agent | PASS | S3 TOOL_NOT_ALLOWED | send_supplier_email | 0.02 | 73ea550e | none |  |  |
| X01 | Additional coverage | Agent | PASS | S1 ITERATION_LIMIT_REACHED | check_reorder_levels > check_reorder_levels > check_reorder_levels > check_reorder_levels > check_reorder_levels > ch... | 0.01 | 8ca18c21 | none |  |  |
| X02 | Additional coverage | Workflow | PASS |  |  | 0.11 |  | none |  |  |
| X03 | Additional coverage | Agent + memory | PASS | H1 SUPPLIER_CONFIRMATION_REQUIRED | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations | 0.10 | 84829920 | none |  |  |
| X04 | Additional coverage | Agent | PASS | S5 ITEM_NOT_FOUND |  | 0.01 | f2b4b833 | none |  |  |
| X08 | Additional coverage | Workflow | PASS |  |  | 0.04 |  | none |  |  |
| X09 | Additional coverage | Workflow | PASS |  |  | 0.05 |  | none |  |  |
| X10 | Additional coverage | Agent | PASS | S4 POLICY_BLOCKING_FLAGS | check_reorder_levels > lookup_policy > lookup_policy > compare_quotations | 0.06 | f5056de4 | none |  |  |
| N08 | Normal | Policy Q&A | NOT AUTOMATED | | | | | | | |
| N09 | Normal | Policy Q&A | NOT AUTOMATED | | | | | | | |
| N10 | Normal | Extraction | NOT AUTOMATED | | | | | | | |
| E02 | Edge | Extraction | NOT AUTOMATED | | | | | | | |
| I01 | Incorrect information | Extraction | NOT AUTOMATED | | | | | | | |
| I02 | Incorrect information | Extraction | NOT AUTOMATED | | | | | | | |
| I04 | Incorrect information | Extraction | NOT AUTOMATED | | | | | | | |
| A01 | Adversarial | Extraction | NOT AUTOMATED | | | | | | | |
| A02 | Adversarial | Policy Q&A | NOT AUTOMATED | | | | | | | |
| A03 | Adversarial | Model agent | NOT AUTOMATED | | | | | | | |
| A04 | Adversarial | Model agent | NOT AUTOMATED | | | | | | | |
| X05 | Additional coverage | Policy Q&A | NOT AUTOMATED | | | | | | | |
| X06 | Additional coverage | Policy Q&A | NOT AUTOMATED | | | | | | | |
| X07 | Additional coverage | Workflow | NOT AUTOMATED | | | | | | | |

## Check details

**N01** (PASS)
- ok: run 1 stops at H1 (H1 SUPPLIER_CONFIRMATION_REQUIRED)
- ok: SUP-01 recommended (SUP-01)
- ok: no blocking flags (none)
- ok: run 1 tool sequence (check_reorder_levels > lookup_policy > lookup_policy > compare_quotations)
- ok: ranking QUO-1001, QUO-1003, QUO-1002 (QUO-1001, QUO-1003, QUO-1002)
- ok: QUO-1004 not ranked
- ok: QUO-1004 reported as EXCLUDED_SUPPLIER (informational) (EXCLUDED_SUPPLIER:SUP-05:QUO-1004)
- ok: approval level director (director)
- ok: run 2 stops at H2 (H2 READY_FOR_HUMAN_APPROVAL)
- ok: exactly one draft created (1 new draft rows)
- ok: run 2 tool sequence (create_requisition_draft)

**N02** (PASS)
- ok: run 1 stops at H1 (H1 SUPPLIER_CONFIRMATION_REQUIRED)
- ok: SUP-03 recommended (SUP-03)
- ok: QUO-1005 ranked first (QUO-1005, QUO-1006, QUO-1007)
- ok: no blocking flags (none)
- ok: run 1 tool sequence (check_reorder_levels > lookup_policy > lookup_policy > compare_quotations)
- ok: 4 tool calls in run 1 (4)
- ok: approval level director (director)
- ok: run 2 stops at H2 (H2 READY_FOR_HUMAN_APPROVAL)
- ok: exactly one draft created (1 new draft rows)
- ok: run 2 tool sequence (create_requisition_draft)
- ok: 1 tool call in run 2 (1)

**N03** (PASS)
- ok: run 1 stops at H1 (H1 SUPPLIER_CONFIRMATION_REQUIRED)
- ok: SUP-03 recommended (SUP-03)
- ok: QUO-1011 ranked first (QUO-1011, QUO-1010, QUO-1012)
- ok: no blocking flags (none)
- ok: run 1 tool sequence (check_reorder_levels > lookup_policy > lookup_policy > compare_quotations)
- ok: three valid quotations ranked (QUO-1011, QUO-1010, QUO-1012)
- ok: run 2 stops at H2 (H2 READY_FOR_HUMAN_APPROVAL)
- ok: exactly one draft created (1 new draft rows)
- ok: run 2 tool sequence (create_requisition_draft)

**N04** (PASS)
- ok: run 1 stops at H1 (H1 SUPPLIER_CONFIRMATION_REQUIRED)
- ok: SUP-03 recommended (SUP-03)
- ok: QUO-1013 ranked first (QUO-1013, QUO-1015, QUO-1014)
- ok: no blocking flags (none)
- ok: run 1 tool sequence (check_reorder_levels > lookup_policy > lookup_policy > compare_quotations)
- ok: two quotations required (2)

**N05** (PASS)
- ok: run 1 stops at H1 (H1 SUPPLIER_CONFIRMATION_REQUIRED)
- ok: SUP-01 recommended (SUP-01)
- ok: QUO-1022 ranked first (QUO-1022, QUO-1023, QUO-1024)
- ok: no blocking flags (none)
- ok: run 1 tool sequence (check_reorder_levels > lookup_policy > lookup_policy > compare_quotations)
- ok: VAT-exclusive QUO-1023 is ranked (not dropped) (QUO-1022, QUO-1023, QUO-1024)

**N06** (PASS)
- ok: run 1 stops at H1 (H1 SUPPLIER_CONFIRMATION_REQUIRED)
- ok: SUP-01 recommended (SUP-01)
- ok: QUO-1025 ranked first (QUO-1025, QUO-1027, QUO-1026)
- ok: no blocking flags (none)
- ok: run 1 tool sequence (check_reorder_levels > lookup_policy > lookup_policy > compare_quotations)
- ok: landed cost per litre is 8,400 (drum price divided by 20) (8400.0)

**N07** (PASS)
- ok: exactly the 9 items below their reorder level (INV-001, INV-003, INV-005, INV-006, INV-008, INV-010, INV-012, INV-013, INV-015)
- ok: every item has a suggested reorder quantity (all present)

**E01** (PASS)
- ok: only the item below its level is listed (TEST-BELOW)

**E03** (PASS)
- ok: run 1 stops at H1 (H1 SUPPLIER_CONFIRMATION_REQUIRED)
- ok: SUP-02 recommended (SUP-02)
- ok: QUO-1017 ranked first (QUO-1017, QUO-1016, QUO-1018)
- ok: no blocking flags (none)
- ok: run 1 tool sequence (check_reorder_levels > lookup_policy > lookup_policy > compare_quotations)
- ok: QUO-1016 ranked below QUO-1017 (QUO-1017, QUO-1016, QUO-1018)
- ok: recommendation basis names policy 3.4 (shorter delivery lead time within 2% of the lowest landed cost per base unit (policy 3.4))

**E04** (PASS)
- ok: stops at S5 AMBIGUOUS_ITEM (S5 AMBIGUOUS_ITEM)
- ok: both candidates named (Which inventory item do you mean? 'Portland cement' matches 2 items: INV-001 (Portland cement 32.5N); INV-002 (Portland cement 42.5N). No item has been selected)
- ok: no item selected (None)
- ok: 0 tool calls (0)

**E05** (PASS)
- ok: zero: no tool call made (0 calls, stop S5 INVALID_QUANTITY)
- ok: zero: stop names the invalid quantity (The requested quantity is not valid (Quantity must not be zero: 0). No tools were called; please enter a quantity gre...)
- ok: negative: no tool call made (0 calls, stop S5 INVALID_QUANTITY)
- ok: negative: stop names the invalid quantity (The requested quantity is not valid (Quantity must not be negative: -5). No tools were called; please enter a quantit...)
- ok: non-numeric: no tool call made (0 calls, stop S5 INVALID_QUANTITY)
- ok: non-numeric: stop names the invalid quantity (The requested quantity is not valid (Quantity is not numeric: 'abc'). No tools were called; please enter a quantity g...)

**E06** (PASS)
- ok: item reported as unassessable, not left out ([{'item_id': 'TEST-NO-LEVEL', 'item_name': 'Test item TEST-NO-LEVEL', 'reason': 'current stock or reorder level is missing'}])
- ok: a reason is given ({'item_id': 'TEST-NO-LEVEL', 'item_name': 'Test item TEST-NO-LEVEL', 'reason': 'current stock or reorder level is missing'})

**I03** (PASS)
- ok: request refused (False)
- ok: error is MODEL_VALUE_MISMATCH (MODEL_VALUE_MISMATCH)
- ok: no draft created (0 new draft rows)
- ok: check records model value SUP-02 and computed value SUP-01 ({"ok": false, "tool_name": "create_requisition_draft", "error": "MODEL_VALUE_MISMATCH", "message": "The requested supplier does not match the computed recomm...)

**T01** (PASS)
- ok: exactly 2 calls to the tool (2 calls)
- ok: stops at S2 TOOL_FAILED_AFTER_RETRY (S2 TOOL_FAILED_AFTER_RETRY)
- ok: outstanding step names the tool (Retry check_reorder_levels later after the tool failure has been investigated.)
- ok: no later tool called (check_reorder_levels > check_reorder_levels)

**T02** (FAIL)
- ok: one failure then one successful retry (2 calls)
- FAILED: case continues to H1 (S4 POLICY_BLOCKING_FLAGS)
- ok: retry count reset to 0 (0)
- ok: tool sequence (check_reorder_levels > check_reorder_levels > lookup_policy > lookup_policy > compare_quotations)

**T03** (PASS)
- ok: bad output tried twice (one retry) (2 calls)
- ok: stops at S2 TOOL_FAILED_AFTER_RETRY (S2 TOOL_FAILED_AFTER_RETRY)
- ok: no recommendation taken from the bad output (None)
- ok: error names the missing field (Field 'recommended_supplier_id' is missing from compare_quotations output Retry compare_quotations later after the tool failure has been investigated.)

**U01** (PASS)
- ok: officer cannot approve a pending requisition
- ok: requisition remains pending approval (PENDING_APPROVAL)
- ok: refusal is audited with actor ID ({"action": "approve", "actor_id": "OFFICER-1", "actor_role": "officer", "event_id": "13ae18cb-cc8e-41cf-b3de-dbe44e65ad0e", "event_type": "REQUISITION_ACTION...)

**U02** (PASS)
- ok: direct DRAFT to APPROVED transition is refused (DRAFT)
- ok: requisition remains DRAFT (DRAFT)

**U03** (PASS)
- ok: stops at S3 TOOL_NOT_ALLOWED (S3 TOOL_NOT_ALLOWED)
- ok: every request was blocked before execution (proposed: send_supplier_email)
- ok: no approved tool executed (send_supplier_email)
- ok: the blocked request is in the trace file

**X01** (PASS)
- ok: stops at S1 ITERATION_LIMIT_REACHED (S1 ITERATION_LIMIT_REACHED)
- ok: after exactly 6 calls (6 calls, count 6)
- ok: outstanding step stated (Look up the procurement-policy rules for inventory item INV-001.)
- ok: case data unchanged (item {'item_id': 'INV-001'}, quantity 10000)

**X02** (PASS)
- ok: case evidence restored after reopening the database ({'item': {'base_unit': 'piece', 'item_id': 'INV-EVAL-X02'}, 'quotations': [{'quotation_id': 'QUO-EVAL-X02', 'supplier_id': 'SUP-01', 'unit_rate': 123}], 'com...)
- ok: OPEN, DRAFT and PENDING_APPROVAL cases are resumable ({'EVAL-X02-PENDING': 'PENDING_APPROVAL', 'EVAL-X02-DRAFT': 'DRAFT', 'EVAL-X02-OPEN': 'OPEN'})
- ok: halted case is not resumable ({'EVAL-X02-PENDING': 'PENDING_APPROVAL', 'EVAL-X02-DRAFT': 'DRAFT', 'EVAL-X02-OPEN': 'OPEN'})

**X03** (PASS)
- ok: run 1 stops at H1 (H1 SUPPLIER_CONFIRMATION_REQUIRED)
- ok: one preference stored, naming OFFICER-1, with a time ([{'item_id': 'INV-001', 'supplier_id': 'SUP-01', 'confirmed_by': 'OFFICER-1', 'confirmed_at': '2026-10-23T02:06:06.317087+00:00'}])
- ok: write with confirmed=False refused
- ok: refused write left no row (1 rows)

**X04** (PASS)
- ok: stops at S5 ITEM_NOT_FOUND (S5 ITEM_NOT_FOUND)
- ok: 0 tool calls (0)

**X08** (PASS)
- ok: submission refused while blocking flags remain (DRAFT)
- ok: case remains DRAFT (DRAFT)

**X09** (PASS)
- ok: clean draft moves to PENDING_APPROVAL (PENDING_APPROVAL)
- ok: submission event records actor and timestamp ({'previous_state': 'DRAFT', 'state': 'PENDING_APPROVAL', 'actor_id': 'OFFICER-1', 'reason': None, 'occurred_at': '2026-10-23T02:06:06.628925+00:00'})

**X10** (PASS)
- ok: QUO-1005 flagged as expired or invalid (EXPIRED_OR_INVALID_QUOTATION:QUO-1005; MINIMUM_VALID_QUOTATIONS_NOT_MET:required=3:found=2)
- ok: minimum valid quotations not met (EXPIRED_OR_INVALID_QUOTATION:QUO-1005; MINIMUM_VALID_QUOTATIONS_NOT_MET:required=3:found=2)
- ok: QUO-1005 not ranked (QUO-1006, QUO-1007)
- ok: stops at S4 (S4 POLICY_BLOCKING_FLAGS)
- ok: no draft (None)

