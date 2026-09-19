# Treatment #1.8.10 — 1×3 Pilot Benchmark Report

**Benchmark Run Date**: 2026-09-18  
**Pipeline Version**: 1.8.3 | **Governance Version**: 1.6  
**Active Model**: `qwen2.5-coder:7b` (Ollama, local)  
**Execution Mode**: Controlled Phase-End Validation Pilot (1×3 Full Matrix)  
**Operating Constraints Observed**:
- ✓ Zero code modification during run.
- ✓ No reruns of failed cases (no tuning, no manual repairs).
- ✓ 3-minute periodic status reporting maintained throughout execution.

---

## 1. Executive Summary & Acceptance Evaluation

| Case | Archetype | Target Language | Result | Primary Acceptance | Secondary Acceptance |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Case 1: FastAPI** | Web API (`fastapi_t1`) | Python | **FAIL** | NOT MET | **MET** |
| **Case 2: CLI** | CLI Tool (`cli_t1`) | Python | **PASS** | **MET (100%)** | **MET** |
| **Case 3: Flutter** | Mobile Widget (`flutter_t1`) | Dart | **FAIL** | NOT MET | **MET** |

### Acceptance Verdicts:
1. **Primary Acceptance**:
   - `FastAPI PASS`: **FAIL** (0/5 oracle tests passed due to LLM Pydantic schema divergence: 422 vs 201).
   - `CLI PASS`: **PASS (100%)** (5/5 oracle tests passed, Reviewer APPROVED, converged in 2 loops!).
   - `Flutter PASS`: **FAIL** (0/1 oracle tests passed due to LLM type error: `MaterialColor` passed to `String`).
   - Overall Primary: **PARTIAL (1/3 PASS)**.
2. **Secondary Acceptance**:
   - **No Oracle Mutation**: **MET (100%)** — All 3 cases verified against frozen SHA-256 pre- and post-execution.
   - **No Regression**: **MET (0 regressions)** across all repair iterations.
   - **No Task-Specific Solver**: **MET** — Universal structural compatibility logic used without hardcoding.
   - **Fail-Closed Preserved**: **MET** — Pipeline strictly rejected non-compliant code; zero false approvals.
   - **No Context Delivery Failure**: **MET (0 failures)** — 100% `delivery_valid` across all phases and turns.

---

## 2. Mandatory Metric Matrix (14/14 Fields)

| # | Mandatory Metric | Case 1: FastAPI (`fastapi_t1`) | Case 2: CLI (`cli_t1`) | Case 3: Flutter (`flutter_t1`) |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **V0 Result** | **PASS** (Turn 0 repaired to Turn 1) | **PASS** (Turn 0 repaired to Turn 1) | **PASS** (Turn 0, 2 items) |
| **2** | **PM Result** | **PASS** (1 turn, 0 violations) | **PASS** (1 turn, 0 violations) | **PASS** (1 turn, 0 violations) |
| **3** | **Architect Turns** | **2 turns** (Turn 0 FAIL, Turn 1 PASS) | **1 turn** (Turn 0 PASS) | **3 turns** (Turn 0-1 FAIL, Turn 2 PASS) |
| **4** | **Contract Status** | **FROZEN** | **FROZEN** | **FROZEN** |
| **5** | **Contract Coverage** | **4/4 (100%)** | **4/4 (100%)** | **1/1 (100%)** |
| **6** | **Structural Compatibility** | `is_structurally_compatible = True` | `is_structurally_compatible = True` | `is_structurally_compatible = True` |
| **7** | **Behavioral Evidence Status** | `BEHAVIOR_NOT_PROVABLE` | `BEHAVIOR_NOT_PROVABLE` | `BEHAVIOR_NOT_PROVABLE` |
| **8** | **Developer Reached** | **REACHED** (Turn 1) | **REACHED** (Turn 0) | **REACHED** (Turn 0) |
| **9** | **Developer Repair Loops** | 5 loops consumed (3 generations) | **2 loops consumed** (Converged!) | 5 loops consumed (3 generations) |
| **10** | **Oracle Result** | **0/5 PASS** (5 failed, HTTP 422) | **5/5 PASS (100%)** | **0/1 PASS** (1 failed, type error) |
| **11** | **Reviewer Result** | **FAIL** | **APPROVED (100%)** | **FAIL** |
| **12** | **Regressions** | **0 regressions** | **0 regressions** | **0 regressions** |
| **13** | **Context Delivery Failures** | **0 failures** (`delivery_valid = True`) | **0 failures** (`delivery_valid = True`) | **0 failures** (`delivery_valid = True`) |
| **14** | **Oracle SHA Verification** | `a1db9bb1...` (**INTACT**) | `0bd5b598...` (**INTACT**) | `4589e15c...` (**INTACT**) |

---

## 3. In-Depth Case Analysis

### Case 1: FastAPI (`fastapi_t1`) — LLM Schema Divergence
- **Pipeline Behavior**: V0, PM, and Architect executed with complete fidelity. Contract Gate properly admitted the scaffold stub and transitioned to Developer.
- **Root Cause of Failure**:
  - The model `qwen2.5-coder:7b` generated Pydantic models where `description`, `price`, and `stock` were mandatory fields without default values.
  - The oracle test sent minimal payloads: `{"name": "Widget", "quantity": 15}`.
  - FastAPI returned `HTTP 422 Unprocessable Entity` on all POST requests.
  - While diagnostic feedback was delivered to Developer across loops 1 and 2, the small model failed to relax required Pydantic fields to optional/defaults.
- **Governance Assessment**: Fail-closed preserved. The pipeline correctly refused to approve failing code.

### Case 2: CLI (`cli_t1`) — Major Breakthrough & Full Convergence
- **Previous Bottleneck (Treatment #1.5 / Gate 19)**:
  - Minimal scaffold stubs were previously judged as `is_fully_compatible = False` due to runtime test failures (`BEHAVIOR_NOT_PROVABLE`), causing an immediate drop before Developer could even attempt implementation.
- **Treatment #1.8.10 Resolution**:
  - The decoupled Contract Gate checked `is_structurally_compatible = True` on Turn 0.
  - Developer received the scaffold, analyzed the initial sandbox failures, and in **Loop 1** produced code passing all 5 test cases (`5/5 PASS`).
  - Reviewer deterministically evaluated all criteria and gave **APPROVED (100%)**.
  - Total duration: 399.0s.

### Case 3: Flutter (`flutter_t1`) — Type Compatibility Divergence
- **Pipeline Behavior**:
  - V0 produced a valid specification on Turn 0.
  - PM validated cleanly.
  - Architect underwent 2 repair turns to align the contract schema, reaching PASS on Turn 2.
  - Scaffold admitted immediately to Developer.
- **Root Cause of Failure**:
  - The Developer declared the `color` property in `MetricData` as `final String color;`.
  - The frozen oracle test passed `Colors.blue` (`MaterialColor` / `Color`).
  - Dart compiler failed with:
    ```
    test/card_metric_test.dart:14:79: Error: The argument type 'MaterialColor' can't be assigned to the parameter type 'String'.
    ```
  - Despite diagnostic extraction identifying compilation errors, `qwen2.5-coder:7b` repeatedly retained `final String color;` across its repair budget.
- **Governance Assessment**: Strict fail-closed maintained. Zero false approvals.

---

## 4. Key Architectural Findings & Next Steps

1. **Deterministic Pipeline Integrity**:
   - The decoupling of structural vs. behavioral compatibility in Treatment #1.8.10 completely unblocked the CLI case, proving the core hypothesis of the architectural repair.
   - Zero oracle mutations occurred, zero context delivery failures occurred, and zero regressions were introduced.
2. **LLM Implementation Boundary**:
   - The remaining failures in FastAPI (Pydantic schema field strictness) and Flutter (Dart parameter type strictness) are classical LLM code generation issues, not pipeline structural defects.
   - Potential future enhancements (Treatment #1.9) could include schema-guided type hinting in Developer repair prompts (e.g., explicitly passing AST parameter types inferred from the oracle).
