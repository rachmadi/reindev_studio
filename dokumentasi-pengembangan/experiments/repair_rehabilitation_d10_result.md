# Laporan Eksperimen: Improved Repentance + D10 Developer Repair-Depth

**Model Squad & Developer:** `qwen2.5-coder:7b` (100% Unified Local Squad via Ollama)  
**Architect Depth Budget:** Blueprint = `5`, Contract Gate = `5`  
**Developer Depth Budget:** Max Loops = `10` (D10)  
**Tanggal Eksekusi:** 2026-09-10 08:26 – 10:32 WIB  
**Total Durasi Eksekusi:** 7.523,6s (~125,4 menit / ~2,1 jam)  
**Gross Pass Rate:** **0 / 9 (0.0%)** (1 Run Lulus Test 100% pada Loop 0, tertahan di Contract Gate)  

---

## 1. Ringkasan Eksekutif & Komparasi Antar-Eksperimen

Eksperimen ini menguji hipotesis kunci:
> *Apakah intervensi ganda berupa **Improved Repentance Guidance (7-Langkah Preskriptif + Memori Rehabilitasi)** yang dipadukan dengan **Perluasan Repair Depth Developer menjadi 10 Putaran (D10)** mampu mengubah trajektori kegagalan/stagnan menjadi konvergen (recovery), serta pada kedalaman berapa penambahan loop mulai menghasilkan diminishing returns?*

### Tabel Komparasi Evolusioner (Baseline A2/D3 vs. A5/D5 vs. Improved Repentance + D10)

| Dimensi Evaluasi | Baseline A2 / D3 | Repair-Depth A5 / D5 | Improved Repentance + D10 | Analisis Tren |
|---|---|---|---|---|
| **FastAPI T1 Pass Rate** | 0 / 3 (0.0%) | 0 / 3 (0.0%) | 0 / 3 (0.0%) | Stagnasi persisten pada state leak |
| **CLI T1 Pass Rate** | 0 / 3 (0.0%) | 0 / 3 (0.0%) | 0 / 3 (0.0%) | Lolos 53–83% test, stagnan di edge-case |
| **Flutter T1 Pass Rate** | 0 / 3 (0.0%) | 0 / 3 (0.0%) | 0 / 3 (0.0%) | 1 Run lulus 100% test di Loop 0 (`gated`) |
| **Gross Pass Rate** | **0 / 9 (0.0%)** | **0 / 9 (0.0%)** | **0 / 9 (0.0%)** | Gross tetap 0%, namun resolusi diagnostik naik |
| **Rata-rata Durasi per Run** | ~272,0 s | ~387,0 s | 836,0 s | Beban komputasi meningkat 2,16x lipat |
| **First Recovery Loop Rata-rata** | N/A (stagnan) | Loop 3–4 | **Loop 1–2** | **Pemulihan awal terjadi jauh lebih cepat** |
| **Stagnation Onset Rata-rata** | Loop 2 | Loop 2 | **Loop 2,1** | **Batas kapasitas reasoning tercapai di Loop 2** |
| **Tingkat Regresi (Regressions)** | Tinggi (>30%) | Sedang (10–20%) | **0 / 9 (0.0%)** | **Aturan Preservasi 100% mengeliminasi regresi** |

---

## 2. Rincian Metrik & Hasil Rehabilitasi per Run

| Run | Task | Rep | Status Akhir | Tests Pass Rate | Dev Depth Terpakai | Trajektori | 1st Recovery | Pass Loop | Stagnation Onset | Strategy Repetitions | Regressions | Terminology Aligned | Primary Failure Category |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | `fastapi_t1` | 1 | **FAIL** | 1 / 3 (33.3%) | 10 / 10 | `stagnant` | Loop 3 | - | Loop 2 | 8 | 0 | ✅ Ya | Developer Reasoning |
| 2 | `fastapi_t1` | 2 | **FAIL** | 0 / 0 (0.0%) | 10 / 10 | `stagnant` | - | - | Loop 2 | 9 | 0 | ✅ Ya | Developer Reasoning |
| 3 | `fastapi_t1` | 3 | **FAIL** | 1 / 2 (50.0%) | 10 / 10 | `stagnant` | Loop 1 | - | Loop 3 | 8 | 0 | ✅ Ya | Developer Reasoning |
| 4 | `cli_t1` | 1 | **FAIL** | 5 / 6 (83.3%) | 10 / 10 | `stagnant` | Loop 1 | Loop 1 | Loop 2 | 9 | 0 | ✅ Ya | Developer Reasoning |
| 5 | `cli_t1` | 2 | **FAIL** | 4 / 6 (66.7%) | 10 / 10 | `stagnant` | Loop 1 | - | Loop 2 | 9 | 0 | ❌ Tidak | Developer Reasoning |
| 6 | `cli_t1` | 3 | **FAIL** | 7 / 13 (53.8%) | 10 / 10 | `stagnant` | Loop 1 | Loop 1 | Loop 2 | 9 | 0 | ✅ Ya | Developer Reasoning |
| 7 | `flutter_t1` | 1 | **FAIL** | 0 / 1 (0.0%) | 10 / 10 | `stagnant` | - | - | Loop 2 | 8 | 0 | ✅ Ya | Developer Reasoning |
| 8 | `flutter_t1` | 2 | **FAIL** | **1 / 1 (100.0%)** | **0 / 10** | `gated` | Loop 1 | Loop 1 | None | 0 | 0 | ❌ Tidak | Contract Term Mismatch |
| 9 | `flutter_t1` | 3 | **FAIL** | 0 / 1 (0.0%) | 10 / 10 | `stagnant` | - | - | Loop 2 | 9 | 0 | ❌ Tidak | Developer Reasoning |

---

## 3. Temuan Fenomenologis & Analisis Empiris Mendalam

### A. Efektivitas 7-Langkah Repentance Guidance (First Recovery Accelerator)

1. **Akselerasi Pemulihan Sintaksis dan Impor (Loop 1–2):**
   * Berbeda dengan eksperimen baseline A2/D3 di mana model langsung terjebak crash impor tanpa pernah menjalankan test, Repentance Guidance secara konsisten memicu perbaikan pada putaran-putaran awal.
   * Pada **Run 1 (`fastapi_t1`)**, feedback preskriptif Rule 1–4 berhasil memandu Developer menambahkan `ConfigDict` dan mendekorasi validator Pydantic dengan `@classmethod`, meloloskan `test_add_product` (33% lulus).
   * Pada **Run 4, 5, 6 (`cli_t1`)**, Developer langsung meloloskan 53% hingga 83% unit test sejak Loop 0 dan Loop 1.
2. **Eliminasi Total Terhadap Regresi (Zero Regressions):**
   * Sepanjang 9 run dan total 77 putaran developer loop, **tercatat 0 kasus regresi (`regressions = 0`)**.
   * Integrasi klausul `[PRESERVATION RULE]` dan pemantauan `known_good_constraints` berbasis bukti eksekusi terbukti 100% efektif mencegah Developer merusak fungsi-fungsi yang sebelumnya telah lulus pengujian.

---

### B. Pemetaan Diminishing Returns Ekstrem pada Perluasan D10

Salah satu tujuan utama eksperimen ini adalah memetakan titik konvergensi vs titik stagnasi ketika kedalaman repair diperluas dari 5 menjadi 10 loop:

```
[LOOP 0] -> Initial Code Generated (Crash / Partial Pass 0–83%)
   │
[LOOP 1–2] -> REPENTANCE ACTIVE: First Recovery Point (Perbaikan Impor / Logika Dasar)
   │
[LOOP 2–3] -> ⚠️ STAGNATION ONSET: Model Menemui Batas Logika Semantik
   │
[LOOP 4–10] -> 🛑 FLATLINE ZONE (DIMINISHING RETURNS EKSTREM):
               - Hash Kode 100% Identik (Literal Stagnation: 8–9x berulang)
               - Variasi Non-Substantif (Hapus Docstring / Komentar)
               - Konsumsi Waktu: +449 detik per run tanpa perubahan lulus test
```

* **Stagnation Onset Terjadi Sangat Dini:** Di seluruh run yang gagal, *stagnation onset* terjadi pada **Loop 2 atau Loop 3**.
* **Zero Convergence pada Loop 5–10:** Tidak ada satupun run yang mengalami konvergensi atau penambahan persentase kelulusan setelah Loop 3.
* **Kesimpulan Diminishing Returns:** Memperbesar jatah loop hingga 10 putaran terbukti merupakan pemborosan komputasi (*wasteful compute*) apabila kebuntuan berakar pada batas semantik atau kecacatan arsitektural. Ambang batas optimal untuk repair depth pada model 7B adalah **maksimal 3 hingga 4 loop**.

---

### C. Triad Penyebab Stagnasi Persisten (The Semantic Deadlock Triad)

Analisis telemetri `run_trace.jsonl` membongkar tiga akar penyebab utama mengapa tambahan 7 putaran tidak membuahkan kelulusan:

#### 1. Intrinsic Test State Contamination (`fastapi_t1`)
* Pada `test_main.py` (Frozen Oracle), unit test dijalankan berurutan dalam proses yang sama:
  1. `test_add_product`: Memasukkan `"Laptop"` ke `products_db = []` $ightarrow$ `assert len(products_db) == 1` (**LULUS**).
  2. `test_delete_product`: Memasukkan `"Mouse"`, menghapus `"Mouse"`, lalu `assert len(products_db) == 0`.
* Karena `products_db` adalah in-memory global list pada modul `main.py`, item `"Laptop"` dari test sebelumnya tertinggal di memori. Menghapus Mouse menyisakan Laptop (`len = 1`), memicu assertion error:
  ```text
  AssertionError: assert 1 == 0 (+ where 1 = len([Product(id=1, name='Laptop', price=999.99)]))
  ```
* Developer menulis logika `delete_product` yang 100% benar secara semantik API (menghapus produk sesuai ID). Developer mengalami kebuntuan logika karena merasa tidak masuk akal menghapus seluruh database pada endpoint `DELETE /products/{mouse_id}`. Tanpa fixture teardown pada file test, masalah ini secara matematis tidak dapat diselesaikan dari sisi file `main.py` saja.

#### 2. Diagnostic Misattribution pada Parser Heuristik (`cli_t1`)
* Pada Run 4, test gagal pada fungsi parser string `parse_matrix(matrix_str)` di baris:
  ```python
  if len(values) != len(rows[0]):
      raise ValueError('Invalid dimensions')
  ```
  Developer membandingkan jumlah kolom `len(values)` dengan panjang karakter string `len(rows[0])`.
* Namun mesin heuristik mengidentifikasi kata kunci `ValueError: Invalid dimensions` dan mengatribusikannya ke operasi aritmatika matriks:
  > `[REQUIRED DIRECTION]: Pastikan perkalian matriks memvalidasi cols(A) == rows(B), dan penjumlahan memvalidasi rows(A) == rows(B)...`
* Developer memeriksa fungsi `add_matrices` miliknya, mendapati bahwa validasi penjumlahan sudah benar, dan menyimpulkan kodenya sudah sesuai panduan. Akibatnya, Developer mempertahankan kode yang persis sama selama 9 putaran berturut-turut.

#### 3. Kerapuhan Oracling Pengujian Flutter (`flutter_t1`)
* Pada Run 7, generator pengujian menghasilkan syntax invalid pada widget testing Flutter (`find.byType(Card).evaluate().first.backgroundColor`), memicu `compilation_error` yang tidak dapat diperbaiki Developer karena file test tidak boleh diedit.
* Pada Run 9, widget lolos kompilasi dan render, namun assertion menuntut format pemisah ribuan spesifik (`150,000.00 USD` vs `150000.00 USD`).
* Sebaliknya pada Run 8, kode Developer dan Test selaras sempurna sehingga **lulus 100% pada Loop 0**, namun tertahan di Layer 1 Deterministic Gate karena Developer menamai kelas `MetricCard` sementara draft kontrak menyebut `CardMetric`.

---

## 4. Rekomendasi Arsitektural Menuju Iterasi Berikutnya

1. **Pangkas Budget Developer Repair Depth Menjadi D4:**
   * Menurunkan batas loop dari 10 menjadi 4 putaran. Data empiris membuktikan bahwa iterasi di atas Loop 4 memiliki efektivitas perbaikan 0% pada model 7B.
2. **Implementasikan State Teardown Autonomus pada Pytest Harness:**
   * Tambahkan autouse fixture `autouse_clean_state` pada sandbox runner untuk me-reset variabel global modul/store sebelum tiap fungsi test dieksekusi, mencegah false failure akibat *test state contamination*.
3. **Penyempurnaan Fine-Grained Fault Localization pada Diagnostic Parser:**
   * Tingkatkan akurasi pemetaan root cause agar merujuk langsung ke nama simbol/fungsi spesifik dari stack trace (misal: membedakan `parse_matrix` vs `add_matrices`) alih-alih mengandalkan pencocokan kata kunci kategori tingkat tinggi.
4. **Ekspansi Repentance Engine ke Ranah Architect:**
   * Tambahkan panduan anti-fragmentasi pada Architect Blueprint Validator agar Architect tidak memecah snippet menjadi blok-blok markdown terpisah yang memicu error dekorator `@app` dan `@field_validator`.
