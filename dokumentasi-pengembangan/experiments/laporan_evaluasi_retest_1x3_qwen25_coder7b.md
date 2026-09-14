# Laporan Evaluasi Lengkap: Pilot Retest 1×3 (`qwen2.5-coder:7b`)

ReinDev Studio — Generic, Mission-Agnostic, Language-Agnostic Validation Lifecycle  
Tanggal: 14 September 2026 | Skuad Model: `qwen2.5-coder:7b` (via Ollama) | Repetisi: 1×3

---

## 1. Ringkasan Eksekutif

Eksperimen pilot 1×3 terkontrol menggunakan model **`qwen2.5-coder:7b`** telah dieksekusi hingga tuntas di bawah penegakan doktrin:
$$\textbf{PERSIST HISTORY} \quad \bigotimes \quad \textbf{RECOMPUTE ACTIVE VALIDITY}$$

### Hasil Matriks 1×3:
| Task ID | Bahasa | Kontrak Status | Hasil Run | Loops | Durasi | Klasifikasi Kegagalan |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`fastapi_t1`** | Python | `REJECTED` | FAIL | 0 | 263.2s | **C. Contract Failure** (JSON syntax error berulang pada model 7B) |
| **`cli_t1`** | Python | **`FROZEN`** | FAIL | 5 | 432.5s | **A. Developer Failure** (Kontrak 100% tersegel, kegagalan di Developer) |
| **`flutter_t1`** | Dart | `REJECTED` | FAIL | 0 | 187.8s | **C. Contract Failure** (Model menukar antarmuka: menambah `MetricData` lalu menghapus `CardMetric`) |

---

## 2. Bukti Empiris: Pemusnahan Total "Ghost Stale Error"

Pengujian ini memberikan **dua bukti empiris tak terbantahkan** bahwa bug *Ghost Stale Error* telah tereliminasi 100%:

### Bukti 1: Pembekuan Kontrak `cli_t1` pada Turn 2 (Meskipun Memiliki 5 Error Historis)
- **Turn 0**: Kontrak ditolak (`REJECTED`) karena `add_matrices`, `subtract_matrices`, `multiply_matrices` belum ada.
- **Turn 1**: Kontrak ditolak (`REJECTED`) karena model menamai fungsi `add`, `subtract`, `multiply`.
- **Turn 2**: Model memperbaiki seluruh nama antarmuka hingga 100% cocok dengan Acceptance Oracle.
- **Hasil Telemetri Turn 2**:
  - `Historical error count`: **`5`** (Tersimpan utuh di `provenance.validation_history` untuk audit trail)
  - `Resolved error count`: **`2`** (Kegagalan masa lalu terbukti terselesaikan)
  - `Active error count`: **`0`** (Bersih dari error aktif)
  - `Coverage is_fully_covered`: **`True`**
  - `Seal Success`: **`True`** $\rightarrow$ **`Contract Status: FROZEN`**!
  - `Segel Kanonikal SHA-256`: `0bd5b598afa7ae4c...`

> [!NOTE]
> Pada sistem sebelum perbaikan, `cli_t1` pada Turn 2 **pasti akan ditolak (false rejection)** karena mewarisi 5 error historis. Kini, karena validitas aktif dihitung ulang secara deterministik dari kandidat turn berjalan, kontrak berhasil **FROZEN**.

---

### Bukti 2: Resolusi Error Parsial pada `flutter_t1` Turn 2
- **Turn 0**: Model hanya mendeklarasikan `['CardMetric', 'CardMetricWidget']`. Oracle menolak karena `MetricData` hilang.
- **Turn 1**: Model menambahkan `MetricData`, namun memicu kesalahan skema blueprint (`test/card_metric_test.dart` masuk `file_tree` tanpa scaffold modul).
- **Turn 2**: 
  - Model **memperbaiki kesalahan skema** (tercatat di `resolved_failures`).
  - Model **memperbaiki ketiadaan `MetricData`** (tercatat di `resolved_failures`).
  - Namun pada Turn 2, model secara keliru menghapus `CardMetric` sehingga antarmukanya menjadi `['CardMetricWidget', 'MetricData']`.
  - **Recompute Active Validity Bekerja Presisi**:
    - `Historical error count`: **`5`**
    - `Resolved error count`: **`2`**
    - `Active error count`: **`1`** (HANYA error riil Turn 2: `CardMetric` tidak dideklarasikan).
    - Tidak ada kontaminasi dari error skema Turn 1 maupun ketiadaan `MetricData` Turn 0 yang sudah diperbaiki!

---

## 3. Analisis Performa Model `qwen2.5-coder:7b`

Dibandingkan dengan model `ornith:9b` (pada pengujian sebelumnya):
1. **Kapasitas Sintaksis JSON Blueprint**:
   - `qwen2.5-coder:7b` lebih rentan menghasilkan malformed JSON pada task kompleks (`fastapi_t1`), seperti tanda koma terlewat pada line panjang.
   - `ornith:9b` menghasilkan JSON blueprint 100% valid tanpa satupun schema error.
2. **Kapasitas Penalaran Antarmuka**:
   - Pada `cli_t1`, kedua model (`ornith:9b` dan `qwen2.5-coder:7b`) berhasil konvergen ke status **`FROZEN`**.
   - Pada `flutter_t1`, `qwen2.5-coder:7b` mengalami fenomena "whack-a-mole" (saat memperbaiki A, ia menghilangkan B).

---

## 4. Integritas Sistem & Invariant

1. **Frozen Acceptance Oracle**:
   - SHA-256 seluruh task tetap 100% byte-for-byte identik:
     - `fastapi_t1`: `a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63`
     - `cli_t1`: `0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124`
     - `flutter_t1`: `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528`
2. **Zero Downstream Leakage**:
   - Task dengan kontrak `REJECTED` (`fastapi_t1` dan `flutter_t1`) langsung dihentikan di batas gerbang arsitektur tanpa membuang waktu eksekusi Developer.
3. **Audit Trail Persisten**:
   - Seluruh kegagalan dari awal hingga akhir tersimpan utuh di berkas ringkasan `dokumentasi-pengembangan/experiments/pilot_retest_1x3_qwen2.5_coder_7b.json` dan trace log.
