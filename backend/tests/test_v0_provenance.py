# -*- coding: utf-8 -*-
"""
Unit Tests for V0 Epistemic Provenance Auditing (Zero Hallucinated Facts)
ReinDev Studio — v2.3 (Upstream Requirement Interpretation & Constructibility Gate)
"""

import pytest
from backend.phase_validators import validate_v0_phase
from backend.v0_schema import (
    V0RequirementOutput,
    V0Metadata,
    EpistemicItem,
    EpistemicStatus,
    RequirementCategory,
    ConstructibilityAssessment,
    ConstructibilityStatus,
    DetectedArchetype,
    ApplicationRequirementModel
)


def test_provenance_valid_anchored_facts():
    """Memverifikasi bahwa fakta yang memiliki token/substring pada task lolos validasi."""
    task = "Bangun modul REST API FastAPI untuk manajemen inventaris produk dengan validasi Pydantic"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.REST_API),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Modul REST API FastAPI manajemen inventaris produk",
                basis="Bangun modul REST API FastAPI untuk manajemen inventaris produk",
                confidence=1.0
            ),
            EpistemicItem(
                id="FACT-02",
                category=RequirementCategory.CONSTRAINT,
                epistemic_status=EpistemicStatus.FACT,
                statement="Validasi menggunakan Pydantic",
                basis="dengan validasi Pydantic",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Fakta lengkap dan terverifikasi.",
            blocking_gaps=[]
        )
    )

    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    contract = validate_v0_phase(state)
    assert contract["verdict"] == "PASS"


def test_provenance_detects_hallucinated_fields_claimed_as_facts():
    """
    Memverifikasi pencegahan kebocoran asumsi:
    Jika agen mengklaim 'Field quantity bertipe int' sebagai FACT padahal pengguna
    hanya meminta 'inventaris produk' umum, validator deterministik WAJIB menolak.
    """
    task = "Bangun modul REST API FastAPI inventaris produk"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.REST_API),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.DATA,
                epistemic_status=EpistemicStatus.FACT,
                statement="Model Produk memiliki kolom quantity bertipe integer",  # Halusinasi / kebocoran tanpa dasar
                basis="Kebutuhan inventaris produk",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Model diklaim workable.",
            blocking_gaps=[]
        )
    )

    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    contract = validate_v0_phase(state)
    assert contract["verdict"] == "FAIL"
    assert any(v["violation_type"] == "HALLUCINATED_FACT_VIOLATION" for v in contract["violations"])


def test_provenance_empty_task_cannot_assert_facts():
    """Memverifikasi bahwa jika task pengguna kosong, tidak ada item FACT yang diizinkan."""
    task = ""
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python"),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Aplikasi default",
                basis="default",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.BLOCKED,
            rationale="Task kosong",
            blocking_gaps=["Task kosong"]
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    contract = validate_v0_phase(state)
    assert contract["verdict"] == "FAIL"
    assert any(v["violation_type"] == "HALLUCINATED_FACT_VIOLATION" for v in contract["violations"])
