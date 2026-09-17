# Forensic Analysis Report: Controlled Architect Capability Pilot 1×3 (Post-Pipeline Integrity Fix)

**Experiment Date**: 2026-09-16  
**Active Model**: `qwen2.5-coder:7b` via Ollama (`num_predict=3000`, `num_ctx=8192`)  
**Pipeline Fix Baseline**: Removal of Language-Biased Schema Default (`authoritative_target_file = "main.py"`) from `backend/blueprint_schema.py`  
**Run Suite**: Controlled Pilot 1×3 (`fastapi_t1`, `cli_t1`, `flutter_t1`)  
**Target Summary**: `backend/output/phase_validation_pilot/treatment1_8_1_r1_post_pipeline_fix_pilot_1x3_summary.json`  
**Pre-Flight Verification**: 741/741 Pytest PASS, Gates A–I 100% PASS, Frozen Oracle SHA-256 byte-for-byte immutable  

---

## 1. Executive Summary

Following the completion of the **Pipeline Integrity Fix** (which eliminated the hardcoded default `"main.py"` from `ArchitecturalBlueprint`), we executed the controlled 1×3 capability pilot on `fastapi_t1`, `cli_t1`, and `flutter_t1`. 

### Key Empirical Outcomes:
1. **Pipeline Integrity Defect 100% Eliminated**:
   In the previous pilot (R1), `flutter_t1` suffered a catastrophic crash in Turn 1 repair with `Value error, authoritative_target_file 'main.py' tidak ditemukan dalam kamus 'files'`. In this post-fix run, `flutter_t1` operated with strict language neutrality: `authoritative_target_file` remained `"lib/card_metric.dart"`, passing Pydantic cross-field validation deterministically. There were **zero schema crashes** and **zero pipeline exceptions** across all 3 tasks.
2. **Deterministic Contract Gate Governance Enforced**:
   All 3 tasks reached the Contract Gate (P0-2.1) without bypassing governance. All 3 halted deterministically when the Architect failed to achieve a FROZEN contract within the 2-revision budget (`contract_status: "REJECTED"`).
3. **Major Confounder Unveiled — Repair Boundary Context Truncation**:
   A forensic deep-dive into the context telemetry revealed that in **every single repair turn across all 3 tasks**, the repair context hit the 7,500 character ceiling (`context_size = 7502–7506`). Due to priority ordering in `compress_context_semantic`:
   - `[6] REPAIR TARGET` was **TRUNCATED/OMITTED**.
   - `[7] REPAIR BOUNDARY` (which explicitly defines ALLOWED vs FORBIDDEN actions, including the rule against dropping valid public symbols) was **COMPLETELY OMITTED**.
   - `[10] RAW DIAGNOSTICS` was **COMPLETELY OMITTED**.
   The telemetry logged `delivery_valid: False` with `ARCHITECT_CONTEXT_DELIVERY_FAILURE: Missing repair boundary (ALLOWED vs FORBIDDEN)`. Consequently, the model was forced to attempt repair without being informed of the forbidden boundaries, leading directly to the observed over-corrections (e.g. CLI dropping `Matrix`).

---

## 2. Quantitative Summary: Progression Across Treatments

| Metric / Attribute | Treatment #1.8 (Baseline) | Treatment #1.8.1-R1 (Pre-Pipeline Fix) | Treatment #1.8.1-R1 (Post-Pipeline Fix) |
| :--- | :--- | :--- | :--- |
| **Pipeline Schema Crashes** | 0 | 1 (`flutter_t1` crashed on `'main.py'`) | **0 (100% Clean Execution)** |
| **FastAPI AST Validity** | Broken (Dict/List distortion) | Valid AST (0 schema errors) | **Valid AST (0 schema errors)** |
| **FastAPI Interface Coverage** | 0/4 (0%) | 2/4 (50%) | **2/4 (50%)** |
| **CLI Obligation Coverage** | 0/4 | 4/4 (Turn 0) -> 0/4 (Turn 1–2) | **4/4 (Turn 0) -> 0/4 (Turn 1–2)** |
| **Flutter Schema Conformance** | Distorted schema | Crashed at Turn 1 repair | **Valid Dart Schema (0 errors, 2 turns repaired)** |
| **Flutter Target File Integrity** | Python-biased (`main.py`) | Injected `"main.py"` in repair | **Pure Dart (`lib/card_metric.dart`)** |
| **Oracle Checksum Integrity** | 100% Intact | 100% Intact | **100% Intact (3/3 identical)** |
| **Pre-Flight Gates A–I** | PASS | PASS | **PASS (741/741 tests pass)** |

---

## 3. Deep Forensic Breakdown by Task

### Task 1: `fastapi_t1` (`pv_pilot_fastapi_t1_rep1_20260916_175124`)
* **Duration**: 345.26s
* **V0 & PM**: Both PASSED (V0 resolved epistemic provenance in 1 iteration; PM produced valid draft contract).
* **Architect Iteration Trace**:
  * **Turn 0**: JSON decoding failure (`Expecting ',' delimiter: line 38 column 50`). Contract status: `REJECTED`, coverage: 0/4.
  * **Turn 1 (Repair)**: Model fixed JSON syntax error. Schema conformance passed (`blueprint_ast_validity: 0 errors`). However, model produced `interface_contracts: []` and an invalid data model name.
  * **Turn 2 (Repair)**: Model added 4 interface contracts (`test_create_product`, `test_delete_product`, `test_get_all_products`, `test_get_product_by_id`). Obligation coverage reached **2/4**. Missing: `HTTP GET /products/{id}` and `HTTP DELETE /products/{id}`. Scenario analysis detected absence of 404 conditional branches in scaffold.
  * **Outcome**: Budget exhausted (2 revisions). Contract halted safely at `REJECTED`.

### Task 2: `cli_t1` (`pv_pilot_cli_t1_rep1_20260916_175710`)
* **Duration**: 345.38s
* **V0 & PM**: Both PASSED.
* **Architect Iteration Trace**:
  * **Turn 0**: Model declared 7 interfaces (`Matrix`, `add_matrices`, `subtract_matrices`, `multiply_matrices`, `transpose_matrix`, `determinant_matrix`, `inverse_matrix`). Obligation coverage was **4/4 (100% COVERED)**!
  * **Contract Gate Finding**: Contract Gate Pilar 4 checked Acceptance Scenarios and detected that the frozen oracle test calls private helpers `_add(a, b)`, `_sub(a, b)`, `_mul(a, b)`, which were absent from the model's scaffold.
  * **Turn 1 (Repair)**: The model received the diagnostic about `_add`, `_sub`, `_mul`. Because `sec_07_repair_boundary` was truncated, the model did not receive the instruction `FORBIDDEN: Dropping previously compatible public interfaces`. The model performed an **over-correction**, replacing its entire interface contract with `['_add', '_sub', '_mul']` and dropping `Matrix`. As a result, public callable symbol `Matrix` was now missing, dropping coverage from 4/4 to 0/4.
  * **Turn 2 (Repair)**: Repeated Turn 1 contract. Budget exhausted. Halted at `REJECTED`.

### Task 3: `flutter_t1` (`pv_pilot_flutter_t1_rep1_20260916_180255`)
* **Duration**: 262.15s
* **V0 & PM**: Both PASSED on Turn 0.
* **Architect Iteration Trace**:
  * **Turn 0**: Model correctly emitted `authoritative_target_file: "lib/card_metric.dart"`. Coverage: 1/2.
    - Contract Gate diagnosed: `CALL_SHAPE_INCOMPATIBILITY: Symbol 'MetricData' constructor expected 0 positional argument(s), but proposed constructor accepts 3.`
  * **Turn 1 (Repair) — THE CRITICAL TEST**:
    - In the pre-fix pilot, Turn 1 crashed immediately with `Value error, authoritative_target_file 'main.py' tidak ditemukan dalam kamus 'files'`.
    - **In this post-fix run**: `lib/card_metric.dart` was preserved cleanly. Zero schema crash!
    - The model successfully read the diagnostic and converted the positional parameters to named parameters in Dart!
    - However, it omitted `'title'` and `'color'` from the named parameter set: `CALL_SHAPE_INCOMPATIBILITY: Symbol 'MetricData' constructor missing named argument(s): ['title', 'color']`.
  * **Turn 2 (Repair)**: Model attempted another revision but still missed `['title', 'color']` and omitted `model_name` in data model #1.
  * **Outcome**: Halted at `REJECTED` when budget reached 2 revisions.

---

## 4. Epistemic Classification of Findings

### FACT (Deterministically Verified by Trace Events):
1. **Pipeline Integrity Fix is 100% Effective**:
   Removing `default="main.py"` completely eliminated the cross-language schema bug. Flutter repaired through 2 iterations with `authoritative_target_file: "lib/card_metric.dart"` without error.
2. **Contract Gate Governance is Intact**:
   All 3 runs were halted at Contract Gate P0-2.1. Zero invalid code was passed to the Developer.
3. **Oracle Integrity is Uncompromised**:
   All 3 frozen oracles remained byte-for-byte identical to their pre-treatment baseline.
4. **Repair Context Truncation is Occurring**:
   Every repair prompt reached 7,502–7,506 characters against a 7,500 ceiling, causing `sec_06_repair_target`, `sec_07_repair_boundary`, `sec_08`, `sec_09`, and `sec_10` to be dropped from the prompt sent to the LLM.

### STRONG EVIDENCE:
1. **Model Over-Correction is Caused by Omission of the Repair Boundary**:
   In `cli_t1`, the model had 4/4 coverage in Turn 0. When told about missing helpers `_add`, it dropped `Matrix` in Turn 1. Had `sec_07_repair_boundary` (`FORBIDDEN: Dropping previously compatible public interfaces`) not been truncated, the model would have had explicit negative constraints preventing this regression.
2. **The 7B Model is Capable of Parameter Transformation in Dart**:
   In `flutter_t1`, the model responded to `constructor expected 0 positional argument(s)` by converting positional parameters to named parameters in Turn 1, demonstrating genuine architectural reactivity.

### INFERENCE:
1. If the repair boundary and specific diagnostic are preserved (by either re-ordering `ARCHITECT_REPAIR_PRIORITY_ORDER` or increasing `max_chars` to match the model's actual context window), the 7B model has a realistic probability of maintaining valid public interfaces while resolving localized mismatches.

### UNKNOWN:
1. Whether `qwen2.5-coder:7b` can deduce the exact constructor parameters `title` and `color` solely from the scenario stimulus without seeing the explicit raw diagnostic or oracle call site.

---

## 5. Architectural Answer to User Research Question

> **User Question**: *"Apakah remaining failure benar-benar berasal dari capability Architect, atau masih ada confounder lain?"*

### Synthesis:
1. **The Language Bias Confounder is DEAD**:
   The canonical schema defect where Pydantic injected `"main.py"` into non-Python tasks has been eradicated. The pipeline is now completely language-agnostic.
2. **A New Confounder Has Been Discovered (Context Assembly Budget Inversion)**:
   We discovered that the Architect repair context assembly suffers from a **semantic truncation bug**:
   - `sec_02_canonical_schema` (~3,000 chars) and `sec_05_current_valid_state` (~2,000 chars) consume the bulk of the 7,500-character budget.
   - The critical guidance sections—`[6] REPAIR TARGET` and `[7] REPAIR BOUNDARY`—are at the bottom of the priority order and get truncated.
   - The model is failing repair partly because it is **deprived of the repair boundaries** that prevent field dropping and over-correction.
3. **Genuine Capability Limits**:
   Even so, model capability plays a real role: in `fastapi_t1`, the model struggled with JSON delimiter syntax on Turn 0, and in `flutter_t1`, it missed two named parameters.

---

## 6. Decision & Recommendation on 3×3 Replication

### Strict Recommendation: **DO NOT PROCEED TO 3×3 YET**

### Rationale:
1. We have identified a deterministic defect in the repair context delivery (`ARCHITECT_CONTEXT_DELIVERY_FAILURE`). Running a 3×3 experiment (9 runs) under active context truncation would simply replicate the known truncation 9 times, consuming ~1 hour of GPU time without measuring true model capability.
2. The STOP RULE was correctly reached at the end of the 1×3 pilot.
3. Before running 3×3, we should address the context delivery priority inversion so that `REPAIR TARGET` and `REPAIR BOUNDARY` are guaranteed delivery to the model.

---

*Report prepared autonomously under Anti-Solver Governance and Verification Integrity Protocol.*
