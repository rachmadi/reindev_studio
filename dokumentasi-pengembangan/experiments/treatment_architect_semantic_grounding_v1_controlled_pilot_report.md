# Treatment — Architect Semantic Grounding v1: Controlled 1×3 E2E Pilot Report

**Tanggal & Waktu:** 2026-09-19 11:28:30 WIB  
**Model Target:** `qwen2.5-coder:7b` (Ollama localhost)  
**Status Eksperimen:** COMPLETED (Controlled 1×3 E2E Pilot)  
**File Summary:** `dokumentasi-pengembangan/experiments/treatment_architect_semantic_grounding_v1_pilot_summary.json`  

---

## Ringkasan Eksekutif

Controlled 1×3 E2E Pilot dieksekusi secara ketat di bawah **Governance Freeze** penuh. Tepat satu modifikasi diterapkan pada Architect (`backend/agents/architect.py`), yaitu injeksi **Canonical Acceptance Obligation Mapping** (Part 1) dan **Satu Generic Worked Example** (Part 2) pada Seksi [2] prompt Turn 0.

Hasil Pilot:
- **CLI (`cli_t1`):** **PASS** (1-shot Turn 0 Frozen Contract, 5/5 tests passed, 0 loops, durasi 354.5s)
- **FastAPI (`fastapi_t1`):** **FAIL** (Contract REJECTED, 0/5 tests, durasi 548.98s)
- **Flutter (`flutter_t1`):** **FAIL** (Contract FROZEN pada Repair Turn 1, gagal di Developer type mismatch `double` vs `String`, durasi 451.65s)
- **E2E Success Rate:** **1 / 3 (33.3%)**

---

## 15-Point Empirical Evaluation

### 1. Preflight Verification (Gates A–I)
- **Status:** **9/9 GATES PASS (100%)**
- **Detail:**
  - Gate A (Compilation): Clean AST syntax across all validation & graph files.
  - Gate B (Regression): 1,062 tests passed in 31.25s (871 modular in `backend/tests/` + 191 foundational in root `backend/`, 0 regressions).
  - Gate C (Oracle SHA-256): 100% match across `fastapi_t1`, `cli_t1`, `flutter_t1`.
  - Gate D (Tester Isolation): QA Tester LLM bypassed; frozen oracle loaded deterministically.
  - Gate E (StateGraph): Phase-validated graph compiled with 16 nodes.
  - Gate F (Validator Boundaries): All 6 phase-end validators verified in graph.
  - Gate G (Halt & Route): Pre-execution failure properly halted and routed.
  - Gate H (PASS Propagation): Clean developer code accepted and passed.
  - Gate I (Telemetry): Trace logging verified (`run_trace.jsonl`).

### 2. Exact Architect Prompt Delta
- **Perubahan Kode:** Tepat 1 file (`backend/agents/architect.py`), penambahan fungsi generik `format_canonical_obligation_blueprint_mapping` dan konstanta `GENERIC_WORKED_EXAMPLE`.
- **Lokasi Injeksi:** Seksi `[2] ACCEPTANCE OBLIGATION LEDGER`.
- **Ukuran Prompt vs LKG Baseline:**
  - `fastapi_t1`: 9,373 $\to$ 12,878 karakter (+3,505 karakter / +37.4%)
  - `cli_t1`: 9,318 $\to$ 12,757 karakter (+3,439 karakter / +36.9%)
  - `flutter_t1`: 7,467 $\to$ 10,244 karakter (+2,777 karakter / +37.2%)
- **Invocations:** Strictly single LLM invocation per turn preserved (`len(recorded) == 1`).

### 3. FastAPI Evaluation (`fastapi_t1`)
- **Run ID:** `pv_pilot_fastapi_t1_rep1_20260919_110555`
- **Final Verdict:** `FAIL`
- **Failure Classification:** `C. Contract Failure`
- **Durasi:** 548.98 detik
- **Analisis Trajektori:**
  - *Turn 0 (192.01s):* Model menerima mapping kanonikal, namun menghasilkan scaffold dengan rute `/inventaris/{id}` (terpengaruh bias teks prompt pengguna bahasa Indonesia) alih-alih rute otoritatif `/products`.
  - *Contract Gate Audit:* Contract Gate P0-2.1 secara deterministik menolak 4 endpoint yang hilang (`POST /products`, `GET /products`, `GET /products/{id}`, `DELETE /products/{id}`).
  - *Turn 1 Repair (91.94s):* Model mengalami `SCHEMA_VIOLATION` (Pydantic ValidationError karena memasukkan dictionary sembarang pada `code_scaffold`).
  - *Turn 2 Repair (73.68s):* Budget perbaikan habis; kontrak tetap `REJECTED`.
  - *Fail-Closed Enforcement:* Kode cacat 100% tertahan di gerbang kontrak dan tidak pernah bocor ke Developer.

### 4. CLI Evaluation (`cli_t1`)
- **Run ID:** `pv_pilot_cli_t1_rep1_20260919_111504`
- **Final Verdict:** `PASS`
- **Review Verdict:** `APPROVED`
- **Durasi:** 354.50 detik
- **Analisis Trajektori:**
  - *Turn 0 (70.84s):* Model memetakan seluruh 4 obligasi (`Matrix`, `add_matrices`, `subtract_matrices`, `multiply_matrices`) dengan 100% presisi.
  - *Contract Gate Audit:* **PASS**, Segel SHA-256 `f4d6fd53efd7a1e4...` terbentuk (FROZEN = True).
  - *Developer Phase (63.63s):* Developer menghasilkan implementasi Python lengkap dengan penanganan error dimensi dan operasi matriks.
  - *Executor Sandbox:* 5/5 unit tests passed dalam 0.10s.
  - *Developer Loops:* 0 loops (First-shot convergence).

### 5. Flutter Evaluation (`flutter_t1`)
- **Run ID:** `pv_pilot_flutter_t1_rep1_20260919_112058`
- **Final Verdict:** `FAIL`
- **Failure Classification:** `A. Developer Failure` (Bukan kegagalan Architect!)
- **Durasi:** 451.65 detik
- **Analisis Trajektori:**
  - *Turn 0 (61.95s):* Architect menghasilkan `CardMetric` (COVERED), tetapi konstruktor `MetricData` dibuat dengan 3 parameter posisional alih-alih named parameter. Contract Gate mendeteksi `CALL_SHAPE_INCOMPATIBILITY` dan menolak kontrak.
  - *Turn 1 Repair (83.12s):* Model menerima paket bukti `EV-B927B7535D94`, memperbaiki konstruktor menjadi `{required this.title, required this.value, required this.color}`. Contract Gate **PASS**, Kontrak **FROZEN** (Segel: `124f7f7ad54b994e...`).
  - *Developer Phase (26.91s):* Developer mendeklarasikan `final double value;` pada model Dart, sedangkan pengujian Oracle mengirimkan `value: '1000'` dan `value: '78%'` (String).
  - *Executor Sandbox:* Kompilasi Dart gagal (`The argument type 'String' can't be assigned to the parameter type 'double'`).
  - *Developer Repair Loops:* Developer menghabiskan 5 turn tanpa menyelaraskan tipe ke `String` atau `dynamic`.

### 6. Architect Fidelity
| Task | Obligation Coverage | Identity Fidelity | Invented Elements | Contract Status |
| :--- | :---: | :---: | :---: | :---: |
| **FastAPI** | 0 / 4 (0%) | 0% (rute diganti `/inventaris/{id}`) | 0 | `REJECTED` |
| **CLI** | 4 / 4 (100%) | 100% | 0 | `FROZEN` |
| **Flutter** | 2 / 2 (100% pada T1) | 100% (T1) | 0 | `FROZEN` |

### 7. Developer Behavior
- **CLI:** Eksekusi sempurna, 0 loop perbaikan, kode matematis lengkap dan stabil.
- **Flutter:** Menghasilkan widget Material 3 & Riverpod yang valid secara sintaksis, namun gagal mendeteksi ketidaksesuaian tipe parameter input Oracle (`String` vs `double`).
- **FastAPI:** Tidak dijalankan karena perlindungan fail-closed Contract Gate.

### 8. Oracle Results
- **CLI:** 5 / 5 tests passed (100%)
- **Flutter:** 0 / 1 tests passed (kompilasi pengujian gagal akibat tipe argumen)
- **FastAPI:** 0 / 5 tests passed (tidak dieksekusi)
- **Integritas Checksum:** Ketiga SHA-256 Oracle frozen terverifikasi 100% utuh tanpa modifikasi.

### 9. E2E Results
- **Total Lulus:** 1 / 3 task (33.3%)
- **Target:** 3 / 3 task (100%)
- **Hasil:** Target E2E 3/3 belum tercapai.

### 10. Regression Analysis
- **CLI Baseline:** Stabil di 1-shot pass (tidak ada regresi).
- **Flutter Baseline:** Kontrak berhasil dibekukan (FROZEN) pada Turn 1 (perbaikan dibandingkan baseline unsealed), namun terhenti di Developer type alignment.
- **Regression Test Inventory Breakdown:**
  - **Full Backend Suite (`backend/` — Gate B Target):** **1,062 / 1,062 passed** (31.25s, 0 regresi).
  - **Modular Architecture & Validator Suite (`backend/tests/`):** **871 / 871 passed** (14.62s).
  - **Foundational Root Unit Suite (`backend/test_*.py`):** **191 / 191 passed** (0.94s).
  - **Total Regresi:** **0**. Semua baseline tests terverifikasi stabil.

### 11. Latency & Resource Utilization
- **FastAPI:** 548.98s (Architect T0: 192.01s, T1: 91.94s, T2: 73.68s)
- **CLI:** 354.50s (Architect T0: 70.84s, Developer: 63.63s, Test: 3.31s)
- **Flutter:** 451.65s (Architect T0: 61.95s, T1: 83.12s, Developer loops: ~300s)

### 12. First Divergence Analysis
- **FastAPI:** Divergensi pertama terjadi pada **Architect Turn 0 (11:12:18 WIB)**. Model `qwen2.5-coder:7b` mengabaikan mapping kanonikal otoritatif `/products` dan memilih rute semantik bebas `/inventaris/{id}` yang berasal dari User Task bahasa Indonesia.
- **Flutter:** Divergensi pertama terjadi pada **Developer Turn 0 (11:26:35 WIB)**. Developer mengasumsikan `value` bertipe `double` padahal pemanggilan Oracle menggunakan string literals (`'1000'`, `'78%'`).

### 13. Comparison with TRUE LKG Baseline
- **CLI:** Setara dengan LKG (PASS 1-shot).
- **Flutter:** Kontrak Architect berhasil FROZEN pada Turn 1 (lebih baik daripada beberapa kegagalan kontrak sebelumnya), namun E2E belum PASS.
- **FastAPI:** Sama dengan baseline (tetap gagal di Architect Contract Gate).

### 14. Classification
Berdasarkan kriteria interpretasi eksperimen:
- **Kategori:** **CASE B**
  *(Architect membaik pada CLI dan Flutter yang berhasil FROZEN, tetapi E2E < 3/3 karena divergensi rute FastAPI dan Developer Flutter).*
- **Klasifikasi:** **PARTIAL**

### 15. Recommendation
- **Rekomendasi:** **FORENSIC ONLY**
- **Tindakan:**
  - JANGAN menetapkan treatment ini sebagai LKG.
  - JANGAN menambahkan perbaikan atau validator baru secara terburu-buru.
  - Tegakkan **STOP CONDITION** dan tunggu arahan eksplisit dari Intent Architect.
