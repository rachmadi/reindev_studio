# Laporan Forensik Eksperimen Ablasi: Komparasi Model Lokal Khusus Rekayasa Kode (`ornith:9b`) pada Flutter `flutter_t1`

**Tanggal Pelaksanaan:** 2026-09-12T13:24:50 — 13:29:50 WIB  
**ID Eksperimen:** `pv_ablation_dev_r3_ornith_9b_flutter_t1_rep1_20260912_132450`  
**Task ID:** `flutter_t1` (`lib/card_metric.dart`)  
**Target Bahasa:** Dart (Flutter Material 3 & Riverpod)  
**Evaluated Model:** `ornith:9b` (via Ollama lokal, Digest: `a75697c14589`, 5.6 GB, 9.0B parameters, Q4_K_M, Agentic Coding Assistant)  
**Baseline Model:** `qwen2.5-coder:7b` (Ollama lokal)  
**Stepwise Model:** `gemma4:e4b` (Ollama lokal, 8.0B)  
**Frontier Model:** `qwen/qwen3-14b` (OpenRouter Cloud)  
**Syntax-Trapped Model:** `qwen3.5:9b` (Ollama lokal, 9.7B)  
**Treatment Variable:** `REINDEV_TREATMENT_B_R3="1"` (Doktrin #6: Caller Consistency Repair)  
**Status Kontrak Input:** `FROZEN` (SHA-256: `9e2742c8cea664a48873c95772b8472b8ccaf3742c52f4b94a55b21471eddde3`)  
**Integritas Frozen Oracle:** `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` (**100% INTACT Pre & Post Flight**)  

---

## 1. Executive Summary: Matriks Komparasi 6 Model Terkontrol (`flutter_t1`)

| Dimensi Evaluasi | DeepSeek 6.7B | Qwen 2.5 7B | Qwen 3.5 9B | Gemma 4 8B | Ornith 9B (Lokal) | Qwen 3 14B (Cloud) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Inference Backend** | Ollama | Ollama | Ollama | Ollama | **Ollama** | OpenRouter API |
| **Ukuran / Parameter** | 3.8 GB (6.7B) | 4.7 GB (7.6B) | 6.6 GB (9.7B) | 9.6 GB (8.0B) | **5.6 GB (9.0B)** | 14.8B (Cloud) |
| **Disiplin Format Tag** | GAGAL | 100% Disiplin | 100% Disiplin | 100% Disiplin | **100% Disiplin** | 100% Disiplin |
| **Penetrasi Gate V3** | Tertahan V3 | Lolos Sandbox | Lolos Sandbox | Lolos Sandbox | **Lolos Sandbox** | Lolos Sandbox |
| **Sintesis `MetricData`** | N/A | GAGAL (Stagnan) | GAGAL (Syntax) | ADAPTIF (Residu) | **BERHASIL 100% (Turn 1)** | **BERHASIL 100% (Turn 1)** |
| **Sandbox Tests Passed** | 0 / 2 (0 run) | 0 / 2 (Exit 1) | 0 / 1 (Exit 1) | 0 / 1 (Exit 1) | **2 / 2 (100% PASS, Exit 0)** | **2 / 2 (100% PASS, Exit 0)** |
| **Reviewer Deterministic Gate** | N/A | N/A | N/A | N/A | **LULUS 100% (CCR=1.0)** | **LULUS 100% (CCR=1.0)** |
| **Reviewer LLM Audit** | FAIL | FAIL | FAIL | FAIL | **NEEDS_REVISION (Blueprint Drift)** | **APPROVED** |
| **Klasifikasi Kegagalan** | Gate V3 Format | A. Developer Failure | A. Developer Failure | A. Developer Failure | **E. Reviewer Failure** | **NONE (PASS)** |
| **Final Run Verdict** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL (Reviewer Gate V6)** | **PASS (Convergent)** |
| **Durasi Total** | 604.98s | 96.13s | 873.59s | 243.65s | **300.59s** | 334.83s |

---

## 2. Temuan Kausal Utama: Model Lokal Pertama yang Menembus 100% Lulus Sandbox

Eksperimen `ornith:9b` menandai tonggak sejarah penting dalam evaluasi komparatif ReinDev Studio:

### A. Keberhasilan Sintesis Simbolik Silang-Entitas (Developer Agent)
Pada Turn 1, menerima paket bukti kausal (B5 CEP) dan Doktrin #6 (R-3), `ornith:9b` langsung menyintesis:
```dart
class MetricData {
  final String title;
  final String value;
  final Color color;

  MetricData({
    required this.title,
    required this.value,
    required this.color,
  });
}

final cardMetricProvider = Provider<MetricData>((ref) => MetricData(
  title: '',
  value: '',
  color: Colors.blue,
));

class CardMetric extends ConsumerWidget {
  const CardMetric({super.key, required this.data});

  final MetricData data;
  ...
```
Model secara presisi:
1. Mendeklarasikan `class MetricData` dengan tipe data yang tepat (`title: String`, `value: String`, `color: Color`).
2. Menambahkan konstruktor `CardMetric({super.key, required this.data})`.
3. Menyelaraskan Riverpod provider dengan model data baru.

### B. Hasil Eksekusi Sandbox Flutter (Trace 32)
```text
00:00 +0: loading D:/Pekerjaan/Antigravity/reindev_studio/backend/sandbox/test/card_metric_test.dart
00:00 +0: renders CardMetric with Material 3 Card and Riverpod state
00:00 +1: renders responsively inside constrained box without overflow
00:00 +2: All tests passed!
```
Eksekusi pengujian Flutter berhasil lulus **100% (2/2 PASS, exit code 0)** dalam waktu 1.8 detik.

---

## 3. Analisis Dinamika Multi-Agent: Reviewer-Blueprint Drift & Intervensi Gate V6

Meskipun kode Developer berhasil lulus 100% di sandbox eksekusi dan lulus audit deterministik Lapis 1 (`deterministic_gate: is_passed=True, ccr=1.0`), terjadi fenomena kognitif baru pada fase Reviewer:

### A. Reviewer Terjebak pada Blueprint Usang (Blueprint Drift)
Reviewer LLM membaca rencana arsitektur awal (blueprint dari Treatment A) yang masih menyebutkan `CardMetricData` dan `StateProvider`. Reviewer menolak kode dengan putusan `[NEEDS_REVISION]`, menuntut:
1. Mengembalikan nama kelas ke `CardMetricData`.
2. Menghapus parameter `required this.data` dari widget `CardMetric`.
3. Meminta `StateProvider` alih-alih `Provider`.

Tuntutan Reviewer ini secara langsung bertentangan dengan orakel pengujian yang sudah terbukti lulus 100%.

### B. Proteksi Immutability oleh Gate V6 (Reviewer Phase-End Validator)
Gate V6 ReinDev mendeteksi bahwa Reviewer menuntut perubahan pada kontrak yang sudah `FROZEN`:
```text
Violations: Reviewer menuntut perubahan pada kontrak yang sudah FROZEN. Kontrak FROZEN mutlak immutable (tidak ada mekanisme unfreeze).
```
Gate V6 secara deterministik memblokir rilis ilegal tersebut dan menandai kegagalan sebagai **`E. Reviewer Failure`**.

---

## 4. Kesimpulan Epistemik & Rekomendasi Arsitektur

1. **Kapasitas Model Lokal `ornith:9b`:**
   `ornith:9b` terbukti menjadi model lokal pertama dengan bobot sub-10B (5.6 GB) yang memiliki kapasitas penalaran simbolik setara model cloud 14B (`qwen/qwen3-14b`), berhasil memecahkan ketergantungan orakel uji Flutter dalam 1 putaran perbaikan.
2. **Reviewer Context Alignment:**
   Reviewer Agent perlu menerima Doktrin #6 (Caller Consistency) dalam prompt auditnya agar tidak menolak kode yang telah terbukti secara deterministik lulus Acceptance Oracle ketika terjadi penyesuaian kelas data sekunder.

---

## 5. Validasi Pasca Perbaikan D-112: Konvergensi Penuh ke Status PASS

Mengikuti mandat **INSTRUKSI IA — V6 REPAIR / REVIEWER CONSISTENCY & FALSE-POSITIVE FIX (D-112)**, dilakukan perbaikan hilir:
- Penegakan Doktrin #6 & Hierarki Bukti Rekayasa pada `REVIEWER_SYSTEM_PROMPT` dan `audit_directive`.
- Penggantian substring match dengan `classify_contract_mutation_demand()` pada Gate V6.

**Hasil Eksekusi Re-Run Terkontrol (`pv_ablation_dev_r3_ornith_9b_flutter_t1_rep1_20260912_143026`, durasi 418.98s):**
- **Turn 1 Sandbox:** 2/2 TESTS PASSED (100%, exit code 0).
- **Reviewer Audit Lapis 2:** Memberikan status **`[APPROVED]`** dengan mengutip Doktrin #6 secara eksplisit: *"Berdasarkan Doktrin #6, bukti eksekutabel dari Acceptance Oracle adalah otoritas tertinggi. Implementasi yang telah lulus 100% tidak boleh ditolak hanya karena deviasi dari blueprint yang tidak frozen."*
- **Gate V6:** **`PASS`** (0 violation, clean approval).
- **Final Verdict:** **`PASS` ✅ (Rilis Sukses ke `END`)**.
- **Kesimpulan:** `ornith:9b` resmi menjadi model lokal sub-10B pertama yang mencapai konvergensi rilis penuh di task Flutter komposit ReinDev.
