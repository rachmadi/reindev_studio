import json
"""
Test Suite: Validator 2 (Architect Phase-End Validator) Deep Hardening & 9-Dimension Matrix
ReinDev Studio — Evaluation Matrix according to Implementation Plan v2.2

Dimensions Tested:
1. Positive Cases: Complete architecture plan, valid AST, FROZEN contract with SHA-256 seal.
2. Negative Cases: Empty or garbage architecture plan fails with STRUCTURAL_INCOMPLETE.
3. Incomplete Cases: Contract missing interface_contracts fails with MANDATORY_FIELD_MISSING.
4. Contradictory / AST Syntax Cases: Blueprint with broken AST/decorator fails.
5. Contract Status / Seal Integrity Cases: Un-frozen status or missing seal fails with CONSTRAINT_VIOLATION.
6. Repair-Success (Attempt 1): Revalidation after 1 repair succeeds and routes to Developer.
7. Repair-Success (Attempt 2): Revalidation after 2 repairs succeeds and routes to Developer.
8. Terminal Failure: Fails after max repairs (2) aborts immediately to END (Zero Downstream Leakage).
9. Mission-Diverse Generality: Validates blueprints across 5 distinct domains (CLI, REST, Algorithm, Flutter, Data Pipeline).
"""

import pytest
from langgraph.graph import END

from backend.phase_validators import validate_architect_phase
from backend.graph import architect_validator_node, route_after_architect_validator
from backend.contract import (
    ContractStatus,
    create_draft_contract,
    complete_aligned_contract,
    seal_and_freeze_contract,
)


# ==============================================================================
# Helper Factories
# ==============================================================================

def make_valid_arch_plan(domain: str = "CLI", lang: str = "python") -> str:
    target_file = "lib/main.dart" if "dart" in lang else "main.py"
    scaffold = (
        "import 'package:flutter/material.dart';\n\nclass MainWidget extends StatelessWidget {\n  const MainWidget({super.key});\n  @override\n  Widget build(BuildContext context) {\n    return const SizedBox();\n  }\n}\n"
        if "dart" in lang
        else f'def process_data(payload: dict) -> dict:\n    return {{"status": "ok", "domain": "{domain}"}}\n'
    )
    bp = {
        "schema_version": "1.0.0",
        "task_id": f"task_{domain.lower()}",
        "target_language": lang,
        "authoritative_target_file": target_file,
        "file_tree": [target_file],
        "architecture_summary": f"Architectural scaffold for {domain}",
        "files": {
            target_file: {
                "file_path": target_file,
                "module_role": "Authoritative Single Module",
                "imports": [],
                "code_scaffold": scaffold,
            }
        },
        "interface_contracts": [
            {
                "identifier": "MainWidget" if "dart" in lang else "process_data",
                "target_file": target_file,
            }
        ]
    }
    return f"=== BLUEPRINT JSON ===\n{json.dumps(bp, indent=2)}\n=== END BLUEPRINT JSON ==="


def make_valid_aligned_contract(domain: str = "CLI_TOOL", lang: str = "python") -> dict:
    target_file = "lib/main.dart" if "dart" in lang else "main.py"
    iface_type = "WIDGET" if "dart" in lang else "FUNCTION"
    ident = "MainWidget" if "dart" in lang else "process_data"
    draft = create_draft_contract(raw_intent=f"Task {domain}", target_language=lang, domain=domain)
    return complete_aligned_contract(
        draft_dict=draft,
        data_models=[],
        interface_contracts=[
            {
                "interface_id": "IFC-01",
                "identifier": ident,
                "target_file": target_file,
                "interface_type": iface_type,
            }
        ],
        testable_assertions=[
            {
                "assertion_id": "AST-01",
                "linked_req_id": "REQ-01",
                "linked_interface_id": "IFC-01",
                "test_scenario": f"Execution of {ident} in {domain}",
                "target_symbol": ident,
                "expected_outcome": {"outcome_type": "VALUE_EQUALS", "value": 0}
            }
        ]
    )


# ==============================================================================
# 1. Positive Case
# ==============================================================================

def test_dim1_positive_case():
    aligned = make_valid_aligned_contract("CLI_TOOL", "python")
    ok, frozen, _, _ = seal_and_freeze_contract(aligned, task_text="Buat service pemrosesan data.")
    assert ok is True

    state = {
        "task": "Buat service pemrosesan data.",
        "target_language": "python",
        "architecture_plan": make_valid_arch_plan("CLI", "python"),
        "contract": frozen,
        "contract_status": ContractStatus.FROZEN.value,
        "contract_sha256": frozen["provenance"]["contract_sha256"],
    }
    result = validate_architect_phase(state)
    assert result["phase"] == "ARCHITECT"
    assert result["validator_type"] == "PHASE_END"
    assert result["verdict"] == "PASS"
    assert len(result["violations"]) == 0
    assert result["confidence"] == 1.0


# ==============================================================================
# 2. Negative Case (Empty / Garbage Architecture Plan)
# ==============================================================================

def test_dim2_negative_empty_arch_plan():
    aligned = make_valid_aligned_contract("CLI_TOOL", "python")
    ok, frozen, _, _ = seal_and_freeze_contract(aligned, task_text="Buat kalkulator.")

    state = {
        "task": "Buat program kalkulator.",
        "target_language": "python",
        "architecture_plan": "terlalu pendek",
        "contract": frozen,
        "contract_status": ContractStatus.FROZEN.value,
        "contract_sha256": frozen["provenance"]["contract_sha256"],
    }
    result = validate_architect_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v.get("criterion") == "arch_plan_present" for v in result["violations"])


# ==============================================================================
# 3. Incomplete Case (Missing Interface Contracts)
# ==============================================================================

def test_dim3_incomplete_missing_interface_contracts():
    aligned = make_valid_aligned_contract("CLI_TOOL", "python")
    aligned["interface_contracts"] = []

    state = {
        "task": "Buat service pemrosesan data.",
        "target_language": "python",
        "architecture_plan": make_valid_arch_plan("CLI", "python"),
        "contract": aligned,
        "contract_status": ContractStatus.FROZEN.value,
        "contract_sha256": "a" * 64,
    }
    result = validate_architect_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v.get("criterion") == "public_interfaces_defined" for v in result["violations"])


# ==============================================================================
# 4. AST Syntax / Broken Blueprint Case
# ==============================================================================

def test_dim4_broken_ast_blueprint():
    broken_bp = {
        "schema_version": "1.0.0",
        "task_id": "test_broken",
        "target_language": "python",
        "authoritative_target_file": "main.py",
        "file_tree": ["main.py"],
        "architecture_summary": "Broken decorator blueprint",
        "files": {
            "main.py": {
                "file_path": "main.py",
                "module_role": "Authoritative Single Module",
                "imports": [],
                "code_scaffold": "@unresolved_decorator_without_import\ndef broken_syntax():\n    pass\n",
            }
        },
        "interface_contracts": [{"identifier": "broken_syntax", "target_file": "main.py"}]
    }
    broken_plan = f"=== BLUEPRINT JSON ===\n{json.dumps(broken_bp, indent=2)}\n=== END BLUEPRINT JSON ==="

    aligned = make_valid_aligned_contract("CLI_TOOL", "python")
    ok, frozen, _, _ = seal_and_freeze_contract(aligned, task_text="Buat modul.")

    state = {
        "task": "Buat modul parser.",
        "target_language": "python",
        "architecture_plan": broken_plan,
        "contract": frozen,
        "contract_status": ContractStatus.FROZEN.value,
        "contract_sha256": frozen["provenance"]["contract_sha256"],
    }
    result = validate_architect_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v.get("criterion") == "blueprint_ast_consistency" for v in result["violations"])


# ==============================================================================
# 5. Contract Status / Seal Integrity Case
# ==============================================================================

def test_dim5_unfrozen_contract_status():
    aligned = make_valid_aligned_contract("CLI_TOOL", "python")

    state = {
        "task": "Buat service data.",
        "target_language": "python",
        "architecture_plan": make_valid_arch_plan("CLI", "python"),
        "contract": aligned,
        "contract_status": ContractStatus.REJECTED.value,
        "contract_sha256": "",
    }
    result = validate_architect_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v.get("criterion") == "contract_frozen_status" for v in result["violations"])
    assert any(v.get("criterion") == "contract_sha256_seal_integrity" for v in result["violations"])


# ==============================================================================
# 6. Repair-Success Attempt 1
# ==============================================================================

def test_dim6_repair_success_attempt_1():
    aligned = make_valid_aligned_contract("CLI_TOOL", "python")

    state = {
        "task": "Buat kalkulator CLI.",
        "target_language": "python",
        "architecture_plan": "terlalu pendek",
        "contract": aligned,
        "repair_attempt_counts": {"architect": 0},
    }

    step1_res = architect_validator_node(state)
    assert step1_res["architect_validator_contract"]["verdict"] == "FAIL"
    state.update(step1_res)
    assert route_after_architect_validator(state) == "architect"

    # Perbaikan pada Attempt #1
    state["architecture_plan"] = make_valid_arch_plan("CLI", "python")

    step2_res = architect_validator_node(state)
    assert step2_res["architect_validator_contract"]["verdict"] == "PASS"
    state.update(step2_res)
    assert route_after_architect_validator(state) == "developer"


# ==============================================================================
# 7. Repair-Success Attempt 2
# ==============================================================================

def test_dim7_repair_success_attempt_2():
    aligned = make_valid_aligned_contract("REST_API", "python")

    state = {
        "task": "Buat service autentikasi.",
        "target_language": "python",
        "architecture_plan": "pendek 1",
        "contract": aligned,
        "repair_attempt_counts": {"architect": 0},
    }

    # Attempt 0 -> FAIL -> count 1
    s1 = architect_validator_node(state)
    assert s1["architect_validator_contract"]["verdict"] == "FAIL"
    state.update(s1)
    assert route_after_architect_validator(state) == "architect"

    # Attempt 1 -> Still fails -> count 2
    state["architecture_plan"] = "masih terlalu pendek untuk lolos"
    s2 = architect_validator_node(state)
    assert s2["architect_validator_contract"]["verdict"] == "FAIL"
    state.update(s2)
    assert route_after_architect_validator(state) == "architect"

    # Attempt 2 -> Perbaikan berhasil -> PASS
    state["architecture_plan"] = make_valid_arch_plan("REST", "python")
    s3 = architect_validator_node(state)
    assert s3["architect_validator_contract"]["verdict"] == "PASS"
    state.update(s3)
    assert route_after_architect_validator(state) == "developer"


# ==============================================================================
# 8. Terminal Failure After Attempt 2 Exhaustion (Zero Downstream Leakage)
# ==============================================================================

def test_dim8_terminal_failure_after_attempt_exhaustion():
    state = {
        "task": "Buat service.",
        "target_language": "python",
        "architecture_plan": "rusak",
        "contract": {},
        "repair_attempt_counts": {"architect": 2},
    }

    res = architect_validator_node(state)
    assert res["architect_validator_contract"]["verdict"] == "FAIL"
    assert res.get("status") == "terminal_failure_architect_boundary"

    state.update(res)
    assert route_after_architect_validator(state) == END


# ==============================================================================
# 9. Mission-Diverse Generality Verification
# ==============================================================================

@pytest.mark.parametrize("domain,lang", [
    ("CLI_TOOL", "python"),
    ("REST_API", "python"),
    ("ALGORITHM", "python"),
    ("FLUTTER_WIDGET", "dart"),
    ("DATA_PIPELINE", "python"),
])
def test_dim9_mission_diverse_generality(domain, lang):
    arch_plan = make_valid_arch_plan(domain, lang)
    aligned = make_valid_aligned_contract(domain, lang)
    ok, frozen, _, _ = seal_and_freeze_contract(aligned, task_text=f"Implementasi sistem {domain}.")
    assert ok is True

    state = {
        "task": f"Implementasi sistem {domain}.",
        "target_language": lang,
        "architecture_plan": arch_plan,
        "contract": frozen,
        "contract_status": ContractStatus.FROZEN.value,
        "contract_sha256": frozen["provenance"]["contract_sha256"],
    }
    result = validate_architect_phase(state)
    assert result["verdict"] == "PASS", f"Failed for domain {domain}: {result['violations']}"
    assert len(result["violations"]) == 0
