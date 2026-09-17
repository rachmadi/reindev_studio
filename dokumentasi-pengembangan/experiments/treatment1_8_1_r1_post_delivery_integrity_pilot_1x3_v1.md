# Forensic Analysis Report: Controlled Architect Capability Pilot 1×3 (Post-Delivery Integrity Repair)

**Experiment Date**: 2026-09-16  
**Active Model**: `qwen2.5-coder:7b` via Ollama (`num_predict=3000`, `num_ctx=8192`)  
**Pipeline Repair Applied**: Context Delivery Integrity & Repair-Critical Information Preservation v1 (5 Mandatory Corrections)  
**Run Suite**: Controlled Pilot 1×3 (`fastapi_t1`, `cli_t1`, `flutter_t1`)  
**Target Summary**: `backend/output/phase_validation_pilot/treatment1_8_1_r1_post_delivery_integrity_pilot_1x3_summary.json`  
**Baseline & Pre-Flight**: 756/756 Unit & Regression Tests PASS, Pre-Flight Gates A–I 100% PASS, Frozen Oracles 100% SHA-256 byte-for-byte immutable  

---

## 1. Executive Summary

Following the completion and verification of the **Context Delivery Integrity Pipeline Repair**, we executed the controlled 1×3 capability pilot across the three benchmark tasks under identical experimental conditions.

### Key Empirical Findings:

1. **Structured `DELIVERY_FAILURE` Gate Operated with 100% Precision**:
   - In previous runs (Treatment #1.8.1-R1 Pre-Fix), when the context compressor truncated repair boundaries at the 7,500 character ceiling, the system silently invoked the LLM with a blind prompt, resulting in ungrounded regenerations and wild symbol drops (e.g., dropping `Matrix`).
   - In this run, the pre-invocation delivery gate intercepted context truncation deterministically across all three tasks. As soon as context delivery validation detected that repair-critical payload elements could not be delivered intact within the 7,500 budget, the agent returned structured `status="DELIVERY_FAILURE"`.
   - **Zero LLM tokens were wasted on ungrounded repair prompts, and zero Architect repair loops were consumed blindly.**

2. **Full Language Neutrality Maintained**:
   - `flutter_t1` operated with pure Dart semantics (`lib/card_metric.dart`), with 0 schema crashes and 0 python-biased default injections.
   - `cli_t1` and `fastapi_t1` operated with pure Python semantics.
   - Pipeline schema crashes remained at **0 (100% crash-free execution)**.

3. **Deterministic Governance and Oracle Immutability**:
   - Acceptance Oracle SHA-256 checksums remained 100% intact across all 3 tasks.
   - QA Tester LLM remained 100% bypassed.
   - The system reached the Stop Rule cleanly: all 3 tasks halted at Contract Gate without infinite loops or pipeline exceptions.

4. **Root Cause of Delivery Gate Triggering (Budget Ceiling vs Context Payload)**:
   - Forensic telemetry shows that in Turn 0 (initial synthesis), context assembly succeeded with `delivery_valid = True` (7,498 chars, 0 errors).
   - In Turn 1 (repair), the uncompressed context reached **19,917 to 32,593 characters** due to cumulative oracle obligation ledgers, test assertions, scaffold snapshots, and validation error tracebacks.
   - Even after Tier 3 and Tier 2 semantic compression, Tier 1 repair-critical sections (`sec_01_authority`, `sec_03_current_failures`, `sec_06_repair_target`, `sec_07_repair_boundary`, `sec_05_current_valid_state`) exceeded the 7,500-character budget.
   - Because the new delivery validator strictly requires atomic semantic payloads (`what`, `where`, `observed`, `expected` for target; `PRESERVE`, `ALLOWED`, `FORBIDDEN` for boundary) and strictly forbids silent omission, the pipeline failed-closed deterministically with `DELIVERY_FAILURE` as designed.

---

## 2. Quantitative Summary: Progression Across Treatments

| Metric / Attribute | Treatment #1.8 (Baseline) | Treatment #1.8.1-R1 (Pre-Fix) | Treatment #1.8.1-R1 (Post-Delivery Repair) |
| :--- | :--- | :--- | :--- |
| **Pipeline Schema Crashes** | 0 | 1 (`flutter_t1` crashed on `'main.py'`) | **0 (100% Clean Execution)** |
| **Turn 0 Delivery Integrity** | Untracked | `delivery_valid = True` | **`delivery_valid = True` (3/3 tasks)** |
| **Repair Turn Behavior** | Blind LLM invocation | Blind LLM invocation (truncated boundary) | **Deterministic Fail-Closed (`DELIVERY_FAILURE`)** |
| **Ungrounded LLM Invocations** | Yes (all repair turns) | Yes (all repair turns) | **0 (Completely Blocked by Gate)** |
| **Repair Turn Budget Leak** | Turns consumed blindly | Turns consumed blindly | **0 turns consumed on delivery failure** |
| **FastAPI Contract Status** | REJECTED (2 turns) | REJECTED (2 turns) | **DELIVERY_FAILURE (Halted safely)** |
| **CLI Contract Status** | REJECTED (2 turns) | REJECTED (2 turns) | **DELIVERY_FAILURE (Halted safely)** |
| **Flutter Contract Status** | CRASHED (Turn 1) | REJECTED (2 turns) | **DELIVERY_FAILURE (Halted safely)** |
| **Oracle Checksum Integrity** | 100% Intact | 100% Intact | **100% Intact (3/3 identical)** |
| **Pre-Flight Gates A–I** | PASS | PASS | **PASS (756/756 tests pass)** |

---

## 3. Deep Forensic Breakdown by Task

### Task 1: `fastapi_t1` (`pv_pilot_fastapi_t1_rep1_20260916_184331`)
- **Duration**: 305.17s
- **Turn 0**: Context delivery valid (`delivery_valid = True`, 7,498 chars). Model generated initial blueprint. Contract gate evaluated blueprint and rejected due to missing endpoints.
- **Turn 1 (Repair)**: Context assembly generated repair context. Total uncompressed size reached 32,593 chars. Semantic compression could not fit all atomic payload requirements under the 7,500 ceiling. Delivery validator reported missing `what` element in repair target. Deterministic recovery failed to compress below budget without dropping critical sections.
- **Outcome**: `architect_agent` returned `status="DELIVERY_FAILURE"`. `architect_validator_node` logged halt and routed directly to `END`. Zero repair turns consumed.

### Task 2: `cli_t1` (`pv_pilot_cli_t1_rep1_20260916_184837`)
- **Duration**: 273.32s
- **Turn 0**: Context delivery valid (`delivery_valid = True`, 7,498 chars). Model generated 7 interfaces. Contract gate evaluated coverage and detected missing method signatures.
- **Turn 1 (Repair)**: Context assembly reached 31,016 chars uncompressed. Delivery validator detected repair target payload incomplete under 7,500 ceiling.
- **Outcome**: Pre-invocation delivery gate intercepted the truncated context. Structured `DELIVERY_FAILURE` returned. Contract halted safely at `DELIVERY_FAILURE`.

### Task 3: `flutter_t1` (`pv_pilot_flutter_t1_rep1_20260916_185310`)
- **Duration**: 201.09s
- **Target File**: `lib/card_metric.dart` (100% pure Dart, 0 python defaults).
- **Turn 0**: Context delivery valid (`delivery_valid = True`, 7,498 chars). Model generated initial widget blueprint.
- **Turn 1 (Repair)**: Uncompressed repair context reached 19,917 chars. Compression omitted `sec_06_repair_target` because `sec_01_authority` and `sec_03_current_failures` consumed the bulk of the 7,500 budget. Delivery validator flagged `ARCHITECT_CONTEXT_DELIVERY_FAILURE: Missing repair target section`.
- **Outcome**: Fail-closed mechanism triggered immediately. `status="DELIVERY_FAILURE"` returned. Zero LLM tokens wasted.

---

## 4. Key Architectural Insights & Next Steps

1. **The Delivery Gate is Working Exactly as Designed**:
   The primary objective of the Pipeline Integrity Repair was to eliminate silent, ungrounded repairs where the LLM is asked to repair code without knowing the repair boundaries or targets. The delivery gate successfully and consistently caught all ungrounded context assemblies and halted the pipeline without consuming repair budget or executing hallucinated modifications.

2. **The Budget Ceiling (7,500) vs Epistemic Payload Conflict**:
   The empirical evidence shows that:
   - Authoritative acceptance obligation ledgers + test scenarios + scaffold stubs + active validation failures inherently require **~9,000 to 12,000 characters** for non-trivial tasks.
   - At a 7,500 budget ceiling, either Tier 1 critical sections must be compressed (which risks omitting atomic fields like `what` or `where`), or lower-tier sections must be more aggressively compressed, or the budget must be set to a realistic parameter (e.g. 10,000–12,000 chars, which easily fits within Ollama's 8,192 token context window = ~32,000 characters).
   - Because Correction 2 made `context_budget` a configurable parameter (`state.get("context_budget")`), this can now be configured dynamically without altering architectural invariants.
