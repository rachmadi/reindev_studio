"""
Unit Tests for Part 3: Context Integrity & Task Isolation
ReinDev Studio — Architectural Hardening v1

Validates:
1. Cross-domain contamination detection and filtering
2. Rejected artifact authority leakage prevention (status REJECTED must not be authoritative)
3. Draft proposal cannot masquerade as FROZEN contract
4. Clean context assembly passes without violations
5. Integration with build_architect_decision_context & build_developer_repair_context
"""

import pytest
from backend.context_integrity import (
    ContextItem,
    ContextIntegrityAuditor,
    AuditResult,
)
from backend.context_hardening import (
    build_architect_decision_context,
    build_developer_repair_context,
)


def test_cross_domain_contamination_detected():
    """
    Items containing domain signatures from other domains (e.g. Flutter widget code
    inside a REST_API task) must be flagged and rejected by the auditor.
    """
    items = [
        ContextItem(
            item_id="item-1",
            item_type="REQUIREMENT",
            domain="REST_API",
            phase="PM",
            content="Create a user endpoint returning JSON list of users.",
            authority_status="PROVEN"
        ),
        ContextItem(
            item_id="item-2",
            item_type="SOURCE_CODE",
            domain="FLUTTER_WIDGET",
            phase="ARCHITECT",
            content="class UserCard extends StatelessWidget { Widget build(BuildContext context) { return MaterialApp(); } }",
            authority_status="PROPOSED"
        )
    ]

    result = ContextIntegrityAuditor.audit_context(items, target_domain="REST_API", target_phase="DEVELOPER")

    assert result.is_clean is False
    assert len(result.violations) >= 1
    assert any("CROSS_DOMAIN" in v for v in result.violations)
    assert len(result.filtered_items) == 1
    assert result.filtered_items[0].item_id == "item-1"
    assert len(result.rejected_items) == 1
    assert result.rejected_items[0][0].item_id == "item-2"


def test_rejected_artifact_cannot_be_authoritative():
    """
    An artifact with status REJECTED must never be accepted as active/authoritative
    contract or requirement.
    """
    items = [
        ContextItem(
            item_id="rejected-contract",
            item_type="CONTRACT",
            domain="REST_API",
            phase="ARCHITECT",
            content="Contract proposal with broken interfaces",
            authority_status="REJECTED"
        )
    ]

    result = ContextIntegrityAuditor.audit_context(items, target_domain="REST_API", target_phase="DEVELOPER")

    assert result.is_clean is False
    assert len(result.violations) == 1
    assert "REJECTED" in result.violations[0]
    assert len(result.filtered_items) == 0


def test_draft_proposal_masquerading_as_frozen_rejected():
    """
    A draft contract attempting to claim 'Status: FROZEN' inside content must be flagged.
    """
    items = [
        ContextItem(
            item_id="fake-frozen-contract",
            item_type="CONTRACT",
            domain="REST_API",
            phase="PM",
            content="Status: FROZEN\nInterfaces: /items",
            authority_status="DRAFT"
        )
    ]

    result = ContextIntegrityAuditor.audit_context(items, target_domain="REST_API", target_phase="ARCHITECT")

    assert result.is_clean is False
    assert any("EPISTEMIC_VIOLATION" in v for v in result.violations)


def test_clean_context_passes_unhindered():
    """
    A well-formed context matching the active domain without authority contradictions
    must pass with is_clean=True and 0 violations.
    """
    items = [
        ContextItem(
            item_id="user-intent",
            item_type="USER_INTENT",
            domain="REST_API",
            phase="PM",
            content="Build a FastAPI app with /items endpoint",
            authority_status="PROVEN"
        ),
        ContextItem(
            item_id="oracle-fact",
            item_type="ORACLE_FACT",
            domain="REST_API",
            phase="ARCHITECT",
            content="[ORACLE_FACT] /items [GET] (Tested endpoint)",
            authority_status="ORACLE"
        )
    ]

    result = ContextIntegrityAuditor.audit_context(items, target_domain="REST_API", target_phase="DEVELOPER")

    assert result.is_clean is True
    assert len(result.violations) == 0
    assert len(result.filtered_items) == 2


def test_audit_context_dict_neutralizes_rejected_contract_leak():
    """
    When contract_status is REJECTED in state, audit_context_dict must sanitize
    any section claiming FROZEN / ORACLE_FACT authority for the rejected contract.
    """
    sections = {
        "authority_contract": "Status: FROZEN (ORACLE_FACT)\nInterfaces: /users",
        "authority_user_intent": "Build users API",
    }
    state = {
        "contract_status": "REJECTED",
        "contract": {"task_intent": {"domain": "REST_API"}}
    }

    cleaned, violations = ContextIntegrityAuditor.audit_context_dict(
        sections,
        target_domain="REST_API",
        target_phase="DEVELOPER",
        state=state
    )

    assert len(violations) >= 1
    assert any("REJECTED_ARTIFACT_LEAKAGE" in v for v in violations)
    assert "NON-AUTHORITATIVE" in cleaned["authority_contract"]
    assert "ORACLE_FACT" not in cleaned["authority_contract"]


def test_context_hardening_telemetry_records_integrity_audit():
    """
    build_architect_decision_context and build_developer_repair_context must
    execute the integrity audit and report integrity_violations_detected in telemetry.
    """
    state = {
        "task": "Build FastAPI service",
        "contract_status": "REJECTED",
        "contract": {
            "task_intent": {"domain": "REST_API"},
            "interface_contracts": [{"identifier": "/test"}]
        }
    }

    ctx, telemetry = build_architect_decision_context(state)
    assert "integrity_violations_detected" in telemetry
    assert telemetry["integrity_violations_detected"] >= 1
    assert "NON-AUTHORITATIVE" in ctx

    dev_ctx, dev_telemetry = build_developer_repair_context(state)
    assert "integrity_violations_detected" in dev_telemetry
    assert dev_telemetry["integrity_violations_detected"] >= 1