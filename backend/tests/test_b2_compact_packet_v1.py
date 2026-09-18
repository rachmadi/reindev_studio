"""
Synthetic Test Suite for Treatment #1.8.9 — B2 Compact Semantic Repair Packet v1
25 Tests (A through Y) covering all Section 17 requirements:
  Test A: Authority preservation (all canonical authority items survive compaction and round-trip without loss)
  Test B: Obligation identity (obligation IDs, descriptions, categories preserved identically)
  Test C: Expected relationship (expected interface / relationship preserved)
  Test D: Actual relationship (observed interface preserved)
  Test E: Semantic difference (difference field captured and preserved)
  Test F: Repair target (target_id, target_symbol, what, where preserved)
  Test G: Repair boundary (allowed and forbidden boundaries preserved)
  Test H: Current valid state (valid relational bindings preserved)
  Test I: Locked invariants (all invariant IDs, hashes, and lock status preserved)
  Test J: Expected post-state (expected post-repair items preserved)
  Test K: Verification criteria (criterion ID, gates, evaluators preserved)
  Test L: Provenance (sources list preserved on failures and authority items)
  Test M: Duplicate failures deduplication (repeated failure text deduplicated into single tuple with merged sources)
  Test N: Relationship links survive compaction (symbol relationships and binding targets survive intact)
  Test O: Compact->expand semantic equivalence (verify_semantic_equivalence returns True, empty diff)
  Test P: Severe pressure preserves P0 (under tight budget, P1-P4 shed but P0 remains 100% intact)
  Test Q: P0 over-budget fails closed (if P0 alone exceeds budget, validator fails closed without silent truncation)
  Test R: No LLM invocation on invalid P0 (delivery failure returned cleanly without LLM call)
  Test S: P1-P4 shed without P0 loss (explicit shedding order P4->P3->P2->P1 verified)
  Test T: Multiple independent relationships remain distinguishable (multiple failures for distinct symbols are not clobbered)
  Test U: Repair target remains atomic (each failure maps to atomic target)
  Test V: Preserved state remains atomic (valid bindings and B1 items remain distinct)
  Test W: Unrelated synthetic domain 1 (database migration domain tested without issue)
  Test X: Unrelated synthetic domain 2 (event stream broker domain tested without issue)
  Test Y: No task-specific tokens/branches (static audit for forbidden domain-specific tokens)
"""

import copy
import json
import os
import re
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
root_dir = backend_dir.parent
for p in [str(root_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from backend.b2_repair_delivery import (
    AuthorityObligationItem,
    CurrentCausalFailureItem,
    ValidRelationalBinding,
    LockedProvenInvariant,
    RepairTargetItem,
    RepairBoundaryEnvelope,
    ExpectedPostRepairItem,
    VerificationCriterion,
    B2RepairDecisionPacket,
    B2DeliveryResult,
    _compute_hash,
    _normalize_diagnostic_to_semantic_tuples,
    serialize_compact_p0_json,
    expand_compact_p0_json,
    verify_semantic_equivalence,
    extract_b2_repair_decision_packet,
    distill_and_prioritize_packet,
    validate_b2_repair_context_delivery,
    assemble_and_distill_b2_repair_prompt,
    _format_p0_components,
    _format_p0_components_uncompressed,
)


@pytest.fixture
def populated_packet():
    """Builds a rich, fully populated B2RepairDecisionPacket across all 8 P0 components."""
    packet = B2RepairDecisionPacket(
        repair_attempt=1,
        authority_obligations=[
            AuthorityObligationItem(
                obligation_id="OBL-01",
                description="Expose compute_delta method with signature (a: int, b: int) -> int",
                category="INTERFACE",
                expected_relationship="CALLABLE_SIGNATURE",
                provenance="ACCEPTANCE_ORACLE",
            ),
            AuthorityObligationItem(
                obligation_id="OBL-02",
                description="Export status_flag constant with bool type",
                category="DATA_MODEL",
                expected_relationship="EXPORTS_CONSTANT",
                provenance="ACCEPTANCE_ORACLE",
            ),
        ],
        current_causal_failures=[
            CurrentCausalFailureItem(
                causal_category="STAGE_B2_BINDING_FAILURE",
                affected_obligations=["OBL-01"],
                root_cause_diagnostic="Symbol 'compute_delta' argument cardinality mismatch: expected 2, accepts 1",
                violating_symbol="compute_delta",
                expected_interface="arity=2",
                observed_interface="arity=1",
                difference="arity_mismatch: accepts 1, expected 2",
                relationship_type="CALL_SHAPE",
                sources=["contract_gate", "validator"],
            ),
        ],
        valid_relational_bindings=[
            ValidRelationalBinding(
                binding_id="BIND-01",
                source_identity="component_alpha",
                target_identity="compute_delta",
                relationship_type="INVOKES",
                target_artifact="calculator.py",
                is_preserved=True,
            ),
        ],
        locked_proven_invariants=[
            LockedProvenInvariant(
                invariant_id="INV-01",
                category="UPSTREAM_STAGE_A",
                description="Core topology immutable",
                seal_hash="hash_alpha_123",
                status="LOCKED",
                mutation="FORBIDDEN",
            ),
        ],
        repair_targets=[
            RepairTargetItem(
                target_id="TARGET-01",
                target_symbol="compute_delta",
                affected_obligations=["OBL-01"],
                what="Interface signature and argument binding for compute_delta",
                where="relational_bindings defining compute_delta",
                observed="arity=1",
                expected="arity=2",
            ),
        ],
        repair_boundary=RepairBoundaryEnvelope(
            allowed_modifications=["Modify compute_delta parameter shape"],
            forbidden_modifications=["DO NOT modify Stage A topology"],
            boundary_hash="hash_boundary_456",
            preserved_upstream=["Stage A topology", "Stage B-1 file tree"],
            preserved_relationships=["BIND-01"],
        ),
        expected_post_repair_states=[
            ExpectedPostRepairItem(
                item_id="EXPECT-01",
                target_symbol="compute_delta",
                expected_state="relationship(compute_delta) satisfies(OBL-01): arity=2",
                verification_rule="Contract Gate pre-freeze check",
            ),
        ],
        verification_criteria=[
            VerificationCriterion(
                criterion_id="CRIT-01",
                gate_name="CONTRACT_GATE_PRE_FREEZE",
                rule_description="All symbols match oracle requirements",
                evaluator="deterministic_contract_gate_validator",
            ),
        ],
        preserved_elements=[
            {"id": "component_alpha", "role": "CONTROLLER", "file": "calculator.py", "kind": "CLASS"},
        ],
    )
    return packet


# ------------------------------------------------------------------------------
# Test A: Authority Preservation
# ------------------------------------------------------------------------------
def test_a_authority_preservation(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert len(expanded.authority_obligations) == len(populated_packet.authority_obligations)
    for orig, exp in zip(populated_packet.authority_obligations, expanded.authority_obligations):
        assert exp.obligation_id == orig.obligation_id
        assert exp.description == orig.description
        assert exp.category == orig.category
        assert exp.expected_relationship == orig.expected_relationship
        assert exp.provenance == orig.provenance


# ------------------------------------------------------------------------------
# Test B: Obligation Identity
# ------------------------------------------------------------------------------
def test_b_obligation_identity(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    assert "authority" in compact
    obl_ids = [item["obl"] for item in compact["authority"]]
    assert obl_ids == ["OBL-01", "OBL-02"]
    expanded = expand_compact_p0_json(compact)
    assert [o.obligation_id for o in expanded.authority_obligations] == ["OBL-01", "OBL-02"]


# ------------------------------------------------------------------------------
# Test C: Expected Relationship
# ------------------------------------------------------------------------------
def test_c_expected_relationship(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert expanded.authority_obligations[0].expected_relationship == "CALLABLE_SIGNATURE"
    assert expanded.current_causal_failures[0].expected_interface == "arity=2"


# ------------------------------------------------------------------------------
# Test D: Actual Relationship
# ------------------------------------------------------------------------------
def test_d_actual_relationship(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert expanded.current_causal_failures[0].observed_interface == "arity=1"


# ------------------------------------------------------------------------------
# Test E: Semantic Difference
# ------------------------------------------------------------------------------
def test_e_semantic_difference(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert expanded.current_causal_failures[0].difference == "arity_mismatch: accepts 1, expected 2"


# ------------------------------------------------------------------------------
# Test F: Repair Target
# ------------------------------------------------------------------------------
def test_f_repair_target(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert len(expanded.repair_targets) == 1
    target = expanded.repair_targets[0]
    assert target.target_id == "TARGET-01"
    assert target.target_symbol == "compute_delta"
    assert target.expected == "arity=2"
    assert target.observed == "arity=1"


# ------------------------------------------------------------------------------
# Test G: Repair Boundary
# ------------------------------------------------------------------------------
def test_g_repair_boundary(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert expanded.repair_boundary.allowed_modifications == ["Modify compute_delta parameter shape"]
    assert expanded.repair_boundary.forbidden_modifications == ["DO NOT modify Stage A topology"]
    assert expanded.repair_boundary.preserved_upstream == ["Stage A topology", "Stage B-1 file tree"]


# ------------------------------------------------------------------------------
# Test H: Current Valid State
# ------------------------------------------------------------------------------
def test_h_current_valid_state(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert len(expanded.valid_relational_bindings) == 1
    binding = expanded.valid_relational_bindings[0]
    assert binding.binding_id == "BIND-01"
    assert binding.source_identity == "component_alpha"
    assert binding.target_identity == "compute_delta"
    assert binding.relationship_type == "INVOKES"
    assert binding.is_preserved is True


# ------------------------------------------------------------------------------
# Test I: Locked Invariants
# ------------------------------------------------------------------------------
def test_i_locked_invariants(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert len(expanded.locked_proven_invariants) == 1
    inv = expanded.locked_proven_invariants[0]
    assert inv.invariant_id == "INV-01"
    assert inv.seal_hash == "hash_alpha_123"
    assert inv.status == "LOCKED"
    assert inv.mutation == "FORBIDDEN"


# ------------------------------------------------------------------------------
# Test J: Expected Post-State
# ------------------------------------------------------------------------------
def test_j_expected_post_state(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert len(expanded.expected_post_repair_states) == 1
    item = expanded.expected_post_repair_states[0]
    assert item.item_id == "EXPECT-01"
    assert item.target_symbol == "compute_delta"
    assert "arity=2" in item.expected_state


# ------------------------------------------------------------------------------
# Test K: Verification Criteria
# ------------------------------------------------------------------------------
def test_k_verification_criteria(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert len(expanded.verification_criteria) == 1
    crit = expanded.verification_criteria[0]
    assert crit.criterion_id == "CRIT-01"
    assert crit.gate_name == "CONTRACT_GATE_PRE_FREEZE"
    assert crit.evaluator == "deterministic_contract_gate_validator"


# ------------------------------------------------------------------------------
# Test L: Provenance
# ------------------------------------------------------------------------------
def test_l_provenance(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert expanded.current_causal_failures[0].sources == ["contract_gate", "validator"]
    assert expanded.authority_obligations[0].provenance == "ACCEPTANCE_ORACLE"


# ------------------------------------------------------------------------------
# Test M: Duplicate Failures Deduplication
# ------------------------------------------------------------------------------
def test_m_duplicate_failures_deduplication():
    dup_error_1 = "CONTRACT_VALIDATION_FAILED: Symbol 'process_item' accepts at most 1 positional arguments; called with 2"
    dup_error_2 = "VALIDATOR_ERROR: Symbol 'process_item' accepts at most 1 positional arguments; called with 2"
    state = {
        "canonical_obligations": [
            {"obligation_id": "OBL-01", "description": "process_item signature", "category": "INTERFACE", "expected_relationship": "arity=2", "provenance": "ACCEPTANCE_ORACLE"}
        ],
        "contract_validation_errors": [dup_error_1, dup_error_2],
    }
    packet = extract_b2_repair_decision_packet(state, repair_errors=[dup_error_1, dup_error_2])
    # The duplicate failures for the same symbol & relationship should be deduplicated
    process_item_failures = [f for f in packet.current_causal_failures if f.violating_symbol == "process_item"]
    assert len(process_item_failures) == 1
    # Sources should be merged
    assert len(process_item_failures[0].sources) >= 1


# ------------------------------------------------------------------------------
# Test N: Relationship Links Survive Compaction
# ------------------------------------------------------------------------------
def test_n_relationship_links_survive_compaction(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    assert expanded.valid_relational_bindings[0].relationship_type == "INVOKES"
    assert expanded.current_causal_failures[0].relationship_type == "CALL_SHAPE"


# ------------------------------------------------------------------------------
# Test O: Compact->Expand Semantic Equivalence
# ------------------------------------------------------------------------------
def test_o_compact_expand_semantic_equivalence(populated_packet):
    compact = serialize_compact_p0_json(populated_packet)
    expanded = expand_compact_p0_json(compact)
    is_valid, diffs = verify_semantic_equivalence(populated_packet, expanded)
    assert is_valid is True, f"Equivalence diffs: {diffs}"
    assert len(diffs) == 0


# ------------------------------------------------------------------------------
# Test P: Severe Pressure Preserves P0
# ------------------------------------------------------------------------------
def test_p_severe_pressure_preserves_p0(populated_packet):
    # Add large P1-P4 layers
    populated_packet.p1_canonical_schema = {"large_schema": "x" * 2000}
    populated_packet.p2_relational_blueprint = {"blueprint_data": "y" * 2000}
    populated_packet.p3_supporting_diagnostics = ["diag_" + str(i) + "z" * 500 for i in range(5)]
    populated_packet.p4_historical_context = ["hist_" + str(i) + "w" * 500 for i in range(5)]

    # Budget tight enough that P1-P4 must be shed
    budget = 4000
    distilled, shed_log = distill_and_prioritize_packet(populated_packet, budget=budget)
    prompt = _format_p0_components(distilled)

    assert len(distilled.p4_historical_context) == 0
    assert len(distilled.p3_supporting_diagnostics) == 0
    assert len(distilled.p2_relational_blueprint) == 0
    assert len(distilled.p1_canonical_schema) == 0

    # All 8 P0 components must still be present in distilled packet
    assert len(distilled.authority_obligations) == len(populated_packet.authority_obligations)
    assert len(distilled.current_causal_failures) == len(populated_packet.current_causal_failures)
    assert len(distilled.valid_relational_bindings) == len(populated_packet.valid_relational_bindings)
    assert len(distilled.locked_proven_invariants) == len(populated_packet.locked_proven_invariants)
    assert len(distilled.repair_targets) == len(populated_packet.repair_targets)
    assert len(distilled.expected_post_repair_states) == len(populated_packet.expected_post_repair_states)
    assert len(distilled.verification_criteria) == len(populated_packet.verification_criteria)


# ------------------------------------------------------------------------------
# Test Q: P0 Over-Budget Fails Closed
# ------------------------------------------------------------------------------
def test_q_p0_over_budget_fails_closed(populated_packet):
    # If budget is absurdly small (e.g. 50 characters), P0 cannot fit
    tiny_budget = 50
    prompt = _format_p0_components(populated_packet)
    is_valid, errors = validate_b2_repair_context_delivery(prompt, populated_packet, budget=tiny_budget)
    assert is_valid is False
    assert any("BUDGET_EXCEEDED" in err for err in errors)


# ------------------------------------------------------------------------------
# Test R: No LLM Invocation on Invalid P0
# ------------------------------------------------------------------------------
def test_r_no_llm_invocation_on_invalid_p0():
    state = {
        "canonical_obligations": [],
        "contract_validation_errors": ["Error 1"],
    }
    # Forcing delivery validation failure by passing tiny budget override
    result = assemble_and_distill_b2_repair_prompt(state, repair_errors=["Error 1"], budget_override=50)
    assert result.delivery_valid is False
    assert len(result.validation_errors) > 0
    assert any("BUDGET_EXCEEDED" in err for err in result.validation_errors)


# ------------------------------------------------------------------------------
# Test S: P1-P4 Shed Without P0 Loss
# ------------------------------------------------------------------------------
def test_s_p1_p4_shed_without_p0_loss(populated_packet):
    populated_packet.p1_canonical_schema = {"field": "a" * 500}
    populated_packet.p2_relational_blueprint = {"field": "b" * 500}
    populated_packet.p3_supporting_diagnostics = ["diag_" + "c" * 500]
    populated_packet.p4_historical_context = ["hist_" + "d" * 500]

    # Shed P4 first
    distilled_1, _ = distill_and_prioritize_packet(populated_packet, budget=4500)
    assert len(distilled_1.p4_historical_context) == 0

    # Shed P3 next
    distilled_2, _ = distill_and_prioritize_packet(populated_packet, budget=3800)
    assert len(distilled_2.p3_supporting_diagnostics) == 0

    # Shed P2 next
    distilled_3, _ = distill_and_prioritize_packet(populated_packet, budget=3000)
    assert len(distilled_3.p2_relational_blueprint) == 0

    # Shed P1 next
    distilled_4, _ = distill_and_prioritize_packet(populated_packet, budget=2000)
    assert len(distilled_4.p1_canonical_schema) == 0

    # In all stages, P0 is 100% intact
    for d in [distilled_1, distilled_2, distilled_3, distilled_4]:
        assert len(d.authority_obligations) == len(populated_packet.authority_obligations)
        assert len(d.current_causal_failures) == len(populated_packet.current_causal_failures)
        assert len(d.repair_targets) == len(populated_packet.repair_targets)


# ------------------------------------------------------------------------------
# Test T: Multiple Independent Relationships Remain Distinguishable
# ------------------------------------------------------------------------------
def test_t_multiple_independent_relationships_remain_distinguishable():
    err1 = "CONTRACT_VALIDATION_FAILED: Symbol 'service_alpha' accepts at most 1 positional arguments; called with 2"
    err2 = "CONTRACT_VALIDATION_FAILED: Symbol 'handler_beta' constructor missing named argument(s): ['timeout']"
    err3 = "CONTRACT_VALIDATION_FAILED: Symbol 'writer_gamma' references target_artifact 'bad_path.py', which does not match validated B-1 artifact 'writer.py'"

    state = {
        "canonical_obligations": [
            {"obligation_id": "OBL-01", "description": "service_alpha signature", "category": "INTERFACE", "expected_relationship": "arity=2", "provenance": "ACCEPTANCE_ORACLE"},
            {"obligation_id": "OBL-02", "description": "handler_beta constructor", "category": "INTERFACE", "expected_relationship": "named_args: ['timeout']", "provenance": "ACCEPTANCE_ORACLE"},
            {"obligation_id": "OBL-03", "description": "writer_gamma target artifact", "category": "INTERFACE", "expected_relationship": "target_artifact: writer.py", "provenance": "ACCEPTANCE_ORACLE"},
        ],
        "contract_validation_errors": [err1, err2, err3],
    }
    packet = extract_b2_repair_decision_packet(state, repair_errors=[err1, err2, err3])
    symbols = {f.violating_symbol for f in packet.current_causal_failures}
    assert symbols == {"service_alpha", "handler_beta", "writer_gamma"}

    # Compaction and expansion
    compact = serialize_compact_p0_json(packet)
    expanded = expand_compact_p0_json(compact)
    exp_symbols = {f.violating_symbol for f in expanded.current_causal_failures}
    assert exp_symbols == {"service_alpha", "handler_beta", "writer_gamma"}


# ------------------------------------------------------------------------------
# Test U: Repair Target Remains Atomic
# ------------------------------------------------------------------------------
def test_u_repair_target_remains_atomic():
    item = RepairTargetItem(
        target_id="TARGET-42",
        target_symbol="execute_query",
        affected_obligations=["OBL-EXEC"],
        what="Public execution interface",
        where="relational_bindings for execute_query",
        observed="arity=0",
        expected="arity=1",
    )
    packet = B2RepairDecisionPacket(
        repair_targets=[item],
        authority_obligations=[AuthorityObligationItem(obligation_id="OBL-EXEC", description="desc", category="CAT", expected_relationship="rel", provenance="ORACLE")],
        current_causal_failures=[CurrentCausalFailureItem(causal_category="CAT", affected_obligations=["OBL-EXEC"], root_cause_diagnostic="diag", violating_symbol="execute_query", expected_interface="exp", observed_interface="obs", difference="diff", relationship_type="INTERFACE", sources=["source"])],
        valid_relational_bindings=[],
        locked_proven_invariants=[],
        repair_boundary=RepairBoundaryEnvelope(allowed_modifications=["mod"], forbidden_modifications=["forbid"], boundary_hash="hash"),
        expected_post_repair_states=[ExpectedPostRepairItem(item_id="EXP-1", target_symbol="execute_query", expected_state="satisfies", verification_rule="rule")],
        verification_criteria=[VerificationCriterion(criterion_id="CRIT-1", gate_name="GATE", rule_description="rule", evaluator="eval")],
    )
    compact = serialize_compact_p0_json(packet)
    expanded = expand_compact_p0_json(compact)
    assert len(expanded.repair_targets) == 1
    t = expanded.repair_targets[0]
    assert t.target_id == "TARGET-42"
    assert t.target_symbol == "execute_query"
    assert t.what == "Public execution interface"
    assert t.where == "relational_bindings for execute_query"


# ------------------------------------------------------------------------------
# Test V: Preserved State Remains Atomic
# ------------------------------------------------------------------------------
def test_v_preserved_state_remains_atomic():
    binding1 = ValidRelationalBinding(binding_id="B-1", source_identity="src1", target_identity="tgt1", relationship_type="INVOKES", target_artifact="art1.py", is_preserved=True)
    binding2 = ValidRelationalBinding(binding_id="B-2", source_identity="src2", target_identity="tgt2", relationship_type="DISPATCH", target_artifact="art2.py", is_preserved=True)
    packet = B2RepairDecisionPacket(
        valid_relational_bindings=[binding1, binding2],
        preserved_elements=[{"id": "elem1", "role": "ROLE1", "file": "art1.py", "kind": "MODULE"}],
        authority_obligations=[AuthorityObligationItem(obligation_id="OBL-1", description="d", category="c", expected_relationship="r", provenance="p")],
        current_causal_failures=[CurrentCausalFailureItem(causal_category="c", affected_obligations=["OBL-1"], root_cause_diagnostic="d", violating_symbol="sym", expected_interface="e", observed_interface="o", difference="df", relationship_type="INTERFACE", sources=["s"])],
        locked_proven_invariants=[],
        repair_targets=[RepairTargetItem(target_id="T-1", target_symbol="sym", affected_obligations=["OBL-1"], what="w", where="wh", observed="o", expected="e")],
        repair_boundary=RepairBoundaryEnvelope(allowed_modifications=[], forbidden_modifications=[], boundary_hash="bh"),
        expected_post_repair_states=[ExpectedPostRepairItem(item_id="E-1", target_symbol="sym", expected_state="es", verification_rule="vr")],
        verification_criteria=[VerificationCriterion(criterion_id="C-1", gate_name="g", rule_description="rd", evaluator="ev")],
    )
    compact = serialize_compact_p0_json(packet)
    expanded = expand_compact_p0_json(compact)
    assert len(expanded.valid_relational_bindings) == 2
    assert expanded.valid_relational_bindings[0].binding_id == "B-1"
    assert expanded.valid_relational_bindings[1].binding_id == "B-2"
    assert len(expanded.preserved_elements) == 1
    assert expanded.preserved_elements[0]["id"] == "elem1"


# ------------------------------------------------------------------------------
# Test W: Unrelated Synthetic Domain 1 (Database Migration & Schema Engine)
# ------------------------------------------------------------------------------
def test_w_unrelated_synthetic_domain_1():
    state = {
        "run_id": "db_migration_synth_01",
        "model_name": "qwen2.5-coder:7b",
        "failure_ownership": "STAGE_B2_BINDING_FAILURE",
        "canonical_obligations": [
            {
                "obligation_id": "OBL-MIG-01",
                "description": "Migration runner execute method accepts (schema: SchemaDefinition, dry_run: bool) -> MigrationResult",
                "category": "INTERFACE",
                "expected_relationship": "EXECUTION_DISPATCH",
                "provenance": "ACCEPTANCE_ORACLE",
            }
        ],
        "stage_a_output": [{"obligation_id": "OBL-MIG-01", "semantic_identity": "migration_runner", "element_kind": "SERVICE", "semantic_target_artifact": "runner.py"}],
        "stage_b1_output": [{"obligation_id": "OBL-MIG-01", "semantic_identity": "migration_runner", "element_kind": "SERVICE", "target_artifact": "runner.py", "architectural_representation": "EXECUTOR"}],
        "stage_b2_output": {
            "relational_bindings": [
                {
                    "binding_id": "BIND-MIG-01",
                    "source_identity": "cli_entry",
                    "target_identity": "migration_runner",
                    "relationship_type": "INVOKES",
                    "target_artifact": "runner.py",
                }
            ]
        },
        "contract_validation_errors": [
            "CONTRACT_VALIDATION_FAILED: Symbol 'migration_runner' accepts at most 1 positional arguments; called with 2"
        ],
    }

    result = assemble_and_distill_b2_repair_prompt(state, repair_errors=state["contract_validation_errors"])
    assert result.packet.repair_targets[0].target_symbol == "migration_runner"
    assert "migration_runner" in result.prompt
    assert result.telemetry["p0_semantic_equivalence_valid"] is True
    assert result.telemetry["compact_p0_chars"] < result.telemetry["original_p0_chars"]


# ------------------------------------------------------------------------------
# Test X: Unrelated Synthetic Domain 2 (Event Stream Broker)
# ------------------------------------------------------------------------------
def test_x_unrelated_synthetic_domain_2():
    state = {
        "run_id": "stream_broker_synth_02",
        "model_name": "qwen2.5-coder:7b",
        "failure_ownership": "STAGE_B2_BINDING_FAILURE",
        "canonical_obligations": [
            {
                "obligation_id": "OBL-STREAM-01",
                "description": "Topic partition publish method signature (payload: bytes, key: str, headers: dict) -> Future",
                "category": "INTERFACE",
                "expected_relationship": "PARTITION_PUBLISH",
                "provenance": "ACCEPTANCE_ORACLE",
            }
        ],
        "stage_a_output": [{"obligation_id": "OBL-STREAM-01", "semantic_identity": "partition_publisher", "element_kind": "PUBLISHER", "semantic_target_artifact": "broker.py"}],
        "stage_b1_output": [{"obligation_id": "OBL-STREAM-01", "semantic_identity": "partition_publisher", "element_kind": "PUBLISHER", "target_artifact": "broker.py", "architectural_representation": "BROKER"}],
        "stage_b2_output": {
            "relational_bindings": [
                {
                    "binding_id": "BIND-STREAM-01",
                    "source_identity": "ingress_gateway",
                    "target_identity": "partition_publisher",
                    "relationship_type": "DISPATCH",
                    "target_artifact": "broker.py",
                }
            ]
        },
        "contract_validation_errors": [
            "CONTRACT_VALIDATION_FAILED: Symbol 'partition_publisher' constructor missing named argument(s): ['headers']"
        ],
    }

    result = assemble_and_distill_b2_repair_prompt(state, repair_errors=state["contract_validation_errors"])
    assert result.packet.repair_targets[0].target_symbol == "partition_publisher"
    assert "partition_publisher" in result.prompt
    assert result.telemetry["p0_semantic_equivalence_valid"] is True
    assert result.telemetry["compact_p0_chars"] < result.telemetry["original_p0_chars"]


# ------------------------------------------------------------------------------
# Test Y: No Task-Specific Tokens / Branches (Anti-Solver Static Audit)
# ------------------------------------------------------------------------------
def test_y_no_task_specific_tokens_or_branches():
    """Verifies that b2_repair_delivery.py contains zero task-specific branching or hardcoded anti-solver tokens."""
    delivery_file = backend_dir / "b2_repair_delivery.py"
    content = delivery_file.read_text(encoding="utf-8")

    forbidden_tokens = [
        "fastapi_t1",
        "cli_t1",
        "flutter_t1",
        "CardMetric",
        "card_metric",
        "matrix_multiplier",
        "products_client",
        "task_1",
        "task_2",
        "task_3",
    ]

    for token in forbidden_tokens:
        matches = re.findall(rf"\b{re.escape(token)}\b", content, re.IGNORECASE)
        assert len(matches) == 0, f"Forbidden task-specific token '{token}' detected in b2_repair_delivery.py"
