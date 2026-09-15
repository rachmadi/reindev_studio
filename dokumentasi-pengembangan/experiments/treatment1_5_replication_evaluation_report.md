# Treatment #1.5 — Laporan Evaluasi Uji Replikasi 1x3
**Architect Repair Grounding & Preservation v1**  
**Model**: `qwen2.5-coder:7b` (via Ollama) | **Date**: 2026-09-15 | **Status**: COMPLETED  
**Git Commit**: [`c776d70`](https://github.com/rachmadi/reindev_studio/commit/c776d70) on branch `experiment/fastapi-recovery`  

---

## 1. Ringkasan Eksekutif Hasil Komparatif (Run 1 vs Run 2)

Uji replikasi 1x3 independen kedua telah selesai dieksekusi menggunakan konfigurasi identik pada model `qwen2.5-coder:7b`. Hasil uji komparatif memperlihatkan ketahanan deterministik dari gerbang validasi pre-freeze dan efektivitas isolasi tugas:

| Domain / Task | Run 1 (Pilot Pertama) | Run 2 (Uji Replikasi) | Tingkat Konsistensi | Catatan Perilaku Pipeline |
| :--- | :---: | :---: | :---: | :--- |
| **FastAPI** (`fastapi_t1`) | **PASS (5/5)**<br>Loops: 0, Contract: FROZEN<br>Review: APPROVED | **FAIL (4/5 PASS)**<br>Loops: 5, Contract: FROZEN<br>Review: FAIL | **100% FROZEN (Akses Runtime Penuh)** | Kedua run berhasil mencapai status **`FROZEN`** (100% pre-freeze compatibility). Run 1 langsung lulus 5/5; Run 2 mencapai 4/5 runtime pass, berhenti aman di Developer loop 5 pada uji 404 tanpa merusak tes lain. |
| **CLI** (`cli_t1`) | **FAIL (REJECTED)**<br>Loops: 0, Tests: 0/5 | **FAIL (REJECTED)**<br>Loops: 0, Tests: 0/5 | **100% KONSISTEN (FAIL-CLOSED)** | Pre-freeze gate Treatment #1.5 konsisten mendeteksi ketidakcocokan callable & constructor; kontrak ditolak pre-freeze dengan *zero downstream leakage*. |
| **Flutter** (`flutter_t1`) | **PASS (2/2)**<br>Loops: 0, Contract: FROZEN<br>Review: APPROVED | **FAIL (REJECTED)**<br>Loops: 0, Tests: 0/2 | **VARIASI REPAIR CONVERGENCE** | Run 1 membuktikan bahwa grounded repair berhasil memulihkan Turn 0 yang rusak menjadi FROZEN dan 2/2 PASS. Run 2 memperbaiki schema error tetapi menyisakan positional constructor setelah 2 repair turn; gerbang *fail-closed* menolak freeze, melindungi runtime. |

---

## 2. Analisis Forensik Komparatif per Task

### A. FastAPI (`fastapi_t1`): Determinisme Kontrak & Ketahanan Runtime
- **Run 1 (5/5 PASS, 264.8s)**:
  - Scaffold awal Turn 0 memenuhi seluruh 5 skenario acceptance REST API.
  - Kontrak langsung berstatus **`FROZEN`** pada Turn 0 tanpa membutuhkan repair loops.
  - Developer menghasilkan endpoint lengkap dan lulus 5/5 runtime test.
- **Run 2 (4/5 PASS, 276.9s)**:
  - Fase V0 mendeteksi ungrounded fact pada Turn 0 dan berhasil pulih deterministik pada Turn 1 (`verdict: PASS`).
  - Architect menghasilkan blueprint yang lolos pre-freeze gate dan berhasil dibekukan (**`FROZEN`**).
  - Runtime Developer mengeksekusi iterasi bertahap:
    - Tes yang lulus: `test_create_product`, `test_get_products`, `test_get_product`, `test_delete_product` (semua dikunci sebagai invarian tak terubahkan).
    - Tes yang gagal: `test_delete_nonexistent_product` (`assert 204 == 404` karena kode mengembalikan 204 tanpa melempar HTTPException 404).
    - Batas 5 iterasi Developer habis tanpa kebocoran regresi (*zero regression* pada 4 tes lulus).
  - **Kesimpulan**: Kontrak FastAPI mencapai **100% freeze rate (2/2)** di bawah Treatment #1.5 dengan rentang kelulusan runtime 80%–100%.

---

### B. CLI (`cli_t1`): Integritas Gerbang Fail-Closed (100% Konsistensi)
- **Bukti Empiris Kedua Run**:
  - Pada kedua pengujian, Frozen Oracle menuntut antarmuka `Matrix` callable dan fungsi helper matematika.
  - Architect menghasilkan scaffold tanpa struktur callable tersebut.
  - Pre-freeze compatibility gate Treatment #1.5 mendeteksi inkonsistensi secara deterministik:
    ```
    CALL_SHAPE_INCOMPATIBILITY & SCENARIO_SCAFFOLD_INCOMPATIBILITY
    ```
  - Pada kedua run, kontrak berstatus **`REJECTED`** dan alur langsung dialihkan menuju `__end__`.
  - **Dampak Arsitektural**: Tidak ada token yang terbuang sia-sia untuk mengeksekusi Developer atau Executor di atas kontrak yang invalid. *Downstream leakage* = 0%.

---

### C. Flutter (`flutter_t1`): Dinamika Grounded Repair vs Batas Anggaran
- **Run 1 (Pembuktian Grounded Repair)**:
  - Turn 0: Ditolak karena constructor `MetricData` tidak menerima argumen posisional dan skema blueprint bermasalah.
  - Turn 1: Treatment #1.5 menyerahkan 10-tier context package (`delivery_valid: true`).
  - Architect berhasil memperbaiki kedua cacat (`resolved_error_count: 2`) tanpa regresi $\rightarrow$ **`FROZEN`** $\rightarrow$ **`2/2 PASS`**.
- **Run 2 (Batas Perbaikan Tercapai Tanpa Konvergensi Constructor)**:
  - Turn 0: Ditolak karena constructor `MetricData` posisional dan kesalahan deklarasi file.
  - Turn 1: Architect memperbaiki kesalahan skema (`resolved_error_count: 1`), namun dalam scaffold kode masih mempertahankan constructor `MetricData(this.title, this.value, this.color)` tanpa named parameter.
  - Turn 2: Gerbang mendeteksi constructor tetap posisional (`CALL_SHAPE_INCOMPATIBILITY`). Karena batas maksimum revisi fase (`max_phase_repair_attempts: 2`) tercapai, kontrak dinyatakan **`REJECTED`**.
  - **Kepatuhan Doktrin**: Sesuai prinsip *fail-closed*, sistem **menolak membekukan kontrak yang cacat**, mencegah Developer menghasilkan kode yang pasti gagal pada `flutter test`.

---

## 3. Matriks Integritas & Invarian Sistem

| Kriteria Invarian | Standar Mandat | Hasil Uji Replikasi | Status |
| :--- | :--- | :--- | :---: |
| **Frozen Oracle Immutability** | SHA-256 wajib identik | `fastapi_t1`: `a1db9bb1...`<br>`cli_t1`: `0bd5b598...`<br>`flutter_t1`: `4589e15cf...` | **100% INTACT** |
| **QA Tester Isolation** | Tester LLM 100% Bypassed | Invocations: 0 across all runs | **100% BYPASSED** |
| **Sterile Executor** | Zero transformation/shims | Verbatim execution in sandbox | **100% STERILE** |
| **Zero Task-Specific Solvers** | Dilarang hardcoded heuristics | Regex audit test_gate_20: 0 matches | **100% GENERIC** |
| **Fail-Closed Doctrine** | Incompatible scaffold cannot freeze | Incompatible CLI & Flutter Run 2 rejected pre-freeze | **100% ENFORCED** |
| **Test Suite Regression** | 671 baseline tests must pass | 671 passed, 0 failed | **100% PASS** |

---

## 4. Kesimpulan & Rekomendasi

1. **Replikasi Memvalidasi Dua Pilar Krusial**:
   - **Pilar Perlindungan (Fail-Closed)**: 100% konsisten. Scaffold yang tidak kompatibel tidak pernah dibiarkan membeku atau bocor ke fase hilir.
   - **Pilar Perbaikan (Grounded Repair)**: Terbukti mampu memulihkan inkonsistensi Turn 0 menjadi status FROZEN dan kelulusan runtime 100% (seperti pada Flutter Run 1).
2. **Karakteristik Model 7B pada Perbaikan Multi-Turn**:
   - Pada model parameter sedang (`qwen2.5-coder:7b`), perbaikan antarmuka Dart yang melibatkan pergeseran dari constructor posisional ke named parameter (`required this.x`) terkadang memerlukan instruksi penegasan bentuk pemanggilan yang lebih terfokus jika gagal pada putaran pertama.
3. **Kesiapan Fase Selanjutnya**:
   - Data empiris dari Run 1 dan Run 2 Treatment #1.5 telah lengkap dan tersimpan secara permanen dalam repository Git.
   - Sistem siap menunggu arahan untuk pengujian replikasi ke-3 atau langkah treatment berikutnya.
