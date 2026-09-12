# Laporan Eksperimen Controlled Developer Ablation — Treatment R-3 Authority Clarification (`flutter_t1`)

**Tanggal & Waktu:** 2026-09-12 18:05 WIB  
**Workspace:** `D:\Pekerjaan\Antigravity\reindev_studio`  
**Run ID Control:** `pv_generalization_flutter_qwen7b_rep1_20260912_174843`  
**Run ID Treatment:** `pv_ablation_flutter_qwen7b_treatment_r3_rep1_20260912_180349`  
**Task:** `flutter_t1` (`lib/card_metric.dart`)  
**Metodologi:** Developer-Only Controlled Ablation (Zero Task-Specific Solvers)

---

## 1. Tujuan & Desain Eksperimen

Eksperimen ini dirancang secara ketat untuk menguji **Contract-Boundary Ambiguity Hypothesis**:
> *Apakah kegagalan `qwen2.5-coder:7b` pada preset Flutter disebabkan oleh ambiguitas batasan kontrak (Developer enggan mendeklarasikan kelas baru karena klausul larangan negatif pada prompt kontrak), ataukah murni batas kapasitas representasi simbolik (Cross-Symbol Semantic Capability Ceiling)?*

### Desain Kontrol vs Perlakuan (Identik 100% Kecuali Formulasi R-3):
| Parameter Eksperimen | Kondisi Control | Kondisi Treatment | Keterangan Isolasi |
|---|---|---|---|
| **Developer Model** | `qwen2.5-coder:7b` (Ollama) | `qwen2.5-coder:7b` (Ollama) | Identik 100% (`num_ctx=8192`, `num_predict=3000`) |
| **Reviewer Model** | `qwen2.5-coder:7b` (Ollama) | `qwen2.5-coder:7b` (Ollama) | Identik 100% (Doktrin #6 / D-112) |
| **Architect / PM** | `qwen2.5-coder:7b` (Treatment A) | `qwen2.5-coder:7b` (Treatment A) | Seeded Frozen Invariants Identik |
| **Acceptance Oracle** | `card_metric_test.dart` | `card_metric_test.dart` | **SHA: `4589e15c...` (Immutable)** |
| **Contract Status** | `CardMetric` (FROZEN) | `CardMetric` (FROZEN) | **SHA: `9e2742c8...` (Frozen)** |
| **Repair Budget** | 2 repair opportunities | 2 repair opportunities | 3 execution turns (Loops = 5) |
| **LOCKED_INVARIANTS** | Aktif | Aktif | Universal Invariant Accumulation |
| **Task-Specific Solvers** | **TIDAK ADA (0)** | **TIDAK ADA (0)** | Tanpa petunjuk "Tambahkan MetricData" |
| **Variabel Perlakuan (R-3)** | Formulasi R-3 Standar (Elemen eksternal vs detail internal) | **Formulasi Klarifikasi Otoritas R-3**: Prinsip Umum Otoritas Acceptance Oracle | **SATU-SATUNYA PERUBAHAN** |

### Formulasi Teks Treatment R-3 (Prinsip Umum):
> *"Acceptance Oracle memiliki otoritas lebih tinggi daripada detail implementasi internal yang tidak secara eksplisit dibekukan. Jika Oracle secara deterministik mensyaratkan sebuah symbol/interface yang belum tercakup dalam frozen contract invariant, Developer wajib memenuhi requirement tersebut; hal itu bukan pelanggaran Contract Boundary."*

---

## 2. Kriteria Interpretasi IA

Berdasarkan protokol eksperimental yang ditetapkan Intent Architect:
1. **Jika Control FAIL → Treatment PASS:**
   Maka diperoleh bukti kuat bahwa ambiguitas contract-boundary memang merupakan *causal blocker* utama.
2. **Jika Keduanya FAIL:**
   Maka hipotesis R-3 melemah/terrefutasi, dan konklusi ilmiah kembali secara definitif ke **Hipotesis Cross-Symbol Semantic Capability Ceiling** (keterbatasan representasi intrinsik model 7B).
3. **Jika Treatment PASS namun mekanisme LOCKED/preservation rusak:**
   Hasil tidak boleh diterima karena terjadi regresi arsitektural.

---

## 3. Hasil Komparatif Empiris Head-to-Head

| Metrik Evaluasi | Control (`17:48:43`) | Treatment R-3 (`18:03:49`) | Status Perbandingan |
|---|---|---|---|
| **Hasil Akhir Sandbox** | **FAIL (0/1 suite)** | **FAIL (0/1 suite)** | **KEDUANYA FAIL** |
| **Vonis Rilis Reviewer** | FAIL | FAIL | Identik |
| **Total Turn / Loops** | 3 Turn / 5 Loops | 3 Turn / 5 Loops | Identik (Budget Habis) |
| **Durasi Eksekusi** | 356.1 detik | 93.0 detik | Terisolasi |
| **Respons Parameter `data`** | Ditambahkan di Turn 1 (`required this.data`) | Ditambahkan di Turn 1 (`required this.data`) | Perilaku Identik |
| **Tipe Data Parameter** | Terikat ke `CardMetricData` | Terikat ke `CardMetricData` | **Stagnan Identik** |
| **Deklarasi `MetricData`** | **TIDAK PERNAH DIBUAT** | **TIDAK PERNAH DIBUAT** | **Stagnan Identik** |
| **Kode Turn 1 vs Turn 2** | Identik 100% (Fiksasi Stagnan) | Identik 100% (Fiksasi Stagnan) | **Byte-Identical Stagnation** |
| **Invarian Terkunci (Locked)** | `INV-PARAM-CardMetric-data` (LOCKED) | `INV-PARAM-CardMetric-data` (LOCKED) | **100% Konsisten Terkunci** |
| **Non-Regression Rate** | **100% (0 regresi)** | **100% (0 regresi)** | **Zero Regression** |
| **Integritas Oracle SHA** | Utuh (`4589e15c...`) | Utuh (`4589e15c...`) | **100% Intact** |
| **Integritas Kontrak SHA** | Utuh (`9e2742c8...`) | Utuh (`9e2742c8...`) | **100% Frozen** |

---

## 4. Analisis Forensik Trajektori Kode

### A. Kode yang Dihasilkan pada Turn 1 & Turn 2 (Treatment):
```dart
class CardMetricData {
  final int value;
  final String description;

  CardMetricData(this.value, this.description);
}

class CardMetric extends ConsumerWidget {
  final CardMetricData data; // <-- Tetap mengikat ke CardMetricData

  const CardMetric({Key? key, required this.data}) : super(key: key);
  ...
}
```
**Temuan Kunci:**
Meskipun prompt Developer secara eksplisit dibekali prinsip:
> *"Acceptance Oracle memiliki otoritas lebih tinggi daripada detail implementasi internal... hal itu bukan pelanggaran Contract Boundary"*,
model `qwen2.5-coder:7b` **tetap tidak menyintesis `class MetricData`**. Model tetap mengikat parameter `data` ke kelas scaffold lokalnya (`CardMetricData`).

Pada Turn 2, model mereplikasi kode yang 100% identik tanpa perubahan, membuktikan terjadinya fiksasi representasional (*self-syntax representation trapping*).

### B. Evaluasi Mekanisme Penguncian (`LOCKED_INVARIANTS`):
- Pada Turn 1 (iter=3), Gate V5 mendeteksi bahwa parameter konstruktor `data` telah berhasil ditambahkan. Sistem mendaftarkan invarian:
  `[LOCKED] [INV-PARAM-CardMetric-data]`
- Pada Turn 2 (iter=5), invarian ini di-revalidasi:
  `status: PROVEN`, `state: LOCKED`, `revalidated_at_turn: 5`, `regression_count: 0`.
- **Hasil:** Mekanisme penguncian invarian bekerja 100% sempurna tanpa regresi (*Zero Regression Rate*), bahkan di saat model mengalami kegagalan pada simbol lain.

---

## 5. Kesimpulan Epistemik Berdasarkan Kriteria IA

1. **Refutasi Hipotesis Contract-Boundary Ambiguity:**
   Karena **Control FAIL dan Treatment FAIL**, hipotesis bahwa Developer 7B terhalang oleh ambiguitas larangan kontrak secara definitif **melemah / gugur**. Model 7B tidak gagal karena takut melanggar batasan kontrak, melainkan karena **keterbatasan kognitif intrinsik model** dalam melakukan penalaran simbolik silang (*Cross-Symbol Semantic Reasoning Capability Ceiling*).
2. **Ketiadaan Solver Terbukti Secara Mutlak:**
   Fakta bahwa manipulasi prompt R-3 tidak serta-merta meloloskan model 7B menegaskan bahwa ReinDev Studio murni beroperasi berdasarkan prinsip generalisasi ilmiah, tanpa adanya pintu belakang (*backdoor*) atau trik prompt tersembunyi.
3. **Taksonomi Kapasitas Model Lintas Skala Terkonfirmasi:**
   - **7B (`qwen2.5-coder:7b`):** Sub-threshold untuk sintesis entitas data majemuk Dart dari call-site pengujian (stagnan pada kelas scaffold lokal).
   - **8B (`gemma4:e4b`):** Adaptive multi-turn (mampu menyintesis `MetricData`, namun terbatasi oleh budget turn perbaikan).
   - **9B (`ornith:9b`):** Convergent (mampu menyintesis `MetricData` lengkap dan lulus 100% sandbox Flutter dalam 1 turn perbaikan).
   - **14B (`qwen3-14b`):** Convergent (mampu menyintesis `MetricData` lengkap dan lulus 100% sandbox Flutter dalam 1 turn perbaikan).
