# Laporan Hasil Eksperimen & Investigasi Forensik Lintas Ekosistem (flutter_t1)
## Validasi Kasus Empiris: Pengujian Generalisasi Staged Causal Evidence pada Dart/Flutter, Evaluasi Self-Healing Trajectory, & Dekonstruksi Gridlock Kontrak

**Tanggal Eksperimen:** 12 September 2026  
**Pelaksana Eksperimen:** Antigravity AI Engineering Squad  
**Otoritas Tata Kelola (Intent Architect):** Muhammad Rachmadi  
**Objek Eksperimen:** Pilot Run `pv_pilot_flutter_t1_rep1_20260912_060619` (`flutter_t1`), Telemetri 54 Event  
**Model Subjek Uji:** `qwen2.5-coder:7b` (Unified Local Squad via Ollama, `num_ctx=8192`, `num_predict=3000`)  
**Status Evaluasi Epistemik:** **INVESTIGASI FORENSIK LENGKAP — PEMBUKTIAN KEPATUHAN PARSIAL CEP & PENEMUAN CONTRACT GRIDLOCK**

---

## 1. Rantai Bukti Digital (Digital Chain of Custody)

| Parameter Kriptografis / Metrik | Nilai Faktual Tercatat | Verifikasi Kepatuhan |
| :--- | :--- | :--- |
| **Run ID Terakhir** | `pv_pilot_flutter_t1_rep1_20260912_060619` | Tercatat di `run_trace.jsonl` (54 event) |
| **Task ID & Target** | `flutter_t1` (`lib/card_metric.dart`) | Authoritative single module target |
| **Frozen Oracle SHA-256** | `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` | **100% INTACT & TIDAK BERMUTASI** |
| **Status Kontrak Akhir** | **`FROZEN`** (Segel SHA-256: `6717ada9e8ef...`) | Lolos Gate V2 pada Iterasi 0 |
| **Pemanggilan QA Tester LLM** | **0 pemanggilan** | Bypass mutlak via Frozen Oracle |
| **Treatment B (Constraint / R-3)** | **NONAKTIF** (`REINDEV_TREATMENT_B_R3="0"`) | **Terisolasi murni** |
| **Hasil Eksekusi Sandbox** | **0/1 PASS (0.0%)** | `test/card_metric_test.dart` compilation error |
| **Jumlah Putaran (Loops)** | **5 loops** | Budget habis tanpa konvergensi |
| **Vonis Akhir** | **FAIL** | Stagnasi pada Iterasi 4 |
| **Durasi Eksekusi** | 163,33 detik (~2,72 menit) | Waktu komputasi efisien |

---

## 2. Tujuan Eksperimen & Desain Metodologis

Tujuan utama dari eksperimen ini adalah menguji apakah arsitektur **Staged Causal Evidence** yang terbukti sukses memulihkan pipeline Python/FastAPI (`fastapi_t1`) dapat digeneralisasi secara mulus ke ekosistem Dart/Flutter tanpa aturan solver spesifik kasus (*pure non-solver principle*).

### Batasan Eksperimen yang Dikunci Otoritas IA:
1. **Zero Case-Specific Logic:** Tidak boleh menyematkan kata kunci benchmark (misal `CardMetricData`, `MetricData`) ke dalam prompt atau validator.
2. **Non-Solver Prescriptions:** Preskripsi hanya menyatakan *WHAT* (disparitas kontrak/simbol faktual), bukan mendikte alternatif kode (*HOW*).
3. **Epistemic Attribution:** Call-site hanya boleh diatribusikan sebagai "Oracle test call site" jika terbukti berada di dalam `test_files`.
4. **Treatment B (R-3) Isolation:** `REINDEV_TREATMENT_B_R3="0"` wajib dipertahankan untuk menguji apakah pemulihan dapat tercapai di bawah rezim Treatment A.

---

## 3. Rekonstruksi Trajektori Forensik Turn-by-Turn (Run 3)

### A. Analisis Fase Hulu & Pembentukan Kontrak (Iterasi 0)
1. **Halusinasi Arsitek (Redundant Suffix & Entity Inversion):**
   Pada saat merancang arsitektur awal, Architect LLM (`qwen2.5-coder:7b`) memecah konsep `kartu metrik` menjadi dua kelas:
   - Model Data: `class CardMetric { int value; String label; }`
   - Widget UI: `class CardMetricWidget extends ConsumerWidget`
   - Provider: `final cardMetricProvider = StateProvider<CardMetric>((ref) => CardMetric());`
2. **Pembekuan Kontrak Discrepant:**
   Gate V2 mengekstrak interface dari blueprint menjadi:
   `interface_contracts: [ {"identifier": "CardMetricWidget", "target_file": "lib/card_metric.dart"} ]`
   Status kontrak disegel menjadi **`FROZEN`**.
3. **Eksekusi Sandbox Awal:**
   Frozen Oracle (`test/card_metric_test.dart`) mengeksekusi:
   `body: CardMetric( data: MetricData(title: 'Revenue', value: '1000', color: Colors.blue) )`
   Kompiler Dart menolak karena pemanggil membutuhkan `MetricData` dan named parameter `data`.

### B. Bukti Kepatuhan Otonom Terhadap CEP (Iterasi 1 -> 2)
Preskripsi Gate B5 (`EV-35FE911E82E2`) mengirimkan direktif non-solver:
- `RX-B5-DART-SYMBOL-001`: Simbol `MetricData` dirujuk oleh pemanggil, wajib didefinisikan di `lib/card_metric.dart`.
- `RX-B5-DART-PARAM-002`: Pemanggil memerlukan named parameter `data`.

**Tindakan Developer LLM (100% Taat Sinyal Kausal):**
Developer merespons preskripsi secara presisi:
- Model data `MetricData` dibuat lengkap dengan 3 field (`title`, `value`, `color`).
- Named parameter `data` disematkan pada widget constructor.
Model membuktikan kapasitas kognitif pemulihan mandiri: struktur data dibuat lengkap dan parameter disematkan.

### C. Titik Kemacetan (Contract Gridlock & Harvester Shadowing) pada Iterasi 3 -> 4
Meskipun `MetricData` dan parameter `data` berhasil diselesaikan, kompilasi tetap gagal karena:
1. Developer menghapus `class CardMetric` lama (karena mengira fungsinya telah digantikan oleh `MetricData`), tetapi menyisakan baris riverpod di atas:
   `final cardMetricProvider = Provider<CardMetric>((ref) => CardMetric());`
2. Developer tetap menamai widget `CardMetricWidget` karena terikat kontrak resmi.
3. Kompiler mengeluarkan pesan error gabungan:
   - `lib/card_metric.dart:4:37: Error: 'CardMetric' isn't a type.`
   - `test/card_metric_test.dart:13:19: Error: Method not found: 'CardMetric'. body: CardMetric(`
   - `test/card_metric_test.dart:22:24: Error: Undefined name 'CardMetric'. expect(find.byType(CardMetric), findsOneWidget);`
4. **Harvester Deduplication Shadowing:**
   Harvester memproses baris error secara linier. Karena `lib/card_metric.dart:4` muncul pertama, Harvester mengatribusikan ketiadaan `CardMetric` pada file implementasi lokal (`Implementation declaration at lib/card_metric.dart:4`).
   Saat membaca error kedua pada `test/card_metric_test.dart:13`, Harvester mengabaikannya karena simbol `CardMetric` sudah tercatat. Akibatnya, konteks panggilan orakel `body: CardMetric(...)` hilang dari preskripsi.
5. **Double-Bind:**
   Developer menerima preskripsi untuk mendefinisikan `CardMetric` di line 4, namun di saat bersamaan Dokumen Kontrak Resmi dan Section 5 Invariants menyatakan:
   `Antarmuka Resmi: CardMetricWidget`
   `! Rename authoritative interface names defined in contract`
   Terjebak dalam kontradiksi ini, Developer mengulangi kode yang sama pada Iterasi 4 hingga budget habis.

---

## 4. Analisis Awal Pasca-Run 3 & Evaluasi Usulan Solusi

Dari investigasi forensik Run 3, diajukan dua usulan penyempurnaan:
1. **Provenance-Preserving Deduplication pada Evidence Layer:** Menjamin call-site test suite acceptance tidak terhapus oleh error internal deklarasi kode. (Putusan IA: **GO** dengan penegasan pemeliharaan provenance berjenjang).
2. **Konvensi Penamaan Widget PascalCase:** Menambahkan aturan bahwa `lib/card_metric.dart` harus menjadi `CardMetric`, bukan `CardMetricWidget`. (Putusan IA: **NO-GO Mutlak** karena merupakan *architectural prior* / *confounder* yang mendikte desain).

---

## 5. Implementasi Provenance-Preserving Deduplication & Unit Testing

Perbaikan diimplementasikan pada fungsi `synthesize_b5_actionable_prescriptions` di `backend/context_assembler.py`:
- Kandidat call-site yang berasal dari `test_files` diberi label otoritas tertinggi: `[AUTHORITATIVE ORACLE CALL-SITE]`.
- Rujukan deklarasi internal dari source file dipreservasi sebagai bukti pendukung: `[INTERNAL IMPLEMENTATION REFERENCE]`.
- Suite unit test `backend/tests/test_dart_diagnostic_harvester.py` diperluas dari 8 menjadi 10 test case, mencakup pengujian simetris dua arah (internal-first dan test-first), semuanya lulus 100% (**10/10 PASS**).
- Seluruh rangkaian unit test evidence (`test_v5_evidence_delivery.py`, `test_runtime_evidence_enrichment`, `test_contextual_evidence.py`) lulus 100% (**114/114 PASS**).

---

## 6. Hasil & Forensik Eksekusi Pilot Run 4 (`pv_pilot_flutter_t1_rep1_20260912_062738`)

* **Waktu:** 2026-09-12 06:27:38 WIB s.d. 06:30:38 WIB (Durasi: 179.0s)
* **Hasil:** Verdict FAIL, Loops: 5, Tests: 0/3 passed.
* **Frozen Oracle SHA-256:** `4589e15cfb8f37ba...` (100% INTACT & IMMUTABLE).
* **Treatment B (R-3):** Tetap NONAKTIF (`0`).

### A. Pembuktian Empiris: Evidence Layer 100% Berhasil
Pada Event 20 (setelah kompilasi pertama gagal), CEP menghasilkan preskripsi:
```
- [RX-B5-DART-SYMBOL-001] MetricData -> [AUTHORITATIVE ORACLE CALL-SITE] test/card_metric_test.dart:14
- [RX-B5-DART-SYMBOL-002] CardMetric -> [AUTHORITATIVE ORACLE CALL-SITE] test/card_metric_test.dart:13
```
Kedua simbol acceptance Oracle berhasil dipreservasi dan dihantarkan ke Developer secara utuh. Cacat *deduplication shadowing* pada Run 3 telah terselesaikan secara tuntas.

### B. Penemuan Kritis: Hierarchy-of-Authority Failure
Meskipun preskripsi B5 telah memuat pemanggilan `CardMetric(...)`, Developer pada Iterasi 2 (Event 25) dan Iterasi 3 (Event 41) **tetap menghasilkan `class CardMetricWidget`** dan menolak mengganti nama menjadi `CardMetric`.

Audit terhadap prompt Developer di Event 21 mengungkap terjadinya kontradiksi direktif (*Directive Deadlock*):
1. **Perintah Kontrak FROZEN:**
   - `Antarmuka Resmi: CardMetricWidget, updateCardMetric`
   - `FORBIDDEN CHANGES: ! Rename authoritative interface names defined in contract`
   - `Batasan: DILARANG menambah endpoint, fungsi, atau model di luar kontrak resmi ini!`
2. **Perintah Preskripsi B5:**
   - `REQUIRED CHANGE (CONTRACT): Symbol 'CardMetric' is invoked or referenced by the caller at Oracle test call site at test/card_metric_test.dart:13... Define or export class/method 'CardMetric'`

Developer memilih mematuhi larangan kontrak resmi dan tidak me-rename interface, sehingga pengujian acceptance tetap gagal kompilasi.

---

## 7. Putusan Otoritatif Intent Architect (Church of Goat 🐐)

Intent Architect menetapkan bahwa Run 4 merupakan *breakthrough discovery*, bukan kegagalan eksperimental biasa:
- **Run 3 menemukan:** Evidence kehilangan provenance.
- **Run 4 memperbaikinya dan menemukan:** Evidence sekarang benar, tetapi sistem telah membekukan klaim Architect yang bertentangan dengan acceptance authority.

### A. Matriks Putusan IA
| Isu / Usulan | Putusan IA | Rasional Ilmiah |
| :--- | :---: | :--- |
| **Provenance-Preserving Deduplication** | 🟢 **KEEP** | Terbukti empiris 100% sukses menghantarkan call-site Oracle. |
| **Oracle Call-Site Provenance** | 🟢 **KEEP** | Otoritas acceptance harus dibedakan dari deklarasi internal. |
| **Treatment B (R-3)** | 🔒 **LOCK OFF** | Menjaga kondisi eksperimen terkontrol bersih. |
| **Izinkan Developer Langgar Kontrak Frozen** | ❌ **NO-GO** | Merusak makna kontrak immutable; tidak boleh ada pengecualian ad-hoc. |
| **Ubah Kontrak Manual Menjadi CardMetric** | ❌ **NO-GO** | Prematur; validator dilarang memilih desain implementasi. |
| **Naming Convention Prior Flutter** | ❌ **NO-GO** | Architectural prior / confounder yang mendikte arsitektur. |
| **Contract–Oracle Consistency Gate Sebelum Freeze** | 🟢 **GO** | Memvalidasi klaim Architect terhadap Acceptance Authority di hulu (V2). |
| **Penyempurnaan Preskripsi Pure Non-Solver** | 🟢 **GO** | Menyatakan requirement tingkat kontrak, bukan solusi implementasi. |
| **Eksekusi Pilot Run 5 Sekarang** | 🔴 **STOP** | Dilarang menjalankan Run 5 sebelum konsistensi gerbang hulu terpasang. |

### B. Doktrin Epistemik Baru
$$\text{"No contract may become immutable before its consistency with the immutable acceptance authority has been deterministically established."}$$

Jangan percaya Architect. Jangan percaya Contract. Bahkan jangan percaya status FROZEN. Seluruh status beku wajib dibenarkan oleh bukti (*evidence*) terhadap acceptance authority sebelum disegel.

### C. Formulasi Non-Solver Preskripsi Baru
- **Evidence:** `[AUTHORITATIVE ORACLE CALL-SITE] CardMetric(...)`
- **Requirement-Level Prescription:**  
  *"The implementation must satisfy the authoritative CardMetric call-site while preserving all valid frozen external requirements."*  
  (Dilarang mendikte: *"Define or export class/method CardMetric"*).

