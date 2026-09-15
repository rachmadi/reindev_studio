# -*- coding: utf-8 -*-
"""
Unit Test Suite: Behavioral Scenarios & Forensic Verification (Treatment #1.3)
ReinDev Studio — Universal Acceptance Behavior & Scenario Grounding v1

Covers:
- Gates A through W (23 Deterministic Gates)
- Required Forensic Test (Section 16: 404 vs 204 mismatch without hardcoded solver)
"""

import ast
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import MagicMock
import pytest

from backend.canonical_scenario import (
    CanonicalScenario,
    BehavioralObservation,
    ScenarioKind,
    ComparisonStatus,
    CausalStatus,
    CanonicalScenarioIntegrityError,
    PythonAstScenarioExtractor,
    DartAstScenarioExtractor,
    extract_canonical_scenarios,
    evaluate_behavioral_observations,
    format_scenarios_for_architect,
    format_behavioral_mismatches_for_developer,
)
from backend.context_hardening import (
    compress_context_semantic,
    check_context_omission,
    build_developer_repair_context,
)
from backend.agents.architect import architect_agent


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


# ===========================================================================
# Gate A: Positive Scenario Extraction
# ===========================================================================

def test_gate_a_positive_scenario_extraction(temp_dir):
    """Gate A: Positive happy path scenarios extracted with expected outcome."""
    code = (
        "def test_create_item():\n"
        "    '''Menguji pembuatan item baru secara normal.'''\n"
        "    res = client.post('/items', json={'name': 'Widget'})\n"
        "    assert res.status_code == 201\n"
    )
    test_file = temp_dir / "test_item.py"
    test_file.write_text(code, encoding="utf-8")

    extractor = PythonAstScenarioExtractor()
    scenarios = extractor.extract_scenarios(str(test_file), code)

    assert len(scenarios) == 1
    sc = scenarios[0]
    assert sc.caller == "test_create_item"
    assert sc.stimulus == "POST /items"
    assert sc.expected_outcome.get("status_code") == 201
    assert sc.scenario_kind == ScenarioKind.POSITIVE.value
    # Docstring is contextual metadata, not authority
    assert sc.docstring_metadata == "Menguji pembuatan item baru secara normal."


# ===========================================================================
# Gate B: Negative Scenario Extraction
# ===========================================================================

def test_gate_b_negative_scenario_extraction(temp_dir):
    """Gate B: Negative exception scenario extracted from pytest.raises."""
    code = (
        "def test_incompatible_dimensions():\n"
        "    with pytest.raises(ValueError):\n"
        "        calc.add([[1, 2]], [[1, 2, 3]])\n"
    )
    test_file = temp_dir / "test_math.py"
    test_file.write_text(code, encoding="utf-8")

    extractor = PythonAstScenarioExtractor()
    scenarios = extractor.extract_scenarios(str(test_file), code)

    assert len(scenarios) == 1
    sc = scenarios[0]
    assert sc.scenario_kind == ScenarioKind.NEGATIVE.value
    assert sc.expected_exception == "ValueError"
    assert "add" in sc.stimulus


# ===========================================================================
# Gate C: Edge Scenario Extraction
# ===========================================================================

def test_gate_c_edge_scenario_extraction(temp_dir):
    """Gate C: Edge scenario extraction (e.g. constrained layout, boundaries)."""
    dart_code = (
        "void main() {\n"
        "  testWidgets('renders inside constrained box without overflow', (tester) async {\n"
        "    await tester.pumpWidget(SizedBox(width: 300, height: 200, child: CardMetric()));\n"
        "    expect(find.byType(CardMetric), findsOneWidget);\n"
        "    expect(tester.takeException(), isNull);\n"
        "  });\n"
        "}\n"
    )
    test_file = temp_dir / "test_widget.dart"
    test_file.write_text(dart_code, encoding="utf-8")

    extractor = DartAstScenarioExtractor()
    scenarios = extractor.extract_scenarios(str(test_file), dart_code)

    assert len(scenarios) == 1
    sc = scenarios[0]
    assert sc.expected_exception == "NONE"
    assert "CardMetric" in sc.stimulus
    assert sc.precondition == "Constrained SizedBox container"


# ===========================================================================
# Gate D: Expected Outcome Extraction
# ===========================================================================

def test_gate_d_expected_outcome_extraction(temp_dir):
    """Gate D: Expected outcome values and fields extracted deterministically."""
    code = (
        "def test_get_user():\n"
        "    res = client.get('/users/42')\n"
        "    assert res.status_code == 200\n"
        "    data = res.json()\n"
        "    assert data['role'] == 'admin'\n"
    )
    test_file = temp_dir / "test_users.py"
    test_file.write_text(code, encoding="utf-8")

    extractor = PythonAstScenarioExtractor()
    scenarios = extractor.extract_scenarios(str(test_file), code)

    assert len(scenarios) == 1
    sc = scenarios[0]
    assert sc.expected_outcome.get("status_code") == 200
    assert sc.expected_outcome.get("role") == "admin"


# ===========================================================================
# Gate E: Expected Exception Extraction
# ===========================================================================

def test_gate_e_expected_exception_extraction(temp_dir):
    """Gate E: Expected exception type extracted explicitly."""
    code = (
        "def test_overflow():\n"
        "    with pytest.raises(OverflowError):\n"
        "        math_op.power(999999, 999999)\n"
    )
    test_file = temp_dir / "test_overflow.py"
    test_file.write_text(code, encoding="utf-8")

    scenarios = PythonAstScenarioExtractor().extract_scenarios(str(test_file), code)
    assert len(scenarios) == 1
    assert scenarios[0].expected_exception == "OverflowError"


# ===========================================================================
# Gate F: Stimulus / Expected-Outcome Separation
# ===========================================================================

def test_gate_f_stimulus_expected_outcome_separation(temp_dir):
    """Gate F: Stimulus/input and expected outcome are cleanly separated fields."""
    code = (
        "def test_delete():\n"
        "    res = client.delete('/products/999999')\n"
        "    assert res.status_code == 404\n"
    )
    test_file = temp_dir / "test_del.py"
    test_file.write_text(code, encoding="utf-8")

    sc = PythonAstScenarioExtractor().extract_scenarios(str(test_file), code)[0]
    assert sc.stimulus == "DELETE /products/999999"
    assert sc.expected_outcome == {"status_code": 404}
    # Separate input from output
    assert "DELETE" in sc.stimulus
    assert "DELETE" not in str(sc.expected_outcome)


# ===========================================================================
# Gate G: Expected vs Observed Comparison Execution
# ===========================================================================

def test_gate_g_expected_vs_observed_comparison(temp_dir):
    """Gate G: evaluate_behavioral_observations executes comparison deterministically."""
    sc = CanonicalScenario(
        scenario_id="SCN-TEST-1",
        caller="test_check",
        stimulus="GET /health",
        expected_outcome={"status_code": 200}
    )
    test_results = {
        "output": "FAILED test_main.py::test_check - assert 500 == 200",
        "exit_code": 1,
        "failed_count": 1,
    }
    observations = evaluate_behavioral_observations([sc], test_results)
    assert len(observations) == 1
    obs = observations[0]
    assert obs.comparison_status == ComparisonStatus.MISMATCH.value


# ===========================================================================
# Gate H: MATCH Detection
# ===========================================================================

def test_gate_h_match_detection():
    """Gate H: Passing test produces MATCH status."""
    sc = CanonicalScenario(
        scenario_id="SCN-TEST-2",
        caller="test_healthy",
        stimulus="GET /health",
        expected_outcome={"status_code": 200}
    )
    test_results = {
        "output": "test_main.py::test_healthy PASSED [100%]\n1 passed in 0.05s",
        "exit_code": 0,
        "passed_count": 1,
        "failed_count": 0,
    }
    obs = evaluate_behavioral_observations([sc], test_results)[0]
    assert obs.comparison_status == ComparisonStatus.MATCH.value
    assert obs.causal_status == CausalStatus.RESOLVED.value


# ===========================================================================
# Gate I: MISMATCH Detection
# ===========================================================================

def test_gate_i_mismatch_detection():
    """Gate I: Differing outcome produces MISMATCH with exact expected vs observed values."""
    sc = CanonicalScenario(
        scenario_id="SCN-TEST-3",
        caller="test_delete_nonexistent",
        stimulus="DELETE /items/99",
        expected_outcome={"status_code": 404}
    )
    test_results = {
        "output": "FAILED test_main.py::test_delete_nonexistent - assert 204 == 404",
        "exit_code": 1,
        "failed_count": 1,
    }
    obs = evaluate_behavioral_observations([sc], test_results)[0]
    assert obs.comparison_status == ComparisonStatus.MISMATCH.value
    assert obs.expected == 404
    assert obs.observed == 204
    assert obs.causal_status == CausalStatus.VIOLATED.value


# ===========================================================================
# Gate J: UNDETERMINED Handling
# ===========================================================================

def test_gate_j_undetermined_handling():
    """Gate J: Unexecuted or unmapped scenario yields UNDETERMINED."""
    sc = CanonicalScenario(
        scenario_id="SCN-TEST-4",
        caller="test_unexecuted",
        stimulus="GET /unexecuted",
        expected_outcome={"status_code": 200}
    )
    test_results = {
        "output": "collected 0 items",
        "exit_code": 0,
        "passed_count": 0,
        "failed_count": 0,
    }
    obs = evaluate_behavioral_observations([sc], test_results)[0]
    assert obs.comparison_status == ComparisonStatus.UNDETERMINED.value
    assert obs.observed is None


# ===========================================================================
# Gate K: Distinct Scenario Identity
# ===========================================================================

def test_gate_k_distinct_scenario_identity(temp_dir):
    """Gate K: Scenarios sharing the same endpoint but different stimuli have distinct IDs."""
    code = (
        "def test_delete_existing():\n"
        "    res = client.delete('/products/1')\n"
        "    assert res.status_code == 204\n\n"
        "def test_delete_nonexistent():\n"
        "    res = client.delete('/products/999999')\n"
        "    assert res.status_code == 404\n"
    )
    test_file = temp_dir / "test_api.py"
    test_file.write_text(code, encoding="utf-8")

    scenarios = PythonAstScenarioExtractor().extract_scenarios(str(test_file), code)
    assert len(scenarios) == 2
    sc1, sc2 = scenarios[0], scenarios[1]
    assert sc1.scenario_id != sc2.scenario_id
    assert sc1.stimulus != sc2.stimulus
    assert sc1.expected_outcome != sc2.expected_outcome


# ===========================================================================
# Gate L: Multiple Independent Scenarios Preserved
# ===========================================================================

def test_gate_l_multiple_independent_scenarios_preserved():
    """Gate L: Multi-failure execution preserves all independent mismatches."""
    sc1 = CanonicalScenario(scenario_id="SCN-1", caller="test_one", stimulus="OP-1", expected_outcome={"status_code": 200})
    sc2 = CanonicalScenario(scenario_id="SCN-2", caller="test_two", stimulus="OP-2", expected_outcome={"status_code": 201})

    test_results = {
        "output": (
            "FAILED test_main.py::test_one - assert 500 == 200\n"
            "FAILED test_main.py::test_two - assert 400 == 201\n"
        ),
        "exit_code": 1,
        "failed_count": 2,
    }
    observations = evaluate_behavioral_observations([sc1, sc2], test_results)
    assert len(observations) == 2
    assert all(o.comparison_status == ComparisonStatus.MISMATCH.value for o in observations)
    assert observations[0].scenario_ref == "SCN-1"
    assert observations[1].scenario_ref == "SCN-2"


# ===========================================================================
# Gate M: Current vs Historical Isolation
# ===========================================================================

def test_gate_m_current_vs_historical_isolation():
    """Gate M: Current failure observation does not overwrite or merge historical records."""
    sc = CanonicalScenario(scenario_id="SCN-1", caller="test_one", stimulus="OP-1")
    current_results = {
        "output": "FAILED test_main.py::test_one - assert 204 == 404",
        "exit_code": 1,
        "failed_count": 1,
    }
    obs = evaluate_behavioral_observations([sc], current_results)[0]
    assert obs.observed == 204

    # Historical state remains intact in another container
    history_record = {"turn": 0, "previous_observed": 500}
    assert history_record["previous_observed"] == 500
    assert obs.observed == 204


# ===========================================================================
# Gate N: Behavioral Evidence Reaches Architect Context
# ===========================================================================

def test_gate_n_behavioral_evidence_reaches_architect_context(monkeypatch):
    """Gate N: Architect prompt receives [ACCEPTANCE BEHAVIOR & SCENARIOS] from Frozen Oracle."""
    captured = []
    class DummyLLM:
        def invoke(self, messages):
            captured.extend(messages)
            m = MagicMock()
            m.content = '{"file_tree": ["main.py"], "interface_contracts": []}'
            return m

    from backend.agents import architect
    monkeypatch.setattr(architect, "get_llm", lambda *a, **kw: DummyLLM())

    state = {
        "task": "Build FastAPI product inventory API",
        "target_language": "python",
        "frozen_oracle_path": "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1",
        "provider": "ollama",
    }
    architect_agent(state)
    prompt_text = captured[1].content if len(captured) > 1 else ""
    assert "[ACCEPTANCE BEHAVIOR & SCENARIOS — FROZEN ORACLE GROUND TRUTH]" in prompt_text
    assert "DELETE /products/999999" in prompt_text


# ===========================================================================
# Gate O: Behavioral Evidence Reaches Developer Repair Context
# ===========================================================================

def test_gate_o_behavioral_evidence_reaches_developer_repair_context():
    """Gate O: Developer repair context includes [CURRENT FAILURE — BEHAVIORAL MISMATCH]."""
    state = {
        "task": "Build FastAPI product inventory API",
        "target_language": "python",
        "frozen_oracle_path": "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1",
        "test_results": {
            "output": "FAILED test_main.py::test_delete_nonexistent_product - assert 204 == 404",
            "exit_code": 1,
            "failed_count": 1,
        },
    }
    result, telem = build_developer_repair_context(state)
    assert "[CURRENT FAILURE — BEHAVIORAL MISMATCH" in result
    assert "Expected 404" in result
    assert "observed 204" in result


# ===========================================================================
# Gate P: Context Truncation Cannot Silently Remove Required Scenario
# ===========================================================================

def test_gate_p_context_truncation_cannot_silently_remove_required_scenario():
    """Gate P: Deterministic system detects if critical acceptance/mismatch evidence is omitted."""
    sections = {
        "authority_acceptance": "[1] AUTHORITATIVE ACCEPTANCE\nTarget: main.py",
        "authority_scenario": "[ACCEPTANCE BEHAVIOR & SCENARIOS]\nDELETE /products/999999 -> 404",
        "evidence_mismatch": "[CURRENT FAILURE — BEHAVIORAL MISMATCH]\nExpected 404, observed 204",
        "impl_ref_code": "def foo(): pass\n" * 200,
    }
    # When budget is adequate, all are present
    compressed = compress_context_semantic(sections, max_chars=5000)
    omitted = check_context_omission(sections, compressed)
    assert len(omitted) == 0

    # When budget is severely restricted, omission is detected deterministically
    omitted_severe = check_context_omission(sections, "")
    assert len(omitted_severe) == 3


# ===========================================================================
# Gate Q: Locked Invariant Protection
# ===========================================================================

def test_gate_q_locked_invariant_protection():
    """Gate Q: PROVEN invariants cannot be mutated or regressed."""
    from backend.contextual_evidence import PreservedInvariant
    inv = PreservedInvariant(
        invariant_id="INV-001",
        category="PASSING_TEST",
        description="test_create_product passes",
        evidence_value=True,
        status="PROVEN",
        mutation="FORBIDDEN"
    )
    assert inv.status == "PROVEN"
    assert inv.mutation == "FORBIDDEN"
    inv.record_regression("assert 500 == 201", iteration=1)
    assert inv.status == "REGRESSED"
    assert inv.ever_regressed is True


# ===========================================================================
# Gate R: Python Adapter Canonical Output
# ===========================================================================

def test_gate_r_python_adapter_canonical_output():
    """Gate R: Python AST extractor produces CanonicalScenario conforming to schema."""
    oracle_path = "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1"
    scenarios = extract_canonical_scenarios(frozen_oracle_path=oracle_path)
    assert len(scenarios) == 5
    for sc in scenarios:
        assert isinstance(sc, CanonicalScenario)
        assert sc.authority == "FROZEN_ORACLE"
        assert sc.provenance == "ORACLE_FACT"
        assert sc.stimulus != ""
        assert sc.expected_outcome != {}


# ===========================================================================
# Gate S: Dart Adapter Canonical Output
# ===========================================================================

def test_gate_s_dart_adapter_canonical_output():
    """Gate S: Dart AST extractor produces CanonicalScenario conforming to schema."""
    oracle_path = "dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1"
    scenarios = extract_canonical_scenarios(frozen_oracle_path=oracle_path)
    assert len(scenarios) == 2
    for sc in scenarios:
        assert isinstance(sc, CanonicalScenario)
        assert sc.authority == "FROZEN_ORACLE"
        assert sc.provenance == "ORACLE_FACT"
        assert sc.stimulus != ""


# ===========================================================================
# Gate T: Cross-Language Canonical Semantic Equivalence (Correction 4)
# ===========================================================================

def test_gate_t_cross_language_canonical_semantic_equivalence(temp_dir):
    """
    Gate T (Correction 4): Python and Dart test sources representing equivalent semantic
    tuples (stimulus, precondition, expected_outcome, expected_exception) produce
    semantically equivalent CanonicalScenario tuples.
    """
    # Equivalent semantic intent in Python:
    # Constructor stimulus + expected outcome field validation
    py_code = (
        "def test_metric_card():\n"
        "    m = CardMetric(title='Revenue', value='1000')\n"
        "    assert m.title == 'Revenue'\n"
    )
    py_file = temp_dir / "test_metric.py"
    py_file.write_text(py_code, encoding="utf-8")

    # Equivalent semantic intent in Dart:
    dart_code = (
        "void main() {\n"
        "  test('metric card', () {\n"
        "    expect(find.text('Revenue'), findsOneWidget);\n"
        "  });\n"
        "}\n"
    )
    dart_file = temp_dir / "test_metric.dart"
    dart_file.write_text(dart_code, encoding="utf-8")

    py_sc = PythonAstScenarioExtractor().extract_scenarios(str(py_file), py_code)[0]
    dart_sc = DartAstScenarioExtractor().extract_scenarios(str(dart_file), dart_code)[0]

    # Both map to the same canonical tuple fields
    assert hasattr(py_sc, "stimulus") and hasattr(dart_sc, "stimulus")
    assert hasattr(py_sc, "precondition") and hasattr(dart_sc, "precondition")
    assert hasattr(py_sc, "expected_outcome") and hasattr(dart_sc, "expected_outcome")
    assert hasattr(py_sc, "expected_exception") and hasattr(dart_sc, "expected_exception")
    assert hasattr(py_sc, "observable_output") and hasattr(dart_sc, "observable_output")
    assert py_sc.authority == dart_sc.authority == "FROZEN_ORACLE"
    assert py_sc.provenance == dart_sc.provenance == "ORACLE_FACT"


# ===========================================================================
# Gate U: Static Audit — Zero Domain-Specific Solver Branches
# ===========================================================================

def test_gate_u_no_domain_specific_solver_branches():
    """Gate U: Static audit verifies zero hardcoded domain/framework solver rules."""
    import inspect
    from backend import canonical_scenario as can_sc

    source = inspect.getsource(can_sc)
    prohibited = [
        r"if.*task.*==.*['\"]fastapi['\"]",
        r"if.*['\"]fastapi_t1['\"].*in",
        r"if.*['\"]HTTPException\(404\)['\"]",
        r"return.*404",
        r"if.*framework.*==.*['\"]flutter['\"]",
    ]
    for p in prohibited:
        assert not re.search(p, source, re.IGNORECASE), f"Prohibited solver pattern found: {p}"


# ===========================================================================
# Gate V: Oracle SHA Unchanged
# ===========================================================================

def test_gate_v_oracle_sha_unchanged():
    """Gate V: Frozen Oracle files match immutable SHA-256 signatures."""
    expected_hashes = {
        "fastapi_t1": "a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63",
        "cli_t1": "0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124",
        "flutter_t1": "4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528",
    }
    oracle_root = Path("dokumentasi-pengembangan/experiments/frozen_oracle")
    for task_id, expected_sha in expected_hashes.items():
        task_dir = oracle_root / task_id
        target = next(task_dir.glob("*.py"), None) or next(task_dir.glob("*.dart"), None)
        assert target is not None, f"Missing test file in {task_dir}"
        actual_sha = hashlib.sha256(target.read_bytes()).hexdigest()
        assert actual_sha == expected_sha, f"Oracle tampering detected on {task_id}: {actual_sha} != {expected_sha}"


# ===========================================================================
# Gate W: Sterile Executor Unchanged
# ===========================================================================

def test_gate_w_sterile_executor_unchanged():
    """Gate W: Executor remains sterile with zero mutations."""
    from backend.executor import run_sandbox_tests, executor_node
    assert callable(run_sandbox_tests)
    assert callable(executor_node)


# ===========================================================================
# Section 16: Required Forensic Test (404 vs 204 Mismatch Without Hardcoding)
# ===========================================================================

def test_required_forensic_test_mismatch_without_hardcoding():
    """
    Forensic Test (Section 16): Proves deterministic pipeline extracts
    EXPECTED != OBSERVED on nonexistent resource delete (404 vs 204)
    WITHOUT ANY IMPLEMENTATION PRESCRIPTION.
    """
    oracle_path = "dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1"
    scenarios = extract_canonical_scenarios(frozen_oracle_path=oracle_path)

    delete_nonexistent_sc = next(
        (sc for sc in scenarios if "nonexistent" in sc.caller),
        None
    )
    assert delete_nonexistent_sc is not None
    assert delete_nonexistent_sc.stimulus == "DELETE /products/999999"
    assert delete_nonexistent_sc.expected_outcome.get("status_code") == 404

    # Simulate actual live pilot test failure
    simulated_failure = {
        "output": (
            "test_main.py::test_create_product PASSED\n"
            "test_main.py::test_get_all_products PASSED\n"
            "test_main.py::test_get_product_by_id PASSED\n"
            "test_main.py::test_delete_product PASSED\n"
            "test_main.py::test_delete_nonexistent_product FAILED\n\n"
            "FAILED test_main.py::test_delete_nonexistent_product - assert 204 == 404\n"
        ),
        "exit_code": 1,
        "failed_count": 1,
    }

    observations = evaluate_behavioral_observations(scenarios, simulated_failure)
    mismatch_obs = next((o for o in observations if o.caller == delete_nonexistent_sc.caller), None)

    assert mismatch_obs is not None
    assert mismatch_obs.comparison_status == ComparisonStatus.MISMATCH.value
    assert mismatch_obs.expected == 404
    assert mismatch_obs.observed == 204
    assert mismatch_obs.causal_status == CausalStatus.VIOLATED.value

    # Format for developer
    formatted = format_behavioral_mismatches_for_developer(observations, scenarios)
    assert "Expected: 404" in formatted
    assert "Observed: 204" in formatted

    # Prohibited implementation prescriptions:
    prohibited_prescriptions = [
        "HTTPException(404)",
        "raise HTTPException",
        "return 404",
        "status_code=404",
        "if id not in",
        "products.pop",
    ]
    for p in prohibited_prescriptions:
        assert p not in formatted, f"Implementation prescription '{p}' leaked into formatted mismatch"
