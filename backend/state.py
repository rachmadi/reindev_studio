from typing import TypedDict, Dict, List, Any

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
