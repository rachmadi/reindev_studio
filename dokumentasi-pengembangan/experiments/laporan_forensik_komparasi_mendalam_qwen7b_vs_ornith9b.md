# Laporan Investigasi & Audit Forensik Mendalam: Evaluasi Empiris 2 Model Terakhir (Qwen2.5-Coder:7B vs Ornith:9B)

**Tanggal Audit:** 2026-09-14 19:30 WIB  
**Otoritas Investigasi:** Software Architecture & AI Systems Forensic Team  
**Subjek Audit:** 
1. `qwen2.5-coder:7b` (Retest 1×3: `pv_pilot_*_20260914_161731` s.d. `162906`)
2. `ornith:9b` (Retest 1×3 Post-Lifecycle-Repair: `pv_pilot_*_20260914_163859` s.d. `172323`)  
**Metodologi:** Intent-Driven Development (IIDD) — Dual-Lock Acceptance Authority, Deterministic Phase-End Validation (V0–V6), Pre-Flight Gates A–I.

---

## 1. Eksekutif Ringkasan & Matriks Komparatif

Investigasi forensik ini membedah secara menyeluruh setiap event, transisi state, output inferensi LLM, dan log eksekusi runner dari 2 eksperimen terkontrol terakhir yang dijalankan pada dua model *open-weights* lokal: **`qwen2.5-coder:7b`** dan **`ornith:9b`**.

Kedua eksperimen dieksekusi di bawah kondisi pipeline yang **100% identik**:
- **Baseline Suite:** 552/552 Pytest Unit Tests PASS.
- **Dual-Lock Acceptance Authority:** Frozen Acceptance Oracle SHA-256 terverifikasi 100% utuh byte-for-byte sebelum dan sesudah setiap eksperimen.
- **Lifecycle Engine:** Active Validation State Lifecycle v1 aktif (*Persist History & Recompute Active Validity*).
- **Budget Alokasi:** 3 Turn Architect (2 revisi), 5 Loop Developer (10 batas maksimum).

### Matriks Forensik Hasil 6 Run

| Parameter Evaluasi | `qwen2.5-coder:7b` (3 Kasus) | `ornith:9b` (3 Kasus) | Rasio / Komparasi Kualitatif |
|---|---|---|---|
| **FastAPI T1 (`fastapi_t1`)** | **REJECTED (Turn 2)**<br>0 Dev Loops (0/5 PASS) | **FROZEN (Turn 0)**<br>2 Dev Loops (1/5 PASS) | **Ornith Unggul Telak**: Ornith membekukan kontrak pada Turn 0; Qwen gagal melewati Gate V2. |
| **CLI Calculator (`cli_t1`)** | **FROZEN (Turn 2)**<br>5 Dev Loops (0/5 PASS) | **REJECTED (Turn 2)**<br>0 Dev Loops (0/5 PASS) | **Qwen Unggul di Fase Arsitek**: Qwen berhasil merevisi kontrak pada Turn 2; Ornith kehilangan blok JSON terformat. |
| **Flutter Widget (`flutter_t1`)** | **REJECTED (Turn 2)**<br>0 Dev Loops (0/2 PASS) | **FROZEN (Turn 1)**<br>5 Dev Loops (0/1 PASS) | **Ornith Unggul Telak**: Bukti empiris keberhasilan eliminasi *Ghost Stale Error*; Ornith masuk ke sandbox Dart. |
| **Tingkat Kontrak Beku (Freezing Rate)** | **1 / 3 (33.3%)** | **2 / 3 (66.7%)** | **Ornith 2× Lebih Tinggi (Pelipatgandaan Tingkat Pembekuan Kontrak)** |
| **Total Pengujian Lolos di Sandbox** | 0 passed | **1 test passed** (`test_delete_nonexistent_product`) | Kemajuan fungsional pertama pada level sandbox tercapai oleh Ornith. |
| **Total Waktu Komputasi Inferensi** | 883,45 detik (~14,7 menit) | 3.984,64 detik (~66,4 menit) | Ornith membutuhkan komputasi ~4.5× lebih lama akibat kedalaman token dan loop sandbox. |

---

## 2. Pembedahan Kasus per Kasus: Dimana Masalah & Apa Penyebabnya?

---

### KASUS 1: `fastapi_t1` (FastAPI Product Inventory CRUD)

#### A. Pada Model `qwen2.5-coder:7b` (Status: REJECTED pada Turn 2)
- **Gejala:** Pipeline terhenti total di Gate V2 tanpa satupun baris kode Developer dieksekusi di sandbox (`loops_consumed: 0`).
- **Rekonstruksi Forensik per Turn:**
  - **Turn 0 (Event 7):** Model menghasilkan teks blueprint JSON. Parsing gagal seketika dengan error:
    ```
    SCHEMA_VIOLATION: Blueprint JSON parse failure: Gagal mendekode JSON blueprint: 
    Expecting ',' delimiter: line 24 column 54 (char 710)
    ```
    *Penyebab:* Model 7B mengalami *token emission truncation* pada deklarasi field schema Pydantic, melupakan karakter koma pemisah antar-properti.
  - **Turn 1 (Event 12):** Model menerima umpan balik perbaikan dari validator. Pada iterasi ini, model kembali menghasilkan JSON yang rusak:
    ```
    SCHEMA_VIOLATION: Blueprint JSON parse failure: Gagal mendekode JSON blueprint: 
    Expecting ',' delimiter: line 27 column 50 (char 914)
    ```
  - **Turn 2 (Event 17 & 18):** Pada turn terakhir, model berhasil memperbaiki struktur sintaksis JSON sehingga parser berhasil membaca objek blueprint. Namun, saat Gate V2 mengevaluasi konsistensi kontrak terhadap Acceptance Authority (Frozen Oracle), terdeteksi pelanggaran fatal Pilar 4:
    ```
    ORACLE_OBLIGATION: HTTP GET /products
    CONTRACT_DECLARED_INTERFACES: ['Product', 'add_product', 'delete_product']
    CONTRACT_COVERAGE: MISSING
    DIAGNOSIS: HTTP endpoint '/products' declared with method(s) ['POST', 'DELETE'], 
    but expected method [GET] is missing from contract
    RESULT: INCOMPATIBLE — CONTRACT MUST NOT FREEZE
    ```
- **Akar Masalah (Root Cause):**
  1. *Keterbatasan Sintaksis (Turn 0–1):* Model 7B kesulitan mempertahankan integritas sintaksis JSON saat menghasilkan skema RESTful multi-file yang panjang.
  2. *Upstream Requirement Omission (Turn 2):* Model tidak menyertakan operasi pembacaan `GET /products` ke dalam deklarasi antarmuka, hanya mendeklarasikan `POST` dan `DELETE`. Sesuai doktrin *Hierarchy-of-Authority*, Gate V2 menolak pembekuan kontrak yang tidak lengkap secara deterministik.

---

#### B. Pada Model `ornith:9b` (Status: FROZEN pada Turn 0 $\to$ FAIL pada Developer Loop 2)
- **Gejala:** Arsitek berhasil 100% pada Turn 0 dan membekukan kontrak resmi. Namun, fase Developer gagal mencapai konvergensi di sandbox setelah 2 loop.
- **Rekonstruksi Forensik per Turn & Loop:**
  - **Turn 0 Architect (Event 7):** Ornith-9B menghasilkan blueprint JSON sempurna tanpa kesalahan sintaksis, mencakup seluruh 4 obligasi Oracle (`POST /products`, `GET /products`, `GET /products/{id}`, `DELETE /products/{id}`). Kontrak **langsung FROZEN** pada giliran pertama (`seal_success: True`).
  - **Developer Loop 0 (Event 18):** Developer menghasilkan implementasi awal `main.py`. Kode dieksekusi di runner Pytest sandbox dengan hasil: **1 PASSED, 4 FAILED (20% PASS)**.
    - `test_delete_nonexistent_product` $\to$ **PASSED** (HTTP 404).
    - `test_create_product` $\to$ **FAILED: `assert 422 == 201`**.
    - `test_get_all_products` $\to$ **FAILED: `assert 0 >= 1`**.
    - `test_get_product_by_id` $\to$ **FAILED: `assert 422 == 201`**.
    - `test_delete_product` $\to$ **FAILED: `assert 422 == 201`**.
    *Penyebab Kegagalan Sandbox:* Terjadi *Schema Validation Error* (HTTP 422 Unprocessable Entity). Model Pydantic `Product` buatan Developer mewajibkan field yang tidak dikirim oleh Frozen Oracle runner, atau terdapat perbedaan tipe data sehingga FastAPI melempar 422.
  - **Developer Loop 1 (Event 27 & 29):** Developer menerima feedback diagnostik HTTP 422. Alih-alih menyesuaikan schema `Product` (misal membuat field opsional atau menambahkan default value), model mengalami **Hyper-Mutation / Architectural Drifting**:
    Developer menghapus fungsi endpoint top-level (`create_product`, `list_products`, `get_product`, `delete_product`) dan menggantinya dengan kelas storage stateful `class InventoryStore` dengan metode `get_all`, `get_by_id`, `quantity_non_negative`.
  - **Pencegahan oleh Gate B3 (Event 29):**
    Gate B3 (`developer_validation`) melakukan audit kepatuhan statis terhadap kontrak beku sebelum eksekusi sandbox. Gate mendeteksi pelanggaran kritis:
    ```
    VIOLATION: contract_symbols_conformance (CRITICAL)
    Message: Antarmuka mandatory kontrak tidak dideklarasikan: 
             ['list_products', 'create_product', 'get_product', 'delete_product']
    Location: main.py
    ```
    Gate B3 mengarantina eksekusi sandbox guna mencegah pemborosan siklus uji. Developer mengulang mutasi yang sama pada Loop 2 hingga batas anggaran habis.
- **Akar Masalah (Root Cause):**
  1. *Pydantic Payload Mismatch (Loop 0):* Ketidaksesuaian field wajib pada model Pydantic terhadap payload yang dikirim oleh test runner Acceptance Oracle.
  2. *Architectural Drifting Under Repair Stress (Loop 1–2):* Di bawah tekanan error 422, model Developer mengabaikan batasan antarmuka kontrak yang telah dibekukan dan melakukan refactor sepihak ke pola OOP internal (`InventoryStore`), yang secara sah ditolak oleh Gate B3.

---

### KASUS 2: `cli_t1` (CLI Matrix Operations Calculator)

#### A. Pada Model `qwen2.5-coder:7b` (Status: FROZEN pada Turn 2 $\to$ FAIL pada Developer Loop 5)
- **Gejala:** Arsitek berhasil memulihkan kontrak hingga `FROZEN` pada Turn 2. Namun, Developer mengalami kegagalan total 0/5 PASS di sandbox sepanjang 5 loop.
- **Rekonstruksi Forensik per Turn & Loop:**
  - **Turn 0–1 Architect:** Turn 0 gagal karena deklarasi simbol belum lengkap. Turn 1 memperbaiki relasi simbol. Pada **Turn 2 (Event 18)**, kontrak berhasil mencakup seluruh obligasi `Matrix`, `add_matrices`, `subtract_matrices`, `multiply_matrices` $\to$ Status **`FROZEN`**.
  - **Developer Loop 0 s.d. Loop 5 (Event 30, 47, 64):**
    Developer menulis kode implementasi di `main.py`. Eksekusi sandbox Pytest langsung mengalami crash seketika di baris pertama setiap fungsi uji:
    ```python
    def test_matrix_addition():
    >   m1 = Matrix([[1, 2], [3, 4]])
    E   TypeError: BaseModel.__init__() takes 1 positional argument but 2 were given
    test_main.py:6: TypeError
    ```
    Seluruh 5 test case (`test_matrix_addition`, `test_matrix_subtraction`, `test_matrix_multiplication`, `test_matrix_addition_incompatible_dimensions`, `test_matrix_multiplication_incompatible_dimensions`) gagal 100% dengan `TypeError` yang identik.
- **Akar Masalah (Root Cause):**
  - *Cross-Domain Archetype Hallucination (Halusinasi Arketipe Lintas Domain):*
    Meskipun task adalah kalkulator matematika CLI murni, model `qwen2.5-coder:7b` mengimpor `from pydantic import BaseModel` dan mendeklarasikan:
    ```python
    class Matrix(BaseModel):
        data: list[list[int]]
    ```
    Pada Pydantic v2, konstruktor `BaseModel.__init__()` hanya menerima *keyword arguments* (`Matrix(data=[[...]])`). Sementara itu, pemanggil Frozen Acceptance Oracle memanggil konstruktor dengan *positional argument* (`Matrix([[1, 2], [3, 4]])`).
  - *Semantic Stagnation Loop:* Model 7B tidak memahami akar penyebab `TypeError: BaseModel.__init__() takes 1 positional argument`, dan berulang kali menghasilkan variasi kode yang tetap mewarisi `BaseModel` selama 5 loop penuh.

---

#### B. Pada Model `ornith:9b` (Status: REJECTED pada Turn 2)
- **Gejala:** Arsitek gagal membekukan kontrak resmi (`loops_consumed: 0`).
- **Rekonstruksi Forensik per Turn:**
  - **Turn 0 (Event 7 & 8):** Arsitek mendeklarasikan antarmuka:
    `['Matrix', 'add_matrices', 'health', 'multiply_matrices']`.
    Namun, Arsitek **mengabaikan operasi pengurangan** (`subtract_matrices`). Gate V2 mendeteksi:
    ```
    ORACLE_OBLIGATION: Callable symbol 'subtract_matrices'
    CONTRACT_COVERAGE: MISSING
    DIAGNOSIS: Callable symbol/interface 'subtract_matrices' is missing from contract interface_contracts
    RESULT: INCOMPATIBLE — CONTRACT MUST NOT FREEZE
    ```
  - **Turn 1 (Event 11 & 12):** Validator mengirimkan paket Contextual Evidence Package (CEP) yang merinci kewajiban `subtract_matrices`. Model Ornith-9B melakukan inferensi selama **4 menit 22 detik** (262 detik). Namun, output teks yang dihasilkan **tidak memuat blok markdown ````json ... ````**, melainkan teks analisis obrolan biasa:
    ```
    SCHEMA_VIOLATION: Blueprint JSON parse failure: 
    Tidak ditemukan blok JSON blueprint yang valid dalam teks input
    ```
  - **Turn 2 (Event 16 & 17):** Kejadian serupa berulang. Model kembali melakukan inferensi selama 262 detik dan menghasilkan teks tanpa format JSON yang valid. Budget 2 revisi habis $\to$ Kontrak resmi dinyatakan ditolak (**`REJECTED`**).
- **Akar Masalah (Root Cause):**
  1. *Omission Awal (Turn 0):* Arsitek melewatkan salah satu operasi aritmatika dasar (`subtract_matrices`).
  2. *Instruction-Following Breakdown under Context Pressure (Turn 1–2):* Ketika menerima prompt perbaikan yang panjang berisi pelanggaran skema, model 9B beralih mode dari *structured JSON emitter* menjadi *conversational explanatory mode*, menghilangkan blok kode JSON terstruktur.

---

### KASUS 3: `flutter_t1` (Flutter CardMetric Widget)

#### A. Pada Model `qwen2.5-coder:7b` (Status: REJECTED pada Turn 2)
- **Gejala:** Arsitek gagal menuntaskan kontrak yang konsisten dengan Acceptance Oracle.
- **Rekonstruksi Forensik per Turn:**
  - **Turn 0 (Event 5 & 6):** Arsitek mendeklarasikan antarmuka `['CardMetric', 'CardMetricWidget']`, tetapi tidak mendeklarasikan model data `MetricData` yang dituntut oleh Frozen Oracle. Gate V2 menolak.
  - **Turn 1 (Event 10 & 11):** Arsitek menambahkan `MetricData`, namun secara keliru memasukkan berkas pengujian Oracle ke dalam pohon berkas blueprint (`file_tree: ['test/card_metric_test.dart']`) tanpa scaffold files. Ini memicu Pydantic Schema Validation Error di Gate V2.
  - **Turn 2 (Event 15 & 16):** Arsitek memperbaiki error skema, namun mengalami **Attention Drift / Interface Regression**:
    Arsitek mendeklarasikan widget dengan nama `CardMetricWidget` dan entitas `MetricData`. Padahal call-site Acceptance Oracle pada `test/card_metric_test.dart` secara eksplisit memanggil widget `CardMetric`:
    ```
    ORACLE_OBLIGATION: Widget/Model 'CardMetric'
    CONTRACT_DECLARED_INTERFACES: ['CardMetricWidget', 'MetricData']
    CONTRACT_COVERAGE: MISSING
    DIAGNOSIS: Observable runtime component/widget 'CardMetric' is not declared in interface_contracts
    RESULT: INCOMPATIBLE — CONTRACT MUST NOT FREEZE
    ```
- **Akar Masalah (Root Cause):**
  - *Cognitive Attention Drift:* Model 7B tidak mampu mempertahankan kepatuhan simultan terhadap nama widget (`CardMetric`) dan model data pendukung (`MetricData`). Ketika memperbaiki `MetricData`, model mengubah nama widget menjadi `CardMetricWidget`.

---

#### B. Pada Model `ornith:9b` (Status: FROZEN pada Turn 1 $\to$ FAIL pada Developer Loop 5)
- **Gejala:** Kontrak berhasil dibekukan pada Turn 1, namun fase perbaikan Developer gagal menyelesaikan kesalahan kompilasi Dart di sandbox setelah 5 loop.
- **Rekonstruksi Forensik per Turn & Loop:**
  - **Turn 0 Architect (Event 7 & 8):** Arsitek awal ditolak karena `MetricData` belum lengkap.
  - **Turn 1 Architect (Event 12 & 13) — Pembuktian Epistemik Lifecycle v1:**
    Pada giliran kedua, Arsitek merevisi kontrak dan berhasil mencakup 100% kewajiban Oracle (`CardMetric` dan `MetricData`).
    Engine Active Validation Lifecycle v1 menginisialisasi `active_validation_errors = []`, mengarsipkan 2 error lama ke `validation_history`, dan menjalankan deterministik check segar:
    $$\text{active\_error\_count} = 0, \quad \text{historical\_error\_count} = 2, \quad \text{uncovered} = 0 \implies \mathbf{FROZEN!}$$
    **Temuan:** Kontrak berhasil dibekukan tanpa terblokir oleh bug residual *Ghost Stale Error*.
  - **Developer Loop 0 s.d. Loop 5 (Event 32, 49, 66):**
    Developer menulis implementasi di `lib/card_metric.dart`. Runner `flutter test` di sandbox gagal kompilasi pada seluruh 5 loop:
    ```dart
    lib/card_metric.dart:21:15: Error: Member not found: 'cpu'.
    lib/card_metric.dart:37:17: Error: Member not found: 'cpu'.
    test/card_metric_test.dart:14:32: Error: No named parameter with the name 'title'.
    lib/card_metric.dart:10:9: Context: Found this candidate, but the arguments don't match.
    test/card_metric_test.dart:14:15: Error: No named parameter with the name 'data'.
    lib/card_metric.dart:43:9: Context: Found this candidate, but the arguments don't match.
    ```
    Developer mengalami disonansi antarmuka konstruktor:
    1. Widget `CardMetric` mengharapkan parameter bernama `icon` atau konstruktor dengan signature berbeda dari pemanggilan tes (`title: ..., data: ...`).
    2. Kode Developer mencoba mengakses getter `.cpu` pada objek metrik, padahal model data hanya memiliki properti generic seperti `value` atau `label`.
    Meskipun dieksekusi selama 5 loop, Developer gagal menyelaraskan signature konstruktor widget Dart terhadap pemanggilan tes Acceptance Oracle.
- **Akar Masalah (Root Cause):**
  - *Constructor Signature Incompatibility:* Ketidakcocokan antara argumen bernama (*named parameters*) pada konstruktor widget buatan Developer dengan call-site acceptance test. Model 9B tidak mampu menyimpulkan struktur parameter yang diharapkan dari error diagnostik kompiler Dart.

---

## 3. Analisis Komparasi Lintas Model: 7B vs 9B

### 1. Kapasitas Penalaran Arsitektur (Architect-Level Reasoning)
- **Struktur JSON Kompleks:** Ornith-9B memiliki kapasitas superior dalam menyusun struktur data bertingkat (berhasil membekukan 2 dari 3 kontrak, 66.7%). Qwen-7B sering menghasilkan JSON cacat sintaksis (koma hilang, delimiter rusak).
- **Stabilitas Instruksional:** Ornith-9B rentan kehilangan kepatuhan format saat menerima prompt perbaikan yang sangat panjang pada kasus CLI (berubah menjadi respons obrolan), sedangkan Qwen-7B tetap mempertahankan format JSON meskipun isinya salah.

### 2. Patologi Eksekusi Developer (Developer-Level Execution)
- **Kontaminasi Domain (Domain Contamination):** Qwen-7B sangat rentan mencampuradukkan domain (mengimpor Pydantic ke CLI). Ornith-9B bersih dari kontaminasi ini.
- **Respon terhadap Kegagalan (Failure Reaction):**
  - Qwen-7B cenderung mengalami **stagnasi pasif** (menghasilkan kode yang hampir identik berulang-ulang).
  - Ornith-9B cenderung mengalami **mutasi agresif / architectural drifting** (merombak arsitektur fungsional menjadi class OOP internal saat menghadapi HTTP 422, sehingga memicu intervensi Gate B3).

---

## 4. Evaluasi Sistemik Arsitektur ReinDev Studio

1. **Integritas Dual-Lock Acceptance Authority: 100% Efektif**
   Sepanjang seluruh pengujian pada kedua model, hash SHA-256 Frozen Acceptance Oracle tidak pernah termutasi sedikitpun (100% byte-for-byte match). Acceptance Authority tetap menjadi otoritas tertinggi yang tidak dapat diintervensi oleh model.

2. **Validasi Siklus Hidup (Active Validation Lifecycle v1): Terbukti Sukses**
   Pengujian membuktikan bahwa pemisahan `validation_history` (audit trail) dan `active_validation_errors` (recomputed fresh) berhasil 100%. Pada kasus `flutter_t1` (Ornith-9B), Turn 1 yang sebelumnya dijamin gagal oleh Ghost Stale Error kini berhasil `FROZEN` seketika.

3. **Titik Lemah Sistemik yang Terungkap (Systemic Gaps):**
   - *Ketiadaan Schema Invariant pada Developer Loop:* Saat menghadapi kegagalan runtime (seperti 422 di FastAPI), Developer belum dibekali batasan bahwa antarmuka kontrak yang telah dibekukan tidak boleh dirombak menjadi arsitektur class OOP internal.
   - *Umpan Balik Parameter Konstruktor Dart:* Harvester diagnostik Dart perlu memperjelas ekstraksi parameter yang diharapkan dari call-site pengujian untuk mencegah disonansi parameter named vs positional.

---

## 5. Kesimpulan & Rekomendasi Tindak Lanjut

1. **Kesimpulan Ilmiah:**
   - Kegagalan pengujian pada kedua model tidak disebabkan oleh kebocoran sistem atau bug pada lifecycle validator (yang terbukti bekerja 100% deterministik), melainkan murni bersumber dari **keterbatasan kapasitas representasi dan penalaran model lokal (7B dan 9B)** dalam menyeimbangkan kepatuhan multi-kendala secara simultan.
   - Peningkatan kapasitas model dari 7B ke 9B melipatgandakan *contract freezing rate* dari **33.3% menjadi 66.7%**, membuktikan bahwa kapasitas model adalah faktor determinan utama dalam pemenuhan kontrak arsitektur hulu.

2. **Rekomendasi Langkah Berikutnya bagi Intent Architect:**
   - **Rekomendasi 1 (Prompt Hardening B3 - Anti-Drift Guard):** Menambahkan klausul eksplisit pada prompt perbaikan Developer: *"When fixing runtime or test assertion failures, you MUST preserve all existing top-level function names and signatures defined in the frozen contract. Do NOT refactor top-level functions into internal class methods."*
   - **Rekomendasi 2 (Constructor Signature Diagnostic Enhancement):** Memperkuat preskripsi B5 untuk compiler error Dart `No named parameter with the name 'X'` agar secara eksplisit memancarkan daftar parameter yang diharapkan oleh call-site pengujian.
   - **Rekomendasi 3 (Evaluasi Model Frontier):** Mempertimbangkan pengujian pada model yang lebih tinggi (misal Qwen-2.5-Coder-32B atau model frontier API) untuk membuktikan apakah pipeline deterministik ReinDev Studio mencapai konvergensi 100% ketika cognitive ceiling model dilipatgandakan.
