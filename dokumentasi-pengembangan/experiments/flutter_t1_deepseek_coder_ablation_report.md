# Laporan Forensik Eksperimen Ablasi: Komparasi Model Lokal Alternatif (`deepseek-coder:6.7b`) pada Flutter `flutter_t1`

**Tanggal Pelaksanaan:** 2026-09-12T12:18:55 — 12:29:00 WIB  
**ID Eksperimen:** `pv_ablation_dev_r3_deepseek_flutter_t1_rep1_20260912_121855`  
**Baseline Pembanding (7B Lokal):** `pv_ablation_dev_r3_flutter_t1_rep1_20260912_115501` (`qwen2.5-coder:7b`)  
**Frontier Pembanding (14B Cloud):** `pv_ablation_dev_r3_qwen3_14b_flutter_t1_rep1_20260912_120849` (`qwen/qwen3-14b`)  
**Task ID:** `flutter_t1` (`lib/card_metric.dart`)  
**Target Bahasa:** Dart (Flutter Material 3 & Riverpod)  
**Evaluated Model:** `deepseek-coder:6.7b` (via Ollama lokal, Digest: `ce298d984115`, 3.8 GB)  
**Treatment Variable:** `REINDEV_TREATMENT_B_R3="1"` (Doktrin #6: Caller Consistency Repair)  
**Status Kontrak Input:** `FROZEN` (SHA-256: `9e2742c8cea664a48873c95772b8472b8ccaf3742c52f4b94a55b21471eddde3`)  
**Integritas Frozen Oracle:** `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` (**100% INTACT Pre & Post Flight**)  

---

## 1. Executive Summary: Matriks Perbandingan Tri-Model

| Metrik / Dimensi | Baseline 7B (`qwen2.5-coder:7b`) | Alternatif Lokal 6.7B (`deepseek-coder:6.7b`) | Skala 14B (`qwen/qwen3-14b`) |
| :--- | :--- | :--- | :--- |
| **Inference Backend** | Ollama (Lokal) | Ollama (Lokal) | OpenRouter API (Cloud) |
| **Treatment B (R-3)** | Aktif (`"1"`) | Aktif (`"1"`) | Aktif (`"1"`) |
| **Input Kontrak** | FROZEN (`9e2742c8...`) | FROZEN (`9e2742c8...`) | FROZEN (`9e2742c8...`) |
| **Frozen Oracle SHA** | `4589e15c...` (Intact) | `4589e15c...` (Intact) | `4589e15c...` (Intact) |
| **Kepatuhan Tag Format** | 100% Disiplin (`=== FILE ===`) | **GAGAL (Kutipan & Markdown liar)** | 100% Disiplin (`=== FILE ===`) |
| **Penetrasi Gate V3** | **Lolos ke Sandbox** | **TERTAHAN DI V3 (Karantina)** | **Lolos ke Sandbox** |
| **Turn 0 (Initial)** | GAGAL (`MetricData` missing) | GAGAL (Target file `lib/card_metric.dart` missing) | GAGAL (`MetricData` missing) |
| **Turn 1 (Repair 1)** | GAGAL (Hanya param `data`) | GAGAL (Scaffold liar: 5 files, `max_files` violated) | **LULUS (2/2 Tests PASS)** |
| **Turn 2 (Repair 2)** | GAGAL (Stagnan, identik Turn 1) | GAGAL (Mengeluarkan kode test, target missing) | N/A (Sudah konvergen di Turn 1) |
| **Sandbox Execution** | Dieksekusi (Compiler error) | **0 Kali (Sandbox Terproteksi 100%)** | Dieksekusi (100% PASS) |
| **Reviewer Verdict** | N/A (Terhenti di Developer) | FAIL | **APPROVED** |
| **Final Run Verdict** | **FAIL (Stagnant Logic)** | **FAIL (Format Divergence)** | **PASS (Convergent)** |
| **Total Durasi** | 96.13s | 604.98s | 334.83s |

---

## 2. Analisis Kausal: Mengapa `deepseek-coder:6.7b` Gagal Menembus Gate V3?

### A. Tag Delimiter Hallucination & Prompt Non-Compliance
Arsitektur ReinDev mewajibkan Developer mengeluarkan artefak kode dalam format kanonikal:
`=== FILE: <path/ke/berkas> ===` diikuti blok kode, kemudian `=== END_FILE ===`.

Pada `deepseek-coder:6.7b`:
1. **Turn 0 (Initial Generation - Latency 123.86s):**
   - Alih-alih mengeluarkan penanda berkas murni di baris baru, model menghasilkan pembuka percakapan naratif:
     `Berikut adalah kode program lengkap yang sesuai dengan format penanda “=== FILE: ... ===”:`
   - Parser kode ReinDev mendeteksi pola tag dan mengekstrak nama berkas palsu: `...`.
   - Berkas target authoritative `lib/card_metric.dart` tidak ditemukan di dalam keluaran.
   - **Evaluasi Gate V3:** Ditolak deterministik dengan pelanggaran `authoritative_target_file_compliance`. Paket bukti kausal (CEP) `EV-0A9999A87329` diterbitkan.

2. **Turn 1 (Repair Attempt 1 - Latency 277.30s):**
   - Model menerima resep perbaikan dari Gate V3 untuk memperbaiki format berkas.
   - Model terdisorientasi dan memuntahkan scaffold multi-berkas:
     `lib/module_1.dart`, `lib/module_2.dart`, `lib/module_3.dart`, `lib/module_4.dart`.
   - Berkas target `lib/card_metric.dart` tetap tidak dihasilkan.
   - **Evaluasi Gate V3:** Ditolak kembali karena:
     - Pelanggaran `authoritative_target_file_compliance` (target tidak ada).
     - Pelanggaran `constraint_compliance` (jumlah berkas = 5, melebihi constraint `max_files = 3`).

3. **Turn 2 (Repair Attempt 2 - Latency 203.76s):**
   - Pada kesempatan perbaikan terakhir, model beralih menghasilkan kode unit test alih-alih berkas implementasi widget:
     `Anda juga perlu menulis test untuk komponen ini: ...`
   - Berkas implementasi target `lib/card_metric.dart` tetap absen.
   - **Evaluasi Gate V3:** Ditolak untuk ketiga kalinya. Kuota perbaikan habis (`repair_attempt_counts['developer'] == 2`).
   - Routing: `developer_preflight_rejected` -> `END`.

---

## 3. Efektivitas & Pembuktian Proteksi Gate V3 (Phase-End Validator)

Meskipun model menghasilkan kode yang cacat format dan terdisorientasi, eksperimen ini memberikan **pembuktian empiris krusial terhadap integritas arsitektur keamanan ReinDev**:

1. **Deterministic Quarantine (Karantina Pre-Eksekusi):**
   - Gate V3 berhasil mendeteksi dan mengkarantina kode cacat format sebelum satu baris pun menyentuh sandbox eksekusi (`tester_agent_invocations: 0`).
   - Tidak terjadi eksekusi liar, pemborosan waktu build Dart, atau kegagalan misterius di tingkat runtime OS.

2. **Zero Downstream Contamination:**
   - Direktori sandbox dan repositori tetap 100% bersih dari berkas halusinasi (`lib/module_1.dart`, dll).
   - Orakel pengujian (`test/card_metric_test.dart`) terbukti tetap 100% utuh tanpa perubahan hash (`4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528`).

3. **Strict Loop Budgeting:**
   - Mekanisme kuota perbaikan beroperasi dengan presisi absolut: setelah 2 perbaikan gagal berturut-turut, graph secara deterministik menghentikan proses (`converged_within_3_loops: False`) tanpa loop tak hingga.

---

## 4. Kesimpulan Kausal & Komparasi Ekosistem Model

1. **`deepseek-coder:6.7b` vs `qwen2.5-coder:7b`:**
   - `qwen2.5-coder:7b` memiliki **instruksi format following yang superior** (100% disiplin format tag kanonikal `=== FILE ===`), mampu menembus Gate V3 ke sandbox, namun memiliki kelemahan penalaran simbolik sekunder (`MetricData`).
   - `deepseek-coder:6.7b` memiliki **instruksi format following yang jauh lebih rapuh** di bawah prompt terstruktur panjang (terdistorsi oleh tanda kutip naratif dan scaffold multi-berkas fiktif), sehingga langsung tertahan di gerbang validasi pre-eksekusi.

2. **Rekomendasi Arsitektur Engine:**
   - Untuk node `Developer`, model `deepseek-coder:6.7b` **tidak direkomendasikan** untuk pipeline ReinDev tanpa fine-tuning prompt delimiter khusus.
   - Model kelas 14B (`qwen/qwen3-14b`) tetap menjadi pemenang mutlak dari segi kepatuhan format, penetrasi gate, dan kemampuan sintesis simbolik adaptif.
