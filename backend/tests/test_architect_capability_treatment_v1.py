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

        assert "OBSERVABLE BEHAVIOR" in ctx or "OBSERVABLE NEGATIVE BEHAVIOR" in ctx
        assert "Scaffolds must represent" in ctx
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
        assert "OBSERVABLE BEHAVIOR" in ARCHITECT_SYSTEM_PROMPT or "OBSERVABLE NEGATIVE BEHAVIOR" in ARCHITECT_SYSTEM_PROMPT
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


class TestTreatment181StructuralFidelityAndRepairPreservation:
    """
    Treatment #1.8.1: Universal Structural Blueprint Fidelity & Repair Preservation v1
    10 Deterministic Tests using Synthetic Generic Fixtures (Entity A, Interface X, Artifact Y, Scenario Z)
    with deliberate structural perturbations.
    """

    def test_01_obligation_to_representation_linkage(self):
        """Test 1: Acceptance obligations must map deterministically to architectural representations."""
        from backend.canonical_obligation import CanonicalObligation, ObligationKind

        syn_ob = CanonicalObligation(
            obligation_id="OBL-ALPHA-01",
            public_identity="operation_alpha",
            obligation_kind=ObligationKind.CALLABLE_INTERFACE.value,
            source_reference="test_synthetic.py",
            observable_behavior="operation_alpha(entity: EntityA) -> EntityA",
        )
        state = {
            "task": "Perform synthetic calculation",
            "contract_status": "DRAFT",
            "contract": {"interface_contracts": []},
            "frozen_oracle_path": "non_existent_path"
        }
        # Inject canonical obligation directly into format_relational_blueprint_state
        from backend.context_hardening import format_relational_blueprint_state
        rel_text = format_relational_blueprint_state(
            oracle_obs=[syn_ob],
            oracle_items=[],
            scenarios=[],
            contract=state["contract"],
            auth_file="artifact_alpha.py"
        )
        assert "operation_alpha" in rel_text
        assert "artifact_alpha.py" in rel_text
        assert "Relational Dependency Mapping:" in rel_text

    def test_02_interface_to_artifact_linkage(self):
        """Test 2: Every interface contract must link to a declared target artifact in files."""
        from backend.blueprint_schema import ArchitecturalBlueprint, BlueprintFileModule, BlueprintInterfaceContract

        # Deliberate perturbation: target_file 'artifact_missing.py' does NOT exist in files
        with pytest.raises(ValueError, match="tidak eksis dalam blueprint files"):
            ArchitecturalBlueprint(
                authoritative_target_file="artifact_alpha.py",
                file_tree=["artifact_alpha.py"],
                architecture_summary="Synthetic architecture",
                files={
                    "artifact_alpha.py": BlueprintFileModule(
                        file_path="artifact_alpha.py",
                        module_role="Core Module",
                        code_scaffold="def operation_alpha(): pass"
                    )
                },
                interface_contracts=[
                    BlueprintInterfaceContract(
                        identifier="operation_alpha",
                        target_file="artifact_missing.py"  # Perturbation
                    )
                ]
            )

    def test_03_identifier_preservation(self):
        """Test 3: Interface identifiers must be preserved without distortion across state transitions."""
        from backend.blueprint_schema import BlueprintInterfaceContract

        contract = BlueprintInterfaceContract(
            identifier="execute_synthetic_operation",
            target_file="artifact_main.py",
            route="/synthetic",
            method="POST"
        )
        # Verify identity is stable and unchanged
        d = contract.model_dump()
        assert d["identifier"] == "execute_synthetic_operation"
        assert d["target_file"] == "artifact_main.py"
        assert d["method"] == "POST"

    def test_04_target_artifact_preservation(self):
        """Test 4: Target artifact paths must be preserved during normalization."""
        from backend.blueprint_schema import normalize_blueprint_data_models

        raw_models = [
            {
                "model_name": "EntityA",
                "target_file": "custom_path/artifact_entity.py",
                "fields": [{"field_name": "attr_a", "field_type": "str"}]
            }
        ]
        norm_models, errs = normalize_blueprint_data_models(
            raw_models,
            default_target_file="default_fallback.py"
        )
        assert len(errs) == 0
        assert norm_models[0]["target_file"] == "custom_path/artifact_entity.py"
        assert norm_models[0]["model_name"] == "EntityA"

    def test_05_file_structure_consistency(self):
        """Test 5: Strict 1-to-1 consistency between file_tree and files collection (Zero Phantom Files)."""
        from backend.blueprint_schema import ArchitecturalBlueprint, BlueprintFileModule

        # Deliberate perturbation: file_tree declares phantom file not in files
        with pytest.raises(ValueError, match="tidak memiliki modul scaffold di 'files'"):
            ArchitecturalBlueprint(
                authoritative_target_file="artifact_alpha.py",
                file_tree=["artifact_alpha.py", "phantom_module.py"],  # Perturbation
                architecture_summary="Inconsistent file tree",
                files={
                    "artifact_alpha.py": BlueprintFileModule(
                        file_path="artifact_alpha.py",
                        module_role="Core",
                        code_scaffold="def foo(): pass"
                    )
                }
            )

    def test_06_scaffold_relationship_consistency(self):
        """Test 6: Declared scaffold must contain interface signature declared in interface_contracts."""
        from backend.blueprint_schema import ArchitecturalBlueprint, BlueprintFileModule, BlueprintInterfaceContract

        # Consistent scaffold and interface contract
        bp = ArchitecturalBlueprint(
            authoritative_target_file="artifact_alpha.py",
            file_tree=["artifact_alpha.py"],
            architecture_summary="Consistent Blueprint",
            files={
                "artifact_alpha.py": BlueprintFileModule(
                    file_path="artifact_alpha.py",
                    module_role="Core",
                    code_scaffold="def operation_alpha(x: int) -> int:\n    return x * 2\n"
                )
            },
            interface_contracts=[
                BlueprintInterfaceContract(
                    identifier="operation_alpha",
                    target_file="artifact_alpha.py"
                )
            ]
        )
        assert bp.authoritative_target_file in bp.files
        assert bp.interface_contracts[0].identifier in bp.files["artifact_alpha.py"].code_scaffold

    def test_07_generic_repair_preservation(self):
        """Test 7: Repair context must mandate localized repair without discarding valid state."""
        state = {
            "task": "Repair synthetic service",
            "contract_revision_count": 1,
            "architecture_plan": "def operation_alpha(): pass\ndef operation_beta(): pass",
            "locked_invariants": {
                "INV-SYNTH": {"status": "PROVEN", "description": "operation_alpha signature must remain stable"}
            }
        }
        ctx, telem = build_architect_repair_context(state)

        assert "GENERIC REPAIR PRESERVATION (Anti-Field-Loss)" in ctx
        assert "CURRENT VALID STATE + REPAIRED ELEMENT" in ctx
        assert "Dropping fields or elements that remain valid under the canonical schema" in ctx
        assert "INV-SYNTH" in ctx

    def test_08_generic_field_loss_detection(self):
        """Test 8: Dropping required schema fields during repair must be detected and rejected."""
        from backend.blueprint_schema import parse_blueprint_json

        # Deliberate perturbation: interface_contracts item missing required 'identifier' field
        malformed_json_plan = """
=== BLUEPRINT JSON ===
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "Malformed blueprint missing identifier",
  "files": {
    "main.py": {
      "module_role": "Core",
      "code_scaffold": "def foo(): pass"
    }
  },
  "interface_contracts": [
    {
      "target_file": "main.py"
    }
  ]
}
=== END BLUEPRINT JSON ===
"""
        bp, err = parse_blueprint_json(malformed_json_plan)
        assert bp is None
        assert "Field required" in err or "validation error" in err.lower() or "identifier" in err

    def test_09_schema_serialization_fidelity(self):
        """Test 9: Structural perturbation of collection types (list vs object) must be rejected."""
        from backend.blueprint_schema import parse_blueprint_json

        # Perturbation 1: file_tree serialized as list of objects instead of list of strings
        perturbed_file_tree_plan = """
=== BLUEPRINT JSON ===
{
  "authoritative_target_file": "main.py",
  "file_tree": [{"path": "main.py"}],
  "architecture_summary": "Perturbed file tree",
  "files": {
    "main.py": {
      "module_role": "Core",
      "code_scaffold": "def foo(): pass"
    }
  }
}
=== END BLUEPRINT JSON ===
"""
        bp1, err1 = parse_blueprint_json(perturbed_file_tree_plan)
        assert bp1 is None
        assert "str" in err1.lower() or "validation error" in err1.lower()

        # Perturbation 2: interface_contracts serialized as dict mapping instead of list
        perturbed_ifaces_plan = """
=== BLUEPRINT JSON ===
{
  "authoritative_target_file": "main.py",
  "file_tree": ["main.py"],
  "architecture_summary": "Perturbed interface contracts",
  "files": {
    "main.py": {
      "module_role": "Core",
      "code_scaffold": "def foo(): pass"
    }
  },
  "interface_contracts": {
    "foo": {"identifier": "foo", "target_file": "main.py"}
  }
}
=== END BLUEPRINT JSON ===
"""
        bp2, err2 = parse_blueprint_json(perturbed_ifaces_plan)
        assert bp2 is None
        assert "list" in err2.lower() or "validation error" in err2.lower()

    def test_10_cross_language_structural_equivalence(self):
        """Test 10: Canonical schema constraints must apply identically across distinct language architectures."""
        from backend.blueprint_schema import ArchitecturalBlueprint, BlueprintFileModule, BlueprintInterfaceContract

        # Archetype A: Multi-module service (Python-style modular file tree)
        bp_a = ArchitecturalBlueprint(
            authoritative_target_file="service_main.py",
            file_tree=["service_main.py", "service_models.py"],
            architecture_summary="Modular multi-file service",
            files={
                "service_main.py": BlueprintFileModule(
                    file_path="service_main.py",
                    module_role="Service Entrypoint",
                    code_scaffold="def process_record(): pass"
                ),
                "service_models.py": BlueprintFileModule(
                    file_path="service_models.py",
                    module_role="Data Definitions",
                    code_scaffold="class RecordModel: pass"
                )
            },
            interface_contracts=[
                BlueprintInterfaceContract(
                    identifier="process_record",
                    target_file="service_main.py"
                )
            ]
        )

        # Archetype B: Cohesive single-module widget (Dart/Flutter-style cohesive widget)
        bp_b = ArchitecturalBlueprint(
            authoritative_target_file="lib/card_widget.dart",
            file_tree=["lib/card_widget.dart"],
            architecture_summary="Cohesive single-module UI widget",
            files={
                "lib/card_widget.dart": BlueprintFileModule(
                    file_path="lib/card_widget.dart",
                    module_role="Cohesive UI Widget & State",
                    code_scaffold="class MetricCardWidget { ... }"
                )
            },
            interface_contracts=[
                BlueprintInterfaceContract(
                    identifier="MetricCardWidget",
                    target_file="lib/card_widget.dart"
                )
            ]
        )

        # Both archetypes satisfy the exact same canonical relational model without language-specific branches
        assert len(bp_a.file_tree) == len(bp_a.files)
        assert len(bp_b.file_tree) == len(bp_b.files)
        assert bp_a.authoritative_target_file in bp_a.files
        assert bp_b.authoritative_target_file in bp_b.files
        assert bp_a.interface_contracts[0].target_file in bp_a.files
        assert bp_b.interface_contracts[0].target_file in bp_b.files

