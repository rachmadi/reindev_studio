"""
Synthetic Test Suite for Treatment #1.8.9: Stage B Decision Decomposition v1
Tests A through P covering all specified invariants:
- Test A: multiple obligations survive B1
- Test B: B1 preserves identities
- Test C: B1 rejects silent deletion
- Test D: B1 rejects silent rename
- Test E: B2 references only validated B1 elements
- Test F: B2 cannot invent obligations
- Test G: B2 cannot delete B1 elements
- Test H: B2 repair preserves B1
- Test I: B3 preserves B1+B2 semantic state
- Test J: raw multiline source remains lossless
- Test K: representation failure cannot mutate semantic state
- Test L: generic multi-element task
- Test M: generic cross-language task
- Test N: repair with multiple simultaneous failures
- Test O: regression containment after later-stage repair
- Test P: no task-specific tokens or branches (anti-solver audit)
"""

import os
import sys
import re
from pathlib import Path
import pytest

from backend.architect_staged import (
    StageAObligationMapping,
    FrozenStageAMappings,
    StageB1ElementRealization,
    StageB1Output,
    FrozenStageB1State,
    StageB2BindingDecision,
    StageB2Output,
    FrozenStageB2State,
    validate_stage_b1_realization,
    validate_stage_b2_bindings,
    parse_stage_b1_output,
    parse_stage_b2_output,
    assemble_decomposed_stage_b_blueprint,
    build_stage_b1_prompt,
    build_stage_b2_prompt,
    format_stage_b1_repair_evidence,
    format_stage_b2_repair_evidence
)


def _create_sample_stage_a_mappings():
    m1 = StageAObligationMapping(
        obligation_id="OBL-01",
        semantic_element="ComputeTax",
        element_kind="FUNCTION",
        semantic_identity="compute_tax",
        semantic_target_artifact="tax_engine.py",
        semantic_parameters=({"name": "amount", "type": "float", "location": "ARGUMENT", "required": True},),
        semantic_return={"type": "float", "description": "Calculated tax"}
    )
    m2 = StageAObligationMapping(
        obligation_id="OBL-02",
        semantic_element="TaxRecord",
        element_kind="DATA_MODEL",
        semantic_identity="TaxRecord",
        semantic_target_artifact="tax_engine.py",
        semantic_parameters=({"name": "id", "type": "str", "required": True}, {"name": "rate", "type": "float", "required": True}),
        semantic_return={"type": "TaxRecord"}
    )
    m3 = StageAObligationMapping(
        obligation_id="OBL-03",
        semantic_element="TaxApiHandler",
        element_kind="ENDPOINT",
        semantic_identity="tax_endpoint",
        semantic_target_artifact="tax_engine.py",
        semantic_parameters=({"name": "request_body", "type": "dict", "location": "BODY", "required": True},),
        semantic_return={"type": "dict", "status_code": 200}
    )
    return FrozenStageAMappings.freeze([m1, m2, m3])


# ------------------------------------------------------------------------------
# Test A: multiple obligations survive B1
# ------------------------------------------------------------------------------
def test_a_multiple_obligations_survive_b1():
    frozen_a = _create_sample_stage_a_mappings()
    b1_out = StageB1Output(
        elements=[
            StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_TAX_CALCULATOR"),
            StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_ENTITY"),
            StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "HTTP_REST_CONTROLLER"),
        ]
    )
    is_valid, errors = validate_stage_b1_realization(frozen_a, b1_out)
    assert is_valid, f"Validation failed unexpectedly: {errors}"
    assert len(errors) == 0
    assert len(b1_out.elements) == 3


# ------------------------------------------------------------------------------
# Test B: B1 preserves identities
# ------------------------------------------------------------------------------
def test_b_b1_preserves_identities():
    frozen_a = _create_sample_stage_a_mappings()
    b1_out = StageB1Output(
        elements=[
            StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
            StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
            StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "REST_HANDLER"),
        ]
    )
    is_valid, errors = validate_stage_b1_realization(frozen_a, b1_out)
    assert is_valid
    frozen_b1 = FrozenStageB1State.freeze(b1_out.elements)
    assert frozen_b1.get_element("OBL-01").semantic_identity == "compute_tax"
    assert frozen_b1.get_element("OBL-02").semantic_identity == "TaxRecord"
    assert frozen_b1.get_element("OBL-03").semantic_identity == "tax_endpoint"


# ------------------------------------------------------------------------------
# Test C: B1 rejects silent deletion
# ------------------------------------------------------------------------------
def test_c_b1_rejects_silent_deletion():
    frozen_a = _create_sample_stage_a_mappings()
    # OBL-03 is deleted
    b1_out = StageB1Output(
        elements=[
            StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
            StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
        ]
    )
    is_valid, errors = validate_stage_b1_realization(frozen_a, b1_out)
    assert not is_valid
    assert any("STAGE_B1_SILENT_DELETION" in e and "OBL-03" in e for e in errors)


# ------------------------------------------------------------------------------
# Test D: B1 rejects silent rename
# ------------------------------------------------------------------------------
def test_d_b1_rejects_silent_rename():
    frozen_a = _create_sample_stage_a_mappings()
    # compute_tax renamed to calculate_taxes
    b1_out = StageB1Output(
        elements=[
            StageB1ElementRealization("OBL-01", "calculate_taxes", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
            StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
            StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "REST_HANDLER"),
        ]
    )
    is_valid, errors = validate_stage_b1_realization(frozen_a, b1_out)
    assert not is_valid
    assert any("STAGE_B1_SILENT_RENAMING" in e and "compute_tax" in e for e in errors)


# ------------------------------------------------------------------------------
# Test E: B2 references only validated B1 elements
# ------------------------------------------------------------------------------
def test_e_b2_references_only_validated_b1_elements():
    frozen_a = _create_sample_stage_a_mappings()
    b1_elements = [
        StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
        StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
        StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "REST_HANDLER"),
    ]
    frozen_b1 = FrozenStageB1State.freeze(b1_elements)

    # B2 introduces an unknown reference 'unknown_helper'
    b2_out = StageB2Output(
        bindings=[
            StageB2BindingDecision("BIND-01", "compute_tax", "tax_engine.py", "IMPLEMENTS_INTERFACE", "tax_engine.py"),
            StageB2BindingDecision("BIND-02", "TaxRecord", "tax_engine.py", "USES_MODEL", "tax_engine.py"),
            StageB2BindingDecision("BIND-03", "tax_endpoint", "/api/tax", "BINDS_ROUTE", "tax_engine.py"),
            StageB2BindingDecision("BIND-04", "unknown_helper", "tax_engine.py", "CALLS_DELEGATE", "tax_engine.py"),
        ]
    )
    is_valid, errors = validate_stage_b2_bindings(frozen_a, frozen_b1, b2_out)
    assert not is_valid
    assert any("STAGE_B2_UNKNOWN_ELEMENT" in e and "unknown_helper" in e for e in errors)


# ------------------------------------------------------------------------------
# Test F: B2 cannot invent obligations
# ------------------------------------------------------------------------------
def test_f_b2_cannot_invent_obligations():
    frozen_a = _create_sample_stage_a_mappings()
    # Model attempts to invent an obligation in B1
    b1_out = StageB1Output(
        elements=[
            StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
            StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
            StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "REST_HANDLER"),
            StageB1ElementRealization("OBL-99", "invented_feature", "FUNCTION", "tax_engine.py", "EXTRA_HANDLER"),
        ]
    )
    is_valid, errors = validate_stage_b1_realization(frozen_a, b1_out)
    assert not is_valid
    assert any("STAGE_B1_INVENTED_ELEMENT" in e and "OBL-99" in e for e in errors)


# ------------------------------------------------------------------------------
# Test G: B2 cannot delete B1 elements
# ------------------------------------------------------------------------------
def test_g_b2_cannot_delete_b1_elements():
    frozen_a = _create_sample_stage_a_mappings()
    b1_elements = [
        StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
        StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
        StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "REST_HANDLER"),
    ]
    frozen_b1 = FrozenStageB1State.freeze(b1_elements)

    # B2 omits binding for 'TaxRecord'
    b2_out = StageB2Output(
        bindings=[
            StageB2BindingDecision("BIND-01", "compute_tax", "tax_engine.py", "IMPLEMENTS_INTERFACE", "tax_engine.py"),
            StageB2BindingDecision("BIND-03", "tax_endpoint", "/api/tax", "BINDS_ROUTE", "tax_engine.py"),
        ]
    )
    is_valid, errors = validate_stage_b2_bindings(frozen_a, frozen_b1, b2_out)
    assert not is_valid
    assert any("STAGE_B2_MISSING_BINDING" in e and "TaxRecord" in e for e in errors)


# ------------------------------------------------------------------------------
# Test H: B2 repair preserves B1
# ------------------------------------------------------------------------------
def test_h_b2_repair_preserves_b1():
    frozen_a = _create_sample_stage_a_mappings()
    b1_elements = [
        StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
        StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
        StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "REST_HANDLER"),
    ]
    frozen_b1 = FrozenStageB1State.freeze(b1_elements)
    original_b1_seal = frozen_b1.sha256_seal

    # Simulate B2 failure and repair evidence generation
    rep_evidence = format_stage_b2_repair_evidence(
        frozen_stage_a=frozen_a,
        frozen_b1=frozen_b1,
        repair_errors=["STAGE_B2_MISSING_BINDING: TaxRecord missing binding"]
    )
    assert "LOCKED STAGE B-1 ELEMENTS" in rep_evidence
    assert "TaxRecord" in rep_evidence
    assert "FORBIDDEN: Do NOT mutate B-1 symbols" in rep_evidence

    # Repaired B2 output provided
    repaired_b2 = StageB2Output(
        bindings=[
            StageB2BindingDecision("BIND-01", "compute_tax", "tax_engine.py", "IMPLEMENTS_INTERFACE", "tax_engine.py"),
            StageB2BindingDecision("BIND-02", "TaxRecord", "tax_engine.py", "USES_MODEL", "tax_engine.py"),
            StageB2BindingDecision("BIND-03", "tax_endpoint", "/api/tax", "BINDS_ROUTE", "tax_engine.py"),
        ]
    )
    is_valid, errors = validate_stage_b2_bindings(frozen_a, frozen_b1, repaired_b2)
    assert is_valid, f"Repaired B2 failed: {errors}"
    # B1 seal remains identical
    assert frozen_b1.sha256_seal == original_b1_seal


# ------------------------------------------------------------------------------
# Test I: B3 preserves B1+B2 semantic state
# ------------------------------------------------------------------------------
def test_i_b3_preserves_b1_b2_semantic_state():
    frozen_a = _create_sample_stage_a_mappings()
    b1_elements = [
        StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
        StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
        StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "REST_HANDLER"),
    ]
    frozen_b1 = FrozenStageB1State.freeze(b1_elements)

    b2_out = StageB2Output(
        bindings=[
            StageB2BindingDecision(
                "BIND-01", "compute_tax", "tax_engine.py", "IMPLEMENTS_INTERFACE", "tax_engine.py",
                {"parameters": [{"name": "amount", "type": "float", "required": True}], "return_semantics": {"type": "float"}}
            ),
            StageB2BindingDecision(
                "BIND-02", "TaxRecord", "tax_engine.py", "USES_MODEL", "tax_engine.py",
                {"fields": [{"name": "id", "type": "str", "required": True}, {"name": "rate", "type": "float", "required": True}]}
            ),
            StageB2BindingDecision(
                "BIND-03", "tax_endpoint", "/api/tax", "BINDS_ROUTE", "tax_engine.py",
                {"route": "/api/tax", "http_method": "POST", "parameters": [{"name": "body", "type": "dict", "required": True}], "return_semantics": {"type": "dict", "status_code": 200}}
            ),
        ],
        scaffold_files={
            "tax_engine.py": "class TaxRecord:\n    pass\n\ndef compute_tax(amount: float) -> float:\n    pass\n"
        }
    )

    bp, errors = assemble_decomposed_stage_b_blueprint(frozen_a, frozen_b1, b2_out, task_id="tax_task", target_language="python")
    assert bp is not None, f"Assembly failed: {errors}"
    assert len(errors) == 0

    # Verify Blueprint preserved all entities
    ifc_ids = {ifc.identifier for ifc in bp.interface_contracts}
    assert "compute_tax" in ifc_ids
    assert "tax_endpoint" in ifc_ids

    model_ids = {m.model_name for m in bp.data_models}
    assert "TaxRecord" in model_ids


# ------------------------------------------------------------------------------
# Test J: raw multiline source remains lossless
# ------------------------------------------------------------------------------
def test_j_raw_multiline_source_remains_lossless():
    raw_code = (
        'from fastapi import FastAPI, HTTPException\n'
        'app = FastAPI(title="Tax API")\n\n'
        '@app.post("/calculate")\n'
        'def compute(payload: dict) -> dict:\n'
        '    """Docstring with \"quotes\" and \'single quotes\'.\n'
        '    Line 2 with {curly: "braces"}.\n'
        '    """\n'
        '    return {"result": 42.0}\n'
    )
    text_input = """=== STAGE B-2: RELATIONSHIP BINDINGS ===
{
  "bindings": [
    {
      "binding_id": "BIND-01",
      "source_identity": "compute",
      "target_identity": "/calculate",
      "relationship_type": "BINDS_ROUTE",
      "target_artifact": "main.py",
      "signature_details": {
        "parameters": [],
        "return_semantics": {"type": "dict"}
      }
    }
  ]
}
=== END STAGE B-2 ===

=== STAGE B: SCAFFOLD ARTIFACTS ===
=== FILE: main.py ===
""" + raw_code + """
=== END FILE ===
=== END STAGE B SCAFFOLDS ==="""

    parsed, errors = parse_stage_b2_output(text_input)
    assert parsed is not None, f"Parse failed: {errors}"
    assert "main.py" in parsed.scaffold_files
    extracted_code = parsed.scaffold_files["main.py"]
    assert extracted_code.strip() == raw_code.strip()


# ------------------------------------------------------------------------------
# Test K: representation failure cannot mutate semantic state
# ------------------------------------------------------------------------------
def test_k_representation_failure_cannot_mutate_semantic_state():
    frozen_a = _create_sample_stage_a_mappings()
    b1_elements = [
        StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
        StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
        StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "REST_HANDLER"),
    ]
    frozen_b1 = FrozenStageB1State.freeze(b1_elements)
    original_b1_seal = frozen_b1.sha256_seal

    # Malformed text output for B2 (invalid JSON)
    malformed_b2_text = """=== STAGE B-2: RELATIONSHIP BINDINGS ===
{
  "bindings": [
    { "binding_id": "BIND-01", INVALID_JSON_HERE
  ]
}
=== END STAGE B-2 ==="""

    parsed_b2, parse_errs = parse_stage_b2_output(malformed_b2_text)
    assert parsed_b2 is None
    assert len(parse_errs) > 0

    # Validated B-1 state remains entirely untouched
    assert frozen_b1.sha256_seal == original_b1_seal
    assert len(frozen_b1.elements) == 3


# ------------------------------------------------------------------------------
# Test L: generic multi-element task
# ------------------------------------------------------------------------------
def test_l_generic_multi_element_task():
    # 5 obligations
    mappings = [
        StageAObligationMapping(f"OBL-{idx:02d}", f"Elem{idx}", "FUNCTION" if idx < 4 else "DATA_MODEL", f"symbol_{idx}", "app.py")
        for idx in range(1, 6)
    ]
    frozen_a = FrozenStageAMappings.freeze(mappings)

    b1_out = StageB1Output(
        elements=[
            StageB1ElementRealization(f"OBL-{idx:02d}", f"symbol_{idx}", "FUNCTION" if idx < 4 else "DATA_MODEL", "app.py", f"ROLE_{idx}")
            for idx in range(1, 6)
        ]
    )
    b1_valid, b1_errs = validate_stage_b1_realization(frozen_a, b1_out)
    assert b1_valid, b1_errs

    b2_out = StageB2Output(
        bindings=[
            StageB2BindingDecision(f"BIND-{idx:02d}", f"symbol_{idx}", "app.py", "IMPLEMENTS_INTERFACE", "app.py", {"parameters": [], "return_semantics": {"type": "str"}})
            for idx in range(1, 6)
        ],
        scaffold_files={"app.py": "# Full scaffold for 5 elements\n"}
    )
    b2_valid, b2_errs = validate_stage_b2_bindings(frozen_a, b1_out, b2_out)
    assert b2_valid, b2_errs

    bp, asm_errs = assemble_decomposed_stage_b_blueprint(frozen_a, b1_out, b2_out, task_id="multi_task", target_language="python")
    assert bp is not None, asm_errs
    assert len(bp.interface_contracts) == 3
    assert len(bp.data_models) == 2


# ------------------------------------------------------------------------------
# Test M: generic cross-language task
# ------------------------------------------------------------------------------
def test_m_generic_cross_language_task():
    # Dart/Flutter case
    dart_m = StageAObligationMapping("OBL-01", "CardMetricWidget", "WIDGET", "CardMetric", "lib/card_metric.dart")
    frozen_dart_a = FrozenStageAMappings.freeze([dart_m])

    b1_dart = StageB1Output(
        elements=[StageB1ElementRealization("OBL-01", "CardMetric", "WIDGET", "lib/card_metric.dart", "UI_WIDGET_COMPONENT")]
    )
    val_b1_ok, _ = validate_stage_b1_realization(frozen_dart_a, b1_dart)
    assert val_b1_ok

    b2_dart = StageB2Output(
        bindings=[
            StageB2BindingDecision("BIND-01", "CardMetric", "lib/card_metric.dart", "EXPOSES_WIDGET", "lib/card_metric.dart", {"parameters": []})
        ],
        scaffold_files={"lib/card_metric.dart": "class CardMetric extends StatelessWidget {}\n"}
    )
    val_b2_ok, _ = validate_stage_b2_bindings(frozen_dart_a, b1_dart, b2_dart)
    assert val_b2_ok

    bp_dart, asm_errs = assemble_decomposed_stage_b_blueprint(frozen_dart_a, b1_dart, b2_dart, task_id="dart_task", target_language="dart")
    assert bp_dart is not None, asm_errs
    assert any(ifc.identifier == "CardMetric" for ifc in bp_dart.interface_contracts)


# ------------------------------------------------------------------------------
# Test N: repair with multiple simultaneous failures
# ------------------------------------------------------------------------------
def test_n_repair_with_multiple_simultaneous_failures():
    frozen_a = _create_sample_stage_a_mappings()
    # Simultaneous failures:
    # 1. OBL-01 is renamed
    # 2. OBL-02 is omitted (silent deletion)
    # 3. OBL-99 is invented
    b1_bad = StageB1Output(
        elements=[
            StageB1ElementRealization("OBL-01", "wrong_name", "FUNCTION", "tax_engine.py", "CALCULATOR"),
            StageB1ElementRealization("OBL-99", "invented_sym", "FUNCTION", "tax_engine.py", "EXTRA"),
        ]
    )
    is_valid, errors = validate_stage_b1_realization(frozen_a, b1_bad)
    assert not is_valid
    # All three distinct errors detected in a single validation pass
    assert any("STAGE_B1_SILENT_RENAMING" in e for e in errors)
    assert any("STAGE_B1_SILENT_DELETION" in e and "OBL-02" in e for e in errors)
    assert any("STAGE_B1_INVENTED_ELEMENT" in e and "OBL-99" in e for e in errors)


# ------------------------------------------------------------------------------
# Test O: regression containment after later-stage repair
# ------------------------------------------------------------------------------
def test_o_regression_containment_after_later_stage_repair():
    frozen_a = _create_sample_stage_a_mappings()
    b1_elements = [
        StageB1ElementRealization("OBL-01", "compute_tax", "FUNCTION", "tax_engine.py", "CORE_CALCULATOR"),
        StageB1ElementRealization("OBL-02", "TaxRecord", "DATA_MODEL", "tax_engine.py", "DOMAIN_MODEL"),
        StageB1ElementRealization("OBL-03", "tax_endpoint", "ENDPOINT", "tax_engine.py", "REST_HANDLER"),
    ]
    frozen_b1 = FrozenStageB1State.freeze(b1_elements)
    seal_initial = frozen_b1.sha256_seal

    # Downstream B2 repair turn occurs
    b2_attempt_1 = StageB2Output(bindings=[]) # Fails validation
    val_ok, _ = validate_stage_b2_bindings(frozen_a, frozen_b1, b2_attempt_1)
    assert not val_ok

    b2_attempt_2 = StageB2Output(
        bindings=[
            StageB2BindingDecision("BIND-01", "compute_tax", "tax_engine.py", "IMPLEMENTS_INTERFACE", "tax_engine.py"),
            StageB2BindingDecision("BIND-02", "TaxRecord", "tax_engine.py", "USES_MODEL", "tax_engine.py"),
            StageB2BindingDecision("BIND-03", "tax_endpoint", "/api/tax", "BINDS_ROUTE", "tax_engine.py"),
        ],
        scaffold_files={"tax_engine.py": "def compute_tax(): pass\n"}
    )
    val_ok_2, _ = validate_stage_b2_bindings(frozen_a, frozen_b1, b2_attempt_2)
    assert val_ok_2

    # Verify B1 seal was not mutated during B2 failure/repair cycles
    assert frozen_b1.sha256_seal == seal_initial


# ------------------------------------------------------------------------------
# Test P: no task-specific tokens or branches (anti-solver audit)
# ------------------------------------------------------------------------------
def test_p_no_task_specific_tokens_or_branches():
    """Static AST and text audit of architect_staged.py and agents/architect.py."""
    forbidden_tokens = [
        "is_fastapi",
        "is_cli",
        "is_flutter",
        "fastapi_t1",
        "cli_t1",
        "flutter_t1",
        "_add",
        "_sub",
        "_mul",
        "CardMetricWidget",
    ]

    backend_dir = Path(__file__).resolve().parent.parent
    staged_py = (backend_dir / "architect_staged.py").read_text(encoding="utf-8")
    architect_py = (backend_dir / "agents/architect.py").read_text(encoding="utf-8")

    # In architect_staged.py, none of the forbidden solver tokens should appear
    for token in forbidden_tokens:
        assert token not in staged_py, f"Forbidden solver token '{token}' found in architect_staged.py!"

    # In architect.py, solver branching is forbidden
    for token in ["is_fastapi", "is_cli", "_add", "_sub", "_mul"]:
        assert token not in architect_py, f"Forbidden solver token '{token}' found in architect.py!"
