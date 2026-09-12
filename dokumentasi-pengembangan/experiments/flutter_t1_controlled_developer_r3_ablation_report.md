# Laporan Forensik Eksperimen Ablasi Terkontrol Developer / R-3
## Pengujian Hipotesis H1 (Contract Boundary Tension) pada Flutter `flutter_t1`

**Tanggal Audit:** 2026-09-12  
**Waktu Eksekusi:** 11:55:01 – 11:56:38 WIB  
**Run ID:** `pv_ablation_dev_r3_flutter_t1_rep1_20260912_115501`  
**Workspace:** `D:\Pekerjaan\Antigravity\reindev_studio`  
**Model Aktif:** `qwen2.5-coder:7b` via Ollama (`num_ctx=8192`, `num_predict=3000`)  
**Variabel Perlakuan:** `REINDEV_TREATMENT_B_R3="1"` (Treatment B / R-3 Aktif)  
**Status Pipeline:** Architect Bypassed (Seeded dari Kontrak FROZEN Treatment A)  

---

## 1. Ringkasan Eksekusi & Status Akhir

| Parameter Audit | Nilai Pengamatan | Evaluasi Forensik |
| :--- | :--- | :--- |
| **Run ID** | `pv_ablation_dev_r3_flutter_t1_rep1_20260912_115501` | Tercatat lengkap di `run_trace.jsonl` (54 event) |
| **Task ID & Target** | `flutter_t1` (`lib/card_metric.dart`) | Single authoritative module |
| **Status Kontrak Input** | `FROZEN` (Segel SHA-256: `9e2742c8cea6...`) | Di-seed dari Treatment A (`..._105346`), 100% konsisten Oracle |
| **Frozen Oracle SHA-256** | `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` | **100% INTACT & IMMUTABLE** (Pre & Post Verified) |
| **Treatment B (R-3) Status** | **AKTIF (1)** | Terinjeksi ke Doktrin #6 & Prompt Perbaikan Developer |
| **Budget Perbaikan** | 2 repair opportunities (3 iterasi Developer) | Universal Two-Repair Policy (`max_phase_repair_attempts=2`) |
| **Hasil Eksekusi Sandbox** | 0/1 PASS (0.0%) | Kompilasi gagal pada kedua kasus uji `card_metric_test.dart` |
| **Jumlah Putaran (Loops)** | 5 loops (3 eksekusi Developer + 3 validasi) | Kuota perbaikan Developer habis (Terminal Failure) |
| **Vonis Akhir** | **FAIL** | Stagnasi pada Developer iterasi 2 (identik dengan iterasi 1) |
| **Durasi Eksekusi** | 96.13 detik (~1.60 menit) | Efisien, Architect sepenuhnya dibypass |
| **One-Turn Repair Rate** | 0.0% | Gagal memulihkan kegagalan kompilator |

---

## 2. Integritas Kontrak & Frozen Oracle

1. **Frozen Oracle Integrity:**
   - Pre-flight SHA-256: `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` (**PASS**)
   - Post-flight SHA-256: `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` (**PASS**)
   - Zero Mutation: Berkas uji acceptance tidak tersentuh sama sekali selama eksperimen berlangsung.

2. **Seeded Frozen Contract Integrity:**
   - Kontrak awal diinjeksi langsung dari Turn 0 Treatment A (`pv_pilot_flutter_t1_rep1_20260912_105346`).
   - Canonical SHA-256 Seal: `9e2742c8cea664a48873c95772b8472b8ccaf3742c52f4b94a55b21471eddde3`.
   - `verify_contract_checkpoint(frozen_contract, 'developer_pre_flight')`: **PASS** tanpa error.
   - Status kontrak: **FROZEN** dipertahankan secara stabil di seluruh iterasi (Event 7, 22, 38).

---

## 3. Rekonstruksi Trajektori Turn-by-Turn Developer

### A. Turn 0 (Iterasi 0) — Generasi Awal
- **Prompt:** Menerima spesifikasi PM dan rencana arsitektur dari Treatment A (Scaffold: widget `CardMetric` dan model `CardMetricData(value, description)`).
- **Hasil Kode:** `lib/card_metric.dart` (999 karakter).
  - Mendeklarasikan `class CardMetricData(this.value, this.description)`.
  - Mendeklarasikan `class CardMetric extends ConsumerWidget` tanpa parameter konstruktor.
- **Hasil Sandbox Flutter:** Kompilasi gagal dengan 2 galat spesifik:
  1. `test/card_metric_test.dart:14:21: Error: Method not found: 'MetricData'.`
  2. `test/card_metric_test.dart:14:15: Error: No named parameter with the name 'data'.`

### B. Turn 1 (Iterasi 1 / Perbaikan 1) — Efek Perlakuan R-3
- **Prompt:** Menerima Contextual Evidence Package (CEP) B5, kode Turn 0, cuplikan Oracle call-site, dan **Rule 3 `[CONTRACT BOUNDARY PRINCIPLE]`**.
- **Hasil Kode:** `lib/card_metric.dart` (1.076 karakter).
  - Mengubah `StateProvider` menjadi `Provider` (sesuai larangan penggunaan provider usang).
  - Menambahkan parameter `data` pada konstruktor `CardMetric`:
    ```dart
    final CardMetricData data;
    const CardMetric({Key? key, required this.data}) : super(key: key);
    ```
  - **TETAP MEMPERTAHANKAN** `class CardMetricData` dan **TIDAK MENDEKLARASIKAN** `class MetricData`.
- **Hasil Sandbox Flutter:**
  - Galat `No named parameter with the name 'data'` **BERHASIL TERSELESAIKAN (RESOLVED)**.
  - Namun galat `Method not found: 'MetricData'` **TETAP MUNCUL** pada baris 14 dan baris 38:
    ```
    test/card_metric_test.dart:14:21: Error: Method not found: 'MetricData'.
    test/card_metric_test.dart:38:23: Error: Method not found: 'MetricData'.
    ```

### C. Turn 2 (Iterasi 2 / Perbaikan 2) — Stagnasi Model
- **Prompt:** Menerima umpan balik kompilator persisten mengenai `MetricData`.
- **Hasil Kode:** `lib/card_metric.dart` (1.076 karakter).
  - **100% Identik secara byte (0 baris perubahan diff)** dengan Turn 1.
  - Model mengalami fiksasi konseptual / pengulangan stokastik (stagnation).
- **Vonis Validator V5:** Kuota perbaikan habis (`repair_attempt_counts['executor'] = 2`), terminal failure boundary dipicu.

---

## 4. Komparasi Head-to-Head: Treatment A vs Ablasi Terkontrol B

| Parameter Kunci | Treatment A (`REINDEV_TREATMENT_B_R3="0"`) | Ablasi Terkontrol (`REINDEV_TREATMENT_B_R3="1"`) | Evaluasi Kausal |
| :--- | :--- | :--- | :--- |
| **Kontrak Input** | FROZEN `CardMetric` (`9e2742c8...`) | FROZEN `CardMetric` (`9e2742c8...`) | Identik 100% |
| **Kode Turn 0** | 999 char | 999 char | **Identik 100%** |
| **Respon Turn 1** | Tambah `required this.data` bertipe `CardMetricData` | Tambah `required this.data` bertipe `CardMetricData` | **Identik 100%** |
| **Kode Turn 1** | 1.076 char | 1.076 char | **Identik 100%** |
| **Kode Turn 2** | 1.076 char (stagnasi) | 1.076 char (stagnasi) | **Identik 100%** |
| **Resolusi `MetricData`** | Gagal | Gagal | **Nol diferensiasi** |
| **Vonis Akhir** | FAIL | FAIL | **Nol diferensiasi** |

---

## 5. Evaluasi Ilmiah Hipotesis H1 (Contract Boundary Tension)

### Rumusan Hipotesis H1:
> *"Contract-Boundary Tension menghambat Developer melakukan perbaikan yang secara deterministik diperlukan oleh caller Oracle (seperti mendeklarasikan kelas sekunder `MetricData`) karena Developer takut melanggar batasan kontrak FROZEN yang melarang penambahan model di luar kontrak."*

### Temuan Empiris:
1. **R-3 Terbukti Dikonsumsi:** Bukti trace menunjukkan `REINDEV_TREATMENT_B_R3="1"` sukses menyuntikkan prinsip kelonggaran internal ke dalam prompt Developer dan doktrin engineering.
2. **Kelonggaran Konstruktor Terjadi di Kedua Kondisi:** Baik dengan R-3 maupun tanpa R-3, model 7B sama-sama bersedia memodifikasi signature konstruktor `CardMetric` untuk menerima `required this.data`.
3. **Kegagalan `MetricData` Bukan Karena Ketakutan Kontrak:**
   - Pada Treatment B (R-3 aktif), CEP B5 secara eksplisit memberikan dispensasi:
     `REPAIR BOUNDARY (ALLOWED): Implement or expose 'MetricData' in 'lib/card_metric.dart' to satisfy caller invocation while maintaining contract integrity`.
   - Meskipun secara legal kontrak diizinkan dan diinstruksikan oleh B5, Developer **TETAP TIDAK PERNAH** mendeklarasikan `MetricData`.
   - Developer mengikat parameter `data` ke kelas yang sudah ada di scaffold arsitektur (`CardMetricData`), bukan karena tertekan oleh segel kontrak, melainkan karena model 7B **terpaku secara kognitif pada scaffold bawaan (`CardMetricData`)** dan tidak memiliki kapasitas inferensi simbolik untuk menyintesis kelas data baru dari sintaks pemanggil di berkas tes (`MetricData(title: ..., value: ..., color: ...)`).

### Vonis Ilmiah:
**HIPOTESIS H1 DITOLAK SECARA EMPIRIS (REFUTED).**  
Kegagalan Developer 7B menyelesaikan `MetricData` **BUKAN** disebabkan oleh ketegangan batas kontrak (Contract Boundary Tension). Penyebab utamanya adalah **keterbatasan intrinsik kapasitas penalaran (intrinsic reasoning capacity) model 7B** dalam menyintesis deklarasi kelas Dart baru berdasarkan error kompilasi caller-site ketika scaffold awal sudah menyediakan nama kelas yang mirip (`CardMetricData`).

---

## 6. Rekomendasi Langkah Berikutnya untuk IA

1. **Tutup Pengujian R-3 pada Developer 7B:**
   - Tidak diperlukan perlakuan relaksasi prompt lebih lanjut untuk Developer pada model 7B karena R-3 terbukti tidak memberikan efek kausal.
2. **Uji Efek Model Scale (qwen2.5-coder:14b / 32b):**
   - Jalankan controlled Developer ablation yang sama menggunakan model dengan kapasitas penalaran lebih tinggi (misal 14B atau 32B) untuk menguji apakah model yang lebih besar mampu memetakan `MetricData` dari Oracle call-site secara mandiri.
3. **Pertimbangkan Eksplisit Contract Scope di Architect:**
   - Jika arsitektur menuntut widget menerima data terstruktur, kontrak Architect di hulu idealnya memuat deklarasi model data pendukung (`data_models: [MetricData]`), sehingga Developer tidak perlu melakukan inferensi blind-spot terhadap tipe sekunder.
