# Laporan Forensik Eksperimen Ablasi: Komparasi Model Lokal Generasi Baru (`qwen3.5:9b`) pada Flutter `flutter_t1`

**Tanggal Pelaksanaan:** 2026-09-12T12:56:40 — 13:11:15 WIB  
**ID Eksperimen:** `pv_ablation_dev_r3_qwen35_9b_flutter_t1_rep1_20260912_125640`  
**Task ID:** `flutter_t1` (`lib/card_metric.dart`)  
**Target Bahasa:** Dart (Flutter Material 3 & Riverpod)  
**Evaluated Model:** `qwen3.5:9b` (via Ollama lokal, Digest: `6488c96fa5fa`, 6.6 GB, 9.7B parameters, Q4_K_M)  
**Baseline Model:** `qwen2.5-coder:7b` (Ollama lokal)  
**Stepwise Model:** `gemma4:e4b` (Ollama lokal, 8.0B)  
**Frontier Model:** `qwen/qwen3-14b` (OpenRouter Cloud)  
**Format-Fragile Model:** `deepseek-coder:6.7b` (Ollama lokal)  
**Treatment Variable:** `REINDEV_TREATMENT_B_R3="1"` (Doktrin #6: Caller Consistency Repair)  
**Status Kontrak Input:** `FROZEN` (SHA-256: `9e2742c8cea664a48873c95772b8472b8ccaf3742c52f4b94a55b21471eddde3`)  
**Integritas Frozen Oracle:** `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` (**100% INTACT Pre & Post Flight**)  

---

## 1. Executive Summary: Matriks Komparasi 5 Model Terkontrol (`flutter_t1`)

| Dimensi Evaluasi | DeepSeek Coder 6.7B (Lokal) | Qwen 2.5 Coder 7B (Lokal) | Qwen 3.5 9B (Lokal) | Gemma 4 e4b (8B Lokal) | Qwen 3 14B (Cloud) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Inference Backend** | Ollama | Ollama | Ollama | Ollama | OpenRouter API |
| **Ukuran / Parameter** | 3.8 GB (6.7B) | 4.7 GB (7.6B) | 6.6 GB (9.7B) | 9.6 GB (8.0B) | 14.8B (Cloud) |
| **Disiplin Format Tag** | GAGAL (Kutipan liar) | 100% Disiplin | **100% Disiplin** | 100% Disiplin | 100% Disiplin |
| **Penetrasi Gate V3** | Tertahan di Gate V3 | Lolos ke Sandbox | **Lolos ke Sandbox (3/3)** | Lolos ke Sandbox (3/3) | Lolos ke Sandbox |
| **Turn 0 (Initial)** | Target file missing | Missing `MetricData` | Syntax Error Provider | Missing `MetricData` | Missing `MetricData` |
| **Turn 1 (Repair 1)** | Scaffold 5 files liar | Stagnan (Hanya param `data`) | Modifikasi Kosmetik Card | **Sintesis `MetricData`** | **LULUS (2/2 PASS)** |
| **Turn 2 (Repair 2)** | Keluarkan kode test | Stagnan (Byte-identical) | **Stagnan (Byte-identical)** | **Tambah `Color? color`** | N/A (Sudah PASS) |
| **Akar Hambatan** | Delimiter Hallucination | Total Symbolic Blindspot | **Self-Syntax Stagnation** | Residu Parameter | Bebas Hambatan |
| **Final Run Verdict** | **FAIL (Divergent)** | **FAIL (Stagnant Logic)** | **FAIL (Stagnant Syntax)** | **FAIL (Stepwise)** | **PASS (Convergent)** |
| **Durasi Run** | 604.98s | 96.13s | 873.59s | 243.65s | 334.83s |

---

## 2. Analisis Kausal: Mengapa `qwen3.5:9b` Mengalami Stagnasi Sintaksis Internal?

Meskipun `qwen3.5:9b` adalah model yang lebih besar (9.7B) dan memiliki kapabilitas *reasoning/thinking*, hasil pengujian empiris menunjukkan pola kegagalan yang berbeda secara fundamental dari model lainnya:

### A. Galat Sintaksis Konstruktor Mandiri (Self-Introduced Constructor Error)
Pada Turn 0, model mendefinisikan kelas data dengan *named parameters*:
```dart
class CardMetricData {
  final int value;
  final String description;

  const CardMetricData({
    required this.value,
    required this.description,
  });
}
```
Namun, pada inisialisasi Riverpod provider di baris 4, model menginstansiasikannya dengan *positional arguments*:
```dart
final cardMetricProvider = Provider<CardMetricData>((ref) => CardMetricData(0, 'Initial Data'));
```
Dalam bahasa Dart (Sound Null Safety), pemanggilan argumen posisional pada konstruktor dengan parameter bernama adalah galat fatal. Kompilator menghentikan kompilasi seketika:
```text
lib/card_metric.dart:4:76: Error: Too many positional arguments: 0 allowed, but 2 found.
Try removing the extra positional arguments.
final cardMetricProvider = Provider<CardMetricData>((ref) => CardMetricData(0, 'Initial Data'));
```
Karena galat fatal terjadi pada berkas implementasi itu sendiri, kompilator Dart bahkan belum sempat membaca berkas pengujian (`test/card_metric_test.dart`), sehingga model tidak pernah menerima feedback mengenai `MetricData`.

### B. Misdirected Repair & Fiksasi Stagnan (Turn 1 & Turn 2)
1. **Turn 1 (Repair Attempt 1):**
   - Model menerima trace kompilasi `Too many positional arguments: 0 allowed, but 2 found` pada `CardMetricData`.
   - Namun, proses penalaran model mengalami disorientasi: model mengabaikan baris provider dan justru mengedit properti visual widget `Card`:
     ```diff
     - return Card(
     + return Card(color: Colors.white, elevation: 2.0, child: Padding(
     ```
   - Kompilator kembali menolak dengan error yang sama persis.
2. **Turn 2 (Repair Attempt 2):**
   - Menerima umpan balik yang sama untuk kedua kalinya, model menghasilkan kode yang **100% IDENTIK SECARA BYTE** dengan Turn 1 (`len=1152`).
   - Terjadi fiksasi kognitif total (stagnasi murni).
   - Kuota 2 perbaikan habis, run dihentikan secara deterministik oleh StateGraph.

---

## 3. Temuan Epistemik: Perbandingan Tipologi Model

Eksperimen ini melengkapi taksonomi perilaku LLM terhadap sistem self-healing B5 CEP ReinDev:

1. **Format Fragility (`deepseek-coder:6.7b`):** Model gagal dalam tata bahasa komunikasi protokol (tag delimiter).
2. **Self-Syntax Trapping (`qwen3.5:9b`):** Model menciptakan galat sintaksis pada kodenya sendiri, terdistraksi ke elemen kosmetik, lalu mengalami stagnasi byte-identical tanpa pernah mencapai orakel uji.
3. **Symbolic Blindspot (`qwen2.5-coder:7b`):** Model lolos sintaksis internal, namun tidak mampu menyintesis simbol baru yang dituntut oleh pemanggil pengujian ketika kelas mirip sudah ada.
4. **Stepwise Greedy Adaptation (`gemma4:e4b`):** Model menyelesaikan satu lapisan galat per putaran secara disiplin, namun terhambat batas anggaran putaran (kuota 2x perbaikan).
5. **Holistic Backward-Inference (`qwen/qwen3-14b`):** Model mampu memetakan seluruh hierarki ketergantungan orakel pemanggil secara holistik dan menyelesaikannya dalam 1 putaran perbaikan.

---

## 4. Validasi Konfirmasi Pasca Perbaikan D-112: Pembuktian Zero Downstream Leakage

**Tanggal Eksekusi:** 2026-09-12T14:42:08 — 14:56:41 WIB  
**Run ID:** `pv_ablation_dev_r3_qwen35_9b_flutter_t1_rep1_20260912_144208` (Durasi: 873.37s)  
**Status Kontrak:** `FROZEN` (SHA-256: `9e2742c8cea664a4...`)  
**Frozen Oracle SHA-256:** `4589e15cfb8f...` (**100% INTACT Pre & Post Flight**)  

**Hasil & Temuan Epistemik:**
1. **Reproduksibilitas 100%:** Model mereproduksi secara presisi pola kegagalan yang sama persis:
   - Turn 0: Argumen posisional pada provider (`CardMetricData(0, 'Initial Data')`) membentur konstruktor bernama (`Too many positional arguments: 0 allowed, but 2 found`).
   - Turn 1: Modifikasi kosmetik visual kartu (`Card(color: Colors.white, elevation: 2.0, ...)`).
   - Turn 2: Fiksasi stagnan total (100% byte-identical, hash: `88d3403dc382435274baadf45243602aca879e6627852ac54ed64618e313cca6`).
2. **Zero Downstream Leakage:**
   Karena kode tidak pernah lolos dari kompilator Dart di sandbox eksekutor, kode **tidak pernah mencapai Reviewer maupun Gate V6**. Ini membuktikan secara empiris bahwa perbaikan hilir (toleransi semantik pada Gate V6 dan Reviewer Cognitive Symmetry) sama sekali tidak melonggarkan batas pertahanan di hulu; kode yang cacat sintaksis tetap tertahan ketat di sandbox tanpa kebocoran.
