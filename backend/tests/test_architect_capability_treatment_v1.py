"""
Unit Tests for Treatment #1.8: Universal Acceptance-Grounded Architectural Synthesis v1
ReinDev Studio — Iterasi 6

Tests:
1. 5-Layer Stratified Input Grounding (Layers A-E in Decision Context).
2. Epistemic Stratification of V0 (FACT, INTERPRETATION, ASSUMPTION, UNRESOLVED).
3. Authoritative Acceptance Obligations & Scenarios in Layer A (WHAT vs HOW).
4. Artifact Purity Enforcement (Zero test files in implementation file_tree).
5. Observable Negative Behavior Representation Guidance (No prescriptive HOW).
6. 10-Point Checklist Reasoning Guidance (Validators determine REALITY).
7. Preservative Repair Mode Delegation (Once Proven, Lock It).
8. Cross-Archetype Generality across 5 distinct domains.
"""

import pytest
from typing import Dict, Any, List

from backend.context_hardening import (
    build_architect_decision_context,
    build_architect_repair_context,
    extract_authoritative_oracle_interfaces,
)
from backend.agents.architect import ARCHITECT_SYSTEM_PROMPT


class TestArchitectGroundingLayersV1:
    """Test 5-Layer Stratified Input Grounding in build_architect_decision_context."""

    def test_layer_a_acceptance_authority_extraction(self):
        """Layer A must present Oracle facts, obligations, and scenarios as Acceptance Authority."""
        state = {
            "task": "Build calculator CLI",
            "contract_status": "DRAFT",
            "contract": {
                "interface_contracts": [{"identifier": "add_numbers"}],
            },
            "test_files": {
                "test_main.py": (
                    "import main\n"
                    "def test_calculate():\n"
                    "    assert main.calculate(2, 3) == 5\n"
                    "def test_calculate_invalid():\n"
                    "    import pytest\n"
                    "    with pytest.raises(ValueError):\n"
                    "        main.calculate('bad', 3)\n"
                )
            }
        }
        ctx, telem = build_architect_decision_context(state)

        # Layer A verification
        assert "[5] AUTHORITATIVE ACCEPTANCE ORACLE INTERFACES (ORACLE_FACT" in ctx
        assert "[ORACLE_FACT] calculate" in ctx
        assert "Acceptance Authority" in ctx or "Ground Truth" in ctx
        assert "FORBIDDEN from altering, removing, or omitting" in ctx

    def test_layer_b_requirement_evidence_epistemic_stratification(self):
        """Layer B must clearly distinguish FACT, INTERPRETATION, ASSUMPTION, and UNRESOLVED."""
        state = {
            "task": "Build telemetry pipeline",
            "v0_requirement_model": {
                "constructibility_status": "HIGH",
                "requirements": [
                    {"category": "CORE", "description": "Ingest JSON metrics stream"}
                ],
                "interpretations": [
                    {"description": "Stream requires buffering for burst handling"}
                ],
                "assumptions": [
                    {"description": "Network latency is below 50ms"}
                ],
                "open_ambiguities": [
                    {"description": "Maximum payload size unspecified"}
                ]
            }
        }
        ctx, telem = build_architect_decision_context(state)

        assert "[2] V0 APP REQUIREMENTS (FACT — grounded in user task)" in ctx
        assert "Core Requirements (FACT" in ctx
        assert "Ingest JSON metrics stream" in ctx
        assert "Interpretations (INTERPRETATION" in ctx
        assert "Stream requires buffering" in ctx
        assert "Assumptions (ASSUMPTION" in ctx
        assert "Network latency is below 50ms" in ctx
        assert "Unresolved Gaps (UNRESOLVED" in ctx
        assert "Maximum payload size unspecified" in ctx

    def test_layer_c_pm_proposal_non_authority_notice(self):
        """Layer C must explicitly declare PM Proposal as design reference, NOT acceptance authority."""
        state = {
            "task": "Build task manager",
            "contract_status": "DRAFT",
            "contract": {
                "interface_contracts": [{"identifier": "create_task"}],
                "data_models": [{"model_name": "Task"}]
            }
        }
        ctx, telem = build_architect_decision_context(state)

        assert "[4] PROPOSED CONTRACT SPECIFICATION (PM_PROPOSAL" in ctx
        assert "PM_PROPOSAL" in ctx
        assert "NOT acceptance authority" in ctx
        assert "design information only" in ctx or "design reference only" in ctx

    def test_layer_e_preserved_state_locked_invariants(self):
        """Layer E must present locked invariants as FORBIDDEN to mutate."""
        state = {
            "task": "Refactor service",
            "locked_invariants": {
                "INV-01": {"status": "PROVEN", "description": "Auth middleware must not be bypassed"}
            },
            "previous_passed_tests": [{"test_name": "test_auth_guard"}]
        }
        ctx, telem = build_architect_decision_context(state)

        assert "[6] PROVEN INVARIANTS (LOCKED — mutation FORBIDDEN)" in ctx
        assert "INV-01" in ctx
        assert "Auth middleware must not be bypassed" in ctx
        assert "test_auth_guard" in ctx


class TestArtifactPurityAndNegativeGuidance:
    """Test artifact purity and observable negative behavior representation guidance."""

    def test_output_contract_artifact_purity_mandate(self):
        """Section 11 must mandate artifact purity (no test files in file_tree)."""
        state = {"task": "Build product service"}
        ctx, _ = build_architect_decision_context(state)

        assert "ARTIFACT PURITY" in ctx
        assert "file_tree dan files HANYA untuk modul implementasi" in ctx or "zero test files in file_tree" in ctx
        assert "DILARANG" in ctx or "zero test files" in ctx

    def test_output_contract_negative_behavior_representation(self):
        """Section 11 must guide negative behavior representation without prescribing implementation HOW."""
        state = {"task": "Build order service"}
        ctx, _ = build_architect_decision_context(state)

        assert "OBSERVABLE NEGATIVE BEHAVIOR" in ctx
        assert "Scaffolds must represent the required observable negative behavior" in ctx
        assert "Do not prescribe implementation-specific mechanisms" in ctx

    def test_10_point_checklist_reasoning_guidance_notice(self):
        """The 10-point checklist must include the notice that validators determine reality."""
        state = {"task": "Build auth service"}
        ctx, _ = build_architect_decision_context(state)

        assert "PRE-SEAL SELF-CONSISTENCY CHECKLIST" in ctx
        assert "Architect reasoning guidance" in ctx
        assert "NOT an acceptance authority" in ctx
        assert "Deterministic validators determine REALITY" in ctx

    def test_system_prompt_scaffold_and_purity_principles(self):
        """ARCHITECT_SYSTEM_PROMPT must incorporate artifact purity and negative scenario principles."""
        assert "OBSERVABLE NEGATIVE BEHAVIOR" in ARCHITECT_SYSTEM_PROMPT
        assert "ARTIFACT PURITY" in ARCHITECT_SYSTEM_PROMPT
        assert "Do not prescribe implementation-specific mechanisms" in ARCHITECT_SYSTEM_PROMPT
        assert "Acceptance Authority (WHAT)" in ARCHITECT_SYSTEM_PROMPT


class TestRepairModePreservationDelegation:
    """Test that repair turns delegate cleanly to build_architect_repair_context."""

    def test_repair_turn_delegation(self):
        """When revision count > 0, decision context must delegate to repair context."""
        state = {
            "task": "Fix service",
            "contract_revision_count": 1,
            "architecture_plan": "class Service:\n    pass\n",
            "locked_invariants": {
                "INV-HEALTH": {"status": "PROVEN", "description": "GET /health must return 200"}
            }
        }
        ctx, telem = build_architect_decision_context(state)

        # Must contain repair sections from build_architect_repair_context
        assert "[1] IMMUTABLE ACCEPTANCE AUTHORITY" in ctx
        assert "[2] ACCEPTANCE OBLIGATION LEDGER" in ctx
        assert "[4] LOCKED/PROVEN STATE" in ctx
        assert "INV-HEALTH" in ctx


class TestCrossArchetypeGenerality:
    """Verify context generation operates universally across 5 distinct domains without solver bias."""

    @pytest.mark.parametrize("domain,task,interfaces", [
        ("REST_API", "Build inventory REST API", ["get_items", "add_item"]),
        ("CLI_TOOL", "Build matrix math CLI", ["dot_product", "matrix_inverse"]),
        ("MOBILE_UI", "Build metric summary card widget", ["CardMetricWidget"]),
        ("DATA_PIPELINE", "Build ETL transformation pipeline", ["extract_records", "transform_data"]),
        ("EMBEDDED_SYS", "Build sensor reader daemon", ["read_sensor", "calibrate_offset"]),
    ])
    def test_domain_generality_clean_generation(self, domain: str, task: str, interfaces: List[str]):
        state = {
            "task": task,
            "contract_status": "DRAFT",
            "contract": {
                "task_intent": {"domain": domain},
                "interface_contracts": [{"identifier": ifc} for ifc in interfaces],
            },
            "v0_requirement_model": {
                "constructibility_status": "HIGH",
                "requirements": [{"category": "FUNC", "description": f"Perform {interfaces[0]}"}],
                "interpretations": [{"description": f"Requires {interfaces[0]} handler"}],
                "assumptions": [{"description": "Stateless execution"}],
                "open_ambiguities": [{"description": "Concurrency model unspecified"}]
            }
        }
        ctx, telem = build_architect_decision_context(state)

        assert len(ctx) > 200
        assert "[1] USER INTENT" in ctx
        assert task in ctx
        assert "[2] V0 APP REQUIREMENTS (FACT — grounded in user task)" in ctx
        assert "[4] PROPOSED CONTRACT SPECIFICATION (PM_PROPOSAL" in ctx
        assert "[11] OUTPUT CONTRACT & REASONING GUIDANCE" in ctx
        assert telem.get("context_size", 0) > 0
        assert telem.get("integrity_violations_detected", 0) == 0
