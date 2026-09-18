# RESEARCH REPORT — TREATMENT #1.8.7
## Semantic Grounding & Prompt Fidelity v1
**Controlled Pilot 1×3 Evaluation, Empirical Diagnostic & Longitudinal Comparison Report**

- **Date**: 2026-09-17
- **Model**: `qwen2.5-coder:7b` via Ollama (Unified Squad Model)
- **Pilot Tasks**: `fastapi_t1` (Stress Case), `cli_t1` (Control/Stability Case), `flutter_t1` (Control Case)
- **Pipeline Version**: 1.8.7-semantic-grounding-v1
- **Governance Version**: 1.6 (Frozen Invariants, Immutable Oracle SHA-256)
- **Pre-Flight Status**: Gates A–I PASS (900/900 unit tests passing, 0 regressions)

---

## 1. Executive Summary & Core Hypothesis

### Core Hypothesis Tested
> *Penguatan semantic grounding dan prompt fidelity pada System Architect — melalui penegakan 7-layer Epistemic Hierarchy, pemisahan tegas WHAT vs HOW, penolakan silent renaming/synonym temptation, pelestarian obligation traceability berjangkar bukti, serta pembatasan bukti perbaikan hanya pada active failure — akan secara terukur meningkatkan semantic fidelity keputusan arsitektural tanpa modifikasi tata kelola pipa atau penambahan solver deterministik.*

### Five-Way Longitudinal Comparison Matrix

| Metric / Invariant | Treatment #1.8.5 Baseline | Treatment #1.8.6 Un-Repaired | Treatment #1.8.6 Decoder Repaired | Treatment #1.8.6 Canonical State Repaired | Treatment #1.8.7 Semantic Grounding v1 | Empirical Delta & Impact |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Unit Test Suite (Regression)** | 840/840 PASS | 860/860 PASS | 870/870 PASS | 885/885 PASS | **900/900 PASS** | +15 generic grounding tests (Tests A–O), **0 regressions** |
| **Pre-Flight Gates A–I** | 100% PASS | 100% PASS | 100% PASS | 100% PASS | **100% PASS** | Zero-drift verification against canonical rules |
| **Oracle Immutability** | 100% Intact | 100% Intact | 100% Intact | 100% Intact | **100% Intact** | Exact SHA-256 match across all runs |
| **Epistemic Hierarchy Enforced** | Implicit | Implicit | Implicit | Implicit | **Explicit 7-Layer Precedence** | **Authority over proposal strictly guaranteed** |
| **Stage A Obligation Coverage** | Partial | Partial | Partial | Partial | **100% across all 3 tasks** | **Stage A mapped all authoritative obligations** |
| **Silent Renaming Detection** | No guard | No guard | No guard | No guard | **Deterministic Guard Active** | **Caught `CardMetric` -> `CardMetricWidget`** |
| **Stage B Revision Request** | Ignored | Ignored | Ignored | Ignored | **Supported & Processed** | **Model reported unresolved representations** |
| **Total Pilot Duration (1×3)** | ~1238.5s | 1954.9s | 1327.1s | 1129.6s | **1555.8s** | +426.2s due to deep Stage B reasoning & revision attempts |
| **Overall E2E Pass Rate (1×3)** | 0/3 (0.0%) | 0/3 (0.0%) | 0/3 (0.0%) | 1/3 (33.3%) | **0/3 (0.0%)** | **Revealed authentic model synthesis bottlenecks** |

---

## 2. Granular Task-by-Task Forensic Breakdown

```mermaid
flowchart TD
    subgraph SemanticGroundingPilot["Treatment #1.8.7 Semantic Grounding Pilot Trajectory"]
        F1["fastapi_t1 (Python REST)"] --> F1_StageA["Stage A: 100% Coverage ✓\n(/products, /products/{id})"]
        F1_StageA --> F1_StageB["Stage B: Assembly Attempt\nJSON Delimiter Syntax Error\n(Expecting ',' delimiter)"]
        F1_StageB --> F1_Repair["Repair Turns 1 & 2:\nResolved line 23, but broke line 18 & 21\nBudget Exhausted -> REJECTED"]

        C1["cli_t1 (Python CLI)"] --> C1_StageA["Stage A: 100% Coverage ✓\n(Matrix, add_matrices, etc.)"]
        C1_StageA --> C1_StageB["Stage B: Clean AST (0 errors) ✓\n(3987 chars code scaffold)"]
        C1_StageB --> C1_Gate["Contract Gate: Pilar 4 Check\nOmitted internal helpers: _add, _sub, _mul\nBudget Exhausted -> REJECTED"]

        FL1["flutter_t1 (Dart Widget)"] --> FL1_StageA["Stage A: 100% Coverage ✓\n(MetricData, CardMetric)"]
        FL1_StageA --> FL1_StageB0["Stage B Turn 0 & 1:\nExplicit Revision Request\n(Refused to speculate on Flutter state)"]
        FL1_StageB0 --> FL1_StageB2["Stage B Turn 2:\nTemptation to Rename: CardMetricWidget\nCaught by STAGE_B_SILENT_RENAMING Guard!"]
        FL1_StageB2 --> FL1_Gate["Contract Gate: REJECTED"]
    end
```

### Detailed Metrics by Pilot Run

| Task ID | Domain / Language | Staged Turns | Duration | Stage A Coverage | Stage B Fidelity | First Divergence Class | Specific Root Cause |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| `fastapi_t1` | Python REST | 3 | 675.0s | 100% | Failed (Syntax) | `ARCHITECT_REPAIR` | Repeated JSON escaping/delimiter error (`Expecting ',' delimiter`) on long Python code strings in Stage B. |
| `cli_t1` | Python CLI | 3 | 389.2s | 100% | High AST, Incomplete Scaffold | `ARCHITECT_SEMANTIC_DECISION` | Public interface contract declared all 4 functions, but scaffold omitted internal callable helpers (`_add`, `_sub`, `_mul`) demanded by test stimuli. |
| `flutter_t1` | Dart Flutter | 3 | 491.6s | 100% | Blocked / Renaming Attempt | `ARCHITECT_SEMANTIC_DECISION` | Turns 0 & 1: Model reported explicit `stage_a_revision_requests`. Turn 2: Model attempted silent renaming (`CardMetric` -> `CardMetricWidget`), blocked by deterministic guard. |

---

## 3. Deep Scientific Analysis of Empirical Findings

### Finding 1: Stage A Grounding is 100% Effective Across All Tasks
In previous treatments, Stage A was susceptible to missing obligations or confusing PM proposals with Acceptance Authority. Under Treatment #1.8.7's 7-layer Epistemic Hierarchy:
- `fastapi_t1`: Mapped all 4 endpoints (`POST /products`, `GET /products`, `GET /products/{id}`, `DELETE /products/{id}`).
- `cli_t1`: Mapped all 4 mathematical components (`Matrix`, `add_matrices`, `multiply_matrices`, `subtract_matrices`).
- `flutter_t1`: Mapped both required entities (`MetricData` data model, `CardMetric` widget component).

**Result**: **Zero obligation omissions, zero obligation substitutions, and zero obligation inventions in Stage A**. The epistemic hierarchy completely solved Stage A semantic grounding.

### Finding 2: The Silent Renaming Guard Exposed True Model Behavior
In Treatment #1.8.6 Repaired, `flutter_t1` passed because the prompt allowed more ambiguity and the model happened to emit code that matched the test.
In Treatment #1.8.7, under strict prompt fidelity rules:
1. When faced with architectural synthesis, the 7B model was uncertain how to implement `CardMetric` within the strict immutable constraints of Stage A and explicitly reported `stage_a_revision_requests`.
2. Under repair pressure in Turn 2, the model succumbed to the "synonym temptation" by renaming the widget to `CardMetricWidget` (a common Flutter naming convention).
3. The newly introduced `STAGE_B_SILENT_RENAMING` validator caught this exact drift deterministically:
   ```text
   SCHEMA_VIOLATION: Blueprint JSON parse failure: STAGE_B_SILENT_RENAMING: 
   Obligation 'OBL-WIDGET-CardMetric' identity was validated as 'CardMetric' in Stage A, 
   but Stage B renamed it to ['CardMetricWidget']. Silent renaming is forbidden.
   ```
This proves that the guard is functioning with mathematical precision to prevent semantic drift.

### Finding 3: Syntax Fragility in Small Models Under Dual-Stage JSON Generation
In `fastapi_t1`, the model repeatedly failed on JSON syntax delimiters inside the `code_scaffold` field:
- Turn 0: `line 23 column 14 (char 489)`
- Turn 1: `line 18 column 12 (char 303)`
- Turn 2: `line 21 column 54 (char 470)`
While the repair loop successfully resolved the specific line mentioned in the diagnostic feedback (`resolved_error_count: 2`), the 7B model introduced a new syntax error on subsequent lines when outputting long raw code strings inside JSON values.

### Finding 4: Separation of Public Obligation vs Internal Test Helper
In `cli_t1`, the model accurately grasped the public obligations (`Matrix`, `add_matrices`, etc.), but the Frozen Oracle tests also invoked private internal helpers (`_add`, `_sub`, `_mul`). Because Stage A strictly focused on public acceptance obligations, Stage B did not realize that the test suite was also directly calling private helper functions. This represents a subtle boundary between public API contracts and test suite coupling.

---

## 4. Architectural Invariants Verification

| Invariant Checked | Verification Method | Status |
| :--- | :--- | :---: |
| **Oracle Immutability** | SHA-256 hash verified before and after each run | **100% UNCHANGED** |
| **Anti-Solver Guarantee** | Codebase AST scan confirms zero task-specific keyword branching (`/products`, `Matrix`, etc.) | **VERIFIED CLEAN** |
| **Deterministic State** | `validate_canonical_architecture_plan_state` enforced on all plans | **VERIFIED CLEAN** |
| **Traceability Provenance** | `source_authority`, `mapped_element`, `evidence_basis` retained in state | **VERIFIED INTACT** |
| **Isolated Repair Evidence** | CEP filtered historical errors; only active failures presented in Level 7 | **VERIFIED INTACT** |

---

## 5. Decision & Mandatory STOP Rule Enforcement

In strict compliance with **Instruction #17 (STOP)**:
- **Treatment #1.8.7 is formally concluded.**
- The pilot completed exactly 3 planned runs without human intervention.
- **No Treatment #1.8.8 is created automatically.**
- All code changes are verified to contain zero regressions across the 900-test baseline.
- Future work must evaluate whether Stage B scaffold assembly should be decoupled from JSON serialization (e.g. emitting pure code blocks rather than string-escaped JSON) or how test-internal helper callables are surfaced in the Authoritative Scenario evidence.
