# -*- coding: utf-8 -*-
"""
Unit Tests for V0 Canonical Schema & Pydantic Models
ReinDev Studio — v2.3 (Upstream Requirement Interpretation & Constructibility Gate)
"""

import pytest
from pydantic import ValidationError

from backend.v0_schema import (
    EpistemicStatus,
    RequirementCategory,
    ConstructibilityStatus,
    DetectedArchetype,
    EpistemicItem,
    DataEntityRequirement,
    ApplicationRequirementModel,
    ConstructibilityAssessment,
    V0Metadata,
    V0RequirementOutput,
    to_canonical_json,
    parse_v0_output
)


def test_v0_schema_valid_model():
    """Memverifikasi instansiasi dan kanonikalisasi V0RequirementOutput valid."""
    out = V0RequirementOutput(
        metadata=V0Metadata(
            source_text="Bangun modul REST API inventaris",
            detected_language="python",
            detected_archetype=DetectedArchetype.REST_API
        ),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Modul REST API inventaris",
                basis="Bangun modul REST API inventaris",
                confidence=1.0
            ),
            EpistemicItem(
                id="INT-01",
                category=RequirementCategory.INTERACTION,
                epistemic_status=EpistemicStatus.INTERPRETATION,
                statement="Menyediakan HTTP endpoints untuk inventaris",
                basis="REST API mengimplikasikan interface HTTP",
                confidence=0.9
            )
        ],
        application_requirement_model=ApplicationRequirementModel(
            functional_requirements=["Manajemen inventaris"],
            data_requirements=[
                DataEntityRequirement(
                    entity_name="Item",
                    known_fields=[],
                    unknown_fields=["fields_not_specified"]
                )
            ],
            interaction_requirements=["GET /items", "POST /items"],
            behavioral_requirements=["Validasi input dan return status HTTP tepat"],
            constraints=["Python 3.10+"]
        ),
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Requirement cukup constructible dengan interpretasi standar REST.",
            blocking_gaps=[],
            minimal_viable_interpretation="Implementasikan REST API minimal."
        )
    )

    # Validasi serialization & parsing
    canon_str = to_canonical_json(out)
    assert isinstance(canon_str, str)
    assert "FACT-01" in canon_str

    parsed = parse_v0_output(canon_str)
    assert parsed.metadata.detected_archetype == DetectedArchetype.REST_API
    assert len(parsed.epistemic_ledger) == 2
    assert parsed.constructibility.status == ConstructibilityStatus.WORKABLE


def test_v0_schema_blocking_gaps_inconsistency_workable():
    """Memverifikasi bahwa status WORKABLE dengan blocking_gaps memicu ValueError."""
    with pytest.raises(ValidationError):
        ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Status diklaim workable tetapi ada gap memblokir",
            blocking_gaps=["Gap kritis 1"],
            minimal_viable_interpretation="Solusi"
        )


def test_v0_schema_blocking_gaps_inconsistency_blocked():
    """Memverifikasi bahwa status BLOCKED tanpa blocking_gaps memicu ValueError."""
    with pytest.raises(ValidationError):
        ConstructibilityAssessment(
            status=ConstructibilityStatus.BLOCKED,
            rationale="Status diblokir tetapi tidak menyebutkan gap",
            blocking_gaps=[],
            minimal_viable_interpretation="Solusi"
        )


def test_v0_schema_duplicate_id_detection():
    """Memverifikasi bahwa ID duplikat pada epistemic_ledger ditolak validator Pydantic."""
    with pytest.raises(ValidationError):
        V0RequirementOutput(
            metadata=V0Metadata(source_text="test", detected_language="python"),
            epistemic_ledger=[
                EpistemicItem(
                    id="FACT-01",
                    category=RequirementCategory.FUNCTIONAL,
                    epistemic_status=EpistemicStatus.FACT,
                    statement="Fakta 1",
                    basis="test",
                    confidence=1.0
                ),
                EpistemicItem(
                    id="FACT-01",  # Duplikat ID
                    category=RequirementCategory.CONSTRAINT,
                    epistemic_status=EpistemicStatus.FACT,
                    statement="Fakta 2",
                    basis="test",
                    confidence=1.0
                )
            ],
            constructibility=ConstructibilityAssessment(
                status=ConstructibilityStatus.WORKABLE,
                rationale="Valid",
                blocking_gaps=[]
            )
        )
