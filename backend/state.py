from typing import TypedDict, Dict, List, Any, Optional

class SquadState(TypedDict):
    task: str                          # Deskripsi tugas/fitur awal dari pengguna (Intent)
    provider: str                      # "ollama" atau "openrouter"
    model_name: str                    # Nama model spesifik (misal: qwen2.5-coder:7b)
    target_language: str               # "python" atau "dart"
    specifications: str                # Luaran dari Product Manager (User stories & acceptance criteria)
    architecture_plan: str             # Luaran dari System Architect (File tree & schema)
    code_files: Dict[str, str]         # File kode yang dibuat Developer: {"filename": "content"}
    test_files: Dict[str, str]         # File unit test yang dibuat QA: {"test_filename": "content"}
    test_results: Dict[str, Any]       # Hasil eksekusi test runner: {"passed": bool, "output": str, "exit_code": int}
    iteration_count: int               # Jumlah siklus putaran perbaikan bug (QA -> Dev)
    max_iterations: int                # Batas maksimal putaran perbaikan (default: 3)
    review_notes: str                  # Laporan audit dari Code Reviewer
    status: str                        # Status alur kerja
    logs: List[str]                    # Catatan kronologis pemikiran dan aktivitas agen
    run_id: str                        # ID unik sesi eksekusi untuk observability trace
    output_dir: str                    # Direktori output tempat menyimpan artefak & trace
    executor_intervention_enabled: bool  # Mode eksperimen: apakah Executor mengintervensi/auto-heal artefak (default: True)
    executor_mode: str                 # Mode eksperimen: "ON", "OFF", atau "CODE_ONLY" (default: "ON")
    frozen_oracle_path: Optional[str]  # Path direktori frozen oracle (jika diset, bypass Tester LLM dan load test suite statis)
    developer_feedback: Optional[str]  # Umpan balik diagnostik terstruktur P0-1 untuk Developer (Targeted Error Feedback)
    contract: Optional[Dict[str, Any]]  # Dokumen Machine-Readable Contract formal P0-2 (single authoritative state)
    contract_version: Optional[str]    # Versi kontrak aktif (misal: "1.0.1")
    contract_status: Optional[str]     # Status lifecycle kontrak: DRAFT, ALIGNED, FROZEN, EXECUTING, VALIDATED, REJECTED
    contract_sha256: Optional[str]     # Hash kanonikal SHA-256 (RFC 8785) segel integritas kontrak
    contract_validation_errors: Optional[List[str]] # Daftar pesan galat validasi deterministik aktif turn saat ini
    contract_validation_history: Optional[List[Dict[str, Any]]] # Riwayat kegagalan turn masa lalu yang diarsipkan (immutable)
    contract_feedback: Optional[str]  # Umpan balik terstruktur P0-2.1 jika kontrak ditolak gate
    contract_revision_count: int      # Penghitung putaran revisi kontrak antara gate dan architect (P0-2.1)
    blueprint_revision_count: Optional[int] # Akumulasi putaran revisi Blueprint Validator AST (P0-2.2)
    max_blueprint_revisions: Optional[int] # Batas maksimal revisi AST internal Architect Blueprint Validator (default: 2)
    max_contract_revisions: Optional[int]  # Batas maksimal putaran revisi Contract Validation Gate (default: 2)
    developer_backend: Optional[str]  # Backend khusus Developer: "ollama" atau "openrouter"
    developer_model: Optional[str]    # Model khusus Developer (misal: "google/gemini-3.8-flash")
    repair_history: Optional[List[Dict[str, Any]]] # Riwayat perbaikan per loop untuk Rehabilitation State (D10)
    failed_strategies: Optional[List[Dict[str, Any]]] # Strategi gagal yang pernah dicoba
    known_good_constraints: Optional[List[str]] # Constraint yang sudah terverifikasi benar dan harus dipertahankan

    # Phase-End Validation & Universal Two-Repair Engine (v2.3 with V0)
    v0_requirement_model: Optional[Dict[str, Any]]   # Structured Application Requirement Model dari V0
    v0_validator_contract: Optional[Dict[str, Any]]  # Kontrak hasil evaluasi V0 Validator
    v0_feedback: Optional[str]                       # Umpan balik diagnostik jika V0 Validator FAIL
    repair_attempt_counts: Optional[Dict[str, int]]  # {"v0": 0, "pm": 0, "architect": 0, "developer": 0, "tester": 0, "executor": 0, "reviewer": 0}
    max_phase_repair_attempts: Optional[int]         # Batas maksimal perbaikan per fase (default: 2)
    phase_evidence_packages: Optional[Dict[str, Any]] # Paket bukti CEP per fase
    causal_owner_phase: Optional[str]                # Fase pemilik kausal (misal: "architect", "developer")
    causal_owner_artifact: Optional[str]             # Nama/jenis artefak pemilik kausal
    pm_validator_contract: Optional[Dict[str, Any]]
    architect_validator_contract: Optional[Dict[str, Any]]
    developer_validator_contract: Optional[Dict[str, Any]]
    oracle_validator_contract: Optional[Dict[str, Any]]
    test_suite_validator_contract: Optional[Dict[str, Any]]
    executor_iteration_validator_contract: Optional[Dict[str, Any]]
    reviewer_validator_contract: Optional[Dict[str, Any]]
    latest_evidence_package: Optional[Dict[str, Any]]
    previous_passed_tests: Optional[List[str]]
    invariant_regression_history: Optional[Dict[str, Any]]
    review_verdict: Optional[str]
    expected_oracle_sha: Optional[str]
    locked_invariants: Optional[Dict[str, Any]]  # Invarian deterministik yang berstatus PROVEN/LOCKED
    oscillation_history: Optional[List[Dict[str, Any]]]  # Riwayat osilasi regresi-pemulihan
    # Evidence dari turn sebelumnya untuk discovery kandidat lintas-turn
    # PENTING: hanya digunakan sebagai sumber kandidat, BUKAN sebagai bukti PROVEN langsung
    previous_diagnostic_evidence: Optional[Dict[str, Any]]  # diagnostic_evidence turn N-1
    previous_executor_stderr: Optional[str]  # Stderr kompilasi turn N-1

    # V6 Reviewer Output & Evidence Gate Hardening (v1)
    reviewer_output_classification: Optional[Dict[str, Any]]  # Hasil classify_reviewer_output(): classification, terminal_status, evidence_markers_found, dll.
    reviewer_retry_count: Optional[int]    # Jumlah retry Reviewer yang sudah dilakukan karena output INVALID (default 0)
    reviewer_retry_budget: Optional[int]   # Budget retry Reviewer terkontrol (default 1 → total 2 Reviewer attempts max)

    # Treatment #1.8.6 Canonical Architecture Plan State (v1)
    canonical_blueprint: Optional[Dict[str, Any]]    # Structured canonical ArchitecturalBlueprint dictionary
    stage_a_semantic: Optional[Dict[str, Any]]       # Structured Stage A semantic state (Obligation mappings)
    stage_b_semantic: Optional[Dict[str, Any]]       # Structured Stage B semantic state (Assembly)

