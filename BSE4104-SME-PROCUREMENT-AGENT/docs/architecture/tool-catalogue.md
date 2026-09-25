\# Tool Catalogue and Schemas



\*\*Project:\*\* BSE4104 SME Procurement Preparation Agent

\*\*Week:\*\* 4 â€” Tools and Function Calling

\*\*Task:\*\* W4-01 Tool Catalogue and Schemas

\*\*Owners:\*\* Mable + Tendo

\*\*Status:\*\* Proposed contract for W4-02 implementation and W4-03 orchestration



\## 1. Purpose



This catalogue defines the approved tools available to the procurement-preparation agent.



The catalogue establishes explicit contracts for:



\- tool purpose;

\- input parameters;

\- output structure;

\- caller permissions;

\- side effects;

\- validation requirements; and

\- failure behavior.



The model may request an approved tool, but deterministic application code remains responsible for validation, calculations, state changes, and enforcement of business rules.



The tool router must allow only tools defined in this catalogue.



\## 2. Approved Tools



The Week 4 tool set contains four tools:



1\. `check\_reorder\_levels`

2\. `lookup\_policy`

3\. `compare\_quotations`

4\. `create\_requisition\_draft`



The first three are read-only tools. `create\_requisition\_draft` is the controlled simulated-side-effect tool.



No tool in this catalogue may approve a requisition, make a purchase, award a supplier, make a payment, or create an autonomous financial commitment.



\---



\## 3. Tool: `check\_reorder\_levels`



\### Purpose



Determine whether an inventory item requires replenishment by comparing current stock with its configured reorder level.



\### Caller



The bounded procurement agent/orchestration layer.



\### Side effect



None. Read-only application-data access.



\### Input schema



```json

{

&#x20; "type": "object",

&#x20; "properties": {

&#x20;   "item\_id": {

&#x20;     "type": "string",

&#x20;     "description": "Inventory item identifier, for example INV-001."

&#x20;   }

&#x20; },

&#x20; "required": \["item\_id"],

&#x20; "additionalProperties": false

}

```



\### Output schema



```json

{

&#x20; "type": "object",

&#x20; "properties": {

&#x20;   "item\_id": {"type": "string"},

&#x20;   "item\_name": {"type": "string"},

&#x20;   "current\_stock\_base": {"type": "number"},

&#x20;   "reorder\_level\_base": {"type": "number"},

&#x20;   "target\_stock\_base": {"type": "number"},

&#x20;   "needs\_reorder": {"type": "boolean"},

&#x20;   "assessable": {"type": "boolean"},

&#x20;   "reason": {"type": "string"}

&#x20; },

&#x20; "required": \[

&#x20;   "item\_id",

&#x20;   "needs\_reorder",

&#x20;   "assessable",

&#x20;   "reason"

&#x20; ],

&#x20; "additionalProperties": false

}

```



\### Business behavior



The deterministic implementation compares current stock with the configured reorder level.



An item at the reorder level must be treated as requiring replenishment.



If required inventory information is missing or cannot be assessed reliably, the result must indicate that the assessment is unassessable rather than inventing a Boolean decision.



\### Failure behavior



\- Missing `item\_id`: reject the request.

\- Unknown `item\_id`: return a structured not-found error.

\- Missing stock/reorder data: return an unassessable result.

\- Invalid inventory values: return a validation error.

\- No inventory mutation is permitted.



\---



\## 4. Tool: `lookup\_policy`



\### Purpose



Retrieve the relevant procurement-policy rule or section for a specified topic.



\### Caller



The bounded procurement agent/orchestration layer.



\### Side effect



None. Read-only policy access.



\### Input schema



```json

{

&#x20; "type": "object",

&#x20; "properties": {

&#x20;   "topic": {

&#x20;     "type": "string",

&#x20;     "description": "Procurement policy topic to retrieve."

&#x20;   }

&#x20; },

&#x20; "required": \["topic"],

&#x20; "additionalProperties": false

}

```



\### Output schema



```json

{

&#x20; "type": "object",

&#x20; "properties": {

&#x20;   "topic": {"type": "string"},

&#x20;   "policy\_section": {"type": "string"},

&#x20;   "rule": {"type": "string"},

&#x20;   "source": {"type": "string"}

&#x20; },

&#x20; "required": \[

&#x20;   "topic",

&#x20;   "policy\_section",

&#x20;   "rule",

&#x20;   "source"

&#x20; ],

&#x20; "additionalProperties": false

}

```



\### Business behavior



The implementation must return policy information from the controlled procurement corpus.



Examples of policy topics include:



\- quotation requirements;

\- quotation validity;

\- excluded suppliers;

\- landed-cost comparison;

\- approval thresholds;

\- requisition requirements.



The tool must not invent a policy rule when the controlled corpus does not contain sufficient evidence.



\### Failure behavior



\- Missing `topic`: reject the request.

\- Empty or unsupported topic: return a structured no-match result.

\- Missing policy evidence: return a controlled no-evidence result.

\- The tool must not fabricate policy content.



\---



\## 5. Tool: `compare\_quotations`



\### Purpose



Deterministically compare supplier quotations for an inventory item using the procurement policy's quotation-validity and landed-cost rules.



\### Caller



The bounded procurement agent/orchestration layer.



\### Side effect



None. Read-only quotation and supplier data access.



\### Input schema



```json

{

&#x20; "type": "object",

&#x20; "properties": {

&#x20;   "item\_id": {

&#x20;     "type": "string",

&#x20;     "description": "Inventory item being procured."

&#x20;   },

&#x20;   "quantity\_base": {

&#x20;     "type": "number",

&#x20;     "description": "Required quantity expressed in the item's inventory base unit."

&#x20;   }

&#x20; },

&#x20; "required": \[

&#x20;   "item\_id",

&#x20;   "quantity\_base"

&#x20; ],

&#x20; "additionalProperties": false

}

```



\### Output schema



```json

{

&#x20; "type": "object",

&#x20; "properties": {

&#x20;   "item\_id": {"type": "string"},

&#x20;   "quantity\_base": {"type": "number"},

&#x20;   "quotations\_considered": {

&#x20;     "type": "array",

&#x20;     "items": {

&#x20;       "type": "object",

&#x20;       "properties": {

&#x20;         "quotation\_id": {"type": "string"},

&#x20;         "supplier\_id": {"type": "string"},

&#x20;         "supplier\_name": {"type": "string"},

&#x20;         "valid": {"type": "boolean"},

&#x20;         "excluded": {"type": "boolean"},

&#x20;         "landed\_cost\_total": {"type": "number"},

&#x20;         "landed\_cost\_per\_base\_unit": {"type": "number"},

&#x20;         "delivery\_days": {"type": "number"}

&#x20;       },

&#x20;       "required": \[

&#x20;         "quotation\_id",

&#x20;         "supplier\_id",

&#x20;         "valid",

&#x20;         "excluded"

&#x20;       ],

&#x20;       "additionalProperties": false

&#x20;     }

&#x20;   },

&#x20;   "recommended\_supplier\_id": {

&#x20;     "type": \["string", "null"]

&#x20;   },

&#x20;   "recommendation\_basis": {"type": "string"},

&#x20;   "blocking\_flags": {

&#x20;     "type": "array",

&#x20;     "items": {"type": "string"}

&#x20;   }

&#x20; },

&#x20; "required": \[

&#x20;   "item\_id",

&#x20;   "quantity\_base",

&#x20;   "quotations\_considered",

&#x20;   "recommended\_supplier\_id",

&#x20;   "recommendation\_basis",

&#x20;   "blocking\_flags"

&#x20; ],

&#x20; "additionalProperties": false

}

```



\### Business behavior



All monetary and unit calculations must be performed by deterministic application code.



The implementation must:



1\. identify quotations for the requested item;

2\. validate quotation completeness;

3\. check quotation validity;

4\. exclude suppliers that are not eligible under policy;

5\. account for VAT treatment;

6\. account for delivery/off-loading charges;

7\. normalize quotation units to the inventory base unit;

8\. calculate landed cost per base unit;

9\. identify applicable blocking conditions; and

10\. return the computed comparison.



The model must not be treated as the authoritative calculator for procurement figures.



\### Failure behavior



\- Missing `item\_id` or `quantity\_base`: reject the request.

\- Invalid or non-positive quantity: reject the request.

\- No quotations found: return a structured no-quotes result.

\- No valid eligible quotations: return no recommendation and a blocking flag.

\- Expired quotation: mark invalid and exclude from the recommendation.

\- Excluded supplier: mark excluded and do not recommend or count it toward quotation requirements.

\- Missing quotation unit or other required quotation data: mark the quotation incomplete.

\- Calculation failure: return a controlled error; do not invent a result.



\---



\## 6. Tool: `create\_requisition\_draft`



\### Purpose



Create a procurement requisition in `DRAFT` state using validated procurement information.



\### Caller



The bounded procurement agent/orchestration layer.



\### Side effect



\*\*Simulated side effect.\*\*



The tool creates a draft requisition record and an audit-log entry.



\### Approval boundary



This tool may create only a `DRAFT`.



It must not:



\- approve the requisition;

\- move a requisition directly to `APPROVED`;

\- award a supplier;

\- make a purchase;

\- authorize payment; or

\- create an autonomous financial commitment.



Any later approval must pass through the human approval workflow.



\### Input schema



```json

{

&#x20; "type": "object",

&#x20; "properties": {

&#x20;   "item\_id": {

&#x20;     "type": "string",

&#x20;     "description": "Inventory item identifier."

&#x20;   },

&#x20;   "quantity\_base": {

&#x20;     "type": "number",

&#x20;     "description": "Required quantity in the item's base unit."

&#x20;   },

&#x20;   "recommended\_supplier\_id": {

&#x20;     "type": "string",

&#x20;     "description": "Supplier selected by the deterministic quotation comparison."

&#x20;   },

&#x20;   "comparison\_reference": {

&#x20;     "type": "string",

&#x20;     "description": "Reference to the quotation comparison evidence."

&#x20;   },

&#x20;   "preparing\_officer\_id": {

&#x20;     "type": "string",

&#x20;     "description": "Identifier of the officer preparing the requisition."

&#x20;   }

&#x20; },

&#x20; "required": \[

&#x20;   "item\_id",

&#x20;   "quantity\_base",

&#x20;   "recommended\_supplier\_id",

&#x20;   "comparison\_reference",

&#x20;   "preparing\_officer\_id"

&#x20; ],

&#x20; "additionalProperties": false

}

```



\### Output schema



```json

{

&#x20; "type": "object",

&#x20; "properties": {

&#x20;   "requisition\_id": {"type": "string"},

&#x20;   "state": {

&#x20;     "type": "string",

&#x20;     "enum": \["DRAFT"]

&#x20;   },

&#x20;   "item\_id": {"type": "string"},

&#x20;   "quantity\_base": {"type": "number"},

&#x20;   "recommended\_supplier\_id": {"type": "string"},

&#x20;   "audit\_log\_reference": {"type": "string"}

&#x20; },

&#x20; "required": \[

&#x20;   "requisition\_id",

&#x20;   "state",

&#x20;   "item\_id",

&#x20;   "quantity\_base",

&#x20;   "recommended\_supplier\_id",

&#x20;   "audit\_log\_reference"

&#x20; ],

&#x20; "additionalProperties": false

}

```



\### Business behavior



The implementation creates a system-assigned requisition number, stores the supplied validated information, sets the state to `DRAFT`, and records an audit-log entry.



The tool must not bypass the approval state machine.



\### Failure behavior



\- Missing required parameter: reject without creating a requisition.

\- Invalid quantity: reject without creating a requisition.

\- Unknown inventory item: reject without creating a requisition.

\- Unknown or ineligible supplier: reject without creating a requisition.

\- Missing comparison reference: reject without creating a requisition.

\- Persistence failure: return a controlled error and avoid reporting successful creation.

\- No path may transition the requisition directly to `APPROVED`.



\---



\## 7. Permission and Side-Effect Matrix



| Tool | Read/Write | Side effect | Agent may call | Human approval |

|---|---|---|---|---|

| `check\_reorder\_levels` | Read | None | Yes | No |

| `lookup\_policy` | Read | None | Yes | No |

| `compare\_quotations` | Read/compute | None | Yes | No |

| `create\_requisition\_draft` | Write | Creates DRAFT + audit entry | Yes | Approval remains separate |



\## 8. Router Requirements



The Week 4 orchestration layer must enforce this catalogue.



The router must:



1\. maintain an explicit allow-list of approved tools;

2\. reject unlisted tool requests;

3\. validate required arguments before dispatch;

4\. dispatch only to registered deterministic implementations;

5\. record each tool request and result in a trace;

6\. return structured tool results to the model;

7\. prevent tools from exceeding their documented authority; and

8\. record model-versus-computed figure mismatches where applicable.



An unrecognized tool request must not be dynamically executed.



For example, the router must not execute an arbitrary function merely because the model supplied its function name.



\## 9. Division of Responsibility



\### W4-01 â€” Mable + Tendo



Define and review the tool contracts documented here.



\### W4-02 â€” Azibo



Implement the deterministic tools under `src/tools/` according to these contracts.



\### W4-03 â€” Tendo



Implement the function-calling orchestration layer under `src/agent/tools\_router.py`, including registration, allow-list enforcement, dispatch, tracing, and model-versus-computed mismatch handling.



\### W4-04 â€” Ashley



Test failure and authorization behavior.



\### W4-05 â€” Azibo + Ashley



Implement and test the human approval/state-machine boundary.



\## 10. Design Principle



The system follows a controlled hybrid architecture:



```text

Foundation model

&#x20;     |

&#x20;     | requests an approved tool

&#x20;     v

Tool router

&#x20;     |

&#x20;     | validates + allow-lists + dispatches

&#x20;     v

Deterministic application tool

&#x20;     |

&#x20;     | computed/validated result

&#x20;     v

Tool router

&#x20;     |

&#x20;     v

Foundation model

```



The foundation model is therefore not granted unrestricted access to application functionality.



Deterministic code remains authoritative for procurement calculations, validation, state changes, and other high-impact operations.



Human approval remains the boundary for approval of procurement actions.
