# Laporan Investigasi Forensik: Fresh Flutter Pilot flutter_t1 Pasca D-104

**Tanggal Eksperimen:** 12 September 2026  
**Pelaksana Eksperimen:** Antigravity AI Engineering Squad  
**Otoritas Tata Kelola (Intent Architect):** Muhammad Rachmadi  
**Objek Eksperimen:** Pilot Run pv_pilot_flutter_t1_rep1_20260912_105346 (flutter_t1), Telemetri 54 Event  
**Model Subjek Uji:** qwen2.5-coder:7b (Unified Local Squad via Ollama, num_ctx=8192, num_predict=3000, temp=0.2)  
**Status Evaluasi Epistemik:** INVESTIGASI FORENSIK LENGKAP — PEMBUKTIAN PRESERVASI SEMANTIK D-104 & DIAGNOSIS PROMPT TENSION PADA MODEL SEKUNDER  

---

## 1. Rantai Bukti Digital (Digital Chain of Custody)

| Parameter Kriptografis / Metrik | Nilai Faktual Tercatat | Verifikasi Kepatuhan |
| :--- | :--- | :--- |
| **Run ID** | pv_pilot_flutter_t1_rep1_20260912_105346 | Tercatat di run_trace.jsonl (54 event) |
| **Task ID & Target** | flutter_t1 (lib/card_metric.dart) | Authoritative single module target |
| **Frozen Oracle SHA-256** | 4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528 | 100% INTACT & TIDAK BERMUTASI |
| **Status Kontrak Akhir** | FROZEN (Segel SHA-256: 9e2742c8cea6...) | Lolos Gate V2 pada Turn 0 |
| **Pemanggilan QA Tester LLM** | 0 pemanggilan | Bypass mutlak via Frozen Oracle |
| **Treatment B (Constraint / R-3)** | NONAKTIF (0) | Terisolasi murni (Locked Off) |
| **Hasil Eksekusi Sandbox** | 0/1 PASS (0.0%) | test/card_metric_test.dart compilation error |
| **Jumlah Putaran (Loops)** | 5 loops | Budget iterasi habis |
| **Vonis Akhir** | FAIL | Stagnasi pada Developer iterasi 4 |
| **Durasi Eksekusi** | 191.55 detik (~3.19 menit) | Waktu komputasi wajar |

---

## 2. Tujuan Eksperimen & Desain Metodologis

Tujuan eksperimen ini adalah menguji secara empiris apakah mekanisme D-104 (Semantic State Preservation Across Serialization Repair) mampu mencegah regresi semantik pada fase Architect dan melindungi integritas kontrak:
PROVEN semantic invariant -> serialization failure -> repair -> semantic regression

### Batasan Eksperimen yang Dikunci IA:
1. **Zero Code Change:** Tidak ada modifikasi kode sebelum atau selama pilot.
2. **Treatment B / R-3 Locked Off:** REINDEV_TREATMENT_B_R3='0' dipertahankan untuk mengisolasi efek murni Treatment A + D-104.
3. **Immutable Frozen Oracle:** Checksum 4589e15c... diverifikasi identik 100%.
4. **Single Run Stop Rule:** Sistem wajib berhenti seketika setelah 1 pilot run tunggal selesai.

---

## 3. Rekonstruksi Trajektori Forensik Turn-by-Turn

### A. Turn 0 — Fase PM (Gate V1) & Architect (Gate V2)
- **PM Phase:** Merumuskan spesifikasi (633 char) dan menerbitkan draft kontrak. Lolos Gate V1 (0 pelanggaran).
- **Architect Phase:**
  - Menghasilkan rencana arsitektur (2.744 char) dan blueprint JSON kanonikal.
  - Mendeklarasikan widget CardMetric pada lib/card_metric.dart.
  - Gate V2 mengevaluasi konsistensi terhadap Acceptance Oracle: nama CardMetric terbukti konsisten dengan call-site body: CardMetric(...) pada test/card_metric_test.dart:13.
  - Blueprint JSON berstatus VALID (0 errors).
  - Kontrak resmi disegel menjadi FROZEN pada Turn 0 (SHA-256 seal: 9e2742c8cea6...).
  - Vonis Gate V2: PASS. Kontrak langsung mengalir ke Developer tanpa memerlukan siklus perbaikan Architect.

### B. Turn 0 (Iterasi 0) — Inisiasi Developer & Gate V3/V4
- Developer menerima kontrak FROZEN dan menghasilkan kode awal lib/card_metric.dart.
- Developer secara mandiri mendeklarasikan kelas model data CardMetricData(value, description) dan widget CardMetric extends ConsumerWidget dengan konstruktor default tanpa parameter.
- Gate V3 (AST syntax audit) dan Gate V4 (Oracle test loaded) keduanya PASS.
- Sandbox mengeksekusi flutter test:
  - test/card_metric_test.dart:14:21: Error: Method not found: MetricData.
  - test/card_metric_test.dart:14:15: Error: No named parameter with the name data.
  - lib/card_metric.dart:13:7: Context: The class CardMetric has a constructor that takes no arguments.
- Gate V5 (Iteration Validator): FAIL.

### C. Turn 1 (Iterasi 2) — Developer Repair Attempt 1
- **Preskripsi B5 CEP yang Dikirimkan:**
  - RX-B5-DART-SYMBOL-001: Simbol MetricData tak terdefinisi di call-site test/card_metric_test.dart:14. Direktif: Implement or expose MetricData in lib/card_metric.dart to satisfy caller invocation while maintaining contract integrity.
  - RX-B5-DART-PARAM-002: Named parameter data tidak ada pada konstruktor. Direktif: Update parameter declarations in lib/card_metric.dart to accept named parameter data.
- **Tindakan Developer:**
  - Developer menambahkan parameter: const CardMetric({Key? key, required this.data}) : super(key: key);
  - Developer mendeklarasikan field: final CardMetricData data;
  - Developer mengikat tipe parameter ke model internalnya sendiri (CardMetricData), dan tidak mendeklarasikan kelas MetricData.
- **Hasil Sandbox:** FAIL (Method not found: MetricData).

### D. Turn 2 (Iterasi 4) — Developer Repair Attempt 2
- Developer mengulangi kode identik dengan Attempt 1.
- Hasil Sandbox: FAIL (Method not found: MetricData).
- Budget iterasi Developer (5 loops) habis. Vonis akhir: FAIL.

---

## 4. Evaluasi Khusus Terhadap Klaim D-104

1. **Apakah PROVEN_SEMANTIC_INVARIANT Dipertahankan?**
   - YA (100% TERBUKTI).
   - Di fase Architect, kontrak CardMetric langsung berstatus PROVEN dan FROZEN di Turn 0.
   - Di fase Developer, simbol CardMetric dipertahankan di seluruh 3 turn kode (iterasi 0, 2, dan 4). Tidak pernah terjadi mutasi kembali menjadi CardMetricWidget.
2. **Apakah Terjadi SEMANTIC_REGRESSION?**
   - TIDAK TERJADI (0 SEMANTIC_REGRESSION).
   - Tidak ada degradasi invarian semantik di sepanjang eksekusi.

---

## 5. Analisis Faktor Kausal Kegagalan (Root Cause Analysis)

Kegagalan murni terjadi di fase Developer akibat kombinasi tiga faktor mekanistik:
1. **Selective Attention Model 7B terhadap Multi-Error:**
   Ketika menghadapi error parameter dan error simbol tipe pada baris yang sama, model memprioritaskan perbaikan konstruktor (required this.data) dan mengaitkannya ke kelas data yang sudah ada di memori prompt-nya (CardMetricData).
2. **Prompt Boundary Tension (Ketegangan Konstrain Kontrak vs CEP):**
   Prompt Developer memuat larangan keras:
   - Model Data Resmi: (Sesuai interface)
   - Batasan: DILARANG menambah endpoint, fungsi, atau model di luar kontrak resmi ini!
   - FORBIDDEN CHANGES: ! Invent speculative public interfaces not in contract
   Sementara itu, direktif B5 CEP menuntut:
   - REPAIR BOUNDARY (ALLOWED): Implement or expose MetricData in lib/card_metric.dart
   Model 7B mengalami kebingungan direktif dan memilih untuk tidak menciptakan kelas model baru MetricData demi mematuhi larangan kontrak resmi.
3. **Isolasi Treatment B (R-3 Nonaktif):**
   Prinsip Contract Boundary Principle (yang menjelaskan bahwa detail implementasi internal seperti tipe data pendukung dapat disesuaikan untuk memenuhi bukti pengujian) tidak aktif karena R-3 terkunci pada 0.
