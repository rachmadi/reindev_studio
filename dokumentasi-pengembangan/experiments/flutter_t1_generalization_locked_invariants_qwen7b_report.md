# Laporan Eksperimen Generalisasi Terkontrol: Flutter UI (`flutter_t1`) dengan All-Qwen2.5-Coder 7B

**Tanggal Pelaksanaan:** 2026-09-12T17:48:43 - 17:50:29 (WIB)  
**Run ID:** `pv_generalization_flutter_qwen7b_rep1_20260912_174843`  
**Kasus / Task:** `flutter_t1` (`lib/card_metric.dart`)  
**Tujuan:** Menguji generalisasi mekanisme `LOCKED_INVARIANTS` pada kasus Flutter UI menggunakan squad homogen `qwen2.5-coder:7b` (PM, Architect, Developer, Reviewer).

---

## 1. Konfigurasi Eksperimen Terkontrol

| Parameter | Spesifikasi Konfigurasi | Status Verifikasi |
| :--- | :--- | :---: |
| **PM / Architect** | `qwen2.5-coder:7b` (Treatment A Seeded Provenance) | Terverifikasi |
| **Developer Model** | `qwen2.5-coder:7b` (Ollama lokal, `num_ctx=8192`, `num_predict=3000`) | Aktif |
| **Reviewer Model** | `qwen2.5-coder:7b` (Ollama lokal, Doktrin #6 / D-112) | Aktif |
| **Task / File Target** | `flutter_t1` (`lib/card_metric.dart`) | Sesuai Mandat |
| **LOCKED_INVARIANTS** | Aktif | Terverifikasi |
| **Universal Repair Budget**| Maksimal 2 repair opportunities (3 loop eksekusi Developer) | Dipatuhi |
| **R-3 Contract Boundary**| Aktif (`REINDEV_TREATMENT_B_R3="1"`) | Terverifikasi |
| **Pre-Flight Oracle SHA** | `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` | **PASS (Intact)** |
| **Post-Flight Oracle SHA**| `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` | **PASS (100% Immutable)** |
| **Seeded Contract SHA** | `9e2742c8cea664a48873c95772b8472b8ccaf3742c52f4b94a55b21471eddde3` | **FROZEN** |
| **Task-Specific Solvers** | **TIDAK ADA** (Zero task-specific solvers / rules) | Terverifikasi |

---

## 2. Hasil Eksekusi & Metrik

- **Final Verdict:** **`FAIL`**
- **Review Verdict:** `FAIL`
- **Loops Consumed:** 5 (3 execution turns: Initial Turn 0 + Repair Turn 1 + Repair Turn 2; budget habis)
- **Tests Passed:** 0 / 1 test suite (kompilasi gagal)
- **Total Durasi:** 105.65 detik (~1.76 menit)
- **Trajectory:** `stagnant`
- **Failure Classification:** `A. Developer Failure`
- **OTRR:** 0.0%

---

## 3. Analisis Kausal & Forensik Turn-by-Turn

### A. Turn 0 (Loop 0) — Implementasi Awal
Developer `qwen2.5-coder:7b` menghasilkan kode awal:
```dart
final cardMetricProvider = StateProvider<CardMetricData>((ref) => CardMetricData(0, 'Initial Data'));

class CardMetricData {
  final int value;
  final String description;
  CardMetricData(this.value, this.description);
}

class CardMetric extends ConsumerWidget { ... } // Konstruktor tanpa parameter
```
**Hasil Sandbox:** Kompilasi gagal pada `test/card_metric_test.dart`:
1. `Error: Method not found: 'MetricData'` (Oracle memanggil `MetricData(title: ..., value: ..., color: ...)`).
2. `Error: No named parameter with the name 'data'` pada `CardMetric`.

### B. Promosi & Feedback Gate V5
Evaluator B5 mengidentifikasi kegagalan dan menyusun Contextual Evidence Package (CEP `EV-36F454B1A849`):
- Preskripsi 1: `RX-B5-DART-SYMBOL-001` (Implementasikan atau ekspos `MetricData`).
- Preskripsi 2: `RX-B5-DART-PARAM-002` (Tambahkan parameter `required this.data` pada `CardMetric`).

### C. Turn 1 (Loop 1 - Repair 1) — Resolusi Parsial & Kuncian Parameter
Developer memproses feedback dan merespons:
```dart
class CardMetricData {
  final int value;
  final String description;
  CardMetricData(this.value, this.description);
}

class CardMetric extends ConsumerWidget {
  final CardMetricData data;
  const CardMetric({Key? key, required this.data}) : super(key: key);
  ...
}
```
- **Efek Penguncian (LOCKED):**
  Konstruktor `CardMetric` kini menerima named parameter `data`. Parameter ini resmi dipromosikan dan **dikunci** oleh gate V5:
  `[LOCKED] [INV-PARAM-CardMetric-data]` (status: `PROVEN`, state: `LOCKED`, regression_count: 0).
- **Kelemahan Model 7B:**
  Meskipun preskripsi `RX-B5-DART-SYMBOL-001` secara eksplisit mengutip call-site Oracle `MetricData(title: ..., value: ..., color: ...)`, model 7B tetap menamai kelas datanya sebagai `CardMetricData` (bukan `MetricData`), sehingga galat `Method not found: 'MetricData'` masih tersisa.

### D. Turn 2 (Loop 2 - Repair 2) — Stagnasi Model 7B
- Pada Turn 2, batas invarian `INV-PARAM-CardMetric-data` **berhasil diproteksi 100%** (tidak terjadi regresi parameter `data`).
- Namun, model `qwen2.5-coder:7b` mereplikasi kode identik tanpa mengganti nama kelas `CardMetricData` menjadi `MetricData`.
- Repair budget habis (2 repair opportunities). Pipeline berhenti deterministik dengan status `FAIL`.

---

## 4. Komparasi Pembelajaran Model: `qwen2.5-coder:7b` vs `ornith:9b` pada Flutter UI

| Dimensi | `ornith:9b` (Developer) | `qwen2.5-coder:7b` (Developer) |
| :--- | :--- | :--- |
| **Kemampuan Resolusi Simbol Oracle** | **Sangat Tinggi**: Membaca call-site `MetricData` dan langsung mendeklarasikan `class MetricData` lengkap dengan `title`, `value`, `color`. | **Rendah pada Dart**: Terpaku pada blueprint `CardMetricData` awal dan mengabaikan substitusi simbol `MetricData` meskipun diberi preskripsi eksplisit. |
| **Respon terhadap Preskripsi Parameter** | Lolos (menambahkan `required this.data`). | Lolos (menambahkan `required this.data`). |
| **Perilaku LOCKED_INVARIANTS** | Mengunci `INV-SYM-MetricData` dan `INV-PARAM-CardMetric-data` $\\rightarrow$ **PASS (2/2)**. | Berhasil mengunci `INV-PARAM-CardMetric-data` (zero regresi), namun simbol `MetricData` tidak pernah lahir. |
| **Hasil Akhir** | **PASS (100% CCR, 2 loops)** | **FAIL (0/1 CCR, 5 loops/budget exhausted)** |

---

## 5. Kesimpulan Epistemik

1. **Integritas Mekanisme LOCK Tetap Valid:**
   Mekanisme `LOCKED_INVARIANTS` bekerja sebagaimana mestinya: parameter `CardMetric.data` yang berhasil diperbaiki pada Turn 1 langsung dikunci (`LOCKED`) dan terbukti **nol regresi** pada Turn 2.
2. **Batas Kapasitas Domain-Specific Model 7B pada Flutter/Dart:**
   Sementara `qwen2.5-coder:7b` menunjukkan performa luar biasa pada domain Python (100% PASS pada FastAPI dan CLI Matrix), pada domain Flutter/Dart model 7B mengalami kesulitan dalam menyelaraskan simbol data model asing (`MetricData` vs `CardMetricData`) secara zero-shot repair tanpa solver bantuan.
3. **Ketiadaan Solver Terbukti Nyata:**
   Fakta bahwa run ini berakhir `FAIL` justru mempertegas bahwa ReinDev Studio **tidak memiliki solver tersembunyi / cheat rules** untuk memaksakan PASS pada kasus Flutter. Keberhasilan `ornith:9b` sebelumnya adalah murni kapasitas penalaran representasi simboliknya yang lebih besar (9B parameter).
