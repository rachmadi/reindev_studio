"""
Unit Test Suite: Treatment #1.7 — PM Requirement Fidelity & Constructible Completion v1 (Refined)
Location: backend/tests/test_pm_capability_treatment_v1.py

Validates:
1. Full V0 Model Ingestion with Epistemic Stratification into PM Prompt (FACT, INTERPRETATION, ASSUMPTION, UNRESOLVED).
2. Substantive Requirement Formulation passing validate_pm_phase with 0 violations.
3. Epistemic Fidelity & Gap Preservation (Interpretation ≠ Invention).
4. Preservative Repair Prompting on Turn 1+ (Preserve valid, repair violations, anti-collapse).
5. Empty-Completion Collapse Recovery Prompting without Python Synthetic Fallback.
6. Strictly Bounded DRAFT Contract Schema Fidelity (Reusing existing create_draft_contract path).
7. Mission Generality across 5 domains (REST, CLI, Flutter, Data Pipeline, Algorithm).
"""

from unittest.mock import MagicMock, patch
import pytest

from backend.agents.pm import pm_agent, PM_SYSTEM_PROMPT
from backend.phase_validators import validate_pm_phase


# ==============================================================================
# Helper Fixtures
# ==============================================================================

def make_sample_v0_model():
    return {
        "metadata": {
            "source_text": "Buat service REST API inventaris produk dengan FastAPI.",
            "detected_language": "python",
            "detected_archetype": "REST_API"
        },
        "epistemic_ledger": [
            {
                "id": "FACT-01",
                "category": "FUNCTIONAL",
                "epistemic_status": "FACT",
                "statement": "Layanan menggunakan framework FastAPI.",
                "basis": "Kutipan dari task",
                "confidence": 1.0
            },
            {
                "id": "FACT-02",
                "category": "DATA",
                "epistemic_status": "FACT",
                "statement": "Entitas utama adalah inventaris produk.",
                "basis": "Kutipan dari task",
                "confidence": 1.0
            },
            {
                "id": "INTERP-01",
                "category": "FUNCTIONAL",
                "epistemic_status": "INTERPRETATION",
                "statement": "Operasi dasar inventaris mencakup pencatatan dan pembacaan item.",
                "basis": "Inferensi logis dari inventaris",
                "confidence": 0.85
            },
            {
                "id": "ASSUMP-01",
                "category": "CONSTRAINT",
                "epistemic_status": "ASSUMPTION",
                "statement": "Penyimpanan data in-memory cukup untuk implementasi minimal.",
                "basis": "Asumsi rekayasa standar",
                "confidence": 0.8
            },
            {
                "id": "UNRES-01",
                "category": "DATA",
                "epistemic_status": "UNRESOLVED",
                "statement": "Format penomoran SKU atau kode produk belum dispesifikasi pengguna.",
                "basis": "Ketiadaan instruksi format",
                "confidence": 0.9
            }
        ],
        "application_requirement_model": {
            "functional_requirements": [
                "Endpoint pembuatan item produk baru",
                "Endpoint pengambilan daftar produk inventaris"
            ],
            "data_requirements": [
                {
                    "entity_name": "Product",
                    "known_fields": ["name"],
                    "unknown_fields": ["sku_format", "pricing_model"],
                    "notes": "Entitas produk dasar"
                }
            ],
            "interaction_requirements": ["REST JSON payload"],
            "behavioral_requirements": ["Return status 200/201 on success"],
            "constraints": ["Gunakan single module main.py"]
        },
        "constructibility": {
            "status": "PARTIALLY_WORKABLE",
            "rationale": "Kebutuhan inti dapat dikonstruksi meskipun format SKU terbuka.",
            "blocking_gaps": [],
            "minimal_viable_interpretation": "Implementasikan REST API dengan field name dan id otomatis."
        }
    }


def make_sample_substantive_spec():
    return """Ringkasan Sistem:
Sistem ini mengimplementasikan REST API inventaris produk menggunakan framework FastAPI berbasis Python untuk pencatatan dan pembacaan data.

Kebutuhan Fungsional & Kemampuan Utama:
- Sebagai pengguna API, saya ingin membuat item produk baru sehingga data tersimpan dalam inventaris.
- Sebagai pengguna API, saya ingin mengambil daftar produk sehingga saya dapat melihat inventaris terkini.

Kriteria Penerimaan Terukur:
- Skenario 1: Input POST /items dengan name valid menghasilkan output status 200/201 dan payload item tersimpan.
- Skenario 2: Input GET /items menghasilkan output list produk dengan status 200.

Batasan Epistemik & Kebutuhan Terbuka:
Format SKU belum dispesifikasi pengguna dan dipertahankan sebagai field terbuka; penyimpanan in-memory digunakan sebagai batas rekayasa minimal."""


# ==============================================================================
# Test 1: Full V0 Model Ingestion with Epistemic Stratification
# ==============================================================================

def test_v0_structured_model_ingestion():
    v0_model = make_sample_v0_model()
    state = {
        "task": "Buat service REST API inventaris produk dengan FastAPI.",
        "target_language": "python",
        "v0_requirement_model": v0_model,
        "repair_attempt_counts": {"pm": 0}
    }

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=make_sample_substantive_spec())

    with patch("backend.agents.pm.get_llm", return_value=mock_llm):
        res = pm_agent(state)

    assert mock_llm.invoke.called
    call_args = mock_llm.invoke.call_args[0][0]
    human_msg = call_args[1].content

    # Ground truth & stratified ledger checks
    assert "PARTIALLY_WORKABLE" in human_msg
    assert "Implementasikan REST API dengan field name dan id otomatis" in human_msg
    assert "Fakta Terverifikasi (Ground Truth - Batasan Mutlak):" in human_msg
    assert "Layanan menggunakan framework FastAPI" in human_msg
    assert "Interpretasi Logis (Boleh digunakan sebagai derived requirements):" in human_msg
    assert "Asumsi Rekayasa Standar (JANGAN promosikan menjadi Fakta pengguna):" in human_msg
    assert "Kebutuhan Terbuka / Epistemik Gap (Pertahankan sebagai batasan terbuka, JANGAN diisi tebakan):" in human_msg
    assert "Format penomoran SKU atau kode produk belum dispesifikasi" in human_msg
    assert "INTERPRETATION ≠ INVENTION" in call_args[0].content


# ==============================================================================
# Test 2: Substantive Requirement Formulation passing validate_pm_phase
# ==============================================================================

def test_substantive_specification_passes_validation():
    v0_model = make_sample_v0_model()
    state = {
        "task": "Buat service REST API inventaris produk dengan FastAPI.",
        "target_language": "python",
        "v0_requirement_model": v0_model,
        "repair_attempt_counts": {"pm": 0}
    }

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=make_sample_substantive_spec())

    with patch("backend.agents.pm.get_llm", return_value=mock_llm):
        out = pm_agent(state)

    combined_state = {**state, **out}
    result = validate_pm_phase(combined_state)

    assert result["verdict"] == "PASS"
    assert len(result["violations"]) == 0
    assert result["confidence"] == 1.0
    assert out["status"] == "pm_done"


# ==============================================================================
# Test 3: Epistemic Fidelity & Provenance Traceability
# ==============================================================================

def test_epistemic_fidelity_and_provenance():
    v0_model = make_sample_v0_model()
    state = {
        "task": "Buat service REST API inventaris produk dengan FastAPI.",
        "target_language": "python",
        "v0_requirement_model": v0_model,
        "repair_attempt_counts": {"pm": 0}
    }

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=make_sample_substantive_spec())

    with patch("backend.agents.pm.get_llm", return_value=mock_llm):
        out = pm_agent(state)

    contract = out["contract"]
    assert contract["provenance"]["v0_grounded"] is True
    assert contract["provenance"]["pm_capability_version"] == "treatment_1_7_v1"
    # Ensure standard schema intact without foreign keys
    assert "contract_id" in contract
    assert "status" in contract
    assert contract["status"] == "DRAFT"


# ==============================================================================
# Test 4: Preservative Repair Prompting on Turn 1+
# ==============================================================================

def test_preservative_repair_prompting_on_turn_1():
    v0_model = make_sample_v0_model()
    state = {
        "task": "Buat service REST API inventaris produk dengan FastAPI.",
        "target_language": "python",
        "v0_requirement_model": v0_model,
        "specifications": "Ringkasan Sistem: Layanan API inventaris produk.",
        "pm_feedback": "Spesifikasi kehilangan Acceptance Criteria / Skenario Penerimaan konkret.",
        "repair_attempt_counts": {"pm": 1}
    }

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=make_sample_substantive_spec())

    with patch("backend.agents.pm.get_llm", return_value=mock_llm):
        out = pm_agent(state)

    human_msg = mock_llm.invoke.call_args[0][0][1].content
    assert "PERINGATAN PERBAIKAN REINDEVSQUAD (Percobaan #1)" in human_msg
    assert "KANDIDAT SPESIFIKASI SEBELUMNYA:" in human_msg
    assert "Spesifikasi kehilangan Acceptance Criteria" in human_msg
    assert "PANDUAN PERBAIKAN PRESERVATIF:" in human_msg
    assert "PRESERVE: Pertahankan bagian spesifikasi sebelumnya" in human_msg
    assert "REPAIR: Perbaiki secara spesifik pelanggaran yang dilaporkan" in human_msg


# ==============================================================================
# Test 5: Empty-Completion Collapse Recovery Prompting without Python Fallback
# ==============================================================================

def test_empty_completion_collapse_recovery_prompting():
    v0_model = make_sample_v0_model()
    state = {
        "task": "Buat program CLI kalkulator matriks.",
        "target_language": "python",
        "v0_requirement_model": v0_model,
        "specifications": "",  # Empty collapse on turn 0
        "pm_feedback": "Spesifikasi terlalu pendek atau kosong (0 kata)",
        "repair_attempt_counts": {"pm": 1}
    }

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=make_sample_substantive_spec())

    with patch("backend.agents.pm.get_llm", return_value=mock_llm):
        out = pm_agent(state)

    human_msg = mock_llm.invoke.call_args[0][0][1].content
    assert "KANDIDAT SPESIFIKASI SEBELUMNYA: [KOSONG / GENERATION COLLAPSE]" in human_msg
    assert "ANTI-COLLAPSE & V0 GROUNDING" in human_msg
    assert "JANGAN menekan luaran!" in human_msg
    # Ensure no hardcoded Python synthetic fallback was injected into output
    assert out["specifications"] == make_sample_substantive_spec()


# ==============================================================================
# Test 6: Strictly Bounded DRAFT Contract Schema Fidelity
# ==============================================================================

def test_draft_contract_schema_fidelity():
    state = {
        "task": "Buat service REST API inventaris produk dengan FastAPI.",
        "target_language": "python",
        "v0_requirement_model": make_sample_v0_model(),
        "repair_attempt_counts": {"pm": 0}
    }

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=make_sample_substantive_spec())

    with patch("backend.agents.pm.get_llm", return_value=mock_llm):
        out = pm_agent(state)

    contract = out["contract"]
    # Verify exact standard schema fields
    assert "contract_id" in contract
    assert "contract_version" in contract
    assert "status" in contract
    assert "provenance" in contract
    assert "task_intent" in contract
    assert "target_ecosystem" in contract
    assert "functional_requirements" in contract
    assert "requirements" in contract
    assert contract["status"] == "DRAFT"
    # Ensure NO foreign custom schema fields were created
    for req in contract["functional_requirements"]:
        assert "req_id" in req
        assert "description" in req
        assert "acceptance_semantics" in req


# ==============================================================================
# Test 7: Mission Generality across 5 Domains
# ==============================================================================

@pytest.mark.parametrize("domain_key, task_str, lang, expected_domain", [
    ("REST", "Buat service REST API endpoint inventaris barang FastAPI.", "python", "REST_API"),
    ("CLI", "Buat program CLI kalkulator matriks penjumlahan.", "python", "CLI_TOOL"),
    ("FLUTTER", "Buat widget card metric untuk dashboard flutter.", "dart", "FLUTTER_WIDGET"),
    ("PIPELINE", "Buat data pipeline ETL stream processing.", "python", "DATA_PIPELINE"),
    ("ALGORITHM", "Buat fungsi algoritma sorting binary search.", "python", "ALGORITHM"),
])
def test_mission_generality_across_domains(domain_key, task_str, lang, expected_domain):
    state = {
        "task": task_str,
        "target_language": lang,
        "v0_requirement_model": None,
        "repair_attempt_counts": {"pm": 0}
    }

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=make_sample_substantive_spec())

    with patch("backend.agents.pm.get_llm", return_value=mock_llm):
        out = pm_agent(state)

    contract = out["contract"]
    assert contract["task_intent"]["domain"] == expected_domain
    assert contract["status"] == "DRAFT"
    assert len(contract["functional_requirements"]) >= 1
