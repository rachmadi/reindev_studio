# PHASE 1A — FORENSIC AUDIT: ARCHITECT TURN 0 INPUT & REPRESENTATION COMPETITION

**Date & Time:** 2026-09-18T21:45:00+07:00  
**Active Branch:** `experiment/treatment-1.8-agent-capability`  
**Purpose:** Reconstruct the exact Turn 0 input delivered to System Architect across the 3 pilot tasks (`fastapi_t1`, `cli_t1`, `flutter_t1`) to determine whether the model is burdened by competing and redundant representations.

---

## 1. OVERALL INPUT SIZE & BREAKDOWN

| Task ID | Target Lang | System Prompt | User Message | Total Input Chars | Estimated Tokens |
|---|---|---|---|---|---|
| `fastapi_t1` | Python | 7,751 chars | 10,845 chars | **18,596 chars** | ~4,650 tokens |
| `cli_t1` | Python | 7,751 chars | 10,742 chars | **18,493 chars** | ~4,623 tokens |
| `flutter_t1` | Dart | 7,751 chars | 7,853 chars | **15,604 chars** | ~3,901 tokens |

---

## 2. SECTION-BY-SECTION AUDIT (TURN 0 USER MESSAGE)

Reconstructed from runtime path in `backend/agents/architect.py`:

| # | Section Name | Source / Generator | Size in `fastapi_t1` | Size in `cli_t1` | Size in `flutter_t1` |
|---|---|---|---|---|---|
| 0 | Target Language & Rules | `structure_rule` | 642 chars | 642 chars | 592 chars |
| 0b | Fact Card | `generate_fact_card_for_architect` | 669 chars | 669 chars | 544 chars |
| 1 | User Task | `state["task"]` | 110 chars | 97 chars | 105 chars |
| 2 | Acceptance Scenarios | `format_scenarios_for_architect` | **1,922 chars** | **2,086 chars** | **1,267 chars** |
| 3 | Acceptance Obligation Ledger | `format_authoritative_obligation_ledger` | **2,175 chars** | **2,084 chars** | **1,292 chars** |
| 4 | Acceptance Usage Evidence | `format_acceptance_usage_evidence` | **1,952 chars** | **1,865 chars** | **1,531 chars** |
| 5 | V0 Requirements | `state["v0_requirement_model"]` | ~450 chars | ~450 chars | ~450 chars |
| 6 | PM Specification | `state["specifications"]` | **1,400 chars** | **1,250 chars** | **950 chars** |
| 7 | Blueprint Schema & Constraints | Hardcoded prompt template | 1,475 chars | 1,475 chars | 1,475 chars |

---

## 3. AUDIT OF COMPETING AND DUPLICATED REPRESENTATIONS

### Finding 1: Triple-Redundancy of Oracle Acceptance Facts (~6,050 chars per task)
The exact same acceptance obligations are delivered to the Architect in **three competing representations**:
1. **Representation 1 — Obligation Ledger (`format_authoritative_obligation_ledger`)**: 2,175 chars. Lists Obligation ID, Symbol, Type, Parameters, Expected Return.
2. **Representation 2 — Usage Evidence (`format_acceptance_usage_evidence`)**: 1,952 chars. Repeats the exact same callables with AST call snippets from pytest/dart test files.
3. **Representation 3 — Scenarios (`format_scenarios_for_architect`)**: 1,922 chars. Repeats the exact same callables a third time with stimulus and expected outcome status.

**Impact:** Over 6,000 characters (32% of total context) describe the exact same 4 endpoints/callables. This creates severe token bloat and representation competition.

### Finding 2: Namespace Collision Between PM Proposal and Oracle Authority
- In `fastapi_t1`, the PM specification uses Indonesian field names (`nama`, `harga`, `stok`).
- The Oracle Ledger uses English field names (`name`, `price`, `quantity`).
- Because PM is presented without an explicit "PM = PROPOSAL (Design Reference Only — NOT Authority)" boundary, the LLM is forced to mediate between two competing authorities. In Treatment #1.8.10, this led directly to the Developer hallucinating `stock` and omitting `quantity`.

### Finding 3: Repair-Only Information Leaking to Turn 0
In `ARCHITECT_SYSTEM_PROMPT` (7,751 chars):
- **Lines 223–231:** Invariants A–H ("INVARIANT-F (Non-Destructive Repair)").
- **Lines 232–235:** Generic Repair Preservation ("CURRENT VALID STATE + REPAIRED ELEMENT").
- **Lines 237–240:** Deep scenario error path requirements and positional constructor warnings.
These instructions are exclusively relevant to **repair turns**, yet they occupy significant attention budget on Turn 0 where no prior state exists.

### Finding 4: Vestigial Delimiters in Contract Provenance
`aligned_contract["provenance"]` continues to inject dummy `raw_stage_a_output` (`=== STAGE A: OBLIGATION MAPPING ===`) and `raw_stage_b_output` (`=== STAGE B: ARCHITECTURAL ASSEMBLY ===`) to satisfy historical tests, even though Stages A and B have been deactivated.

---

## 4. CONCLUSION & RECOMMENDATION FOR PHASE 1B

1. **Enforce Strict Priority Context Order:**
   ```
   [1] USER INTENT / V0 REQUIREMENTS
   [2] ACCEPTANCE OBLIGATION LEDGER
   [3] PM SPECIFICATION
   [4] BLUEPRINT SCHEMA
   [5] ARCHITECT CONSTRUCTION RULES
   ```
2. **Eliminate Competing Representations:**
   - Use the **Acceptance Obligation Ledger** as the single authoritative acceptance representation.
   - Eliminate redundant inline duplication of Usage Evidence and Scenarios from Turn 0 context unless requested as secondary evidence.
3. **Explicit PM Boundary:**
   - Clearly label PM as `PROPOSAL (Design Reference Only)`.
   - Explicitly declare: `If PM proposal conflicts with Acceptance Obligation Ledger, Acceptance Obligation Ledger STRICTLY GOVERNS.`
4. **Condense Scaffolding Mandate:**
   - Minimal stubs (`pass`) only. Developer owns full implementation.
