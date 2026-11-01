# ClaimRecon AI
## Bounded Agentic Claim-Package Validation and Supported-Amount Analysis

*Consolidated project report based on the final design decisions.*

---

### Project Metadata
* **Status:** Final Two-Day Hackathon Blueprint
* **Scope:** One commercial-property fire stock claim
* **Agentic Behavior:** LLM document interpretation and supervisor tool planning
* **Deterministic Controls:** Checklist validation, rule execution, completion evaluation, and financial calculation
* **Build Target:** One junior engineer, one day preferred, two days maximum
* **Date:** 28 October 2026

---

## Executive Summary: Final MVP Decision

ClaimRecon AI will be a bounded agentic workflow that evaluates whether a submitted claim package is complete, selects applicable integrity tools, executes controlled checks, determines whether all checks finished, and calculates how much of the claimed stock amount is supported by the submitted records.

### Responsibilities Breakdown

#### Agentic Responsibilities (LLM)
* Interpret ambiguously named files.
* Plan which approved tools should run.
* Adapt execution plan to available evidence.
* Explain verified findings to the investigator.

#### Deterministic Responsibilities (Code)
* Validate document checklist and schemas.
* Validate the Supervisor execution plan.
* Execute duplicate, date, and amount checks.
* Determine check completion.
* Calculate supported and unsupported amounts.

> **Core Principle:** The LLM decides what approved action to take next. Python decides whether evidence conflicts and performs all financial arithmetic.

---

## Specification Navigation

| Section | Topic | Scope & Description |
| :--- | :--- | :--- |
| **1** | Problem and scope | Claims investigator workflow, in-scope & out-of-scope boundaries |
| **2** | Synthetic claim and packages | Loss parameters, complete & incomplete test packages, designed findings |
| **3** | Checklist and rule configuration | Business checklist JSON schema, mandatory documents, approved tool catalog |
| **4** | Final agentic architecture | LangGraph pipeline architecture and node transitions |
| **5** | Shared state | `ClaimState` TypedDict complete schema definition |
| **6** | Node contracts | Complete 10-node I/O and model usage specification |
| **7** | LLM document classification | `classify_documents` prompt context, JSON input, and structured output |
| **8** | LLM Supervisor planning | `supervisor_plan` input context, tool selection schema, and blocked logic |
| **9** | Deterministic execution | `validate_plan` Python loop and `TOOL_REGISTRY` execution rules |
| **10** | Integrity tools & findings | Structured findings output (`FND-001`, `FND-002`, `FND-003`) |
| **11** | Deterministic completion evaluation | State machine logic, check status resolution, and next action rules |
| **12** | Financial calculation engine | Exact Python `Decimal` calculation node preventing double-deductions |
| **13** | Output schemas | Complete vs. Incomplete final package payload contracts |
| **14** | LLM investigator summary | Summary generation output schema and hard operational guardrails |
| **15** | LangGraph conditional routing | Graph edge definitions, routing callback, and loop safeguards |
| **16** | Implementation plan | One-to-two-day phased delivery roadmap (Day 1 / Day 2) |
| **17** | Investigator dashboard | Streamlit UI layout, KPI metrics strip, and evidence drawers |
| **18** | Five-minute demonstration | Step-by-step hackathon pitch and live testing script |
| **19** | Acceptance & Definition of Done | Acceptance checklist and golden calculation invariant |
| **20** | References | LangGraph and StateGraph architectural documentation citations |

---

## 1. Problem, User, and Boundaries

A claims investigator receives records supporting a commercial-property stock-loss claim. The investigator needs to know whether the minimum package is present, whether the records conflict, and how much of the claimed amount is currently supported.

### Operating Envelope

| In Scope | Out of Scope |
| :--- | :--- |
| Predefined document checklist | Agent inventing mandatory documents |
| One synthetic fire-stock claim | Multiple claim types and production integrations |
| Completeness and three integrity checks | Fraud, coverage, approval, or denial |
| Structured JSON and Excel inputs | OCR and general PDF extraction |
| Claimed, supported, and unsupported amounts | Machinery or business-interruption valuation |
| Streamlit dashboard and evidence rows | Authentication and enterprise workflow |

> **Final Positioning:** ClaimRecon AI is a bounded agentic investigation workflow. The Supervisor interprets the claim package and selects approved integrity tools; Deterministic nodes execute checks, verify completion, and calculate the amount supported by submitted evidence.

---

## 2. Synthetic Claim and Packages

### Claim Metadata
* **Claim ID:** `CLM-2026-0042`
* **Insured:** Northstar Components LLC
* **Loss Date:** 15 Aug 2026
* **Claimed Stock:** $\$824,000$ USD
* **Currency:** USD

### Designed Findings
* **Duplicate:** $\$38,000$
* **Post-loss delivery:** $\$24,000$
* **Amount mismatch:** $\$2,000$
* **Total unsupported:** $\$64,000$
* **Supported:** $\$760,000$

### Test Packages

| Package | Files Included | Expected Result |
| :--- | :--- | :--- |
| **Complete** | Claim form, fire report, purchase ledger, supplier invoices, delivery records | All checks complete; supported amount calculated ($\$760,000$). |
| **Incomplete** | Same package without delivery records | Delivery check blocked; only partial unsupported amount shown ($\$40,000$). |

> **Why two packages:** The complete package proves the financial calculation; the incomplete package proves evidence-aware planning and safe partial results.

---

## 3. Business Checklist and Approved Tools

The business provides the required-document checklist. The agent may classify files into allowed categories, but cannot create new mandatory requirements.

### Required Document Checklist
```json
{
  "checklist_id": "COMMERCIAL_PROPERTY_FIRE_STOCK_V1",
  "required_documents": [
    "CLAIM_FORM",
    "FIRE_REPORT",
    "PURCHASE_LEDGER",
    "SUPPLIER_INVOICES",
    "DELIVERY_RECORDS"
  ]
}
```

### Approved Rule Catalog

| Rule | Dependencies | Financial Treatment |
| :--- | :--- | :--- |
| `DUPLICATE_INVOICE_V1` | Purchase ledger | Deduct repeated occurrence |
| `DELIVERY_AFTER_LOSS_V1` | Fire report + delivery records + ledger | Deduct full affected line |
| `INVOICE_AMOUNT_MISMATCH_V1` | Purchase ledger + supplier invoices | Deduct positive unsupported difference |

```json
{
  "DUPLICATE_INVOICE_V1": ["PURCHASE_LEDGER"],
  "DELIVERY_AFTER_LOSS_V1": ["FIRE_REPORT", "DELIVERY_RECORDS", "PURCHASE_LEDGER"],
  "INVOICE_AMOUNT_MISMATCH_V1": ["PURCHASE_LEDGER", "SUPPLIER_INVOICES"]
}
```

---

## 4. Final Bounded Agentic Graph Architecture

```
[ load_package ] (Python)
       │
       ▼
[ classify_documents ] (LLM)
       │
       ▼
[ validate_classification ] (Python)
       │
       ▼
[ check_completeness ] (Python)
       │
       ▼
[ supervisor_plan ] (LLM) ◄────────┐ (loop on pending)
       │                           │
       ▼                           │
[ validate_plan ] (Python)         │
       │                           │
       ▼                           │
[ execute_checks ] (Python)        │
       │                           │
       ▼                           │
[ evaluate_completion ] (Python) ──┘
       │
       ├───► [ calculate_amounts ] (Python)
       │            │
       │            ▼
       └───► [ generate_summary ] (LLM)
                    │
                    ▼
                 [ END ]
```

*LangGraph uses shared state, nodes, and edges; nodes read state and return updates, while conditional edges route the next step. The graph is compiled before invocation.*

---

## 5. Shared State Definition

```python
class ClaimState(TypedDict, total=False):
    run_id: str
    claim_folder: str
    checklist_id: str
    claim: dict
    file_inventory: list[dict]
    document_classifications: list[dict]
    documents: dict[str, dict]
    normalized_data: dict[str, list[dict]]
    completeness_result: dict
    available_tools: list[dict]
    supervisor_plan: dict
    completed_checks: list[str]
    blocked_checks: list[dict]
    failed_checks: list[dict]
    integrity_findings: list[dict]
    check_evaluation: dict
    financial_summary: dict
    investigator_summary: dict
    planning_iteration: int
    status: str
```

> **Implementation Rule:** Nodes return partial state updates. DataFrames are converted into serializable row dictionaries before entering shared state.

---

## 6. Node Responsibilities and Model Usage

| Node Name | LLM? | Reads (Inputs) | Returns (Outputs) |
| :--- | :---: | :--- | :--- |
| `load_claim_package` | No | Claim folder | Inventory and normalized data |
| `classify_documents` | **Yes** | File names, columns, samples, allowed types | Candidate type, confidence, reason |
| `validate_classification` | No | LLM classification and checklist | Accepted types or review items |
| `check_completeness` | No | Accepted types and checklist | Missing/invalid documents |
| `supervisor_plan` | **Yes** | Completeness, completed checks, approved tools | Selected and blocked tools |
| `validate_plan` | No | Supervisor plan and dependencies | Executable approved plan |
| `execute_selected_checks` | No | Plan and normalized records | Structured findings and tool results |
| `evaluate_check_completion` | No | Configured/completed/blocked/failed checks | Status and next action |
| `calculate_supported_amount` | No | Claim amount and findings | Claimed/supported/unsupported amounts |
| `generate_investigator_summary`| **Yes** | Verified structured output | Explanation and follow-ups |

---

## 7. LLM Document Classification Node (`classify_documents`)

This node maps nonstandard filenames and schemas to document types already allowed by the checklist.

### Example Context & Input to LLM
```json
{
  "allowed_types": [
    "CLAIM_FORM",
    "FIRE_REPORT",
    "PURCHASE_LEDGER",
    "SUPPLIER_INVOICES",
    "DELIVERY_RECORDS"
  ],
  "file": {
    "filename": "warehouse_dispatch_august.xlsx",
    "columns": [
      "dispatch_reference",
      "related_invoice",
      "delivered_on"
    ],
    "sample_rows": [
      {
        "related_invoice": "INV-9102",
        "delivered_on": "2026-08-17"
      }
    ]
  }
}
```

### Structured LLM Output
```json
{
  "document_type": "DELIVERY_RECORDS",
  "confidence": 0.94,
  "reason": "The file contains invoice-linked dispatch and delivery dates.",
  "column_mapping": {
    "related_invoice": "invoice_number",
    "delivered_on": "delivery_date"
  },
  "requires_human_review": false
}
```

> **Python Validation:** The next node verifies that the proposed type is allowed and that required fields can be mapped. Low-confidence or invalid mappings become review items.

---

## 8. LLM Supervisor Planning Node (`supervisor_plan`)

The Supervisor observes evidence availability and prior check status, then chooses from a fixed tool catalog. The LLM cannot create a new tool or bypass dependencies.

### Structured Input
```json
{
  "available_documents": [
    "CLAIM_FORM",
    "FIRE_REPORT",
    "PURCHASE_LEDGER",
    "SUPPLIER_INVOICES"
  ],
  "completed_checks": [],
  "available_tools": [
    {
      "name": "check_duplicate_invoices",
      "requires": ["PURCHASE_LEDGER"]
    },
    {
      "name": "check_delivery_after_loss",
      "requires": ["FIRE_REPORT", "DELIVERY_RECORDS"]
    },
    {
      "name": "check_invoice_amount_mismatch",
      "requires": ["PURCHASE_LEDGER", "SUPPLIER_INVOICES"]
    }
  ]
}
```

### Structured LLM Output
```json
{
  "selected_tools": [
    {
      "tool": "check_duplicate_invoices",
      "reason": "Purchase ledger is available."
    },
    {
      "tool": "check_invoice_amount_mismatch",
      "reason": "Ledger and supplier invoice records are available."
    }
  ],
  "blocked_tools": [
    {
      "tool": "check_delivery_after_loss",
      "reason": "Delivery records are missing."
    }
  ],
  "next_action": "EXECUTE_AVAILABLE_CHECKS"
}
```

---

## 9. Deterministic Plan Validation & Execution

### Plan Validation Logic (`validate_plan`)
* Reject unknown tools.
* Reject tools with missing dependencies.
* Remove checks already completed.
* Enforce a maximum of two planning iterations.

```python
approved = []
for selection in supervisor_plan["selected_tools"]:
    tool = TOOL_CATALOG.get(selection["tool"])
    if tool and dependencies_present(tool, state):
        approved.append(selection["tool"])
```

### Deterministic Execution (`execute_selected_checks`)
```python
TOOL_REGISTRY = {
    "check_duplicate_invoices": check_duplicate_invoices,
    "check_delivery_after_loss": check_delivery_after_loss,
    "check_invoice_amount_mismatch": check_invoice_amount_mismatch
}

for tool_name in approved_tools:
    result = TOOL_REGISTRY[tool_name](state)
    tool_results.append(result)
```

> **Control Boundary:** The LLM selects approved tools. Python validates and executes them.

---

## 10. Structured Integrity Findings Output

### 1. Duplicate Invoice Finding
```json
{
  "finding_id": "FND-001",
  "rule_id": "DUPLICATE_INVOICE_V1",
  "claim_line_key": "INV-5521",
  "financial_treatment": "DEDUCT_FULL_LINE",
  "financial_impact": "38000.00",
  "evidence": [
    "purchase_ledger.xlsx:PL-1001",
    "purchase_ledger.xlsx:PL-1092"
  ]
}
```

### 2. Post-Loss Delivery Finding
```json
{
  "finding_id": "FND-002",
  "rule_id": "DELIVERY_AFTER_LOSS_V1",
  "claim_line_key": "INV-9102",
  "financial_treatment": "DEDUCT_FULL_LINE",
  "financial_impact": "24000.00",
  "facts": {
    "loss_date": "2026-08-15",
    "delivery_date": "2026-08-17"
  },
  "evidence": [
    "fire_report.json:loss_date",
    "delivery_records.xlsx:DEL-9102"
  ]
}
```

### 3. Amount Mismatch Finding
```json
{
  "finding_id": "FND-003",
  "rule_id": "INVOICE_AMOUNT_MISMATCH_V1",
  "claim_line_key": "INV-7742",
  "financial_treatment": "DEDUCT_DIFFERENCE",
  "financial_impact": "2000.00",
  "facts": {
    "ledger_amount": "52000.00",
    "invoice_amount": "50000.00"
  }
}
```

---

## 11. Deterministic Completion Evaluation

The Supervisor does not decide completion through free-form reasoning. Python compares configured checks with completed, blocked, failed, and pending checks.

```python
configured = set(state["configured_checks"])
completed = {x["rule_id"] for x in state["tool_results"] if x["status"] == "COMPLETED"}
failed = {x["rule_id"] for x in state["tool_results"] if x["status"] == "FAILED"}
blocked = {x["rule_id"] for x in state["blocked_checks"]}
pending = configured - completed - failed - blocked

if failed:
    next_action = "PROCESSING_REVIEW"
elif pending:
    next_action = "CONTINUE_INVESTIGATION"
elif blocked:
    next_action = "CALCULATE_PARTIAL_RESULT"
else:
    next_action = "CALCULATE_SUPPORTED_AMOUNT"
```

### Evaluation State Payloads

#### All-Complete Output
```json
{
  "status": "COMPLETED",
  "completed_checks": [
    "DUPLICATE_INVOICE_V1",
    "DELIVERY_AFTER_LOSS_V1",
    "INVOICE_AMOUNT_MISMATCH_V1"
  ],
  "blocked_checks": [],
  "failed_checks": [],
  "pending_checks": [],
  "all_checks_completed": true,
  "next_action": "CALCULATE_SUPPORTED_AMOUNT"
}
```

#### Pending Scenario
```json
{
  "status": "CHECKS_PENDING",
  "completed_checks": ["DUPLICATE_INVOICE_V1", "INVOICE_AMOUNT_MISMATCH_V1"],
  "pending_checks": ["DELIVERY_AFTER_LOSS_V1"],
  "next_action": "CONTINUE_INVESTIGATION"
}
```
*The graph returns to `supervisor_plan`, but only pending checks are eligible.*

#### Blocked Scenario
```json
{
  "status": "PARTIALLY_COMPLETED",
  "completed_checks": ["DUPLICATE_INVOICE_V1", "INVOICE_AMOUNT_MISMATCH_V1"],
  "blocked_checks": ["DELIVERY_AFTER_LOSS_V1"],
  "all_checks_completed": false,
  "next_action": "CALCULATE_PARTIAL_RESULT"
}
```

> **Safety Behavior:** A blocked financial check prevents a definitive supported amount. The UI shows only the affected amount identified by completed checks.

---

## 12. Financial Calculation Node (Python Math)

### Supported & Unsupported Definitions
* **Claimed Amount:** Stock-loss amount submitted by the insured.
* **Unsupported Amount:** Unique financial impact identified by completed integrity checks.
* **Supported Amount:** Claimed amount minus unsupported amount, only when all financial checks completed.
* **Difference Amount:** Claimed minus supported; equal to unsupported at claim-summary level.

$$\text{Supported Amount} + \text{Unsupported Amount} = \text{Claimed Amount}$$

```
Claimed amount:         $824,000
Less duplicate:          $38,000
Less post-loss:          $24,000
Less mismatch:            $2,000
--------------------------------
Unsupported amount:      $64,000
Supported amount:       $760,000
```

### Python Calculation Implementation
```python
from decimal import Decimal

def calculate_supported_amount(state):
    if not state["check_evaluation"]["all_checks_completed"]:
        raise ValueError("All financial checks must complete first")
    
    claimed = Decimal(state["claim"]["claimed_stock_amount"])
    impact_by_line = {}

    for finding in state["integrity_findings"]:
        key = finding["claim_line_key"]
        impact = Decimal(finding["financial_impact"])
        impact_by_line[key] = max(impact_by_line.get(key, Decimal("0")), impact)

    unsupported = sum(impact_by_line.values(), Decimal("0"))
    supported = claimed - unsupported

    return {
        "financial_summary": {
            "claimed_amount": str(claimed),
            "supported_amount": str(supported),
            "unsupported_amount": str(unsupported),
            "difference_amount": str(claimed - supported),
            "calculation_complete": True,
            "currency": state["claim"]["currency"]
        }
    }
```

> **Safeguard:** The maximum-impact-per-line rule is a simple MVP safeguard against deducting the same claim line twice when two findings overlap.

---

## 13. System Output Schemas

### Complete Package Final Output
```json
{
  "status": "READY_FOR_SUMMARY",
  "check_summary": {
    "configured": 3,
    "completed": 3,
    "blocked": 0,
    "failed": 0
  },
  "financial_summary": {
    "claimed_amount": "824000.00",
    "supported_amount": "760000.00",
    "unsupported_amount": "64000.00",
    "difference_amount": "64000.00",
    "supported_percentage": 92.23,
    "unsupported_percentage": 7.77,
    "currency": "USD",
    "calculation_complete": true
  },
  "breakdown": [
    {
      "reason": "DUPLICATE INVOICE",
      "invoice": "INV-5521",
      "amount": "38000.00"
    },
    {
      "reason": "DELIVERY AFTER LOSS",
      "invoice": "INV-9102",
      "amount": "24000.00"
    },
    {
      "reason": "INVOICE AMOUNT MISMATCH",
      "invoice": "INV-7742",
      "amount": "2000.00"
    }
  ]
}
```

### Incomplete Package Final Output
```json
{
  "status": "PARTIALLY_COMPLETED",
  "check_summary": {
    "configured": 3,
    "completed": 2,
    "blocked": 1,
    "failed": 0
  },
  "financial_summary": {
    "claimed_amount": "824000.00",
    "supported_amount": null,
    "identified_unsupported_amount": "40000.00",
    "calculation_complete": false,
    "reason": "Delivery-after-loss check was not performed"
  },
  "blocked_checks": [
    {
      "rule_id": "DELIVERY_AFTER_LOSS_V1",
      "missing_dependencies": ["DELIVERY_RECORDS"]
    }
  ]
}
```

> **UI Wording Rule:** *"$40,000 unsupported in completed checks."* Do not display $\$784,000$ as supported because one financial check is unavailable.

---

## 14. LLM Investigator Summary Node (`generate_summary`)

The final LLM receives only verified structured results. It explains the result and drafts follow-up actions without changing amounts or statuses.

### Structured Summary Output
```json
{
  "executive_summary": "The submitted package is complete. Three integrity findings affect $64,000 of the $824,000 claimed stock amount. Documents currently support $760,000.",
  "recommended_actions": [
    "Confirm the valid ledger occurrence for INV-5521.",
    "Request clarification for the post-loss delivery linked to INV-9102.",
    "Reconcile the $2,000 difference for INV-7742."
  ],
  "disclaimer": "This output supports investigation and does not approve, deny, or determine coverage."
}
```

### LLM Operational Restrictions
* Cannot modify check status, severity, evidence, or amount.
* Cannot label a finding as fraud.
* Cannot determine payable amount or coverage.
* Falls back to a deterministic text template if unavailable.

---

## 15. LangGraph Conditional Routing

```python
def route_after_evaluation(state):
    return {
        "CONTINUE_INVESTIGATION": "supervisor_plan",
        "CALCULATE_SUPPORTED_AMOUNT": "calculate_supported_amount",
        "CALCULATE_PARTIAL_RESULT": "calculate_partial_result",
        "PROCESSING_REVIEW": "processing_review"
    }[state["check_evaluation"]["next_action"]]

builder.add_conditional_edges(
    "evaluate_check_completion",
    route_after_evaluation,
    {
        "supervisor_plan": "supervisor_plan",
        "calculate_supported_amount": "calculate_supported_amount",
        "calculate_partial_result": "calculate_partial_result",
        "processing_review": "processing_review"
    }
)
```

### Loop Safeguards
* Maximum two planning iterations.
* Completed checks cannot be selected again.
* Only catalogued tools may execute.
* Dependencies are validated in Python.
* Any failed financial rule prevents a definitive supported amount.

---

## 16. One-to-Two-Day Implementation Plan

### Day 1, First Half
1. Create complete and incomplete synthetic packages.
2. Create checklist, tool catalog, and dependency configuration.
3. Build JSON/Excel loaders and normalizers.
4. Define ClaimState and graph skeleton.
5. Implement LLM document classifier with structured output.
6. Implement deterministic completeness validation.

### Day 1, Second Half
1. Implement LLM Supervisor plan with fixed tool choices.
2. Implement plan validator.
3. Implement three Python checks.
4. Implement deterministic completion evaluation.
5. Implement supported/unsupported calculation.
6. Build basic Streamlit dashboard.

### Day 2, Only If Needed
* Add summary LLM and template fallback.
* Add graph-step status and evidence expanders.
* Add saved JSON fallback and rehearse three times.

---

## 17. Investigator Dashboard View (Streamlit UI Layout)

```
========================================================================================
ClaimRecon AI • CLM-2026-0042 • Ready for review
========================================================================================

  [ Claimed ]               [ Supported ]                 [ Unsupported ]
   $824,000                   $760,000                        $64,000

----------------------------------------------------------------------------------------
Finding              Invoice     Impact     Evidence
----------------------------------------------------------------------------------------
Duplicate invoice    INV-5521    $38,000    Two ledger rows
Delivery after loss  INV-9102    $24,000    Fire date and delivery row
Amount mismatch      INV-7742     $2,000    Ledger and supplier invoice
----------------------------------------------------------------------------------------

Secondary Status:
• Package completeness: 100%
• Checks completed, blocked, failed, and pending: 3 completed, 0 blocked, 0 failed
• Supervisor-selected tools and reasons: Available in execution trace
• Evidence rows for each finding: Accessible via audit expanders
```

---

## 18. Five-Minute Demonstration Script

1. Explain that the business supplies the checklist and approved tool catalog.
2. Load the incomplete package with a nonstandard filename.
3. Show LLM classification, missing delivery evidence, and Supervisor tool plan.
4. Show duplicate and mismatch checks completing while delivery check is blocked.
5. Show partial unsupported amount and no definitive supported amount.
6. Run the complete package.
7. Show all three checks complete, then $\$824\text{K}$ claimed, $\$760\text{K}$ supported, and $\$64\text{K}$ unsupported.
8. Open evidence for one finding and show the generated summary.

> **Judge-ready explanation:** The system is agentic because the LLM interprets evidence and plans approved tool use based on case state. It remains controlled because Python validates plans, executes rules, evaluates completion, and performs financial calculations.

---

## 19. Definition of Done (DoD) & Acceptance

### Verification Checklist

#### Agentic Behavior
* [x] Ambiguous file classified
* [x] Supervisor selects tools
* [x] Plan adapts to missing evidence
* [x] Pending checks can loop once
* [x] Final summary generated

#### Deterministic Controls
* [x] Checklist validated
* [x] Tool dependencies enforced
* [x] Three checks return evidence
* [x] Completion evaluated in Python
* [x] No double counting
* [x] Financial invariant passes

### Expected Golden Result
```
Claimed:      824000.00
Supported:    760000.00
Unsupported:   64000.00

Check: 760000.00 + 64000.00 == 824000.00 (INVARIANT PASSES)
```

---

## 20. Design References

1. **LangChain Reference, StateGraph:** StateGraph nodes read and write shared state, return partial updates, and require compilation before invocation.  
   `https://reference.langchain.com/python/langgraph/graph/state/StateGraph` (accessed 28 Oct 2026).
2. **LangChain Docs, Graph API overview:** LangGraph workflows are composed from state, nodes, and edges; nodes may contain LLM calls or ordinary code.  
   `https://docs.langchain.com/oss/python/langgraph/graph-api` (accessed 28 Oct 2026).
3. **LangChain Docs, Use the graph API:** Demonstrates TypedDict state, node updates, graph construction, and compilation.  
   `https://docs.langchain.com/oss/python/langgraph/use-graph-api` (accessed 28 Oct 2026).

> **Final Architecture Statement:** LLM-powered perception and planning are bounded by a predefined checklist and approved tool catalog. Deterministic Python controls every evidence check, completion decision, and financial result.