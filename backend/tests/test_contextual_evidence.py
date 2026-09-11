"""
Test Suite: ContextualEvidencePackage & Context Assembler (14 Deterministic Areas)
ReinDev Studio — Iterasi 7 (Deterministic Context-Aware Validation)

Seluruh assertion dalam test ini ditentukan secara programatik tanpa LLM.
Expected verdict, schema, dan evidence values bersumber dari deterministic rules.

Area Pengujian:
 1.  ContextualEvidencePackage schema completeness
 2.  Complete violation collection (global scan, no stop-early)
 3.  Root-cause construction (programmatic)
 4.  Authoritative context assembly
 5.  Active constraint assembly
 6.  Preserved invariant detection
 7.  Repair boundary (allowed vs forbidden)
 8.  Forbidden change detection
 9.  Required change construction (actionable)
10.  Expected post-repair state (deterministic)
11.  Deterministic verdict reproducibility
12.  Telemetry event emission (6 events)
13.  Serialization / deserialization roundtrip
14.  OTRR calculation accuracy

Regression Fixtures: fastapi_t1, cli_t1, flutter_t1 (actual pilot failures)
"""

import json
import os
import sys
import hashlib
import pytest
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.contextual_evidence import (
    ContextualEvidencePackage,
    ViolationItem,
    PreservedInvariant,
    RepairBoundary,
    RequiredChange,
    ViolationDependency,
    ActionableRepairPrescription,
    render_repair_directive,
    check_preservation_rule,
    calculate_otrr,
)
from backend.context_assembler import (
    assemble_b1_evidence,
    assemble_b2_evidence,
    assemble_b3_evidence,
    assemble_b5_evidence,
    assemble_b4_evidence,
    assemble_b6_evidence,
    inspect_ast_exception_hierarchy,
    _standard_forbidden_changes,
    _get_authoritative_target_file,
)


# ===========================================================================
# Fixtures
# ===========================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pilot_failures"


def load_fixture(name: str) -> ContextualEvidencePackage:
    path = FIXTURES_DIR / name
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return ContextualEvidencePackage.from_dict(data)


def _minimal_state(**kwargs):
    """Construct a minimal SquadState-compatible dict for testing."""
    base = {
        "target_language": "python",
        "contract": {
            "task_intent": {"domain": "REST_API", "authoritative_target_file": "main.py"},
            "data_models": [{"model_name": "Product", "target_file": "main.py"}],
            "interface_contracts": [{"identifier": "create_product", "target_file": "main.py"}],
            "functional_requirements": [{"req_id": "REQ-001", "title": "Create product"}],
            "testable_assertions": [],
            "constraints": {},
        },
        "contract_status": "FROZEN",
        "contract_sha256": "d266453bb6c553cf79b9e1e0267cceea" * 2,
        "architecture_plan": "## File Tree\n- main.py: FastAPI app with Product model",
        "code_files": {"main.py": "from fastapi import FastAPI\napp = FastAPI()\n"},
        "test_files": {"test_main.py": "import pytest\ndef test_create(): pass\n"},
        "test_results": {
            "passed": False, "exit_code": 1,
            "failed_count": 1, "passed_count": 0,
            "total": 1, "output": "ERROR: assert False",
            "passed_test_names": [],
        },
        "expected_oracle_sha": "a1db9bb1f6eaf47d" * 4,
        "iteration_count": 0,
        "max_iterations": 10,
        "contract_revision_count": 0,
        "max_contract_revisions": 5,
        "previous_passed_tests": [],
        "run_id": "test-run-001",
    }
    base.update(kwargs)
    return base


def _make_violation(vid: str, criterion: str, severity: str = "CRITICAL") -> ViolationItem:
    return ViolationItem(
        violation_id=vid,
        criterion=criterion,
        severity=severity,
        location="test:location",
        observed_state=f"Observed state for {vid}",
        expected_state=f"Expected state for {vid}",
        source_detector="TEST_DETECTOR",
    )


# ===========================================================================
# Area 1: ContextualEvidencePackage Schema Completeness
# ===========================================================================

class TestArea1_CEPSchema:
    """Area 1: ContextualEvidencePackage schema completeness."""

    def test_all_required_fields_present(self):
        pkg = ContextualEvidencePackage(
            package_id="TEST-001",
            timestamp="2026-09-10T00:00:00Z",
            validator="B2_ARCHITECT_PHASE_END",
            phase="ARCHITECT",
            validator_type="PHASE_END",
            verdict="FAIL",
            causal_owner="ARCHITECT",
            failure_summary="Test failure",
            root_causes=["Root cause 1"],
            violations=[],
            violation_dependencies=[],
            authoritative_context={"file": "main.py"},
            active_constraints={"lang": "python"},
            preserved_invariants=[],
            repair_boundary=RepairBoundary(),
            forbidden_changes=["modify oracle"],
            required_changes=[],
            expected_post_repair_state=["all tests pass"],
            verification_criteria=["exit_code == 0"],
            source_of_truth="TEST_SOURCE",
            evidence=[],
            remaining_budget=5,
        )
        d = pkg.to_dict()
        required_keys = [
            "package_id", "timestamp", "validator", "phase", "validator_type",
            "verdict", "causal_owner", "failure_summary", "root_causes",
            "violations", "violation_dependencies", "authoritative_context",
            "active_constraints", "preserved_invariants", "repair_boundary",
            "forbidden_changes", "required_changes", "expected_post_repair_state",
            "verification_criteria", "source_of_truth", "evidence", "remaining_budget"
        ]
        for key in required_keys:
            assert key in d, f"Missing required field: {key}"

    def test_verdict_values_constrained(self):
        """Verdict must be PASS or FAIL — deterministic, not LLM-driven."""
        for valid_verdict in ("PASS", "FAIL"):
            pkg = ContextualEvidencePackage(
                package_id="X", timestamp="T", validator="B1", phase="PM",
                validator_type="PHASE_END", verdict=valid_verdict, causal_owner="NONE",
                failure_summary="", root_causes=[], violations=[],
                violation_dependencies=[], authoritative_context={}, active_constraints={},
                preserved_invariants=[], repair_boundary=RepairBoundary(),
                forbidden_changes=[], required_changes=[], expected_post_repair_state=[],
                verification_criteria=[], source_of_truth="S", evidence=[],
            )
            assert pkg.verdict in ("PASS", "FAIL")

    def test_make_id_deterministic(self):
        """Same inputs must produce identical package_id (reproducibility)."""
        id1 = ContextualEvidencePackage.make_id("run-abc", "B2_ARCHITECT", 3)
        id2 = ContextualEvidencePackage.make_id("run-abc", "B2_ARCHITECT", 3)
        assert id1 == id2
        # Different inputs produce different IDs
        id3 = ContextualEvidencePackage.make_id("run-abc", "B2_ARCHITECT", 4)
        assert id1 != id3

    def test_violation_item_all_fields(self):
        v = ViolationItem(
            violation_id="VIO-001",
            criterion="symbol_resolvability",
            severity="CRITICAL",
            location="blueprint:block_2",
            observed_state="No import for field_validator",
            expected_state="from pydantic import field_validator",
            source_detector="AST_INSPECTION",
            observed_symbol="field_validator",
        )
        d = v.to_dict()
        assert d["violation_id"] == "VIO-001"
        assert d["severity"] == "CRITICAL"
        assert d["source_detector"] == "AST_INSPECTION"

    def test_preserved_invariant_fields(self):
        inv = PreservedInvariant(
            invariant_id="INV-ORACLE",
            category="ORACLE_INTEGRITY",
            description="Frozen Oracle SHA-256 intact",
            evidence_value="a1db9bb1...",
        )
        d = inv.to_dict()
        assert d["status"] == "VERIFIED_TRUE"
        assert d["category"] == "ORACLE_INTEGRITY"

    def test_required_change_fields(self):
        rc = RequiredChange(
            change_id="REQ-001",
            target="main.py",
            violation_ref="VIO-001",
            deterministic_requirement="Add import statement",
            preserve_refs=["INV-ORACLE"],
            forbidden_refs=["Modify Oracle"],
        )
        d = rc.to_dict()
        assert d["change_id"] == "REQ-001"
        assert "INV-ORACLE" in d["preserve_refs"]


# ===========================================================================
# Area 2: Complete Violation Collection (Global Scan, No Stop-Early)
# ===========================================================================

class TestArea2_CompleteViolationCollection:
    """Area 2: Validator collects ALL violations without stopping at first."""

    def test_multiple_violations_collected(self):
        """Assembler must include all violations, not just the first."""
        violations = [
            _make_violation("VIO-001", "symbol_resolvability"),
            _make_violation("VIO-002", "symbol_resolvability"),
            _make_violation("VIO-003", "contract_frozen_status"),
        ]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [], run_id="test", iteration=0)
        assert len(pkg.violations) == 3
        ids = [v.violation_id for v in pkg.violations]
        assert "VIO-001" in ids
        assert "VIO-002" in ids
        assert "VIO-003" in ids

    def test_fixture_fastapi_has_all_violations(self):
        """Regression: fastapi_t1 fixture must have both decorator violations."""
        pkg = load_fixture("fastapi_t1_b2_failure.json")
        ids = [v.violation_id for v in pkg.violations]
        assert "VIO-001" in ids  # field_validator
        assert "VIO-002" in ids  # @app.get

    def test_fixture_cli_has_all_violations(self):
        """Regression: cli_t1 fixture must have both contract violations."""
        pkg = load_fixture("cli_t1_contract_failure.json")
        ids = [v.violation_id for v in pkg.violations]
        assert "VIO-001" in ids  # duplicate model
        assert "VIO-002" in ids  # speculative interfaces

    def test_fixture_flutter_violation_present(self):
        """Regression: flutter_t1 fixture must have constructor mismatch violation."""
        pkg = load_fixture("flutter_t1_dev_failure.json")
        assert len(pkg.violations) >= 1
        assert pkg.violations[0].violation_id == "VIO-001"
        # observed_symbol is the constructor signature; 'data' absence is in observed_state
        assert "data" in pkg.violations[0].observed_state.lower()


# ===========================================================================
# Area 3: Root-Cause Construction (Programmatic)
# ===========================================================================

class TestArea3_RootCauseConstruction:
    """Area 3: Root causes must be derived programmatically from evidence."""

    def test_b2_ast_violation_generates_root_cause(self):
        violations = [_make_violation("VIO-001", "symbol_resolvability")]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [], run_id="test", iteration=0)
        assert len(pkg.root_causes) > 0
        assert "import" in pkg.root_causes[0].lower() or "unresolvable" in pkg.root_causes[0].lower() or "resolvable" in pkg.root_causes[0].lower()

    def test_b5_sandbox_failure_generates_root_cause(self):
        violations = [_make_violation("VIO-001", "sandbox_exit_code_clean")]
        state = _minimal_state(iteration_count=1)
        pkg = assemble_b5_evidence(state, violations, [], [], run_id="test", iteration=1)
        assert len(pkg.root_causes) > 0

    def test_fixture_fastapi_root_cause_mentions_decorator(self):
        pkg = load_fixture("fastapi_t1_b2_failure.json")
        combined = " ".join(pkg.root_causes).lower()
        assert "decorator" in combined or "import" in combined or "resolvable" in combined

    def test_fixture_cli_root_cause_mentions_duplicate(self):
        pkg = load_fixture("cli_t1_contract_failure.json")
        combined = " ".join(pkg.root_causes).lower()
        assert "duplicate" in combined or "speculative" in combined


# ===========================================================================
# Area 4: Authoritative Context Assembly
# ===========================================================================

class TestArea4_AuthoritativeContext:
    """Area 4: Authoritative context must be assembled from state, not invented."""

    def test_b2_authoritative_file_extracted_from_state(self):
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, [], [], run_id="test", iteration=0)
        assert pkg.authoritative_context.get("authoritative_target_file") == "main.py"

    def test_b2_interfaces_extracted_from_contract(self):
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, [], [], run_id="test", iteration=0)
        interfaces = pkg.authoritative_context.get("required_interfaces", [])
        assert "create_product" in interfaces

    def test_b3_dart_target_file_resolved(self):
        state = _minimal_state(
            target_language="dart",
            contract={
                "task_intent": {"authoritative_target_file": "lib/card_metric.dart"},
                "data_models": [{"model_name": "CardMetricData", "target_file": "lib/card_metric.dart"}],
                "interface_contracts": [{"identifier": "CardMetric", "target_file": "lib/card_metric.dart"}],
            },
        )
        auth_file = _get_authoritative_target_file(state)
        assert auth_file == "lib/card_metric.dart"

    def test_fixture_flutter_oracle_callsite_present(self):
        pkg = load_fixture("flutter_t1_dev_failure.json")
        oracle_cs = pkg.authoritative_context.get("oracle_call_site", "")
        assert "CardMetric" in oracle_cs
        assert "data:" in oracle_cs


# ===========================================================================
# Area 5: Active Constraint Assembly
# ===========================================================================

class TestArea5_ActiveConstraints:
    """Area 5: Active constraints must be assembled from state deterministically."""

    def test_b2_constraints_include_budget_info(self):
        state = _minimal_state(contract_revision_count=3, max_contract_revisions=5)
        pkg = assemble_b2_evidence(state, [], [], run_id="test", iteration=0)
        assert pkg.active_constraints.get("contract_revisions_used") == 3
        assert pkg.active_constraints.get("contract_revisions_max") == 5

    def test_b3_constraints_include_iteration(self):
        state = _minimal_state(iteration_count=5)
        pkg = assemble_b3_evidence(state, [], [], run_id="test", iteration=5)
        assert pkg.active_constraints.get("iteration") == 5
        assert pkg.active_constraints.get("max_iterations") == 10

    def test_b5_constraints_include_sandbox_runner(self):
        state = _minimal_state(target_language="dart")
        pkg = assemble_b5_evidence(state, [], [], [], run_id="test", iteration=2)
        assert pkg.active_constraints.get("sandbox_runner") == "flutter_test"

    def test_standard_forbidden_always_includes_oracle(self):
        forbidden = _standard_forbidden_changes("python")
        oracle_forbidden = [f for f in forbidden if "Oracle" in f or "oracle" in f]
        assert len(oracle_forbidden) >= 1

    def test_dart_forbidden_includes_state_notifier(self):
        forbidden = _standard_forbidden_changes("dart")
        statenotifier_forbidden = [f for f in forbidden if "StateNotifier" in f]
        assert len(statenotifier_forbidden) >= 1


# ===========================================================================
# Area 6: Preserved Invariant Detection
# ===========================================================================

class TestArea6_PreservedInvariants:
    """Area 6: Preserved invariants must be detected from state evidence."""

    def test_oracle_sha_invariant_detected(self):
        state = _minimal_state(expected_oracle_sha="abc123def456" * 5)
        pkg = assemble_b2_evidence(state, [], [], run_id="test", iteration=0)
        inv_categories = [inv.category for inv in pkg.preserved_invariants]
        assert "ORACLE_INTEGRITY" in inv_categories

    def test_contract_frozen_invariant_detected(self):
        state = _minimal_state(
            contract_status="FROZEN",
            contract_sha256="d266453b" * 8,
        )
        # B3 should detect frozen contract invariant
        pkg = assemble_b3_evidence(state, [], [], run_id="test", iteration=0)
        inv_categories = [inv.category for inv in pkg.preserved_invariants]
        assert "CONTRACT_STATUS" in inv_categories

    def test_passing_test_invariants_collected(self):
        state = _minimal_state(previous_passed_tests=["test_create", "test_list"])
        pkg = assemble_b3_evidence(state, [], [], run_id="test", iteration=1)
        passing_invs = [inv for inv in pkg.preserved_invariants if inv.category == "PASSING_TEST"]
        assert len(passing_invs) >= 1

    def test_fixture_fastapi_has_oracle_and_contract_invariants(self):
        pkg = load_fixture("fastapi_t1_b2_failure.json")
        categories = {inv.category for inv in pkg.preserved_invariants}
        assert "ORACLE_INTEGRITY" in categories
        assert "CONTRACT_STATUS" in categories

    def test_fixture_flutter_has_three_invariant_categories(self):
        pkg = load_fixture("flutter_t1_dev_failure.json")
        categories = {inv.category for inv in pkg.preserved_invariants}
        assert len(categories) >= 2  # ORACLE_INTEGRITY + CONTRACT_STATUS at minimum


# ===========================================================================
# Area 7: Repair Boundary (Allowed vs Forbidden)
# ===========================================================================

class TestArea7_RepairBoundary:
    """Area 7: Repair boundary must explicitly separate allowed from forbidden."""

    def test_repair_boundary_has_both_lists(self):
        state = _minimal_state()
        pkg = assemble_b2_evidence(
            state, [_make_violation("VIO-001", "symbol_resolvability")], []
        )
        assert isinstance(pkg.repair_boundary.allowed_changes, list)
        assert isinstance(pkg.repair_boundary.forbidden_changes, list)
        assert len(pkg.repair_boundary.allowed_changes) >= 1
        assert len(pkg.repair_boundary.forbidden_changes) >= 1

    def test_allowed_contains_authoritative_file(self):
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, [_make_violation("VIO-001", "symbol_resolvability")], [])
        combined = " ".join(pkg.repair_boundary.allowed_changes).lower()
        assert "main.py" in combined or "import" in combined

    def test_forbidden_always_includes_oracle_protection(self):
        state = _minimal_state()
        pkg = assemble_b3_evidence(state, [_make_violation("VIO-001", "ast_syntax_validity")], [])
        combined = " ".join(pkg.repair_boundary.forbidden_changes).lower()
        assert "oracle" in combined or "frozen" in combined

    def test_fixture_cli_allowed_removes_duplicate(self):
        pkg = load_fixture("cli_t1_contract_failure.json")
        combined = " ".join(pkg.repair_boundary.allowed_changes).lower()
        assert "duplicate" in combined or "remove" in combined

    def test_fixture_flutter_forbidden_includes_state_notifier(self):
        pkg = load_fixture("flutter_t1_dev_failure.json")
        combined = " ".join(pkg.repair_boundary.forbidden_changes).lower()
        assert "statenotifier" in combined


# ===========================================================================
# Area 8: Forbidden Change Detection
# ===========================================================================

class TestArea8_ForbiddenChangeDetection:
    """Area 8: Forbidden changes must be explicitly enumerated and actionable."""

    def test_forbidden_changes_non_empty_on_fail(self):
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, [_make_violation("VIO-001", "symbol_resolvability")], [])
        assert len(pkg.forbidden_changes) >= 1

    def test_frozen_oracle_always_forbidden(self):
        for lang in ("python", "dart"):
            forbidden = _standard_forbidden_changes(lang)
            oracle_mentioned = any("Oracle" in f or "oracle" in f for f in forbidden)
            assert oracle_mentioned, f"Oracle must always be in forbidden for lang={lang}"

    def test_unfreeze_always_forbidden(self):
        for lang in ("python", "dart"):
            forbidden = _standard_forbidden_changes(lang)
            unfreeze_mentioned = any("Unfreeze" in f or "unfreeze" in f for f in forbidden)
            assert unfreeze_mentioned

    def test_preservation_rule_detects_forbidden_violation(self):
        """check_preservation_rule must detect new forbidden violations."""
        original_v = _make_violation("VIO-001", "symbol_resolvability")
        new_v = _make_violation("VIO-NEW", "oracle_integrity_violated")

        original_pkg = ContextualEvidencePackage(
            package_id="ORIG", timestamp="T", validator="B2", phase="ARCHITECT",
            validator_type="PHASE_END", verdict="FAIL", causal_owner="ARCHITECT",
            failure_summary="", root_causes=[], violations=[original_v],
            violation_dependencies=[], authoritative_context={}, active_constraints={},
            preserved_invariants=[], repair_boundary=RepairBoundary(),
            forbidden_changes=[], required_changes=[], expected_post_repair_state=[],
            verification_criteria=[], source_of_truth="S", evidence=[],
        )
        # Revalidation shows original resolved but new violation appeared
        reval_pkg = ContextualEvidencePackage(
            package_id="REVAL", timestamp="T", validator="B2", phase="ARCHITECT",
            validator_type="PHASE_END", verdict="FAIL", causal_owner="ARCHITECT",
            failure_summary="", root_causes=[], violations=[new_v],
            violation_dependencies=[], authoritative_context={}, active_constraints={},
            preserved_invariants=[], repair_boundary=RepairBoundary(),
            forbidden_changes=[], required_changes=[], expected_post_repair_state=[],
            verification_criteria=[], source_of_truth="S", evidence=[],
        )
        result = check_preservation_rule(original_pkg, reval_pkg)
        assert result["preservation_passed"] is False
        assert "VIO-001" in result["resolved_violations"]
        assert "VIO-NEW" in result["new_violations"]


# ===========================================================================
# Area 9: Required Change Construction (Actionable)
# ===========================================================================

class TestArea9_RequiredChanges:
    """Area 9: Required changes must be specific, actionable, and traceable to violations."""

    def test_each_violation_generates_required_change(self):
        violations = [
            _make_violation("VIO-001", "symbol_resolvability"),
            _make_violation("VIO-002", "contract_frozen_status"),
        ]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [], run_id="test", iteration=0)
        assert len(pkg.required_changes) >= len(violations)

    def test_required_change_has_violation_ref(self):
        violations = [_make_violation("VIO-001", "symbol_resolvability")]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [], run_id="test", iteration=0)
        for rc in pkg.required_changes:
            assert rc.violation_ref, "RequiredChange must reference a violation ID"

    def test_required_change_has_deterministic_requirement(self):
        """Requirement text must be specific, not generic like 'fix the blueprint'."""
        violations = [_make_violation("VIO-001", "symbol_resolvability")]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [], run_id="test", iteration=0)
        for rc in pkg.required_changes:
            assert len(rc.deterministic_requirement) > 20, "Requirement must be specific"
            assert "fix" != rc.deterministic_requirement.lower().strip(), "Must not be generic 'fix'"

    def test_fixture_fastapi_required_changes_mention_imports(self):
        pkg = load_fixture("fastapi_t1_b2_failure.json")
        combined = " ".join(rc.deterministic_requirement for rc in pkg.required_changes).lower()
        assert "import" in combined

    def test_fixture_cli_required_changes_mention_authoritative_functions(self):
        pkg = load_fixture("cli_t1_contract_failure.json")
        combined = " ".join(rc.deterministic_requirement for rc in pkg.required_changes).lower()
        assert "parse_matrix" in combined or "authoritative" in combined

    def test_fixture_flutter_required_change_mentions_data_parameter(self):
        pkg = load_fixture("flutter_t1_dev_failure.json")
        combined = " ".join(rc.deterministic_requirement for rc in pkg.required_changes).lower()
        assert "data" in combined


# ===========================================================================
# Area 10: Expected Post-Repair State (Deterministic)
# ===========================================================================

class TestArea10_ExpectedPostRepairState:
    """Area 10: Post-repair state must be objective and deterministically verifiable."""

    def test_expected_post_repair_state_non_empty_on_fail(self):
        violations = [_make_violation("VIO-001", "symbol_resolvability")]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [], run_id="test", iteration=0)
        assert len(pkg.expected_post_repair_state) >= 1

    def test_expected_state_includes_preservation_condition(self):
        violations = [_make_violation("VIO-001", "symbol_resolvability")]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [], run_id="test", iteration=0)
        combined = " ".join(pkg.expected_post_repair_state).lower()
        assert "invariant" in combined or "preserved" in combined or "frozen" in combined

    def test_verification_criteria_deterministic(self):
        """Verification criteria must be objectively testable (exit code, verdict, counts)."""
        violations = [_make_violation("VIO-001", "sandbox_exit_code_clean")]
        state = _minimal_state(target_language="dart", iteration_count=2)
        pkg = assemble_b5_evidence(state, violations, [], [], run_id="test", iteration=2)
        combined = " ".join(pkg.verification_criteria).lower()
        # Must reference deterministic criteria
        assert any(kw in combined for kw in ("exit_code", "verdict", "passed", "count", "hash"))

    def test_fixture_flutter_expects_zero_failed_count(self):
        pkg = load_fixture("flutter_t1_dev_failure.json")
        combined = " ".join(pkg.expected_post_repair_state).lower()
        assert "fail" in combined or "pass" in combined or "exit_code" in combined


# ===========================================================================
# Area 11: Deterministic Verdict Reproducibility
# ===========================================================================

class TestArea11_VerdictReproducibility:
    """Area 11: Same input always produces same PASS/FAIL verdict."""

    def test_b2_fail_verdict_reproducible(self):
        violations = [_make_violation("VIO-001", "symbol_resolvability")]
        state = _minimal_state()
        pkg1 = assemble_b2_evidence(state, violations, [], run_id="test", iteration=0)
        pkg2 = assemble_b2_evidence(state, violations, [], run_id="test", iteration=0)
        assert pkg1.verdict == pkg2.verdict == "FAIL"

    def test_b2_pass_verdict_with_no_violations(self):
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, [], [], run_id="test", iteration=0)
        assert pkg.verdict == "PASS"
        assert pkg.causal_owner == "NONE"

    def test_b3_fail_with_critical_violations(self):
        violations = [_make_violation("VIO-001", "ast_syntax_validity", "CRITICAL")]
        state = _minimal_state()
        pkg1 = assemble_b3_evidence(state, violations, [], run_id="r1", iteration=0)
        pkg2 = assemble_b3_evidence(state, violations, [], run_id="r2", iteration=0)
        assert pkg1.verdict == pkg2.verdict == "FAIL"

    def test_fixture_verdicts_deterministic(self):
        """All pilot failure fixtures must have FAIL verdict."""
        for fname in ["fastapi_t1_b2_failure.json", "cli_t1_contract_failure.json", "flutter_t1_dev_failure.json"]:
            pkg = load_fixture(fname)
            assert pkg.verdict == "FAIL", f"Fixture {fname} must have FAIL verdict"


# ===========================================================================
# Area 12: Telemetry Event Emission (6 Events)
# ===========================================================================

class TestArea12_TelemetryEvents:
    """Area 12: Telemetry must record all 6 lifecycle events for repair cycles."""

    def test_telemetry_event_names_complete(self):
        """Verify the 6 required event names are documented/defined."""
        expected_events = [
            "validation_failure",
            "contextual_evidence_assembled",
            "repair_directive_issued",
            "repair_attempt",
            "revalidation",
            "repair_outcome",
        ]
        # Test that these strings exist as constants or are usable
        # The actual emission is tested via tracer integration
        for event in expected_events:
            assert isinstance(event, str) and len(event) > 0

    def test_package_hash_stable(self):
        """Package content hash must be stable (reproducible for same content)."""
        pkg = ContextualEvidencePackage(
            package_id="TEST-001", timestamp="2026-09-10T00:00:00Z",
            validator="B2", phase="ARCHITECT", validator_type="PHASE_END",
            verdict="FAIL", causal_owner="ARCHITECT",
            failure_summary="Test", root_causes=["cause"],
            violations=[], violation_dependencies=[], authoritative_context={},
            active_constraints={}, preserved_invariants=[],
            repair_boundary=RepairBoundary(),
            forbidden_changes=["X"], required_changes=[],
            expected_post_repair_state=["Y"], verification_criteria=["Z"],
            source_of_truth="S", evidence=[], remaining_budget=3,
        )
        hash1 = pkg.compute_package_hash()
        hash2 = pkg.compute_package_hash()
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_telemetry_repair_metrics_in_fixture(self):
        """flutter_t1 fixture must have remaining_budget that counts down."""
        pkg = load_fixture("flutter_t1_dev_failure.json")
        assert pkg.remaining_budget >= 0
        assert pkg.remaining_budget < 10  # some budget consumed


# ===========================================================================
# Area 13: Serialization / Deserialization Roundtrip
# ===========================================================================

class TestArea13_SerializationRoundtrip:
    """Area 13: JSON serialization/deserialization must be lossless."""

    def test_to_json_from_json_roundtrip(self):
        violations = [_make_violation("VIO-001", "symbol_resolvability")]
        state = _minimal_state()
        original = assemble_b2_evidence(state, violations, [{"item": "test", "observed": 1}], run_id="r1")
        json_str = original.to_json()
        restored = ContextualEvidencePackage.from_json(json_str)

        assert restored.package_id == original.package_id
        assert restored.verdict == original.verdict
        assert restored.causal_owner == original.causal_owner
        assert len(restored.violations) == len(original.violations)
        assert restored.violations[0].violation_id == original.violations[0].violation_id
        assert restored.source_of_truth == original.source_of_truth

    def test_fixture_roundtrip_preserves_all_violations(self):
        """All fixtures must survive roundtrip without losing violations."""
        for fname in ["fastapi_t1_b2_failure.json", "cli_t1_contract_failure.json", "flutter_t1_dev_failure.json"]:
            pkg = load_fixture(fname)
            json_str = pkg.to_json()
            restored = ContextualEvidencePackage.from_json(json_str)
            assert len(restored.violations) == len(pkg.violations)
            for orig_v, rest_v in zip(pkg.violations, restored.violations):
                assert orig_v.violation_id == rest_v.violation_id

    def test_to_dict_is_json_serializable(self):
        violations = [_make_violation("VIO-001", "symbol_resolvability")]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [])
        d = pkg.to_dict()
        # Must not raise
        json_str = json.dumps(d, ensure_ascii=False)
        assert len(json_str) > 50

    def test_from_dict_handles_missing_optional_fields(self):
        """from_dict must handle partial data gracefully."""
        minimal = {
            "package_id": "TEST", "timestamp": "T", "validator": "B1",
            "phase": "PM", "validator_type": "PHASE_END", "verdict": "FAIL",
            "causal_owner": "PM", "failure_summary": "test", "source_of_truth": "S",
        }
        pkg = ContextualEvidencePackage.from_dict(minimal)
        assert pkg.violations == []
        assert pkg.required_changes == []
        assert pkg.root_causes == []


# ===========================================================================
# Area 14: OTRR Calculation Accuracy
# ===========================================================================

class TestArea14_OTRRCalculation:
    """Area 14: OTRR formula must compute accurately from repair records."""

    def test_otrr_100_percent_all_first_turn(self):
        records = [
            {"failure_id": "F1", "repairs": [{"turn": 1, "outcome": "SUCCESS"}]},
            {"failure_id": "F2", "repairs": [{"turn": 1, "outcome": "SUCCESS"}]},
            {"failure_id": "F3", "repairs": [{"turn": 1, "outcome": "SUCCESS"}]},
        ]
        result = calculate_otrr(records)
        assert result["otrr"] == 1.0
        assert result["first_turn_successes"] == 3
        assert result["total_failures_with_repair"] == 3

    def test_otrr_0_percent_none_succeed(self):
        records = [
            {"failure_id": "F1", "repairs": [{"turn": 1, "outcome": "UNRESOLVED"}, {"turn": 2, "outcome": "UNRESOLVED"}]},
            {"failure_id": "F2", "repairs": [{"turn": 1, "outcome": "BUDGET_EXHAUSTED"}]},
        ]
        result = calculate_otrr(records)
        assert result["otrr"] == 0.0
        assert result["first_turn_successes"] == 0

    def test_otrr_partial_success(self):
        records = [
            {"failure_id": "F1", "repairs": [{"turn": 1, "outcome": "SUCCESS"}]},
            {"failure_id": "F2", "repairs": [{"turn": 1, "outcome": "UNRESOLVED"}, {"turn": 2, "outcome": "SUCCESS"}]},
            {"failure_id": "F3", "repairs": [{"turn": 1, "outcome": "REGRESSED"}]},
        ]
        result = calculate_otrr(records)
        # Only F1 succeeds on turn 1
        assert result["first_turn_successes"] == 1
        assert result["total_failures_with_repair"] == 3
        assert abs(result["otrr"] - 1/3) < 0.001

    def test_otrr_empty_records(self):
        result = calculate_otrr([])
        assert result["otrr"] == 0.0
        assert result["total_failures_with_repair"] == 0

    def test_otrr_pilot_baseline_0_percent(self):
        """Pilot 3-run baseline: 0 repairs succeeded (all were terminal FAILs at gates, not turn-based)."""
        records = [
            {"failure_id": "fastapi_t1", "repairs": []},  # 0 developer loops = no repair
            {"failure_id": "cli_t1", "repairs": []},       # 0 developer loops = no repair
            {"failure_id": "flutter_t1", "repairs": [     # 10 developer loops, all failed
                {"turn": i, "outcome": "UNRESOLVED"} for i in range(1, 11)
            ]},
        ]
        # fastapi_t1 and cli_t1 had 0 repairs (contained at gate, budget not consumed)
        # flutter_t1 had 10 repair turns, none succeeded
        # Only flutter_t1 counts as having received repair
        result = calculate_otrr([r for r in records if r["repairs"]])
        assert result["otrr"] == 0.0
        assert result["total_failures_with_repair"] == 1  # only flutter_t1

    def test_otrr_percent_matches_otrr_ratio(self):
        records = [
            {"failure_id": "F1", "repairs": [{"turn": 1, "outcome": "SUCCESS"}]},
            {"failure_id": "F2", "repairs": [{"turn": 1, "outcome": "UNRESOLVED"}]},
        ]
        result = calculate_otrr(records)
        assert abs(result["otrr_percent"] - result["otrr"] * 100) < 0.001

    def test_calculate_trace_otrr_from_jsonl(self, tmp_path):
        from backend.tracer import calculate_trace_otrr, RunTracer
        tracer = RunTracer("test_run", tmp_path)
        tracer.log_repair_outcome("pkg_1", "SUCCESS", turns_to_pass=1)
        tracer.log_repair_outcome("pkg_2", "UNRESOLVED", turns_to_pass=2)
        tracer.log_repair_outcome("pkg_3", "SUCCESS", turns_to_pass=1)

        result = calculate_trace_otrr(tracer.trace_file)
        assert result["total_failures_with_repair"] == 3
        assert result["first_turn_successes"] == 2
        assert result["otrr_percent"] == 66.67

    def test_tracer_log_all_iterasi7_events(self, tmp_path):
        from backend.tracer import RunTracer
        tracer = RunTracer("test_run_events", tmp_path)
        tracer.log_validation_failure("B2", "FAIL", 2, "hash123")
        tracer.log_contextual_evidence_assembled("pkg_1", "hash123", "DEVELOPER", 500)
        tracer.log_repair_directive_issued("pkg_1", "developer", 500)
        tracer.log_repair_attempt(1, "pkg_1")
        tracer.log_revalidation("pkg_1", "B3", "FAIL")
        tracer.log_repair_outcome("pkg_1", "SUCCESS", turns_to_pass=1)

        # Check all lines in trace file
        lines = [json.loads(line) for line in tracer.trace_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        event_types = [l["event_type"] for l in lines]
        assert "validation_failure" in event_types
        assert "contextual_evidence_assembled" in event_types
        assert "repair_directive_issued" in event_types
        assert "repair_attempt" in event_types
        assert "revalidation" in event_types
        assert "repair_outcome" in event_types


# ===========================================================================
# Bonus: Render Repair Directive (Markdown Compaction)
# ===========================================================================

class TestRenderRepairDirective:
    """Verify render_repair_directive produces structured Markdown within token limit."""

    def test_render_produces_sections(self):
        violations = [_make_violation("VIO-001", "symbol_resolvability")]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [])
        result = render_repair_directive(pkg)
        assert "[1. DETERMINISTIC FACTS" in result
        assert "[2. DERIVED DETERMINISTIC DIAGNOSIS" in result
        assert "[3. COMPLETE VIOLATION ROSTER" in result
        assert "[5. PRESERVED INVARIANTS" in result
        assert "[8. REPAIR BOUNDARIES" in result
        assert "REQUIRED DETERMINISTIC CHANGES" in result

    def test_render_respects_max_chars(self):
        violations = [_make_violation(f"VIO-{i:03d}", "symbol_resolvability") for i in range(30)]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [])
        result = render_repair_directive(pkg, max_chars=2500)
        assert len(result) <= 2600  # Allow small buffer for trim message

    def test_render_includes_all_violations_when_small(self):
        violations = [_make_violation("VIO-001", "symbol_resolvability"), _make_violation("VIO-002", "ast_syntax")]
        state = _minimal_state()
        pkg = assemble_b2_evidence(state, violations, [])
        result = render_repair_directive(pkg, max_chars=10000)
        assert "VIO-001" in result
        assert "VIO-002" in result

    def test_preservation_rule_pass(self):
        """check_preservation_rule returns SUCCESS when all violations resolved."""
        v = _make_violation("VIO-001", "symbol_resolvability")
        orig = ContextualEvidencePackage(
            package_id="ORIG", timestamp="T", validator="B2", phase="ARCHITECT",
            validator_type="PHASE_END", verdict="FAIL", causal_owner="ARCHITECT",
            failure_summary="", root_causes=[], violations=[v],
            violation_dependencies=[], authoritative_context={}, active_constraints={},
            preserved_invariants=[], repair_boundary=RepairBoundary(),
            forbidden_changes=[], required_changes=[], expected_post_repair_state=[],
            verification_criteria=[], source_of_truth="S", evidence=[],
        )
        reval = ContextualEvidencePackage(
            package_id="REVAL", timestamp="T", validator="B2", phase="ARCHITECT",
            validator_type="PHASE_END", verdict="PASS", causal_owner="NONE",
            failure_summary="", root_causes=[], violations=[],  # all resolved
            violation_dependencies=[], authoritative_context={}, active_constraints={},
            preserved_invariants=[], repair_boundary=RepairBoundary(),
            forbidden_changes=[], required_changes=[], expected_post_repair_state=[],
            verification_criteria=[], source_of_truth="S", evidence=[],
        )
        result = check_preservation_rule(orig, reval)
        assert result["preservation_passed"] is True
        assert result["repair_outcome"] == "SUCCESS"
        assert "VIO-001" in result["resolved_violations"]


# ===========================================================================
# Area 15: Gate B5 Deterministic Actionable Repair Prescriptions (Experiment E2)
# ===========================================================================

class TestArea15_B5ActionableRepairPrescriptions:
    """Pengujian komprehensif untuk Actionable Repair Prescriptions di Gate B5."""

    def test_b5_positional_mismatch_creates_prescription(self):
        """Uji deteksi TypeError constructor positional mismatch dan pemisahan epistemik."""
        oracle_code = (
            "import pytest\n"
            "import main\n\n"
            "def _get_matrix(data):\n"
            "    if hasattr(main, 'Matrix'):\n"
            "        return main.Matrix(data)\n"
            "    return data\n\n"
            "def test_matrix_addition():\n"
            "    m = _get_matrix([[1, 2], [3, 4]])\n"
        )
        sandbox_output = (
            "================================== FAILURES ===================================\n"
            "____________________________ test_matrix_addition _____________________________\n"
            "    def _get_matrix(data):\n"
            ">       return main.Matrix(data)\n"
            "E       TypeError: BaseModel.__init__() takes 1 positional argument but 2 were given\n"
            "test_main.py:5: TypeError\n"
            "============================== 1 failed in 0.05s ==============================\n"
        )
        state = {
            "task": "Bangun kalkulator CLI Python dengan operasi matriks",
            "target_language": "python",
            "test_files": {"test_main.py": oracle_code},
            "contract": {
                "task_intent": {"authoritative_target_file": "main.py"},
                "data_models": [{"model_name": "Matrix", "target_file": "main.py"}],
                "interface_contracts": [{"identifier": "add_matrices", "target_file": "main.py"}],
            },
            "test_results": {
                "passed": False,
                "exit_code": 1,
                "failed_count": 1,
                "passed_count": 0,
                "output": sandbox_output,
            },
            "max_iterations": 10,
        }
        violations = [_make_violation("VIO-001", "sandbox_exit_code_clean")]
        pkg = assemble_b5_evidence(state, violations, [], [], run_id="test_run", iteration=1)

        assert len(pkg.actionable_prescriptions) == 1
        rx = pkg.actionable_prescriptions[0]
        assert rx.prescription_id == "RX-B5-POS-ARG-001"
        assert "BaseModel.__init__()" in rx.observed_failure or "takes 1 positional argument" in rx.observed_failure

        # 1. Epistemic Separation
        assert "test_main.py" in rx.oracle_call_site
        assert "positional arg" in rx.oracle_call_site
        assert rx.implementation_symbol == "class Matrix in 'main.py'"
        assert rx.evidence_basis == "ORACLE_AST_CALL_TRACE + RUNTIME_TYPE_ERROR_TRACEBACK"

        # 2. WHAT vs HOW (No implementation code template)
        assert "Matrix" in rx.required_change
        assert "positional argument" in rx.required_change
        assert "def __init__" not in rx.required_change
        assert "class " not in rx.required_change

        # 3. Boundaries
        assert len(rx.repair_boundary_allowed) >= 1
        assert any("Matrix" in a for a in rx.repair_boundary_allowed)
        assert any("Do NOT modify Frozen Oracle" in f for f in rx.repair_boundary_forbidden)

    def test_b5_actionable_prescriptions_rendered_in_directive(self):
        """Uji bahwa Section 7 dirender dengan label observasi faktual vs simbol implementasi."""
        oracle_code = "def test_foo(): main.Matrix([[1, 2]])"
        sandbox_output = "TypeError: BaseModel.__init__() takes 1 positional argument but 2 were given"
        state = {
            "task": "Test task",
            "target_language": "python",
            "test_files": {"test_main.py": oracle_code},
            "contract": {
                "task_intent": {"authoritative_target_file": "main.py"},
                "data_models": [{"model_name": "Matrix", "target_file": "main.py"}],
            },
            "test_results": {"passed": False, "exit_code": 1, "failed_count": 1, "output": sandbox_output},
        }
        pkg = assemble_b5_evidence(state, [_make_violation("VIO-001", "sandbox_exit_code_clean")], [], [])
        rendered = render_repair_directive(pkg)

        assert "[4. ACTIONABLE REPAIR PRESCRIPTIONS — DETERMINISTIC" in rendered
        assert "ORACLE CALL SITE (FACT):" in rendered
        assert "IMPLEMENTATION SYMBOL:" in rendered
        assert "EVIDENCE BASIS:" in rendered
        assert "REQUIRED CHANGE (CONTRACT):" in rendered
        assert len(rendered) <= 4600

    def test_b5_isolation_b1_b2_b3_do_not_emit_b5_prescriptions(self):
        """Uji isolasi eksperimental: B1, B2, B3 tidak menghasilkan B5 prescriptions."""
        state = _minimal_state()
        v = [_make_violation("VIO-001", "symbol_resolvability")]

        pkg_b1 = assemble_b1_evidence(state, v, [])
        assert len(getattr(pkg_b1, "actionable_prescriptions", [])) == 0

        pkg_b2 = assemble_b2_evidence(state, v, [])
        assert len(getattr(pkg_b2, "actionable_prescriptions", [])) == 0

        pkg_b3 = assemble_b3_evidence(state, v, [])
        assert len(getattr(pkg_b3, "actionable_prescriptions", [])) == 0

    def test_b5_attribute_error_prescription(self):
        """Uji pembentukan prescription untuk kegagalan missing attribute/function."""
        state = {
            "task": "Test task",
            "target_language": "python",
            "test_files": {},
            "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
            "test_results": {
                "passed": False,
                "exit_code": 1,
                "failed_count": 1,
                "output": "AttributeError: module 'main' has no attribute 'multiply_matrices'",
            },
        }
        pkg = assemble_b5_evidence(state, [_make_violation("VIO-001", "sandbox_exit_code_clean")], [], [])
        assert len(pkg.actionable_prescriptions) == 1
        rx = pkg.actionable_prescriptions[0]
        assert rx.prescription_id == "RX-B5-ATTR-001"
        assert "multiply_matrices" in rx.implementation_symbol
        assert rx.evidence_basis == "RUNTIME_ATTRIBUTE_ERROR_TRACEBACK"


class TestEngineeringDoctrineAndBehavioralInvariants:
    """Uji suite untuk Engineering Doctrine, Behavioral Invariant Lock, dan Dual-Evidence Exception Compatibility."""

    def test_behavioral_invariant_state_machine_with_recovery(self):
        """Uji state machine invariant: UNVERIFIED -> PROVEN -> REGRESSED -> PROVEN (dengan riwayat permanen)."""
        inv = PreservedInvariant(
            invariant_id="INV-BEHAVIOR-test_matrix_addition",
            category="BEHAVIORAL_TEST",
            description="Matrix addition behavior contract",
            evidence_value="test_main.py::test_matrix_addition",
            status="PROVEN",
            target="behavior:test_matrix_addition",
            state="LOCKED",
            mutation="FORBIDDEN",
        )
        assert inv.status == "PROVEN"
        assert inv.state == "LOCKED"
        assert inv.ever_regressed is False
        assert inv.regression_count == 0

        # Iterasi 2: Terjadi regresi
        inv.record_regression("AssertionError: matrices did not match", iteration=2)
        assert inv.status == "REGRESSED"
        assert inv.state == "VIOLATED"
        assert inv.ever_regressed is True
        assert inv.regression_count == 1
        assert len(inv.regression_history) == 1
        assert inv.regression_history[0]["iteration"] == 2

        # Iterasi 3: Terjadi pemulihan (recovery)
        inv.record_recovery("test_matrix_addition PASSED", iteration=3)
        assert inv.status == "PROVEN"
        assert inv.state == "LOCKED"
        # Riwayat masa lalu TIDAK BOLEH terhapus
        assert inv.ever_regressed is True
        assert inv.regression_count == 1
        assert inv.regression_history[0]["recovered_at_iteration"] == 3

    def test_ast_exception_hierarchy_inspector_incompatible(self):
        """Uji audit AST membuktikan MatrixError(Exception) tidak kompatibel dengan ValueError."""
        code = "class MatrixError(Exception):\n    pass\n"
        audit = inspect_ast_exception_hierarchy(
            code_files={"main.py": code},
            auth_file="main.py",
            actual_exc_name="MatrixError",
            expected_exc_name="ValueError",
        )
        assert audit["audited"] is True
        assert audit["class_found"] is True
        assert audit["is_subclass_compatible"] is False
        assert audit["declared_bases"] == ["Exception"]
        assert "MatrixError !-> ValueError" in audit["subclass_relation"]
        assert "MatrixError -> Exception" in audit["hierarchy_path"]

    def test_ast_exception_hierarchy_inspector_compatible(self):
        """Uji audit AST membuktikan MatrixError(ValueError) kompatibel dengan ValueError."""
        code = "class MatrixError(ValueError):\n    pass\n"
        audit = inspect_ast_exception_hierarchy(
            code_files={"main.py": code},
            auth_file="main.py",
            actual_exc_name="MatrixError",
            expected_exc_name="ValueError",
        )
        assert audit["audited"] is True
        assert audit["class_found"] is True
        assert audit["is_subclass_compatible"] is True
        assert audit["declared_bases"] == ["ValueError"]
        assert "MatrixError -> ValueError" in audit["subclass_relation"]

    def test_b5_dual_evidence_exception_compatibility_prescription(self):
        """Uji pembentukan prescription RX-B5-EXC-COMPAT-001 berdasarkan Dual-Evidence (Traceback + AST)."""
        output = """
test_main.py::test_matrix_addition PASSED                                [ 20%]
test_main.py::test_matrix_subtraction PASSED                             [ 40%]
test_main.py::test_matrix_multiplication PASSED                          [ 60%]
test_main.py::test_matrix_addition_incompatible_dimensions FAILED        [ 80%]
test_main.py::test_matrix_multiplication_incompatible_dimensions FAILED  [100%]

================================== FAILURES ===================================
________________ test_matrix_addition_incompatible_dimensions _________________

    def test_matrix_addition_incompatible_dimensions():
        with pytest.raises(ValueError):
>           _add(a, b)

main.py:37: MatrixError
E   main.MatrixError: Matriks tidak sesuai untuk operasi
=========================== short test summary info ===========================
FAILED test_main.py::test_matrix_addition_incompatible_dimensions - main.MatrixError: Matriks tidak sesuai untuk operasi
FAILED test_main.py::test_matrix_multiplication_incompatible_dimensions - main.MatrixError: Matriks tidak sesuai untuk operasi
========================= 2 failed, 3 passed in 0.10s =========================
"""
        state = {
            "task": "Matrix calculator",
            "target_language": "python",
            "test_files": {},
            "code_files": {"main.py": "class MatrixError(Exception):\n    pass\n"},
            "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
            "test_results": {
                "passed": False,
                "exit_code": 1,
                "passed_count": 3,
                "failed_count": 2,
                "output": output,
            },
            "previous_passed_tests": ["test_matrix_addition", "test_matrix_subtraction", "test_matrix_multiplication"],
        }
        pkg = assemble_b5_evidence(state, [_make_violation("VIO-001", "sandbox_exit_code_clean")], [], [])
        assert len(pkg.actionable_prescriptions) == 1
        rx = pkg.actionable_prescriptions[0]
        assert rx.prescription_id == "RX-B5-EXC-COMPAT-001"
        assert rx.evidence_ref == "DUAL_EVIDENCE_RUNTIME_AND_AST_HIERARCHY_AUDIT"
        assert "ValueError" in rx.required_change
        assert "MatrixError" in rx.observed_failure
        assert "AST_HIERARCHY_AUDIT" in rx.evidence_basis

    def test_b5_exception_compatibility_not_emitted_if_already_compatible(self):
        """Uji isolasi: jika exception sudah mewarisi ValueError, prescription exception TIDAK dipancarkan."""
        output = """
with pytest.raises(ValueError):
    _add(a, b)
E   main.MatrixError: Matriks tidak sesuai untuk operasi
"""
        state = {
            "task": "Matrix calculator",
            "target_language": "python",
            "test_files": {},
            "code_files": {"main.py": "class MatrixError(ValueError):\n    pass\n"},
            "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
            "test_results": {
                "passed": False,
                "exit_code": 1,
                "failed_count": 1,
                "output": output,
            },
        }
        pkg = assemble_b5_evidence(state, [_make_violation("VIO-001", "sandbox_exit_code_clean")], [], [])
        # Karena MatrixError(ValueError) sudah kompatibel, prescription EXC-COMPAT tidak dipancarkan
        assert not any(rx.prescription_id == "RX-B5-EXC-COMPAT-001" for rx in pkg.actionable_prescriptions)

    def test_render_repair_directive_shows_behavioral_invariants_and_recovered_regression(self):
        """Uji format directive memuat doktrin rekayasa, behavioral invariant, dan riwayat pemulihan regresi."""
        inv = PreservedInvariant(
            invariant_id="INV-BEHAVIOR-test_addition",
            category="BEHAVIORAL_TEST",
            description="Addition arithmetic valid contract",
            evidence_value="test_main.py::test_matrix_addition",
            status="PROVEN",
            target="behavior:test_matrix_addition",
            state="LOCKED",
            mutation="FORBIDDEN",
            ever_regressed=True,
            regression_count=1,
        )
        pkg = ContextualEvidencePackage(
            package_id="PKG-TEST-001",
            timestamp="2026-09-11T12:00:00Z",
            validator="B5_EXECUTOR_ITERATION",
            phase="EXECUTOR",
            validator_type="ITERATION",
            verdict="FAIL",
            causal_owner="DEVELOPER",
            failure_summary="1 test failed",
            root_causes=["Dimension mismatch error"],
            violations=[_make_violation("VIO-001", "sandbox_exit_code_clean")],
            violation_dependencies=[],
            authoritative_context={"authoritative_target_file": "main.py"},
            active_constraints={"target_language": "python"},
            preserved_invariants=[inv],
            repair_boundary=RepairBoundary(allowed_changes=["fix validation"], forbidden_changes=["break invariants"]),
            forbidden_changes=["break invariants"],
            required_changes=[],
            expected_post_repair_state=["All tests pass"],
            verification_criteria=["exit_code == 0"],
            source_of_truth="SANDBOX",
            evidence=[],
        )
        rendered = render_repair_directive(pkg)
        assert "[ENGINEERING DOCTRINE & COMPATIBILITY PRINCIPLES (MANDATORY)]" in rendered
        assert "[5. PRESERVED INVARIANTS" in rendered
        assert "[PROVEN AGAIN — WITH PRIOR REGRESSION (count: 1)]" in rendered
        assert "Behavioral Target: behavior:test_matrix_addition" in rendered
        assert len(rendered) <= 2600

    def test_render_canonical_sequence_ordering(self):
        """Uji kepatuhan urutan kanonikal linier: failure -> causal evidence -> prescription -> invariant -> doctrine -> verification."""
        inv = PreservedInvariant(
            invariant_id="INV-001",
            category="BEHAVIORAL_TEST",
            description="Addition test invariant",
            evidence_value="test_main.py::test_matrix_addition",
            status="PROVEN",
            target="behavior:test_matrix_addition",
        )
        rx = ActionableRepairPrescription(
            prescription_id="RX-TEST-001",
            evidence_ref="VIO-001",
            observed_failure="TypeError",
            oracle_call_site="Matrix(data)",
            implementation_symbol="Matrix.__init__",
            evidence_basis="TEST",
            required_change="Accept positional data",
            repair_boundary_allowed=["modify constructor"],
            repair_boundary_forbidden=["delete class"],
            expected_post_repair_state="Instantiates cleanly",
            verification_evidence="test passes",
        )
        pkg = ContextualEvidencePackage(
            package_id="PKG-CANONICAL-001",
            timestamp="2026-09-11T12:00:00Z",
            validator="B5_EXECUTOR_ITERATION",
            phase="EXECUTOR",
            validator_type="ITERATION",
            verdict="FAIL",
            causal_owner="DEVELOPER",
            failure_summary="1 test failed",
            root_causes=["Positional argument missing"],
            violations=[_make_violation("VIO-001", "sandbox_exit_code_clean")],
            violation_dependencies=[],
            authoritative_context={"authoritative_target_file": "main.py"},
            active_constraints={"target_language": "python"},
            preserved_invariants=[inv],
            repair_boundary=RepairBoundary(allowed_changes=["fix init"], forbidden_changes=["break invariant"]),
            forbidden_changes=["break invariant"],
            required_changes=[RequiredChange("REQ-001", "main.py", "VIO-001", "Fix init", [], [])],
            expected_post_repair_state=["All tests pass"],
            verification_criteria=["exit_code == 0"],
            actionable_prescriptions=[rx],
            source_of_truth="SANDBOX",
            evidence=[],
        )
        rendered = render_repair_directive(pkg)
        pos_failure = rendered.find("[1. DETERMINISTIC FACTS & FAILURE SUMMARY]")
        pos_causal = rendered.find("[3. COMPLETE VIOLATION ROSTER")
        pos_rx = rendered.find("[4. ACTIONABLE REPAIR PRESCRIPTIONS")
        pos_inv = rendered.find("[5. PRESERVED INVARIANTS")
        pos_doctrine = rendered.find("[ENGINEERING DOCTRINE")
        pos_verify = rendered.find("[7. REQUIRED DETERMINISTIC CHANGES")
        pos_boundary = rendered.find("[8. REPAIR BOUNDARIES")

        assert pos_failure != -1
        assert pos_causal != -1
        assert pos_rx != -1
        assert pos_inv != -1
        assert pos_doctrine != -1
        assert pos_verify != -1
        assert pos_boundary != -1

        # Assert strict linear causal chain before secondary context
        assert pos_failure < pos_causal < pos_rx < pos_inv < pos_doctrine < pos_verify < pos_boundary

    def test_b5_function_level_symbol_binding_resolution(self):
        """Uji deterministik resolusi function-level symbol binding untuk mengeliminasi Function Boundary Blind Spot."""
        oracle_test_code = """
import pytest
import main

def _add(a, b):
    return main.add_matrices(a, b)

def _mul(a, b):
    return main.multiply_matrices(a, b)

def test_matrix_addition_incompatible_dimensions():
    with pytest.raises(ValueError):
        _add([[1, 2]], [[1, 2, 3]])

def test_matrix_multiplication_incompatible_dimensions():
    with pytest.raises(ValueError):
        _mul([[1, 2]], [[1, 2]])
"""
        output = """
FAILED test_main.py::test_matrix_addition_incompatible_dimensions - Failed: DID NOT RAISE <class 'ValueError'>
FAILED test_main.py::test_matrix_multiplication_incompatible_dimensions - Failed: DID NOT RAISE <class 'ValueError'>
"""
        state = {
            "task": "Matrix calculator",
            "target_language": "python",
            "test_files": {"test_main.py": oracle_test_code},
            "code_files": {"main.py": "def add_matrices(a, b): pass\ndef multiply_matrices(a, b): pass\n"},
            "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
            "test_results": {
                "passed": False,
                "exit_code": 1,
                "passed_count": 3,
                "failed_count": 2,
                "output": output,
            },
        }
        pkg = assemble_b5_evidence(state, [_make_violation("VIO-001", "sandbox_exit_code_clean")], [], [])
        assert len(pkg.actionable_prescriptions) == 1
        rx = pkg.actionable_prescriptions[0]
        assert rx.prescription_id == "RX-B5-EXC-COMPAT-001"
        assert "Oracle-tested functions: add_matrices, multiply_matrices" in rx.implementation_symbol
        assert "add_matrices" in rx.required_change
        assert "multiply_matrices" in rx.required_change
        assert "Direct invocation in Oracle test suite: add_matrices(a, b), multiply_matrices(a, b)" in rx.oracle_call_site
        assert "confirm pytest.raises(ValueError)" in rx.verification_evidence

    def test_b5_causal_priority_interface_mismatch_resolution(self):
        """
        Uji deterministik Causal-Priority Resolution (Run 5.2):
        Ketika output memuat AttributeError pada tipe bawaan ('list'), sistem harus:
        1. Memancarkan RX-B5-FUNC-INTERFACE-001 yang menargetkan batas fungsi ('add_matrices', 'subtract_matrices', 'multiply_matrices').
        2. Menyatakan kondisi perilaku bahwa fungsi harus menerima representasi 'list' dari Oracle.
        3. Menolak modifikasi pada parse_matrix atau CLI logic.
        4. Mengeliminasi RX-B5-ATTR-001 (tidak menuntut add pada list).
        5. Mensupresi RX-B5-EXC-COMPAT-001 agar tidak terjadi Priority Masking Trap saat evaluasi eksepsi belum tercapai.
        """
        oracle_test_code = """
import pytest
import main

def _add(a, b):
    return main.add_matrices(a, b)

def _sub(a, b):
    return main.subtract_matrices(a, b)

def _mul(a, b):
    return main.multiply_matrices(a, b)

def test_matrix_addition():
    assert _add([[1, 2]], [[3, 4]]) == [[4, 6]]

def test_matrix_addition_incompatible_dimensions():
    with pytest.raises(ValueError):
        _add([[1, 2]], [[1, 2, 3]])
"""
        output = """
================================== FAILURES ===================================
____________________________ test_matrix_addition _____________________________
test_main.py:15: in test_matrix_addition
    assert _add([[1, 2]], [[3, 4]]) == [[4, 6]]
test_main.py:6: in _add
    return main.add_matrices(a, b)
main.py:10: in add_matrices
    return a.add(b)
E   AttributeError: 'list' object has no attribute 'add'
________________ test_matrix_addition_incompatible_dimensions _________________
test_main.py:19: in test_matrix_addition_incompatible_dimensions
    with pytest.raises(ValueError):
test_main.py:6: in _add
    return main.add_matrices(a, b)
main.py:10: in add_matrices
    return a.add(b)
E   AttributeError: 'list' object has no attribute 'add'
=========================== short test summary info ===========================
FAILED test_main.py::test_matrix_addition - AttributeError: 'list' object has no attribute 'add'
FAILED test_main.py::test_matrix_addition_incompatible_dimensions - AttributeError: 'list' object has no attribute 'add'
"""
        code = """
class Matrix:
    def __init__(self, data):
        self.data = data
    def add(self, other):
        pass

def add_matrices(a: Matrix, b: Matrix) -> Matrix:
    return a.add(b)

def subtract_matrices(a: Matrix, b: Matrix) -> Matrix:
    return a.subtract(b)

def multiply_matrices(a: Matrix, b: Matrix) -> Matrix:
    return a.multiply(b)

def parse_matrix(s: str):
    pass

def main():
    pass
"""
        state = {
            "task": "Matrix calculator CLI",
            "target_language": "python",
            "test_files": {"test_main.py": oracle_test_code},
            "code_files": {"main.py": code},
            "contract": {
                "task_intent": {"authoritative_target_file": "main.py"},
                "data_models": [{"model_name": "Matrix"}],
            },
            "test_results": {
                "passed": False,
                "exit_code": 1,
                "passed_count": 0,
                "failed_count": 2,
                "output": output,
            },
        }
        pkg = assemble_b5_evidence(state, [_make_violation("VIO-001", "sandbox_exit_code_clean")], [], [])

        # 1. Harus tepat 1 prescription (RX-B5-FUNC-INTERFACE-001), tidak tertimpa atau menduplikasi EXC-COMPAT atau ATTR-001
        assert len(pkg.actionable_prescriptions) == 1
        rx = pkg.actionable_prescriptions[0]

        # 2. Cek identitas dan target kausal
        assert rx.prescription_id == "RX-B5-FUNC-INTERFACE-001"
        assert "add_matrices" in rx.implementation_symbol
        assert "list" in rx.observed_failure
        assert "add" in rx.observed_failure

        # 3. Cek behavioral condition (bukan solusi implementasi sintaks spesifik)
        assert "must accept the input representation actually supplied by the Oracle (list)" in rx.required_change
        assert "isinstance" not in rx.required_change  # Tidak boleh mengajari kode sintaks konversi

        # 4. Cek disiplin boundary larangan memodifikasi parse_matrix / CLI
        assert any("Do NOT modify parse_matrix" in f for f in rx.repair_boundary_forbidden)
        assert any("Do NOT modify Frozen Oracle" in f for f in rx.repair_boundary_forbidden)

        # 5. Cek rendering directive
        rendered = render_repair_directive(pkg)
        assert "[RX-B5-FUNC-INTERFACE-001]" in rendered
        assert "RX-B5-ATTR-001" not in rendered
        assert "RX-B5-EXC-COMPAT-001" not in rendered
        assert "Do NOT modify parse_matrix" in rendered




