# ReinDev Studio 🚀
**Autonomous Multi-Agent Software Engineering Studio**  
*Dikembangkan oleh Rekayasa Informatika berdasarkan Metodologi IIDD (Iterative Intent-Driven Development) & Siklus I-CERV.*

---

## 📌 Ringkasan Proyek
**ReinDev Studio** adalah studio rekayasa perangkat lunak multi-agent yang mengorkestrasi tim virtual (Product Manager, System Architect, Developer, QA Tester, dan Code Reviewer) untuk merancang, menulis kode, mengeksekusi unit testing otomatis secara riil, dan mengaudit kode aplikasi.

Aplikasi ini dibangun dengan arsitektur:
- **Frontend:** Flutter Desktop (Windows Native) & Flutter Web dengan Material Design 3 (MD3) dan Riverpod.
- **Backend:** Python 3.13, FastAPI, LangGraph, dan Subprocess Sandbox Test Runner (pytest & lutter test).
- **Engine Dukungan:**
  - **Lokal (Offline & Bebas Biaya):** Ollama dengan model *resident* VRAM 6GB (qwen2.5-coder:7b).
  - **Cloud (OpenRouter):** Model skala industri (Gemini 2.0 / 3.8 Flash, Claude 3.5 / 4.5 Sonnet, Qwen3-Coder).

---

## 🔬 Metodologi Pengembangan: IIDD & Siklus I-CERV
Pengembangan ReinDev Studio berfungsi sebagai studi kasus validasi empiris metodologi **IIDD**:
1. **I - Intent Formulation:** Perumusan intensi dan batas kendali oleh sang *Intent Architect*.
2. **C - Context Alignment:** Penyelarasan spesifikasi teknis dan konteks arsitektur.
3. **E - Autonomous Execution:** Eksekusi otonom implementasi kode oleh agen.
4. **R - Critical Re-evaluation:** Pengujian mandiri lokal (*Micro Loop*) via linter, compiler, dan test runner.
5. **V - Multi-Layered Validation Gate:** Evaluasi final tingkat makro (*Global Correctness*) di bawah otoritas tunggal *Intent Architect*.

Seluruh artefak penelitian dan log kumulatif dicatat secara ketat di direktori `dokumentasi-pengembangan/`.

---

## 🛠️ Struktur Repositori
```text
reindev_studio/
├── .gitignore
├── README.md
├── run.bat                          # Launcher 1-klik
├── backend/                         # Engine LangGraph & FastAPI WebSocket
│   ├── agents/
│   ├── config.py
│   ├── executor.py
│   ├── graph.py
│   ├── server.py
│   └── state.py
├── frontend/                        # Aplikasi Flutter Desktop & Web
│   ├── lib/
│   └── pubspec.yaml
└── dokumentasi-pengembangan/        # Artefak & Log Validasi IIDD
    ├── estimasi_waktu.md            # Estimasi durasi fitur seluruh iterasi
    ├── requirement_traceability_matrix.md # Matriks pelacakan kebutuhan (REQ-xxx)
    ├── context_drift_log.md
    ├── validation_log.md
    ├── decision_log.md
    ├── commit_history.md
    ├── iteration_summary.md
    ├── waktu_estimasi_vs_realisasi.md
    ├── durasi_per_fitur.md
    ├── human_intervention.md
    ├── error_log.md
    ├── interactive_test_log.md
    └── screenshots/
```

