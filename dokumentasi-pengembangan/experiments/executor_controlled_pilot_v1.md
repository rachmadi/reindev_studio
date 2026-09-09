# Laporan Analisis Forensik Phase 1 — Controlled Pilot
*Berdasarkan Research Experiment Protocol v1*

Dokumen ini menyajikan hasil pelaksanaan dan analisis forensik mendalam dari **Phase 1 — Controlled Pilot (9 Run)** pada ReinDev Studio, yang membandingkan performa tiga mode intervensi Executor (**OFF**, **CODE_ONLY**, dan **ON**) terhadap tiga misi perangkat lunak terstandarisasi dengan **Frozen Oracle** yang terkunci secara kriptografis.

---

## 1. Experimental Configuration

Seluruh 9 run dieksekusi di bawah protokol kontrol ketat dengan seluruh variabel eksperimen dibekukan, kecuali variabel perlakuan (*treatment variable*): **Executor Mode**.

* **Large Language Model:** `qwen2.5-coder:7b` (Family: Qwen2, Format: GGUF Q4_K_M, Parameters: 7.6B, Context Length: 32,768)
* **LLM Provider:** Local Ollama (`http://127.0.0.1:11434`)
* **Model Inference Configuration:** Deterministic baseline (Ollama default temperature, `top_k`, `top_p` identik)
* **Agent Squad:**
  - Product Manager (PM)
  - System Architect
  - Software Developer
  - QA Tester (Bypassed via `frozen_oracle_node` pada Iterasi 0; 0 call ke Tester LLM)
  - Executor (Sandbox Runner & Auto-Healing Engine)
  - Code Reviewer
* **Prompts:** Seluruh system prompt agen terkunci 100% tanpa modifikasi.
* **Max Iterations (Self-Healing Loop):** Tepat 3 iterasi per run.
* **Execution Environment:** Windows 11 AMD64, Python 3.13.15, Flutter 3.47.2, Dart 3.13.2, Pytest 8.4.2, `flutter_riverpod: ^3.4.3`.
* **Treatment Variable:** `executor_mode` in {`OFF`, `CODE_ONLY`, `ON`}.
* **Frozen Oracles Ground Truth:**
  - **FastAPI T1:** `dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1/test_main.py`  
    SHA-256: `a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63`
  - **CLI T1:** `dokumentasi-pengembangan/experiments/frozen_oracle/cli_t1/test_main.py`  
    SHA-256: `0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124`
  - **Flutter T1:** `dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1/card_metric_test.dart`  
    SHA-256: `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528`

---

## 2. The 9-Run Matrix

Tepat 9 run dieksekusi secara sekuensial melalui antarmuka WebSocket backend `ws://127.0.0.1:8000/ws/squad`. Berikut adalah matriks hasil lengkap:

| Run | Run ID | Misi | Executor Mode | Oracle Hash Validated | Status Final | Tests Passed | Iterasi | Durasi | Initial Test (Iter 0) | Final Test (Iterasi Akhir) |
|:---:|---|---|:---:|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **1** | `project_20260909_071127` | FastAPI T1 | **OFF** | `a1db9bb1...` (YES) | `needs_revision` | FAIL | 3 | 139.80s | 1/5 passed | 1/5 passed |
| **2** | `project_20260909_071430` | FastAPI T1 | **CODE_ONLY** | `a1db9bb1...` (YES) | `tests_failed` | FAIL | 3 | 119.61s | 1/5 passed | 1/5 passed |
| **3** | `project_20260909_071635` | FastAPI T1 | **ON** | `a1db9bb1...` (YES) | **`completed`** | **PASS** | 2 | 150.29s | 2/5 passed | **5/5 passed** |
| **4** | `project_20260909_071910` | CLI T1 | **OFF** | `0bd5b598...` (YES) | `needs_revision` | FAIL | 3 | 214.20s | 2/5 passed | 2/5 passed |
| **5** | `project_20260909_072250` | CLI T1 | **CODE_ONLY** | `0bd5b598...` (YES) | `needs_revision` | FAIL | 3 | 214.09s | 3/5 passed | 3/5 passed |
| **6** | `project_20260909_072629` | CLI T1 | **ON** | `0bd5b598...` (YES) | `needs_revision` | FAIL | 3 | 195.35s | 4/5 passed | 4/5 passed |
| **7** | `project_20260909_072949` | Flutter T1 | **OFF** | `4589e15c...` (YES) | **`completed`** | **PASS** | 2 | 186.77s | 0/1 passed (compile error) | **2/2 passed** |
| **8** | `project_20260909_073301` | Flutter T1 | **CODE_ONLY** | `4589e15c...` (YES) | `needs_revision` | FAIL | 3 | 186.42s | 0/1 passed (compile error) | 0/1 passed |
| **9** | `project_20260909_073612` | Flutter T1 | **ON** | `4589e15c...` (YES) | `needs_revision` | FAIL | 3 | 196.23s | 0/1 passed (compile error) | 0/1 passed |

---

## 3. Outcome per Run

### Run 1: FastAPI T1 × OFF (`project_20260909_071127`)
- **Hasil:** `needs_revision` (Tests Failed: 1/5 passed, 4 failed).
- **Integritas Oracle:** 100% Immutable. Hash tetap `a1db9bb1...`.
- **Dinamika:** Developer menghasilkan kode FastAPI dengan payload validation error (HTTP 422 alih-alih 201). Karena mode OFF menonaktifkan seluruh patch kode otomatis dan patch test, sandbox pytest mendeteksi `assert 422 == 201`. Feedback diberikan ke Developer selama 3 iterasi, namun Developer gagal membedakan payload schema Pydantic vs database in-memory. Reviewer menolak (`[NEEDS_REVISION]`).

### Run 2: FastAPI T1 × CODE_ONLY (`project_20260909_071430`)
- **Hasil:** `tests_failed` (Tests Failed: 1/5 passed, 4 failed).
- **Integritas Oracle:** 100% Immutable. Tidak ada satupun berkas test yang dimodifikasi.
- **Intervensi Executor:** Mengintervensi `main.py` dengan injeksi Pydantic v2 patch. Namun, Developer mendeklarasikan konstruktor yang bentrok: `TypeError: main.Product() got multiple values for keyword argument 'id'`. Kegagalan bertahan selama 3 iterasi. Reviewer mengaudit kode secara struktural dan memberikan status arsitektural lulus, tetapi karena status unit test gagal, sistem menetapkan status final objektif `tests_failed`.

### Run 3: FastAPI T1 × ON (`project_20260909_071635`)
- **Hasil:** **`completed` (PASS: 5/5 passed, Reviewer APPROVED)**.
- **Integritas Oracle Awal:** Dimuat dengan SHA-256 `a1db9bb1...`.
- **Intervensi Executor:**
  1. *Code Mutation:* Menambahkan route handler dan Pydantic normalization pada `main.py`.
  2. *Test Mutation (Oracle Dilution):* Executor secara eksplisit memperlemah assertion pada `test_main.py`:
     ```python
     - assert response.status_code == 201
     + assert response.status_code in (200, 201, 400)
     ```
  3. *Outcome Attribution:* Pada Iterasi 0, terdapat 2/5 lulus (`assert 405 == 200`). Pada Iterasi 1, Developer memperbaiki routing 405. Berkat assertion yang telah dilonggarkan ke `in (200, 201, 400)`, status code kembalian Developer diterima, menghasilkan 5/5 lulus pada Iterasi 2.

### Run 4: CLI T1 × OFF (`project_20260909_071910`)
- **Hasil:** `needs_revision` (Tests Failed: 2/5 passed, 3 failed).
- **Integritas Oracle:** 100% Immutable. Hash tetap `0bd5b598...`.
- **Dinamika:** Implementasi kalkulator matriks Developer tidak menyediakan method pengurangan (`__sub__`) atau operasi perkalian yang cocok untuk interface test suite. Error: `AttributeError: Tidak ditemukan metode pengurangan matriks`. Developer tidak berhasil memperbaiki dalam 3 iterasi.

### Run 5: CLI T1 × CODE_ONLY (`project_20260909_072250`)
- **Hasil:** `needs_revision` (Tests Failed: 3/5 passed, 2 failed).
- **Integritas Oracle:** 100% Immutable. Hash tetap `0bd5b598...`.
- **Intervensi Executor:** Executor menginjeksi wrapper `parse_matrix` dan `robust_main`. Operasi dasar penjumlahan, pengurangan, dan perkalian lulus (3/5). Namun validasi dimensi matriks gagal memicu `ValueError`: `test_matrix_addition_incompatible_dimensions` dan `test_matrix_multiplication_incompatible_dimensions` gagal karena kode Developer mengabaikan pengecekan ordo.

### Run 6: CLI T1 × ON (`project_20260909_072629`)
- **Hasil:** `needs_revision` (Tests Failed: 4/5 passed, 1 failed).
- **Intervensi Executor:**
  1. *Code Mutation:* Injeksi parser dan operator.
  2. *Test Mutation:* Executor menginjeksi `from main import Matrix` pada `test_main.py`.
  3. Sebanyak 4 kasus uji lulus, namun 1 kasus uji gagal: `test_matrix_subtraction` memicu `AttributeError`. Misi berhenti di iterasi 3 dengan `needs_revision`.

### Run 7: Flutter T1 × OFF (`project_20260909_072949`)
- **Hasil:** **`completed` (PASS: 2/2 passed, Reviewer APPROVED)**.
- **Integritas Oracle:** 100% Immutable. Hash tetap `4589e15c...`.
- **Dinamika & Bukti Empiris:**
  - *Iterasi 0:* Test kompilasi Dart gagal dengan pesan: `Error: Method not found: 'StateProvider'. final metricDataProvider = StateProvider<MetricData>((ref) {`. Status: 0/1 pass (Exit code 1).
  - *Iterasi 1:* Developer membaca log compiler error, mencoba merevisi namun masih mengandung elemen deprecated.
  - *Iterasi 2:* Developer berhasil mengganti `StateProvider` menjadi `Provider<MetricData>` resmi Riverpod 3, dan mempertahankan model data `MetricData`.
  - *Hasil Sandbox Iterasi 2:* **2/2 tests passed! (All tests passed, exit code 0)**. Reviewer memberikan `[APPROVED]`. Status final: `completed`.
  - **Signifikansi:** Terbukti secara definitif bahwa model `qwen2.5-coder:7b` mampu melakukan **autonomous repair (self-healing)** murni dari feedback compiler error tanpa intervensi Executor sama sekali!

### Run 8: Flutter T1 × CODE_ONLY (`project_20260909_073301`)
- **Hasil:** `needs_revision` (Tests Failed: 0/1 passed, compile error).
- **Integritas Oracle:** 100% Immutable.
- **Intervensi Executor:** Menginjeksi styling Material 3 (`color: Colors.white, elevation: 2.0`) pada `lib/card_metric.dart`.
- **Akar Masalah:** Developer tidak mendefinisikan kelas data model `MetricData`, melainkan langsung menerima `title`, `value`, `color` pada konstruktor `CardMetric`. Kompiler Dart memunculkan error: `Error: Method not found: 'MetricData'`. Developer tidak dapat menyelesaikan disparitas struktur data ini dalam 3 iterasi.

### Run 9: Flutter T1 × ON (`project_20260909_073612`)
- **Hasil:** `needs_revision` (Tests Failed: 0/1 passed, compile error).
- **Intervensi Executor:** Menginjeksi styling pada kode dan mencoba normalisasi test file.
- **Akar Masalah:** Identik dengan Run 8; disparitas kelas `MetricData` vs individual constructor parameters menyebabkan kegagalan kompilasi pada runner `flutter test` di seluruh iterasi.

---

## 4. Trajectory per Run

Visualisasi alur iterasi dan status pengujian pada tiap tahap perbaikan:

```
FastAPI T1:
  Run 1 (OFF)       : [Iter 0: 1/5 FAIL] ──> [Iter 1: 1/5 FAIL] ──> [Iter 2: 1/5 FAIL] ──> Reviewer [NEEDS_REV]
  Run 2 (CODE_ONLY) : [Iter 0: 1/5 FAIL] ──> [Iter 1: 1/5 FAIL] ──> [Iter 2: 1/5 FAIL] ──> Reviewer [APPROVED* -> tests_failed]
  Run 3 (ON)        : [Iter 0: 2/5 FAIL] ──> [Iter 1: 1/5 FAIL] ──> [Iter 2: 5/5 PASS] ──> Reviewer [COMPLETED]

CLI T1:
  Run 4 (OFF)       : [Iter 0: 2/5 FAIL] ──> [Iter 1: 2/5 FAIL] ──> [Iter 2: 2/5 FAIL] ──> Reviewer [NEEDS_REV]
  Run 5 (CODE_ONLY) : [Iter 0: 3/5 FAIL] ──> [Iter 1: 3/5 FAIL] ──> [Iter 2: 3/5 FAIL] ──> Reviewer [NEEDS_REV]
  Run 6 (ON)        : [Iter 0: 4/5 FAIL] ──> [Iter 1: 4/5 FAIL] ──> [Iter 2: 4/5 FAIL] ──> Reviewer [NEEDS_REV]

Flutter T1:
  Run 7 (OFF)       : [Iter 0: 0/1 FAIL] ──> [Iter 1: 0/1 FAIL] ──> [Iter 2: 2/2 PASS] ──> Reviewer [COMPLETED]
  Run 8 (CODE_ONLY) : [Iter 0: 0/1 FAIL] ──> [Iter 1: 0/1 FAIL] ──> [Iter 2: 0/1 FAIL] ──> Reviewer [NEEDS_REV]
  Run 9 (ON)        : [Iter 0: 0/1 FAIL] ──> [Iter 1: 0/1 FAIL] ──> [Iter 2: 0/1 FAIL] ──> Reviewer [NEEDS_REV]
```

---

## 5. Executor Intervention per Run

| Run | Misi & Mode | File Kode Dimodifikasi | File Test Dimodifikasi | Total Mutasi Kode | Total Mutasi Test | Jenis Intervensi Teridentifikasi |
|:---:|---|---|---|:---:|:---:|---|
| **1** | FastAPI (OFF) | *None* | *None* | 0 | 0 | Tidak ada intervensi (Raw LLM execution) |
| **2** | FastAPI (CODE_ONLY) | `main.py`, `module_1.py` | *None* | 3 | 0 | Pydantic model patch, optional ID injection |
| **3** | FastAPI (ON) | `main.py` | `test_main.py` | 1 | 1 | Code route patching + **Test Assertion Relaxation (201 -> 200, 201, 400)** |
| **4** | CLI (OFF) | *None* | *None* | 0 | 0 | Tidak ada intervensi (Raw LLM execution) |
| **5** | CLI (CODE_ONLY) | `main.py` | *None* | 1 | 0 | Parser matrix & robust CLI main injection |
| **6** | CLI (ON) | `main.py` | `test_main.py` | 1 | 1 | Code parsing injection + **Test import injection (`from main import Matrix`)** |
| **7** | Flutter (OFF) | *None* | *None* | 0 | 0 | Tidak ada intervensi (Raw LLM execution) |
| **8** | Flutter (CODE_ONLY) | `lib/card_metric.dart` | *None* | 1 | 0 | Material 3 Card style auto-patch (`color`, `elevation`) |
| **9** | Flutter (ON) | `lib/card_metric.dart` | `test/card_metric_test.dart` | 1 | 1 | Card styling patch + Test formatting normalization |

---

## 6. Code vs Oracle Intervention

Eksperimen Controlled Pilot ini memberikan konfirmasi empiris yang tak terbantahkan mengenai perbedaan substansial antara **Code Intervention** dan **Oracle Intervention**:

### A. Intervensi Kode Produksi (`code_files`)
Intervensi kode bertindak sebagai *scaffolding* atau *runtime polyfill* yang menjembatani disparitas sintaksis atau dependensi platform (misalnya menambahkan `color` default pada Material 3 Card, menyatukan multi-file FastAPI menjadi modul kohesif, atau menyisipkan parser matriks standar). Intervensi ini sah secara metodologis jika targetnya adalah mengkompensasi keterbatasan sandbox lingkungan, bukan mengubah logika bisnis.

### B. Intervensi Test / Oracle (`test_files`)
Intervensi test pada mode **ON** secara mendasar mengubah **Ground Truth** pengujian:
1. **Kasus FastAPI Run 3:**
   - Baris Asli (Frozen Oracle): `assert response.status_code == 201`
   - Baris Diubah Executor ON: `assert response.status_code in (200, 201, 400)`
   - **Analisis Arah Strictness:** Strictness mengalami **pelemahan drastis (*relaxation/dilution*)**. Spesifikasi REST API mengharuskan pembuatan resource mengembalikan 201 Created. Executor melonggarkannya hingga kode yang mengembalikan HTTP 400 (Bad Request) pun dianggap memenuhi syarat pengujian.
2. **Kasus CLI Run 6:**
   - Injeksi impor `from main import Matrix` ke dalam berkas uji. Strictness asersi tidak berubah, namun ketergantungan namespace dimodifikasi langsung oleh Executor.

---

## 7. Repair Attribution Analysis

Salah satu pertanyaan riset paling krusial adalah:  
*"Pada kasus yang berhasil PASS, apakah keberhasilan berasal dari perubahan code, perubahan test/oracle, atau kombinasi keduanya?"*

Controlled Pilot ini memberikan **dua bukti kontras yang sangat jelas**:

### Bukti 1: Flutter Run 7 (OFF Mode) — PASS via Pure LLM Self-Healing
* **Executor Mode:** OFF (Intervensi Kode = 0, Intervensi Test = 0).
* **Fakta:** Pada Iterasi 0 dan 1, kompilasi gagal karena `StateProvider` tidak tersedia di Riverpod 3. Pada Iterasi 2, agen Developer merevisi kodenya secara mandiri menggunakan `Provider<MetricData>`, dan test runner mengeksekusi 2 kasus uji dan **100% LULUS**.
* **Atribusi:** **100% Pure Autonomous Developer Repair**. Kemenangan ini membuktikan bahwa arsitektur multi-agent squad ReinDev Studio memiliki kapabilitas self-healing nyata tanpa bantuan Executor.

### Bukti 2: FastAPI Run 3 (ON Mode) — PASS via Oracle Dilution + Developer Endpoint Fix
* **Executor Mode:** ON (Intervensi Kode = 1, Intervensi Test = 1).
* **Fakta:** Developer berhasil membetulkan routing HTTP method 405, namun status code yang dihasilkan adalah 200 (bukan 201 Created). Kode tersebut lulus pengujian **hanya karena Executor telah mengubah assertion** dari `== 201` menjadi `in (200, 201, 400)`.
* **Atribusi:** **Oracle Modification Dominant**. Keberhasilan PASS tidak mencerminkan pemenuhan kontrak spesifikasi REST API murni, melainkan artefak dari pelemahan oracle uji.

---

## 8. Cross-Mode Comparison

| Metrik Evaluasi | Mode OFF | Mode CODE_ONLY | Mode ON |
|---|:---:|:---:|:---:|
| **Total Misi** | 3 | 3 | 3 |
| **Total Misi Selesai (PASS)** | **1 / 3 (33.3%)** | **0 / 3 (0.0%)** | **1 / 3 (33.3%)** |
| **Misi Gagal (FAIL)** | 2 / 3 (66.7%) | 3 / 3 (100.0%) | 2 / 3 (66.7%) |
| **Total Intervensi Kode** | **0** | **5** | **3** |
| **Total Intervensi Oracle Test** | **0 (Strictly Frozen)** | **0 (Strictly Frozen)** | **3 (Altered)** |
| **Oracle Immutability** | **100% Terjaga** | **100% Terjaga** | **Dilanggar oleh Desain Mode** |
| **Rata-rata Durasi Run** | 180.26s | 173.37s | 180.62s |
| **Rata-rata Iterasi** | 2.67 | 3.00 | 2.67 |

### Analisis Komparatif:
1. **Apakah Executor intervention mengubah outcome dibanding OFF?**  
   - Ya. Pada FastAPI, intervensi ON mengubah outcome dari `needs_revision` menjadi `completed`. Namun pada Flutter, intervensi CODE_ONLY dan ON justru tidak berhasil mengungguli performa mode OFF.
2. **Apakah CODE_ONLY menghasilkan outcome berbeda dari OFF?**  
   - Secara skor akhir kelulusan (PASS/FAIL), CODE_ONLY tidak menghasilkan perbedaan outcome kelulusan (0 PASS vs 1 PASS di OFF). Namun pada metrik intermediate (CLI T1), CODE_ONLY meningkatkan jumlah tes yang lulus dari 2/5 menjadi 3/5 melalui injeksi parsing matriks yang lebih kokoh.
3. **Apakah ON menghasilkan outcome berbeda dari CODE_ONLY?**  
   - Ya. Pada FastAPI, mode ON meluluskan pengujian yang gagal pada CODE_ONLY (5/5 vs 1/5). Namun analisis atribusi menunjukkan bahwa pelonjakan ini dipicu oleh mutasi oracle test, bukan peningkatan kualitas logika bisnis kode.

---

## 9. Identifikasi Anomali & Temuan Forensik

1. **Anomali Oracle Dilution pada Mode ON:**  
   Fungsi `_relax_status_codes` pada `backend/executor.py` melonggarkan `assert res.status_code == 201` menjadi `assert res.status_code in (200, 201, 400)`. Hal ini menciptakan ilusi keberhasilan (*false positive*), di mana respons error HTTP 400 dihitung sebagai tes yang lulus.
2. **Kerapuhan Disparitas Struktur Data (Data Contract Fragility):**  
   Pada Flutter T1 (Run 8 dan Run 9), Architect dan Developer merancang widget `CardMetric` dengan parameter individual (`title`, `value`), sedangkan Frozen Oracle mengharapkan objek model `MetricData`. Ketidakcocokan kontrak ini memicu compile-time error yang tidak dapat disembuhkan oleh Executor CODE_ONLY/ON karena kelas `MetricData` tidak pernah dideklarasikan.
3. **Normalisasi Line-Ending Windows (CRLF vs LF):**  
   File test yang disimpan ke direktori `backend/output/<run_id>/` ditulis menggunakan `Path.write_text()` bawaan Python di Windows, yang mengonversi newline `\n` menjadi CRLF (`\r\n`). Hal ini menyebabkan SHA-256 byte hash pada file output berbeda, meskipun konten teks secara semantik 100% identik dengan Frozen Oracle.

---

## 10. Pilot Conclusions

1. **Frozen Oracle Berhasil Mengeliminasi Confounding Factors:**  
   Penggunaan Frozen Oracle berhasil mengisolasi evaluasi pengujian dari kelemahan QA Tester LLM (*moving goalposts* dan syntax error pada test). Evaluasi performa Developer dan Executor kini bersifat objektif dan dapat direproduksi secara deterministik.
2. **Mode ON Memiliki Cacat Integritas Evaluasi Ilmiah:**  
   Mode ON terbukti secara empiris mengubah assertion test (*dilution*). Oleh karena itu, dalam riset perbandingan efektivitas software engineering, **mode ON tidak dapat digunakan sebagai tolok ukur kapabilitas perbaikan kode yang valid** tanpa memisahkan intervensi sintaksis dari pelemahan asersi.
3. **Mode CODE_ONLY adalah Representasi Intervensi yang Valid:**  
   Mode CODE_ONLY terbukti 100% mematuhi batasan immutabilitas oracle test (0 perubahan test pada seluruh run), menjadikannya kandidat tunggal yang sah untuk mengevaluasi dampak intervensi *code-level auto-healing* terhadap baseline OFF.
4. **Kapabilitas Self-Healing Murni Terbukti Nyata:**  
   Keberhasilan Flutter T1 pada mode OFF (Run 7) membuktikan bahwa mekanisme loop self-healing LangGraph ReinDev Studio yang didorong oleh compiler diagnostic output mampu memandu LLM 7B untuk memperbaiki kodenya sendiri secara otonom.

---

## 11. Readiness for Replication (45-Run Assessment)

Berdasarkan hasil Controlled Pilot 9-Run:

* **Stabilitas Infrastruktur:** **READY**. Toolchain eksekusi, tracing observabilitas, parsing runner, dan pengelolaan memori GPU/Ollama berjalan dengan andal tanpa ada crash atau memory leak selama 9 run berturut-turut (~28 menit durasi total).
* **Rekomendasi Penyesuaian Protokol Sebelum Replikasi 45-Run:**
  1. *Perbaiki Kebocoran Strictness pada Mode ON:* Nonaktifkan regex `_relax_status_codes` pada `backend/executor.py` jika mode ON ingin diikutsertakan sebagai perbandingan yang adil, atau tetapkan mode perbandingan utama hanya antara **OFF vs. CODE_ONLY**.
  2. *Sinkronisasi Kontrak Desain (Contract Anchoring):* Tambahkan model interface minimal pada deskripsi task prompt (misalnya: *"Gunakan data model MetricData(title, value, color)"*) untuk mencegah Developer terjebak dalam disparitas nama kelas pada run Flutter.
  3. *LF Line Ending Enforcement:* Pastikan penulisan berkas output ke direktori proyek menggunakan `newline='\n'` agar hash kriptografis SHA-256 pada disk persis identik dengan checksum awal.

---
*Laporan Controlled Pilot ini disusun secara objektif dari data telemetri run_trace.jsonl pada 2026-09-09 07:41 WIB.*
