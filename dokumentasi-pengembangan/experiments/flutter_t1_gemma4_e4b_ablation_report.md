# Laporan Forensik Eksperimen Ablasi: Komparasi Model Lokal 8B (`gemma4:e4b`) pada Flutter `flutter_t1`

**Tanggal Pelaksanaan:** 2026-09-12T12:37:28 — 12:41:32 WIB  
**ID Eksperimen:** `pv_ablation_dev_r3_gemma4_flutter_t1_rep1_20260912_123728`  
**Task ID:** `flutter_t1` (`lib/card_metric.dart`)  
**Target Bahasa:** Dart (Flutter Material 3 & Riverpod)  
**Evaluated Model:** `gemma4:e4b` (via Ollama lokal, Digest: `c6eb396dbd59`, 9.6 GB, 8.0B parameters, Q4_K_M)  
**Baseline Model:** `qwen2.5-coder:7b` (Ollama lokal)  
**Frontier Model:** `qwen/qwen3-14b` (OpenRouter Cloud)  
**Format-Fragile Model:** `deepseek-coder:6.7b` (Ollama lokal)  
**Treatment Variable:** `REINDEV_TREATMENT_B_R3="1"` (Doktrin #6: Caller Consistency Repair)  
**Status Kontrak Input:** `FROZEN` (SHA-256: `9e2742c8cea664a48873c95772b8472b8ccaf3742c52f4b94a55b21471eddde3`)  
**Integritas Frozen Oracle:** `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` (**100% INTACT Pre & Post Flight**)  

---

## 1. Executive Summary: Matriks Komparasi Quad-Model Terkontrol (`flutter_t1`)

| Metrik / Dimensi | Baseline 7B (`qwen2.5-coder:7b`) | Alternatif 6.7B (`deepseek-coder:6.7b`) | Model 8B (`gemma4:e4b`) | Skala 14B (`qwen/qwen3-14b`) |
| :--- | :--- | :--- | :--- | :--- |
| **Inference Backend** | Ollama (Lokal) | Ollama (Lokal) | Ollama (Lokal) | OpenRouter API (Cloud) |
| **Parameter & Size** | 7.6B (4.7 GB) | 6.7B (3.8 GB) | 8.0B (9.6 GB) | 14.8B (Cloud) |
| **Disiplin Format Tag** | 100% Disiplin | **GAGAL (Kutipan liar)** | **100% Disiplin** | 100% Disiplin |
| **Penetrasi Gate V3** | **Lolos ke Sandbox** | Tertahan di Gate V3 | **Lolos ke Sandbox (3/3)** | **Lolos ke Sandbox** |
| **Turn 0 (Initial)** | GAGAL (`MetricData` missing) | GAGAL (Target file missing) | GAGAL (`MetricData` missing) | GAGAL (`MetricData` missing) |
| **Turn 1 (Repair 1)** | GAGAL (Stagnan, tidak buat kelas) | GAGAL (Scaffold 5 files liar) | **ADAPTIF BERHASIL**: Deklarasi `MetricData` & `data` opsional | **LULUS (2/2 Tests PASS)** (Sintesis 1-Turn) |
| **Turn 2 (Repair 2)** | GAGAL (Stagnan byte-identical) | GAGAL (Keluarkan kode test) | **ADAPTIF BERHASIL**: Tambah `Color? color` | N/A (Sudah PASS di Turn 1) |
| **Akar Hambatan Akhir** | Total Symbolic Blindspot | Format Tag Hallucination | **Residu `required description` + Kuota Habis** | Tidak ada (0 hambatan) |
| **Sandbox Tests Run** | 3 Kali Dieksekusi | 0 Kali (Karantina) | 3 Kali Dieksekusi | 2 Kali Dieksekusi |
| **Final Run Verdict** | **FAIL (Stagnant)** | **FAIL (Format Divergence)** | **FAIL (Stepwise / Partial)** | **PASS (Convergent)** |
| **Durasi Run** | 96.13s | 604.98s | 243.65s | 334.83s |

---

## 2. Analisis Kausal: Trajektori Adaptif Bertahap (*Stepwise Convergence*) `gemma4:e4b`

Hasil pengujian empiris `gemma4:e4b` memberikan wawasan paling menarik dalam riset ablasi ini:

### A. Kualitas Rekayasa & Arsitektur Kode
`gemma4:e4b` menunjukkan pemahaman arsitektur software Flutter tingkat lanjut. Model tidak sekadar meng-hardcode parameter, melainkan mengimplementasikan pola **Dependency Injection hibrida**:
```dart
class CardMetric extends ConsumerWidget {
  final MetricData? data;
  const CardMetric({super.key, this.data});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Gunakan constructor data jika diinjeksi (untuk test), atau watch Riverpod provider (untuk produksi)
    final MetricData metricData = data ?? ref.watch(cardMetricProvider);
    ...
```
Pola ini secara teknis sangat elegan karena memuaskan isolasi testing sekaligus mempertahankan reaktivitas state management Riverpod.

### B. Trajektori Turn-by-Turn yang Progresif
1. **Turn 0 (Initial Scaffold):**
   - Model mendefinisikan `class CardMetricData { final String title; final String value; final String description; ... }`.
   - Sandbox kompilator gagal: `Method not found: 'MetricData'` dan `No named parameter with the name 'data'`.
2. **Turn 1 (Repair Attempt 1 — Respon terhadap B5 CEP & Doktrin #6):**
   - Berbeda dengan Qwen 7B yang stagnan, `gemma4:e4b` membaca error trace secara aktif.
   - Model menulis dokumentasi: `/// Renamed from CardMetricData to MetricData to satisfy external contract (test suite).`
   - Model mendeklarasikan `class MetricData` dan menambahkan parameter `this.data` pada `CardMetric`.
   - Error kompilator bergeser ke parameter berikutnya: `Error: No named parameter with the name 'color'`.
3. **Turn 2 (Repair Attempt 2 — Respon terhadap Error Parameter):**
   - Model kembali merespon feedback kompilator secara presisi: `/// Updated to include 'color' parameter to satisfy deterministic test requirements.`
   - Model menambahkan `final Color? color;` pada `MetricData` dan menggunakannya pada rendering teks: `metricData.color ?? theme.colorScheme.primary`.
   - **Namun**, model mempertahankan parameter bawaan dari Turn 0: `required this.description;`.
   - Karena test suite memanggil `MetricData(title: 'Revenue', value: '1000', color: Colors.blue)` tanpa `description`, kompilator menghasilkan error: `Error: Required named parameter 'description' must be provided.`
   - Kuota 2 kali perbaikan habis (`repair_attempt_counts['developer'] == 2`). Eksekusi berhenti secara deterministik.

---

## 3. Temuan Epistemik Kunci: Spektrum Penalaran Model Terhadap Perbaikan Diagnostik

Eksperimen ini membuktikan adanya spektrum kapasitas model yang terdefinisi secara sangat jelas:

1. **Sub-threshold Symbolic Capacity (Qwen 2.5 Coder 7B):**
   - Mengalami *cognitive blindspot*. Menerima bukti keberadaan `MetricData` pada trace kompilator, namun tidak mampu menyintesis kelas baru tersebut karena scaffold lokalnya sudah memiliki kelas `CardMetricData`. Terjebak dalam stagnasi 100% byte-identical.
2. **Stepwise Incremental Reasoning (Gemma 4 e4b / 8B):**
   - Mampu merespon bukti diagnostik B5 secara bertahap (1 perubahan per putaran).
   - Pada turn 1 berhasil menyintesis kelas, pada turn 2 berhasil menambah field, namun membawa "residu artefak awal" (`required description`) sehingga membutuhkan >2 putaran perbaikan untuk mencapai konvergensi penuh.
3. **Holistic Single-Turn Backward-Inference (Qwen 3 14B):**
   - Melakukan inferensi komprehensif dalam 1 putaran. Menganalisis seluruh call-site orakel, menyintesis kelas sekunder dengan tepat (hanya `title`, `value`, `color`), membuang seluruh asumsi scaffold awal, dan langsung mencapai konvergensi 100% pada Turn 1.

---

## 4. Rekomendasi Arsitektur
1. **Model Deployment:** `gemma4:e4b` terbukti memiliki disiplin format yang sangat tinggi dan kemampuan adaptif yang nyata, namun kuota 2x perbaikan (*universal two-repair budget*) terlalu ketat untuk pola perbaikan bertahap (*stepwise*).
2. **Evaluasi Pipeline:** Jika `gemma4:e4b` digunakan, preskripsi diagnostik B5 dapat ditingkatkan untuk secara eksplisit menyorot parameter yang tidak dipanggil oleh call-site agar model tidak mempertahankan parameter `required` yang usang.
