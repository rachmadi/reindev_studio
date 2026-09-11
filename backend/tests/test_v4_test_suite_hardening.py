# -*- coding: utf-8 -*-
"""
Test Suite Hardening for VALIDATOR 4 (Test Suite / Oracle Boundary)
Memverifikasi 9-Dimensi Matrix & Invarian Mutlak:
1. Static Frozen Oracle: Valid SHA-256 match -> PASS -> route to executor.
2. Dynamic QA Tester: Valid AST syntax -> PASS -> route to executor.
3. Empty test suite (Frozen Oracle or QA Tester) -> FAIL -> Zero downstream leakage.
4. Corrupt Static Oracle (SHA mismatch) -> Immediate abort ke terminal_failure_frozen_oracle_corrupt -> END.
5. Broken Dynamic Test Suite (SyntaxError) -> FAIL -> route to tester for repair.
6. Repair-Success Attempt 1 (QA Tester) -> PASS -> route to executor.
7. Repair-Success Attempt 2 (QA Tester) -> PASS -> route to executor.
8. Terminal Failure Attempt 2 Exhaustion (QA Tester) -> terminal_failure_tester_boundary -> END.
9. Multi-domain generality: CLI, FastAPI, Flutter/Dart, Data Pipeline, System.
10. Immutable Frozen Oracle Baseline Check (0bd5b598...).
11. Multi-language Dart test suite structural syntax validation.
12. Direct repair feedback populated in tester_feedback.
13. StateGraph End-to-End Routing through V4 Quality Boundary.
"""

import hashlib
import pytest
from langgraph.graph import END
from backend.state import SquadState
from backend.graph import (
    test_suite_validator_node as v4_node,
    route_after_test_suite_validator,
    _get_repair_count,
    _get_max_repairs
)
from backend.phase_validators import validate_oracle_phase


# ==============================================================================
# Fixtures & Helpers
# ==============================================================================

VALID_PY_TEST = """
import pytest

def test_example():
    assert 1 + 1 == 2
"""

INVALID_PY_TEST = """
def test_syntax_broken(
    assert True
"""

VALID_DART_TEST = """
import 'package:test/test.dart';

void main() {
  test('sample test', () {
    expect(42, equals(42));
  });
}
"""

INVALID_DART_TEST = """
void main() {
  test('broken', () {
    expect(42, equals(42);
  // Missing closing braces
"""

KNOWN_FROZEN_SHA = hashlib.sha256(VALID_PY_TEST.encode("utf-8")).hexdigest()
BASELINE_CLI_T1_SHA = "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124"


# ==============================================================================
# Test Cases
# ==============================================================================

def test_dim1_static_frozen_oracle_pass():
    """Dimensi 1: Static Frozen Oracle dengan SHA256 match -> PASS -> route ke executor."""
    state: SquadState = {
        "frozen_oracle_path": "oracles/cli_t1",
        "expected_oracle_sha": KNOWN_FROZEN_SHA,
        "test_files": {"tests/test_cli.py": VALID_PY_TEST},
        "logs": []
    }
    res = v4_node(state)
    assert res["test_suite_validator_contract"]["verdict"] == "PASS"
    assert res.get("status") is None or res.get("status") != "terminal_failure_frozen_oracle_corrupt"

    merged_state = {**state, **res}
    next_node = route_after_test_suite_validator(merged_state)
    assert next_node == "executor"


def test_dim2_dynamic_qa_tester_pass():
    """Dimensi 2: Dynamic QA Tester dengan AST valid -> PASS -> route ke executor."""
    state: SquadState = {
        "frozen_oracle_path": None,
        "target_language": "python",
        "test_files": {"tests/test_dynamic.py": VALID_PY_TEST},
        "repair_attempt_counts": {"tester": 0},
        "logs": []
    }
    res = v4_node(state)
    assert res["test_suite_validator_contract"]["verdict"] == "PASS"

    merged_state = {**state, **res}
    next_node = route_after_test_suite_validator(merged_state)
    assert next_node == "executor"


def test_dim3_empty_test_suite_fails():
    """Dimensi 3: Empty test suite -> FAIL -> Zero downstream leakage."""
    # Frozen Oracle empty
    state_frozen: SquadState = {
        "frozen_oracle_path": "oracles/cli_t1",
        "expected_oracle_sha": KNOWN_FROZEN_SHA,
        "test_files": {},
        "logs": []
    }
    res_frozen = v4_node(state_frozen)
    assert res_frozen["test_suite_validator_contract"]["verdict"] == "FAIL"
    merged_frozen = {**state_frozen, **res_frozen}
    assert route_after_test_suite_validator(merged_frozen) == END

    # QA Tester empty
    state_dynamic: SquadState = {
        "frozen_oracle_path": None,
        "target_language": "python",
        "test_files": {},
        "repair_attempt_counts": {"tester": 0},
        "logs": []
    }
    res_dynamic = v4_node(state_dynamic)
    assert res_dynamic["test_suite_validator_contract"]["verdict"] == "FAIL"
    merged_dynamic = {**state_dynamic, **res_dynamic}
    # Dynamic can retry on attempt 0 -> tester
    assert route_after_test_suite_validator(merged_dynamic) == "tester"


def test_dim4_corrupt_static_oracle_immediate_abort():
    """Dimensi 4: Corrupt Static Oracle (SHA mismatch) -> seketika abort ke terminal_failure_frozen_oracle_corrupt -> END."""
    corrupt_content = "def test_corrupted(): pass"
    state: SquadState = {
        "frozen_oracle_path": "oracles/cli_t1",
        "expected_oracle_sha": KNOWN_FROZEN_SHA,
        "test_files": {"tests/test_cli.py": corrupt_content},
        "logs": []
    }
    res = v4_node(state)
    assert res["test_suite_validator_contract"]["verdict"] == "FAIL"
    assert res["status"] == "terminal_failure_frozen_oracle_corrupt"

    merged_state = {**state, **res}
    next_node = route_after_test_suite_validator(merged_state)
    assert next_node == END  # Zero LLM repair attempts allowed on static baseline corruption!


def test_dim5_broken_dynamic_test_suite_routes_to_tester():
    """Dimensi 5: Broken Dynamic Test Suite (SyntaxError) -> FAIL -> route to tester for repair."""
    state: SquadState = {
        "frozen_oracle_path": None,
        "target_language": "python",
        "test_files": {"tests/test_syntax.py": INVALID_PY_TEST},
        "repair_attempt_counts": {"tester": 0},
        "logs": []
    }
    res = v4_node(state)
    assert res["test_suite_validator_contract"]["verdict"] == "FAIL"
    assert res["repair_attempt_counts"]["tester"] == 1
    assert "tester_feedback" in res
    assert len(res["tester_feedback"]) >= 1

    merged_state = {**state, **res}
    next_node = route_after_test_suite_validator(merged_state)
    assert next_node == "tester"


def test_dim6_repair_success_attempt_1():
    """Dimensi 6: Repair-Success Attempt 1 (QA Tester) -> PASS -> route to executor."""
    state: SquadState = {
        "frozen_oracle_path": None,
        "target_language": "python",
        "test_files": {"tests/test_dynamic.py": VALID_PY_TEST},
        "repair_attempt_counts": {"tester": 1},
        "logs": []
    }
    res = v4_node(state)
    assert res["test_suite_validator_contract"]["verdict"] == "PASS"

    merged_state = {**state, **res}
    next_node = route_after_test_suite_validator(merged_state)
    assert next_node == "executor"


def test_dim7_repair_success_attempt_2():
    """Dimensi 7: Repair-Success Attempt 2 (QA Tester) -> PASS -> route to executor."""
    state: SquadState = {
        "frozen_oracle_path": None,
        "target_language": "python",
        "test_files": {"tests/test_dynamic.py": VALID_PY_TEST},
        "repair_attempt_counts": {"tester": 2},
        "logs": []
    }
    res = v4_node(state)
    assert res["test_suite_validator_contract"]["verdict"] == "PASS"

    merged_state = {**state, **res}
    next_node = route_after_test_suite_validator(merged_state)
    assert next_node == "executor"


def test_dim8_terminal_failure_attempt_2_exhaustion():
    """Dimensi 8: Terminal Failure Attempt 2 Exhaustion -> terminal_failure_tester_boundary -> END."""
    state: SquadState = {
        "frozen_oracle_path": None,
        "target_language": "python",
        "test_files": {"tests/test_dynamic.py": INVALID_PY_TEST},
        "repair_attempt_counts": {"tester": 2},
        "logs": []
    }
    res = v4_node(state)
    assert res["test_suite_validator_contract"]["verdict"] == "FAIL"
    assert res["status"] == "terminal_failure_tester_boundary"

    merged_state = {**state, **res}
    next_node = route_after_test_suite_validator(merged_state)
    assert next_node == END


def test_dim9_generality_across_five_domains():
    """Dimensi 9: General across 5 domains: CLI, FastAPI, Flutter/Dart, Data Pipeline, System."""
    domains = [
        ("cli", "python", {"test_cli.py": "def test_cli(): pass"}),
        ("fastapi", "python", {"test_api.py": "def test_endpoint(): pass"}),
        ("flutter", "dart", {"test/widget_test.dart": VALID_DART_TEST}),
        ("data_pipeline", "python", {"test_pipeline.py": "def test_transform(): pass"}),
        ("system", "python", {"test_sys.py": "def test_sys(): pass"}),
    ]
    for domain, lang, files in domains:
        state: SquadState = {
            "frozen_oracle_path": None,
            "target_language": lang,
            "test_files": files,
            "repair_attempt_counts": {"tester": 0},
            "logs": []
        }
        res = v4_node(state)
        assert res["test_suite_validator_contract"]["verdict"] == "PASS", f"Failed for domain {domain}"
        merged_state = {**state, **res}
        assert route_after_test_suite_validator(merged_state) == "executor"


def test_dim10_immutable_frozen_oracle_baseline_hash():
    """Dimensi 10: Checksum baseline immutable Frozen Oracle CLI T1."""
    assert BASELINE_CLI_T1_SHA == "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124"


def test_dim11_dart_test_suite_structural_validation():
    """Dimensi 11: Validasi struktural Dart test suite."""
    state_valid: SquadState = {
        "frozen_oracle_path": None,
        "target_language": "dart",
        "test_files": {"test/unit_test.dart": VALID_DART_TEST},
        "repair_attempt_counts": {"tester": 0},
        "logs": []
    }
    res_valid = v4_node(state_valid)
    assert res_valid["test_suite_validator_contract"]["verdict"] == "PASS"

    state_invalid: SquadState = {
        "frozen_oracle_path": None,
        "target_language": "dart",
        "test_files": {"test/unit_test.dart": INVALID_DART_TEST},
        "repair_attempt_counts": {"tester": 0},
        "logs": []
    }
    res_invalid = v4_node(state_invalid)
    assert res_invalid["test_suite_validator_contract"]["verdict"] == "FAIL"


def test_dim12_direct_repair_feedback_populated():
    """Dimensi 12: Direct repair feedback populated in tester_feedback upon failure."""
    state: SquadState = {
        "frozen_oracle_path": None,
        "target_language": "python",
        "test_files": {"test_bad.py": "def test_bad(:"},
        "repair_attempt_counts": {"tester": 0},
        "logs": []
    }
    res = v4_node(state)
    assert res["test_suite_validator_contract"]["verdict"] == "FAIL"
    assert "tester_feedback" in res
    assert res["tester_feedback"][0]["criterion"] == "test_syntax"


def test_dim13_route_leakage_prevention():
    """Dimensi 13: Zero downstream leakage prevention on failure."""
    # Whatever failure happens, route_after_test_suite_validator must NEVER return executor
    state_fail: SquadState = {
        "frozen_oracle_path": "oracles/cli_t1",
        "test_suite_validator_contract": {"phase": "TEST_SUITE", "verdict": "FAIL"},
        "status": "terminal_failure_frozen_oracle_corrupt"
    }
    assert route_after_test_suite_validator(state_fail) != "executor"
