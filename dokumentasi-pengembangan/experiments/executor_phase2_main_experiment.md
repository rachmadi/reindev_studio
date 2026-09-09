# Laporan Hasil Eksperimen Utama (Phase 2 — Main Controlled Experiment)

**Tanggal Pelaksanaan:** 9 September 2026  
**Model:** `qwen2.5-coder:7b` (Ollama, local)  
**Tujuan:** Menguji signifikansi komparatif performa multi-agent squad ReinDev di bawah kondisi perlakuan **Executor OFF** vs **Executor CODE_ONLY** menggunakan 3 suite **Frozen Oracle** independen yang tervalidasi secara kriptografis (SHA-256).

---

## Ringkasan Eksekutif & Status Integritas Eksperimen

- **Total Run:** 30/30 selesai penuh (3 task × 2 mode × 5 replikasi).
- **Integritas Frozen Oracle:** **100% Lolos Audit** (0 pelanggaran kriptografis). Nilai SHA-256 oracle sebelum dan sesudah setiap run identik persis di seluruh 30 run:
  - **FastAPI T1:** `a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63`
  - **CLI T1:** `0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124`
  - **Flutter T1:** `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528`
- **Isolasi Node Tester:** `tester_events == 0` pada seluruh 30 run (LLM Tester sepenuhnya di-bypass oleh `frozen_oracle_node`).
- **Imutabilitas Test Suite:**
  - Mode **OFF**: 0 transformasi kode/test (`transformations == 0`, test hash tetap).
  - Mode **CODE_ONLY**: 0 mutasi test suite (`test_before_hash == test_after_hash`), mutasi hanya terjadi secara terisolasi pada source code produksi.

---

## 1. Raw Observations (30-Run Experimental Matrix)

Berikut adalah rekapitulasi forensik lengkap per run:

| # | Run ID | Mission | Rep | Mode | Init Test | Final Test | Iters | Txs | Status | Dur (s) | Valid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | `project_20260909_081720` | FastAPI T1 | 1 | OFF | 1/5 | 1/5 | 3 | 0 | `needs_revision` | 136.3 | OK |
| 02 | `project_20260909_081942` | FastAPI T1 | 1 | CODE_ONLY | 5/5 | 5/5 | 0 | 1 | `completed` | 106.1 | OK |
| 03 | `project_20260909_082133` | FastAPI T1 | 2 | OFF | 0/1 | 2/5 | 3 | 0 | `needs_revision` | 136.3 | OK |
| 04 | `project_20260909_082354` | FastAPI T1 | 2 | CODE_ONLY | 2/5 | 0/1 | 3 | 2 | `needs_revision` | 140.2 | OK |
| 05 | `project_20260909_082619` | FastAPI T1 | 3 | OFF | 2/5 | 2/5 | 3 | 0 | `needs_revision` | 122.6 | OK |
| 06 | `project_20260909_082827` | FastAPI T1 | 3 | CODE_ONLY | 0/1 | 0/1 | 3 | 3 | `needs_revision` | 136.5 | OK |
| 07 | `project_20260909_083049` | FastAPI T1 | 4 | OFF | 1/5 | 5/5 | 2 | 0 | `completed` | 130.7 | OK |
| 08 | `project_20260909_083304` | FastAPI T1 | 4 | CODE_ONLY | 1/5 | 1/5 | 3 | 2 | `needs_revision` | 116.9 | OK |
| 09 | `project_20260909_083506` | FastAPI T1 | 5 | OFF | 5/5 | 5/5 | 0 | 0 | `completed` | 110.2 | OK |
| 10 | `project_20260909_083702` | FastAPI T1 | 5 | CODE_ONLY | 1/5 | 1/5 | 3 | 3 | `needs_revision` | 126.8 | OK |
| 11 | `project_20260909_083914` | CLI T1 | 1 | OFF | 0/5 | 0/5 | 3 | 0 | `tests_failed` | 200.5 | OK |
| 12 | `project_20260909_084239` | CLI T1 | 1 | CODE_ONLY | 2/5 | 2/5 | 3 | 1 | `needs_revision` | 190.7 | OK |
| 13 | `project_20260909_084555` | CLI T1 | 2 | OFF | 3/5 | 3/5 | 3 | 0 | `needs_revision` | 212.5 | OK |
| 14 | `project_20260909_084932` | CLI T1 | 2 | CODE_ONLY | 5/5 | 5/5 | 0 | 1 | `completed` | 104.3 | OK |
| 15 | `project_20260909_085122` | CLI T1 | 3 | OFF | 3/5 | 3/5 | 3 | 0 | `needs_revision` | 197.8 | OK |
| 16 | `project_20260909_085445` | CLI T1 | 3 | CODE_ONLY | 0/5 | 0/5 | 3 | 1 | `needs_revision` | 172.8 | OK |
| 17 | `project_20260909_085743` | CLI T1 | 4 | OFF | 2/5 | 2/5 | 3 | 0 | `needs_revision` | 200.8 | OK |
| 18 | `project_20260909_090109` | CLI T1 | 4 | CODE_ONLY | 2/5 | 2/5 | 3 | 1 | `needs_revision` | 197.3 | OK |
| 19 | `project_20260909_090431` | CLI T1 | 5 | OFF | 0/5 | 0/5 | 3 | 0 | `needs_revision` | 220.9 | OK |
| 20 | `project_20260909_090817` | CLI T1 | 5 | CODE_ONLY | 5/5 | 5/5 | 0 | 1 | `completed` | 132.9 | OK |
| 21 | `project_20260909_091035` | Flutter T1 | 1 | OFF | 0/1 | 0/1 | 3 | 0 | `needs_revision` | 212.7 | OK |
| 22 | `project_20260909_091412` | Flutter T1 | 1 | CODE_ONLY | 0/1 | 0/1 | 3 | 1 | `needs_revision` | 186.3 | OK |
| 23 | `project_20260909_091724` | Flutter T1 | 2 | OFF | 0/1 | 2/2 | 2 | 0 | `needs_revision` | 174.0 | OK |
| 24 | `project_20260909_092023` | Flutter T1 | 2 | CODE_ONLY | 0/3 | 0/1 | 3 | 4 | `needs_revision` | 211.2 | OK |
| 25 | `project_20260909_092359` | Flutter T1 | 3 | OFF | 0/1 | 2/2 | 2 | 0 | `completed` | 171.1 | OK |
| 26 | `project_20260909_092655` | Flutter T1 | 3 | CODE_ONLY | 2/2 | 2/2 | 0 | 1 | `completed` | 105.6 | OK |
| 27 | `project_20260909_092846` | Flutter T1 | 4 | OFF | 0/1 | 0/1 | 3 | 0 | `needs_revision` | 165.7 | OK |
| 28 | `project_20260909_093137` | Flutter T1 | 4 | CODE_ONLY | 0/1 | 0/1 | 3 | 1 | `needs_revision` | 2582.3 | OK |
| 29 | `project_20260909_101444` | Flutter T1 | 5 | OFF | 0/1 | 2/2 | 2 | 0 | `completed` | 202.7 | OK |
| 30 | `project_20260909_101812` | Flutter T1 | 5 | CODE_ONLY | 1/2 | 1/2 | 3 | 1 | `needs_revision` | 207.3 | OK |

---

## 2. Descriptive Results (Hasil Agregat)

### Matriks Performa Per Task & Treatment Mode

| Task | Mode | Runs | Test Passed | Pass Rate | Reviewer Approved | Avg Iterations | Avg Duration (s) | Total Txs |
|---|---|---|---|---|---|---|---|---|
| **FastAPI T1** | **OFF** | 5 | 2 | **40.0%** | 2 | 2.20 | 127.2 | 0 |
| **FastAPI T1** | **CODE_ONLY** | 5 | 1 | **20.0%** | 1 | 2.40 | 125.3 | 11 |
| **CLI T1** | **OFF** | 5 | 0 | **0.0%** | 1* | 3.00 | 206.5 | 0 |
| **CLI T1** | **CODE_ONLY** | 5 | 2 | **40.0%** | 2 | 1.80 | 159.6 | 5 |
| **Flutter T1** | **OFF** | 5 | 3 | **60.0%** | 2* | 2.40 | 185.2 | 0 |
| **Flutter T1** | **CODE_ONLY** | 5 | 1 | **20.0%** | 1 | 2.40 | 658.5** | 8 |
| **TOTAL** | **OFF** | 15 | 5 | **33.3%** | 5 | 2.53 | 173.0 | 0 |
| **TOTAL** | **CODE_ONLY** | 15 | 4 | **26.7%** | 4 | 2.20 | 314.5 | 24 |
| **KESELURUHAN**| **ALL** | 30 | 9 | **30.0%** | 9 | 2.37 | 243.7 | 24 |

*\* Catatan Discrepancy:*
1. **Run 11 (CLI T1 Rep 1 OFF):** Reviewer menyetujui (`is_approved: True`), namun tes gagal (`0/5`), sehingga final status sistem adalah `tests_failed`.
2. **Run 23 (Flutter T1 Rep 2 OFF):** Tes berhasil penuh (`2/2 passed`), namun Reviewer LLM menolak spesifikasi arsitektur (`needs_revision`).
*\*\* Rata-rata durasi Flutter CODE_ONLY terdistorsi oleh latency Ollama stall pada Run 28 (2582.3s).*

---

## 3. Causal Evidence (Bukti Kausal & Atribusi Perbaikan)

Berdasarkan analisis jejak eksekusi mikro (`run_trace.jsonl`), mekanisme perbaikan diklasifikasikan ke dalam 4 kuadran kausal:

### A. Autonomous Developer Self-Healing (Mode OFF) — 4 Kasus (13.3%)
Terjadi ketika Developer LLM menerima feedback error dari unit test Frozen Oracle tanpa intervensi Executor deterministik, kemudian merevisi kodenya sendiri hingga lulus 100%:
1. **Run 07 (FastAPI Rep 4 OFF):**
   - Iter 0: 1/5 passed (`NameError: name 'Product' is not defined`).
   - Iter 1: Developer menambahkan definisi class Pydantic tetapi masih ada masalah type mismatch.
   - Iter 2: Developer memperbaiki endpoint schema -> **5/5 Passed (100%)**.
2. **Run 23 (Flutter Rep 2 OFF):**
   - Iter 0: Syntax error konstruktor CardMetric.
   - Iter 1: Penyesuaian layout `Column` & `Text`.
   - Iter 2: Widget tree lengkap dan konsisten -> **2/2 Passed (100%)**.
3. **Run 25 (Flutter Rep 3 OFF):**
   - Iter 0: Hilang parameter `required this.data`.
   - Iter 1: Penyesuaian test runner.
   - Iter 2: Struktur widget memenuhi seluruh constraint -> **2/2 Passed (100%)**.
4. **Run 29 (Flutter Rep 5 OFF):**
   - Iter 0: Error missing constructor argument.
   - Iter 1: Perbaikan tipe data `MetricData`.
   - Iter 2: Sempurna -> **2/2 Passed (100%)**.

### B. Executor Assisted Direct Pass (Mode CODE_ONLY) — 4 Kasus (13.3%)
Terjadi pada Iterasi 0 di mana Developer menghasilkan kode yang hampir benar namun memiliki defisiensi impor/sintaks minor. Executor secara deterministik menyisipkan polyfill/impor sehingga langsung lulus 100%:
1. **Run 02 (FastAPI Rep 1 CODE_ONLY):**
   - Developer lupa `from pydantic import BaseModel`.
   - Executor mendeteksi penggunaan `BaseModel` tanpa impor -> menyisipkan `from pydantic import BaseModel`.
   - Hasil: **5/5 Passed** dalam 106.1s.
2. **Run 14 (CLI Rep 2 CODE_ONLY):**
   - Executor memperbaiki impor typing `List` / `Tuple` pada CLI matrix math.
   - Hasil: **5/5 Passed** dalam 104.3s.
3. **Run 20 (CLI Rep 5 CODE_ONLY):**
   - Executor mereparasi signature fungsi CLI.
   - Hasil: **5/5 Passed** dalam 132.9s.
4. **Run 26 (Flutter Rep 3 CODE_ONLY):**
   - Executor menambahkan impor dasar widget Material/CardMetric.
   - Hasil: **2/2 Passed** dalam 105.6s.

### C. Zero-Shot Developer Generation (Mode OFF) — 1 Kasus (3.3%)
- **Run 09 (FastAPI Rep 5 OFF):** Developer langsung menulis implementasi FastAPI CRUD yang lengkap dan valid pada iterasi 0 tanpa ada error sama sekali -> **5/5 Passed (110.2s)**.

### D. Persistent Stagnation / Failure — 21 Kasus (70.0%)
21 run mencapai batas maksimum (`max_iterations = 3`) dan gagal lulus:
- **FastAPI (7 run gagal):** Kesalahan logika bisnis Pydantic v2 vs v1 (`id: Optional[int]`), penanganan status code `404` vs exception unhandled.
- **CLI (8 run gagal):** Kesalahan penanganan parsing argumen CLI (misal `argparse` choices dan casting float/int) di mana feedback error berulang tidak direspon secara tepat oleh Developer LLM.
- **Flutter (6 run gagal):** Kegagalan integrasi Riverpod state management dan widget tree nested constraint.

### Temuan Kausal Kunci:
- **Executor CODE_ONLY bukan perbaikan multi-iterasi:** Pada seluruh run di mana tes awal gagal (Iter > 0), Executor **tidak pernah berhasil mengubah kegagalan menjadi kelulusan** di iterasi berikutnya (0 kasus multi-iteration repair).
- **Peran Executor CODE_ONLY adalah Zero-Shot Syntax Polyfill:** Nilai tambah Executor murni terjadi di iterasi 0 untuk memperbaiki missing imports atau trivial syntax slips.
- **Developer LLM Memiliki Kapabilitas Self-Correction:** Bukti empiris pada Mode OFF menunjukkan bahwa `qwen2.5-coder:7b` mampu melakukan self-healing murni berdasarkan pesan kesalahan compiler/test runner jika struktur logika dasarnya sudah dekat dengan solusi.

---

## 4. Evidence Limitations (Batasan Bukti)

1. **Spesifisitas Model:** Seluruh eksperimen dijalankan menggunakan model tunggal `qwen2.5-coder:7b` (parameter 7 miliar quantisasi). Hasil ini tidak dapat digeneralisasi untuk model yang lebih besar (seperti Qwen-72B, Claude 3.5 Sonnet, atau GPT-4o) yang mungkin memiliki kapabilitas self-healing atau penulisan kode awal yang jauh lebih tinggi.
2. **Karakteristik Task:** Tiga task yang diuji mewakili domain yang berbeda (Backend API, CLI Matrix Engine, Flutter UI), tetapi seluruhnya berskala komponen tunggal (T1).
3. **Hardware & Environment Stall:** Pada Run 28, terjadi temporary freeze socket lokal pada Ollama server yang menyebabkan durasi run mencapai 2582 detik sebelum akhirnya kembali pulih.
4. **Ukuran Sampel:** Replikasi 5 per task × mode (total 30 run) memadai untuk mendeteksi tren dan fenomena kausal kualitatif, namun variansi acak LLM (sampling temperature) masih memainkan peran dalam fluktuasi pass rate.

---

## 5. Candidate Implications (Implikasi untuk Desain ReinDev)

1. **Menghapus Mode ON Secara Permanen:** Eksperimen Phase 1 dan Phase 2 membuktikan bahwa mengizinkan Executor memodifikasi test suite merusak validitas ground truth (oracle dilution). Mode Executor harus dibatasi pada validasi produksi.
2. **Reposisi Executor sebagai "Pre-flight Linter & Polyfiller":** Karena Executor hanya efektif pada iterasi 0 (memperbaiki impor dan sintaksis dasar), fungsi Executor sebaiknya diposisikan sebagai tahap *pre-flight static sanitizer* sebelum kode dikirim ke test runner, bukan sebagai pengganti loop reasoning Developer.
3. **Meningkatkan Kualitas Feedback Loop Developer:** Kegagalan pada 21 run yang mengalami stagnasi menunjukkan bahwa Developer sering mengulang kesalahan yang sama selama 3 iterasi. Arsitektur ReinDev memerlukan penajaman prompt *error diagnostics* (misalnya dengan menyertakan diff kode sebelumnya dan penjelasan kegagalan assertion secara lebih terstruktur).
4. **Sinkronisasi Reviewer dan Test Runner:** Ditemukannya divergensi (Run 11 dan Run 23) menegaskan perlunya penegakan aturan deterministik di mana Reviewer LLM tidak boleh membatalkan kelulusan tes teknis kecuali ditemukan pelanggaran keamanan kritis, dan sebaliknya tidak boleh meluluskan kode yang gagal di sandbox.

---
**Status Validasi Eksperimen:** **SELESAI & TERVERIFIKASI PENUH (AUDITED)**
