# Laporan Evaluasi Komparatif: Qwen2.5-Coder:7b vs Ornith:9b
## Rangkaian Pengujian 3 Kasus (FastAPI, CLI, Flutter) di Bawah Boundary V0–V6 Rigid Terkontrol

**Tanggal Pengujian**: 14 September 2026  
**Model Pengujian**: `qwen2.5-coder:7b` (Ollama local instance, `num_predict: 3000`, `num_ctx: 8192`)  
**Baseline Pembanding**: `ornith:9b` (Pengujian pilot dan hardening V6 sebelumnya)  
**Status Eksekusi**: **COMPLETED** (3 dari 3 kasus selesai secara otonom tanpa intervensi manual)

---

## 1. Ringkasan Eksekutif

Pengujian ulang 3 kasus (`fastapi_t1`, `cli_t1`, `flutter_t1`) menggunakan model `qwen2.5-coder:7b` telah selesai dieksekusi secara penuh di bawah kondisi pengujian yang **100% identik dan terkontrol**. Rangkaian pengujian ini membuktikan kestabilan arsitektur sistem otonom dengan isolasi boundary V0–V6, Dual-Lock SHA-256 Oracle, dan Sandbox steril tanpa transformer.

### Ringkasan Hasil Utama (Qwen2.5-Coder:7b):
1. **Total Kasus Lolos**: **2 dari 3 kasus PASS (66.7%)**, yaitu `cli_t1` dan `flutter_t1`.
2. **Efisiensi Waktu (Speedup Dramatis)**: Total durasi 3 kasus hanya **793.2 detik (~13.2 menit)**, dibandingkan dengan `ornith:9b` yang memakan waktu **~55–60 menit** (peningkatan kecepatan inferensi **~4.5x–5.7x**).
3. **Penyelesaian Sempurna Kasus Flutter**: Berbeda dengan `ornith:9b` yang sempat terhenti di rilis akibat Reviewer output kosong (*Reviewer Failure*), pada `qwen2.5-coder:7b`, Reviewer berhasil memproduksi catatan review valid secara substantif, meloloskan firewall **V6 Reviewer Output Gate**, dan memberikan vonis **`APPROVED`** dengan **100% tes widget lulus (2/2)**.
4. **Penyelesaian Kasus CLI**: Lulus sempurna **5/5 tes (100%)** dalam **2 siklus perbaikan** (`converged_within_3_loops: true`), disahkan **`APPROVED`** oleh Reviewer dalam durasi 280.2 detik.
5. **Kegagalan Kasus FastAPI**: Terhenti pada 2/5 tes lulus akibat ketidakmampuan model menyelaraskan route handler decorator HTTP 405 (*Method Not Allowed*) / 422 (*Unprocessable Content*) setelah 5 iterasi. Kegagalan terklasifikasi secara bersih dan presisi sebagai **`A. Developer Failure`** tanpa merusak integritas kontrak maupun Oracle.

---

## 2. Kondisi Eksperimen Terkontrol (Identitas 100%)

Seluruh parameter dan batasan eksperimen dipertahankan secara identik dengan benchmark `ornith:9b`:

| Parameter Kontrol | Spesifikasi yang Ditegakkan | Status Kepatuhan |
| :--- | :--- | :---: |
| **Integritas Oracle** | Dual-Lock SHA-256 immutable checksum pada semua suite tes | **100% Intact** |
| **Sandbox Executor** | Eksekusi steril: 0 regex auto-patch, 0 file transformations | **100% Steril** |
| **V0 Boundary** | Epistemic provenance ledger & detection against ungrounded facts | **Aktif & Lolos** |
| **V1 Boundary** | PM requirement word-count limit (<150 kata) & non-prescriptive | **Aktif & Lolos** |
| **V2 Boundary** | Architect blueprint sealing & FROZEN contract SHA-256 | **Aktif & Lolos** |
| **V3 Boundary** | AST syntax check, symbol conformance, and file isolation | **Aktif & Lolos** |
| **V4 Boundary** | Oracle test suite guard & QA bypass prevention | **Aktif & Lolos** |
| **V5 Boundary** | Sandbox runner, invariant lock, and causal diagnostic extraction | **Aktif & Lolos** |
| **V6 Boundary** | Reviewer output classification, structural evidence gate, green-state protection | **Aktif & Lolos** |
| **Intervensi Manual** | Zero manual intervention / Zero downstream leakage | **Terpenuhi** |

---

## 3. Matriks Hasil Per-Kasus (`qwen2.5-coder:7b`)

| Metrik Evaluasi | Kasus 1: `fastapi_t1` | Kasus 2: `cli_t1` | Kasus 3: `flutter_t1` |
| :--- | :---: | :---: | :---: |
| **Target Bahasa** | Python (FastAPI) | Python (CLI) | Dart (Flutter UI) |
| **Run ID** | `pv_pilot_fastapi_t1_rep1_20260914_000657` | `pv_pilot_cli_t1_rep1_20260914_001020` | `pv_pilot_flutter_t1_rep1_20260914_001501` |
| **Final Verdict** | **FAIL** | **PASS** | **PASS** |
| **Review Verdict** | FAIL | **APPROVED** | **APPROVED** |
| **Tests Passed / Total** | 2 / 5 (40.0%) | **5 / 5 (100.0%)** | **2 / 2 (100.0%)** |
| **Loops Consumed** | 5 (Max Budget) | 2 (Konvergen) | 2 (Konvergen) |
| **Converged $\le$ 3 Loops**| `False` | **`True`** | **`True`** |
| **Failure Classification** | `A. Developer Failure` | `NONE` | `NONE` |
| **Status Kontrak** | FROZEN | FROZEN | FROZEN |
| **Oracle SHA-256 Intact** | `True` (`a1db9bb1...`) | `True` (`0bd5b598...`) | `True` (`4589e15c...`) |
| **Total Durasi Run** | **203.8 detik (~3.4 mnt)** | **280.2 detik (~4.6 mnt)** | **309.2 detik (~5.1 mnt)** |

---

## 4. Analisis Rinci Eksekusi Tiap Kasus

### A. Kasus 1: `fastapi_t1`
* **V0 Self-Healing**: Pada Turn 0, V0 memunculkan pelanggaran grounding fakta ungrounded (`VIO-001`). CEP `EV-...` memicu rekalsifikasi mandiri pada Turn 1 dan berhasil lulus ke fase PM.
* **V1 & V2**: PM memproduksi spesifikasi ringkas (650 karakter). Architect mengunci kontrak arsitektur menjadi **FROZEN** pada Turn 0.
* **V3–V5 Sandbox Execution**:
  - *Iterasi 0*: Developer menghasilkan `main.py`. Pengujian awal meloloskan 2 tes (`test_create_product`, `test_delete_nonexistent_product`), tetapi gagal pada 3 tes lainnya.
  - *Akar Masalah*: Handler endpoint untuk `GET /products` dan `GET /products/{id}` menghasilkan HTTP 405 (*Method Not Allowed*), sementara `DELETE /products/{id}` menghasilkan HTTP 422 (*Unprocessable Content*).
  - *Perilaku Model*: Qwen 7B menerima laporan diagnostik kausal HTTP status mismatch, namun mengalami osilasi pada decorator FastAPI (misal antara `@app.get` vs `@app.post` atau format trailing slash).
  - *Budget Guard*: Setelah mencapai batas maksimal 5 siklus perbaikan tanpa kemajuan, eksekusi dihentikan secara deterministik dengan vonis `FAIL` dan klasifikasi kegagalan murni di layer Developer.

### B. Kasus 2: `cli_t1`
* **V0 Self-Healing**: V0 mendeteksi placeholder `'Kutipan langsung dari task'` pada item `FACT-01`, `FACT-02`, `FACT-03`. V0 memperbaiki dirinya pada Turn 1 dengan mengutip teks tugas secara literal.
* **V1 & V2**: PM dan Architect menyelesaikan blueprint dalam 1 turn. Kontrak disegel FROZEN (SHA: `0bd5b598...`).
* **V3–V5 Sandbox Execution**:
  - *Iterasi 0*: 3/5 tes lulus. 2 tes operasi matriks dengan dimensi tidak cocok (`incompatible_dimensions`) melempar galat yang belum tertangani.
  - *Iterasi 1*: Developer menerima Contextual Evidence Package yang memuat traceback `ValueError`. Developer memperbarui validasi dimensi matriks di `main.py`.
  - *Iterasi 2*: **5/5 TES LULUS (100%)** dengan exit code 0.
* **V6 Reviewer Gate**:
  - Reviewer mengevaluasi implementasi yang telah hijau penuh.
  - Reviewer memproduksi evaluasi substantif dan memberikan status `APPROVED`.
  - Firewall V6 memvalidasi integritas persetujuan terhadap tes sandbox hijau dan status kontrak FROZEN $\rightarrow$ Vonis **`PASS`**.

### C. Kasus 3: `flutter_t1`
* **V0–V2**: Berjalan mulus pada Turn 0. V0 langsung lolos tanpa pelanggaran epistemic. Blueprint Architect disegel FROZEN (SHA: `4589e15c...`).
* **V3–V5 Sandbox Execution**:
  - *Iterasi 0*: Developer menyusun `lib/card_metric.dart`. Kompilasi awal gagal pada penamaan named parameter (`named_parameter_mismatch`).
  - *Iterasi 1*: Developer menerima diagnostik compiler Dart dan menyelaraskan parameter konstruktor `CardMetric({Key? key, required MetricData data})`.
  - *Iterasi 2*: **2/2 WIDGET TESTS LULUS (100%)** dalam 13.3 detik runtime executor! Invarian simbol `MetricData` dan parameter `CardMetric.data` dikunci sebagai PROVEN invariants.
* **V6 Reviewer Gate**:
  - Reviewer menganalisis kode Dart dan hasil pengujian sandbox yang bersih.
  - Reviewer menerbitkan vonis `APPROVED` yang terverifikasi oleh V6 Reviewer Gate.
  - Status run ditutup dengan **`PASS`**, konvergen dalam 2 siklus.

---

## 5. Perbandingan Head-to-Head: `qwen2.5-coder:7b` vs `ornith:9b`

```
====================================================================================================
METRIK KOMPARASI              ORNITH:9B (BASELINE)             QWEN2.5-CODER:7B (UJI SAAT INI)
====================================================================================================
1. KASUS CLI_T1
   - Status Akhir             PASS (5/5 Tests)                 PASS (5/5 Tests)
   - Loops Konvergensi        3 Loops                          2 Loops
   - Reviewer Verdict         APPROVED                         APPROVED
   - Durasi Eksekusi          1603.5 detik (~26.7 menit)       280.2 detik (~4.6 menit) [5.7x LEBIH CEPAT]

2. KASUS FLUTTER_T1
   - Peak Sandbox Tests       2/2 Tests PASS (100%)            2/2 Tests PASS (100%)
   - Reviewer Output          EMPTY (Dicegat V6 Gate)          VALID & APPROVED (Lolos V6 Gate)
   - Status Akhir             FAIL (E. Reviewer Failure)       PASS (Full Release Complete)
   - Perlindungan Green State 100% Terlindungi (0 regresi)     100% Terlindungi (0 regresi)
   - Durasi Eksekusi          1485.5 detik (~24.7 menit)       309.2 detik (~5.1 menit) [4.8x LEBIH CEPAT]

3. KASUS FASTAPI_T1
   - Status Akhir             PASS (5/5 Tests)                 FAIL (2/5 Tests, HTTP 405/422)
   - Loops Konvergensi        2 Loops                          5 Loops (Max Budget Halted)
   - Durasi Eksekusi          ~1200 detik (~20.0 menit)        203.8 detik (~3.4 menit)

4. TOTAL DURASI 3 KASUS       ~4300 detik (~71.5 menit)        793.2 detik (~13.2 menit) [5.4x LEBIH CEPAT]
====================================================================================================
```

---

## 6. Temuan Analitis & Kesimpulan

1. **Efisiensi Inferensi**: `qwen2.5-coder:7b` menyelesaikan seluruh rangkaian 3 kasus dalam waktu **13.2 menit**, dibandingkan dengan `ornith:9b` yang membutuhkan lebih dari 1 jam. Ini memberikan akselerasi siklus feedback pengujian yang signifikan.
2. **Kualitas Reviewer pada Kasus Flutter**: Pada pengujian `ornith:9b`, Reviewer mengalami kegagalan generasi (menghasilkan string kosong) yang memicu mitigasi darurat V6 Gate. Sebaliknya, `qwen2.5-coder:7b` mampu menghasilkan catatan review yang lengkap dan sesuai skema, sehingga pengujian Flutter dapat mencapai status akhir **`PASS` dan `APPROVED` secara tuntas**.
3. **Ketahanan Boundary V0–V6**:
   - V0 Epistemic Grounding terbukti konsisten menangkap ungrounded claims pada Turn 0 dan memicu perbaikan deterministik.
   - V2 Architect Contract Locking mempertahankan SHA-256 frozen contract 100% utuh di seluruh 3 kasus.
   - V6 Reviewer Gate berfungsi mulus memvalidasi persetujuan reviewer ketika tes sandbox hijau.
4. **Area Peningkatan untuk Model 7B**: Pada kasus arsitektur web framework (FastAPI), model 7B menunjukkan kecenderungan kesulitan dalam sintaks decorator HTTP method / path parameter jika dibandingkan dengan model 9B, yang mengarah ke divergensi di layer Developer.
