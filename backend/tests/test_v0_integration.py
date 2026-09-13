# -*- coding: utf-8 -*-
"""
Integration Tests for V0 Across 10 Requirement Depth & Domain Archetypes
ReinDev Studio — v2.3 (Upstream Requirement Interpretation & Constructibility Gate)

Menguji pembentukan model kebutuhan terstruktur dan validasi deterministik
pada 10 spektrum kedalaman dan keberagaman domain:
1. Minimal Requirement
2. Vague / Ambiguous Requirement
3. Conflicting / Paradoxical Requirement
4. Partially Detailed Requirement
5. Highly Detailed / Complete Requirement
6. Implicit Standard (CRUD)
7. CLI Tool Domain
8. Flutter / Dart Widget Domain
9. Algorithm Domain
10. Data Pipeline Domain
"""

import pytest
from backend.phase_validators import validate_v0_phase
from backend.agents.v0 import create_defensive_v0_model
from backend.v0_schema import (
    V0RequirementOutput,
    V0Metadata,
    EpistemicItem,
    EpistemicStatus,
    RequirementCategory,
    DataEntityRequirement,
    ApplicationRequirementModel,
    ConstructibilityAssessment,
    ConstructibilityStatus,
    DetectedArchetype
)


def test_scenario_01_minimal_requirement():
    """1. Minimal: 'buat rest api buku' -> Fakta minimal, fields terbuka."""
    task = "buat rest api buku"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.REST_API),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Rest api buku",
                basis="buat rest api buku",
                confidence=1.0
            ),
            EpistemicItem(
                id="UNR-01",
                category=RequirementCategory.DATA,
                epistemic_status=EpistemicStatus.UNRESOLVED,
                statement="Atribut buku tidak didefinisikan secara spesifik oleh pengguna",
                basis="Pengguna hanya menyebut 'buku' tanpa spesifikasi atribut",
                confidence=1.0
            )
        ],
        application_requirement_model=ApplicationRequirementModel(
            functional_requirements=["Endpoint REST API untuk entitas buku"],
            data_requirements=[
                DataEntityRequirement(
                    entity_name="Book",
                    known_fields=[],
                    unknown_fields=["attributes_not_specified"]
                )
            ]
        ),
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.PARTIALLY_WORKABLE,
            rationale="Kebutuhan sangat minimal tetapi arsitektur dasar REST dapat disiapkan.",
            blocking_gaps=[],
            minimal_viable_interpretation="Sediakan resource /books dengan skema generik"
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"


def test_scenario_02_vague_ambiguous_requirement():
    """2. Vague: 'buat aplikasi inventaris yang bagus dan cepat' -> Kata sifat subjektif diisolasi."""
    task = "buat aplikasi inventaris yang bagus dan cepat"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.REST_API),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Aplikasi inventaris",
                basis="aplikasi inventaris",
                confidence=1.0
            ),
            EpistemicItem(
                id="AMB-01",
                category=RequirementCategory.CONSTRAINT,
                epistemic_status=EpistemicStatus.AMBIGUITY,
                statement="Kualifikasi subjektif 'bagus dan cepat' tidak terukur secara numerik",
                basis="Frase 'yang bagus dan cepat' merupakan preferensi subjektif",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.PARTIALLY_WORKABLE,
            rationale="Subjektivitas diisolasi, fungsi dasar inventaris dapat dikerjakan.",
            blocking_gaps=[],
            minimal_viable_interpretation="Fokus pada fungsionalitas inventaris standar"
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"


def test_scenario_03_conflicting_paradoxical_requirement():
    """3. Conflicting: 'buat endpoint CRUD tapi read-only' -> Status WAJIB BLOCKED."""
    task = "buat endpoint CRUD tapi read-only"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.REST_API),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="CRUD tapi read-only",
                basis="buat endpoint CRUD tapi read-only",
                confidence=1.0
            ),
            EpistemicItem(
                id="AMB-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.AMBIGUITY,
                statement="Kontradiksi mutlak antara CRUD (Create, Update, Delete) dan read-only",
                basis="Operasi penulisan bertentangan langsung dengan batasan read-only",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.BLOCKED,
            rationale="Kontradiksi fundamental antara operasi penulisan data dan pembatasan read-only.",
            blocking_gaps=["Instruksi menuntut operasi CRUD sekaligus melarang perubahan data."],
            minimal_viable_interpretation="Perlu klarifikasi apakah sistem read-only atau mengizinkan mutasi data."
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"


def test_scenario_04_partially_detailed_requirement():
    """4. Partially Detailed: 'REST API FastAPI inventaris produk dengan validasi pydantic'."""
    task = "REST API FastAPI inventaris produk dengan validasi pydantic"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.REST_API),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="REST API FastAPI inventaris produk",
                basis="REST API FastAPI inventaris produk",
                confidence=1.0
            ),
            EpistemicItem(
                id="FACT-02",
                category=RequirementCategory.CONSTRAINT,
                epistemic_status=EpistemicStatus.FACT,
                statement="Validasi pydantic",
                basis="dengan validasi pydantic",
                confidence=1.0
            ),
            EpistemicItem(
                id="UNR-01",
                category=RequirementCategory.DATA,
                epistemic_status=EpistemicStatus.UNRESOLVED,
                statement="Field produk spesifik tidak disebutkan",
                basis="User tidak menentukan daftar field untuk produk",
                confidence=0.9
            )
        ],
        application_requirement_model=ApplicationRequirementModel(
            functional_requirements=["Manajemen inventaris produk"],
            constraints=["FastAPI", "Pydantic"]
        ),
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Framework dan domain jelas, skema terbuka dapat diakomodasi.",
            blocking_gaps=[]
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"


def test_scenario_05_highly_detailed_requirement():
    """5. Highly Detailed: spesifikasi endpoint dan field eksplisit."""
    task = "FastAPI endpoint POST /items menerima name str dan price float, return status 201"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.REST_API),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.INTERACTION,
                epistemic_status=EpistemicStatus.FACT,
                statement="Endpoint POST /items menerima name str dan price float",
                basis="FastAPI endpoint POST /items menerima name str dan price float",
                confidence=1.0
            ),
            EpistemicItem(
                id="FACT-02",
                category=RequirementCategory.BEHAVIORAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Return status code 201",
                basis="return status 201",
                confidence=1.0
            )
        ],
        application_requirement_model=ApplicationRequirementModel(
            data_requirements=[
                DataEntityRequirement(
                    entity_name="Item",
                    known_fields=["name: str", "price: float"],
                    unknown_fields=[]
                )
            ]
        ),
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Spesifikasi sangat lengkap dan presisi.",
            blocking_gaps=[]
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"


def test_scenario_06_implicit_standard_crud():
    """6. Implicit Standard: CRUD mengimplikasikan operasi Create Read Update Delete."""
    task = "Modul CRUD user"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.REST_API),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Modul CRUD user",
                basis="Modul CRUD user",
                confidence=1.0
            ),
            EpistemicItem(
                id="INT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.INTERPRETATION,
                statement="Menyediakan operasi Create, Read, Update, Delete untuk data user",
                basis="Akronim baku rekayasa perangkat lunak CRUD",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Konvensi CRUD standar dapat diinterpretasikan secara sahih.",
            blocking_gaps=[]
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"


def test_scenario_07_cli_tool_domain():
    """7. CLI Tool Domain: Kalkulator CLI sederhana."""
    task = "Kalkulator CLI sederhana dengan operasi tambah dan kurang"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.CLI_TOOL),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Kalkulator CLI sederhana operasi tambah dan kurang",
                basis="Kalkulator CLI sederhana dengan operasi tambah dan kurang",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Scope CLI tool jelas dan terbatas.",
            blocking_gaps=[]
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"


def test_scenario_08_flutter_widget_domain():
    """8. Flutter / Dart Widget Domain: Widget CardMetric."""
    task = "Widget CardMetric menampilkan judul dan nilai metrik di Flutter"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="dart", detected_archetype=DetectedArchetype.FLUTTER_WIDGET),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Widget CardMetric menampilkan judul dan nilai metrik di Flutter",
                basis="Widget CardMetric menampilkan judul dan nilai metrik di Flutter",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Spesifikasi widget UI terdefinisi.",
            blocking_gaps=[]
        )
    )
    state = {"task": task, "target_language": "dart", "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"


def test_scenario_09_algorithm_domain():
    """9. Algorithm Domain: Perkalian matriks 2D dengan validasi dimensi."""
    task = "Fungsi perkalian matriks 2D dengan validasi dimensi"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.ALGORITHM),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Fungsi perkalian matriks 2D dengan validasi dimensi",
                basis="Fungsi perkalian matriks 2D dengan validasi dimensi",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Logika algoritma matematika jelas.",
            blocking_gaps=[]
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"


def test_scenario_10_data_pipeline_domain():
    """10. Data Pipeline Domain: ETL data CSV penjualan."""
    task = "Pipeline ETL membersihkan data CSV penjualan dan menyimpan ke SQLite"
    out = V0RequirementOutput(
        metadata=V0Metadata(source_text=task, detected_language="python", detected_archetype=DetectedArchetype.DATA_PIPELINE),
        epistemic_ledger=[
            EpistemicItem(
                id="FACT-01",
                category=RequirementCategory.FUNCTIONAL,
                epistemic_status=EpistemicStatus.FACT,
                statement="Pipeline ETL membersihkan data CSV penjualan dan menyimpan ke SQLite",
                basis="Pipeline ETL membersihkan data CSV penjualan dan menyimpan ke SQLite",
                confidence=1.0
            )
        ],
        constructibility=ConstructibilityAssessment(
            status=ConstructibilityStatus.WORKABLE,
            rationale="Alur data pipeline CSV ke SQLite terdefinisi.",
            blocking_gaps=[]
        )
    )
    state = {"task": task, "v0_requirement_model": out.model_dump(), "repair_attempt_counts": {"v0": 0}}
    assert validate_v0_phase(state)["verdict"] == "PASS"
