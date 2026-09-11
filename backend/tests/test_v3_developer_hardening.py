"""
Test Suite: Validator 3 (Developer Pre-Execution Validator) Deep Hardening & 9-Dimension Matrix
ReinDev Studio — Evaluation Matrix according to Implementation Plan v2.2

Dimensions Tested:
1. Positive Cases: Complete code files, authoritative target file, valid AST, all contract symbols defined.
2. Negative Cases: Empty code files dictionary fails with code_files_present.
3. Incomplete Cases: Code missing mandatory interface contract symbol fails with contract_symbols_conformance.
4. Syntax / AST Error Cases: Broken code with SyntaxError fails with ast_syntax_validity.
5. Constraint Violation Cases: Exceeding max_files constraint fails with constraint_compliance.
6. Repair-Success (Attempt 1): Revalidation after 1 repair succeeds and routes to test suite (frozen_oracle/tester).
7. Repair-Success (Attempt 2): Revalidation after 2 repairs succeeds and routes to test suite.
8. Terminal Failure: Fails after max repairs (2) aborts immediately to END (Zero Downstream Leakage).
9. Mission-Diverse Generality: Validates code files across 5 distinct domains (CLI, REST, Algorithm, Flutter, Data Pipeline).
"""

import pytest
from langgraph.graph import END

from backend.phase_validators import validate_developer_phase
from backend.graph import developer_validator_node, route_after_developer_validator
from backend.contract import create_draft_contract, complete_aligned_contract, seal_and_freeze_contract


# ==============================================================================
# Helper Factories
# ==============================================================================

def make_sample_contract(domain: str = "CLI_TOOL", lang: str = "python") -> dict:
    target_file = "lib/main.dart" if "dart" in lang else "main.py"
    iface_type = "WIDGET" if "dart" in lang else "FUNCTION"
    ident = "MainWidget" if "dart" in lang else "process_data"
    draft = create_draft_contract(raw_intent=f"Task {domain}", target_language=lang, domain=domain)
    aligned = complete_aligned_contract(
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
                "test_scenario": f"Execution of {ident}",
                "target_symbol": ident,
                "expected_outcome": {"outcome_type": "VALUE_EQUALS", "value": 0}
            }
        ]
    )
    ok, frozen, _, _ = seal_and_freeze_contract(aligned, task_text=f"Task {domain}")
    assert ok is True
    return frozen


def make_valid_code_files(domain: str = "CLI_TOOL", lang: str = "python") -> dict:
    if "dart" in lang:
        return {
            "lib/main.dart": """
import 'package:flutter/material.dart';

class MainWidget extends StatelessWidget {
  const MainWidget({super.key});
  @override
  Widget build(BuildContext context) {
    return const SizedBox();
  }
}
"""
        }
    else:
        return {
            "main.py": f"""
def process_data(payload: dict = None) -> dict:
    return {{"status": "success", "domain": "{domain}"}}
"""
        }


# ==============================================================================
# 1. Positive Case
# ==============================================================================

def test_dim1_positive_case():
    contract = make_sample_contract("CLI_TOOL", "python")
    state = {
        "task": "Implementasi service.",
        "target_language": "python",
        "code_files": make_valid_code_files("CLI_TOOL", "python"),
        "contract": contract,
    }
    result = validate_developer_phase(state)
    assert result["phase"] == "DEVELOPER"
    assert result["validator_type"] == "PHASE_END"
    assert result["verdict"] == "PASS"
    assert len(result["violations"]) == 0
    assert result["confidence"] == 1.0


# ==============================================================================
# 2. Negative Case (Empty Code Files)
# ==============================================================================

def test_dim2_negative_empty_code_files():
    contract = make_sample_contract("CLI_TOOL", "python")
    state = {
        "task": "Implementasi service.",
        "target_language": "python",
        "code_files": {},
        "contract": contract,
    }
    result = validate_developer_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v.get("criterion") == "code_files_present" for v in result["violations"])


# ==============================================================================
# 3. Incomplete Case (Missing Contract Symbol)
# ==============================================================================

def test_dim3_incomplete_missing_contract_interface():
    contract = make_sample_contract("CLI_TOOL", "python")
    # Code defines wrong function name 'unrelated_function' instead of 'process_data'
    wrong_code = {
        "main.py": """
def unrelated_function():
    return True
"""
    }
    state = {
        "task": "Implementasi service.",
        "target_language": "python",
        "code_files": wrong_code,
        "contract": contract,
    }
    result = validate_developer_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v.get("criterion") == "contract_symbols_conformance" for v in result["violations"])


# ==============================================================================
# 4. Syntax Error Case (Broken AST)
# ==============================================================================

def test_dim4_syntax_error_broken_ast():
    contract = make_sample_contract("CLI_TOOL", "python")
    syntax_error_code = {
        "main.py": """
def process_data(
    return 123 +
"""
    }
    state = {
        "task": "Implementasi service.",
        "target_language": "python",
        "code_files": syntax_error_code,
        "contract": contract,
    }
    result = validate_developer_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v.get("criterion") == "ast_syntax_validity" for v in result["violations"])


# ==============================================================================
# 5. Constraint Violation Case (Exceeding max_files)
# ==============================================================================

def test_dim5_constraint_violation_too_many_files():
    contract = make_sample_contract("CLI_TOOL", "python")
    # Provide 5 files when max_files is 3
    too_many_files = {
        "main.py": "def process_data(): pass",
        "file2.py": "x = 2",
        "file3.py": "y = 3",
        "file4.py": "z = 4",
        "file5.py": "w = 5",
    }
    state = {
        "task": "Implementasi service.",
        "target_language": "python",
        "code_files": too_many_files,
        "contract": contract,
    }
    result = validate_developer_phase(state)
    assert result["verdict"] == "FAIL"
    assert any(v.get("criterion") == "constraint_compliance" for v in result["violations"])


# ==============================================================================
# 6. Repair-Success Attempt 1
# ==============================================================================

def test_dim6_repair_success_attempt_1():
    contract = make_sample_contract("CLI_TOOL", "python")
    state = {
        "task": "Implementasi service.",
        "target_language": "python",
        "code_files": {"main.py": "def broken("},
        "contract": contract,
        "repair_attempt_counts": {"developer": 0},
    }

    # Step 1: Pre-execution validator flags FAIL, increments count to 1
    step1_res = developer_validator_node(state)
    assert step1_res["developer_validator_contract"]["verdict"] == "FAIL"
    assert step1_res["repair_attempt_counts"]["developer"] == 1
    assert "developer_feedback" in step1_res
    state.update(step1_res)

    # Routes back to developer for repair
    assert route_after_developer_validator(state) == "developer"

    # Step 2: Developer fixes syntax on Attempt #1
    state["code_files"] = make_valid_code_files("CLI_TOOL", "python")

    # Step 3: Revalidation passes and routes to test suite
    step2_res = developer_validator_node(state)
    assert step2_res["developer_validator_contract"]["verdict"] == "PASS"
    state.update(step2_res)
    assert route_after_developer_validator(state) in ("frozen_oracle", "tester")


# ==============================================================================
# 7. Repair-Success Attempt 2
# ==============================================================================

def test_dim7_repair_success_attempt_2():
    contract = make_sample_contract("REST_API", "python")
    state = {
        "task": "Implementasi service.",
        "target_language": "python",
        "code_files": {},
        "contract": contract,
        "repair_attempt_counts": {"developer": 0},
    }

    # Attempt 0 -> FAIL -> count becomes 1
    s1 = developer_validator_node(state)
    assert s1["developer_validator_contract"]["verdict"] == "FAIL"
    state.update(s1)
    assert route_after_developer_validator(state) == "developer"

    # Attempt 1 -> Still fails (missing interface) -> count becomes 2
    state["code_files"] = {"main.py": "def wrong_name(): pass"}
    s2 = developer_validator_node(state)
    assert s2["developer_validator_contract"]["verdict"] == "FAIL"
    state.update(s2)
    assert route_after_developer_validator(state) == "developer"

    # Attempt 2 -> Successfully repaired
    state["code_files"] = make_valid_code_files("REST_API", "python")
    s3 = developer_validator_node(state)
    assert s3["developer_validator_contract"]["verdict"] == "PASS"
    state.update(s3)
    assert route_after_developer_validator(state) in ("frozen_oracle", "tester")


# ==============================================================================
# 8. Terminal Failure After Attempt 2 Exhaustion (Zero Downstream Leakage)
# ==============================================================================

def test_dim8_terminal_failure_after_attempt_exhaustion():
    contract = make_sample_contract("CLI_TOOL", "python")
    state = {
        "task": "Implementasi service.",
        "target_language": "python",
        "code_files": {"main.py": "def still_broken("},
        "contract": contract,
        "repair_attempt_counts": {"developer": 2},  # Already reached max 2 repairs
    }

    res = developer_validator_node(state)
    assert res["developer_validator_contract"]["verdict"] == "FAIL"
    assert res.get("status") == "terminal_failure_developer_boundary"

    state.update(res)
    # Wajib abort seketika ke END, tidak boleh dieksekusi di sandbox!
    assert route_after_developer_validator(state) == END


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
    contract = make_sample_contract(domain, lang)
    code_files = make_valid_code_files(domain, lang)
    state = {
        "task": f"Implementasi sistem {domain}.",
        "target_language": lang,
        "code_files": code_files,
        "contract": contract,
    }
    result = validate_developer_phase(state)
    assert result["verdict"] == "PASS", f"Failed for domain {domain}: {result['violations']}"
    assert len(result["violations"]) == 0
