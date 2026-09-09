# CODE_ONLY Experiment Investigation

**Tanggal Investigasi:** 2026-09-08  
**Waktu Investigasi:** 22:20 WIB  
**Evaluator:** Intent Architect & Forensic AI Assistant  
**Lingkungan Sistem:** ReinDev Studio (Backend FastAPI port 8000, Frontend Web port 8086, Model Ollama `qwen2.5-coder:7b`)  
**Metode Analisis:** Non-Invasive Read-Only Forensic Analysis berbasis `run_trace.jsonl` dan artefak disk  
**Prinsip Verifikasi:** Tidak ada modifikasi kode aplikasi/prompt/test/konfigurasi, pemisahan tegas antara Fakta Terobservasi, Pola, dan Hipotesis/Interpretasi.

---

## 1. Run Identification

Tiga run eksperimen mode `CODE_ONLY` terbaru telah diidentifikasi dan diverifikasi dari direktori `backend/output`:

### 1.1 FastAPI CRUD
- **Run ID:** `project_20260908_215919`
- **Timestamp Mulai:** 2026-09-08T21:59:19.172218 (21:59:19 WIB)
- **Timestamp Selesai:** 2026-09-08T22:01:20.120509 (22:01:20 WIB)
- **Total Duration:** 120.94 detik
- **Model:** `qwen2.5-coder:7b` (Provider: `ollama`)
- **Target Language:** Python
- **Executor Mode:** `CODE_ONLY` (`executor_intervention_enabled: True`)
- **Max Iterations:** 3
- **Final Iteration / Repair Loops:** 0 (1 eksekusi langsung lulus, 0 repair loop)
- **Final Status:** `completed`
- **Final Test Result:** PASSED (exit code 0, 2/2 tests passed)
- **Reviewer Status:** APPROVED (`is_approved: True`)

### 1.2 Flutter Widget
- **Run ID:** `project_20260908_220147`
- **Timestamp Mulai:** 2026-09-08T22:01:47.845384 (22:01:47 WIB)
- **Timestamp Selesai:** 2026-09-08T22:05:14.624906 (22:05:14 WIB)
- **Total Duration:** 206.77 detik
- **Model:** `qwen2.5-coder:7b` (Provider: `ollama`)
- **Target Language:** Dart / Flutter
- **Executor Mode:** `CODE_ONLY` (`executor_intervention_enabled: True`)
- **Max Iterations:** 3
- **Final Iteration / Repair Loops:** 3 (mencapai batas maksimum 3 repair loop)
- **Final Status:** `needs_revision`
- **Final Test Result:** FAILED (exit code 1, kompilasi test runner gagal pada seluruh iterasi)
- **Reviewer Status:** NOT APPROVED (`is_approved: False`)

### 1.3 CLI Calculator
- **Run ID:** `project_20260908_220528`
- **Timestamp Mulai:** 2026-09-08T22:05:28.844645 (22:05:28 WIB)
- **Timestamp Selesai:** 2026-09-08T22:10:11.097909 (22:10:11 WIB)
- **Total Duration:** 282.25 detik
- **Model:** `qwen2.5-coder:7b` (Provider: `ollama`)
- **Target Language:** Python
- **Executor Mode:** `CODE_ONLY` (`executor_intervention_enabled: True`)
- **Max Iterations:** 3
- **Final Iteration / Repair Loops:** 3 (mencapai batas maksimum 3 repair loop)
- **Final Status:** `needs_revision`
- **Final Test Result:** FAILED (exit code 1: Iter 0 = 1/11 pass, Iter 1 = 1/11 pass, Iter 2 = 2/11 pass)
- **Reviewer Status:** NOT APPROVED (`is_approved: False`)

---

## 2. Experiment Integrity Verification

Mode `CODE_ONLY` mewajibkan aturan ketat: **Executor boleh memodifikasi `code_files`, tetapi DILARANG KERAS memodifikasi atau menambah `test_files` dalam bentuk apa pun.**

Berdasarkan inspeksi forensik pada berkas `run_trace.jsonl`:

| Run ID | Preset Misi | Iterasi | `executor_mode` | `test_before_hash == test_after_hash` | `test_files_modified` | `test_files_added` | Status Integritas |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `project_20260908_215919` | FastAPI CRUD | 0 | `CODE_ONLY` | **True** (`8b1d69b3...` == `8b1d69b3...`) | `[]` (kosong) | `[]` (kosong) | **VALID (100% Intact)** |
| `project_20260908_220147` | Flutter Widget | 0 | `CODE_ONLY` | **True** (`49ec7b58...` == `49ec7b58...`) | `[]` (kosong) | `[]` (kosong) | **VALID (100% Intact)** |
| | | 1 | `CODE_ONLY` | **True** (`49ec7b58...` == `49ec7b58...`) | `[]` (kosong) | `[]` (kosong) | **VALID (100% Intact)** |
| | | 2 | `CODE_ONLY` | **True** (`49ec7b58...` == `49ec7b58...`) | `[]` (kosong) | `[]` (kosong) | **VALID (100% Intact)** |
| `project_20260908_220528` | CLI Calculator | 0 | `CODE_ONLY` | **True** (`02530af4...` == `02530af4...`) | `[]` (kosong) | `[]` (kosong) | **VALID (100% Intact)** |
| | | 1 | `CODE_ONLY` | **True** (`02530af4...` == `02530af4...`) | `[]` (kosong) | `[]` (kosong) | **VALID (100% Intact)** |
| | | 2 | `CODE_ONLY` | **True** (`02530af4...` == `02530af4...`) | `[]` (kosong) | `[]` (kosong) | **VALID (100% Intact)** |

### Kesimpulan Integritas:
1. Seluruh run mencatat `executor_mode: CODE_ONLY`.
2. Pada seluruh iterasi di ketiga run (total 7 eksekusi sandbox), `test_files_before_hashes` identik 100% karakter demi karakter dengan `test_files_after_hashes`.
3. `test_transformations` (`test_files_modified` dan `test_files_added`) bernilai list kosong `[]` pada seluruh event.
4. Mekanisme *fail-loudly assertion* di `executor.py` (`tests_before_hash == tests_after_hash`) tidak pernah terpicu, membuktikan tidak ada modifikasi test tersembunyi.
5. **Integritas eksperimen CODE_ONLY terverifikasi sah dan valid.**

---

## 3. FastAPI Analysis

### 3.1 Detail Alur Run `project_20260908_215919`
- **Developer Input (Iterasi 0):** Menghasilkan `main.py` (839 karakter, hash `87d689f17070`).
- **Tester Output (Iterasi 0):** Menghasilkan `test_main.py` (798 karakter, hash `8b1d69b3d420`).
  - Tes menguji `test_add_product`: payload `{"name": "Laptop", "quantity": 10}` tanpa mengirimkan field `id`. Assertion: `assert response.status_code == 201`.
  - Tes menguji `test_delete_product`: payload `{"name": "Mouse", "quantity": 50}` tanpa `id`. Assertion: `assert response.status_code == 201`, `assert response.status_code == 204`, `assert response.status_code == 404`.

### 3.2 Intervensi Kode oleh Executor
Executor melakukan modifikasi in-place pada `main.py` (hash `87d689f17070` → `16f6e94e66c1`):
```diff
--- before_exec/main.py
+++ after_exec/main.py
@@ -9,7 +9,7 @@
 # Pydantic model
 class Product(BaseModel):
-    id: int
+    id: int | None = None
     name: str
     quantity: int

@@ -24,7 +24,21 @@
 def delete_product(product_id: int):
     global products
     initial_len = len(products)
-    products = [product for product in products if product.id != product_id]
+    products[:] = [product for product in products if product.id != product_id]
     if len(products) == initial_len:
         raise HTTPException(status_code=404, detail='Product not found')
-    return {"detail": "Product deleted"}
+    return {"detail": "Product deleted"}
+
+    @app.get("/products/{product_id}")
+    def get_product(product_id: int):
+        for p in products:
+            p_id = getattr(p, 'id', None) if not isinstance(p, dict) else p.get('id')
+            if p_id == product_id:
+                return p
+        raise HTTPException(status_code=404, detail="Product not found")
+
+    @app.get("/products")
+    @app.get("/products/")
+    def get_all_products():
+        return products
```

### 3.3 Hasil Pengujian & Temuan Signifikan
- Pytest dijalankan pada kode yang telah ditransformasi Executor dan berkas test asli QA Tester (`test_main.py` tidak diubah sama sekali).
- **Hasil:** `2 passed, 1 warning in 0.31s` (exit code 0).
- **Mengapa Lulus Tanpa Mengubah Test?**
  - Pada mode OFF (`210254`), Developer mendefinisikan `id: int` (field wajib tanpa default). Saat Tester mengirim payload `{"name": "Laptop", "quantity": 10}`, FastAPI menolak request dengan HTTP 422 Unprocessable Entity, sehingga gagal pada `assert response.status_code == 201`.
  - Pada mode CODE_ONLY, transformasi Executor mengubah `id: int` menjadi `id: int | None = None`. Request dari Tester kini valid di sisi FastAPI, payload diproses, status 201 dikembalikan, dan list mutasi in-place berjalan benar.
  - **Temuan Kritis:** Keberhasilan FastAPI pada CODE_ONLY tercapai **murni dari perbaikan implementasi kode aplikasi**, bukan karena relaksasi oracle pengujian.

---

## 4. Flutter Analysis

### 4.1 Detail Alur Run `project_20260908_220147`
- **Tester Output:** Menghasilkan `test/card_metric_test.dart` (743 karakter, hash `49ec7b5870a9`).
  - Tes menguji rendering `CardMetric` dengan teks dan ikon standar.
- **Developer Output (Iterasi 0):** Menghasilkan `lib/card_metric.dart` (1532 karakter, hash `c7bb29a2e055`).
  - Mengandung sintaks Material 2 yang usang: `Theme.of(context).textTheme.headline6` dan `Theme.of(context).textTheme.headline5`.

### 4.2 Intervensi Executor vs Kegagalan Kompilasi
- Pada Iterasi 0, Executor mentransformasikan `lib/card_metric.dart` (hash `c7bb29a2e055` → `ef502915f4b8`) dengan menambahkan stub `StateNotifier` dan mengubah instansiasi `metricProvider`.
- Namun Executor **tidak menangani** getter deprecated `headline6` dan `headline5`.
- **Hasil `flutter test` (Iterasi 0):** Exit code 1 (kompilasi gagal):
  ```
  lib/card_metric.dart:54:67: Error: The getter 'headline6' isn't defined for the type 'TextTheme'.
  lib/card_metric.dart:55:86: Error: The getter 'headline5' isn't defined for the type 'TextTheme'.
  ```

### 4.3 Rekonstruksi Repair Loop Developer (Iterasi 1 & 2)
- **Iterasi 1:**
  - Developer menerima `test_results` yang memuat error kompilasi TextTheme.
  - Output Developer: Developer menghasilkan `lib/card_metric.dart` (hash `ef502915f4b8`) dan **mencoba meng-output berkas `test/card_metric_test.dart`** (hash `b6bad875b7b4`).
  - Karena mode `CODE_ONLY`, Executor menolak/mengabaikan perubahan pada berkas test. Berkas test tetap memakai hash Tester asli (`49ec7b5870a9`).
  - Developer **tetap mempertahankan** `headline6` dan `headline5` di dalam `card_metric.dart`.
  - Eksekusi test tetap gagal kompilasi dengan error yang sama persis.
- **Iterasi 2:**
  - Developer menghasilkan `lib/card_metric.dart` baru (hash `5116ed2c4c27`), tetapi **masih tetap memuat `headline6` dan `headline5`**.
  - Eksekusi test tetap gagal kompilasi (exit code 1). Misi berakhir `needs_revision`.

---

## 5. CLI Analysis

### 5.1 Detail Alur Run `project_20260908_220528`
- **Tester Output:** Menghasilkan `test_main.py` (2253 karakter, hash `02530af4d34d`).
  - Terdapat 11 fungsi tes (`test_add_matrices`, `test_subtract_matrices`, `test_multiply_matrices`, dll.).
  - **Defek pada Kode QA Tester:** Pada baris impor `test_main.py`, Tester menulis:
    `from main import add_matrices, subtract_matrices, multiply_matrices, divide_matrices, parse_matrix`
    Namun di dalam badan setiap fungsi pengujian, Tester menulis:
    `matrix1 = Matrix(data=[[1, 2], [3, 4]])`
    Tester **tidak mengimpor class `Matrix` dari `main`**!

### 5.2 Intervensi Executor vs Hasil Pengujian
- **Iterasi 0:**
  - Developer menghasilkan `main.py` (hash `876f7974cb96`).
  - Executor mentransformasi fungsi `parse_matrix` pada `main.py` (hash `876f7974cb96` → `40fa3dbbed67`).
  - `test_files` tidak diubah (`02530af4d34d`).
  - Hasil pytest: Exit code 1 (`1 passed, 10 failed in 0.23s`).
  - Penyebab 10 kegagalan: **`NameError: name 'Matrix' is not defined`** di dalam `test_main.py`! Satu-satunya tes yang lulus adalah `test_parse_matrix_invalid_value` yang tidak memanggil constructor `Matrix`.

### 5.3 Rekonstruksi Repair Loop Developer (Iterasi 1 & 2)
- **Iterasi 1:**
  - Developer menerima traceback `NameError: name 'Matrix' is not defined` pada `test_main.py`.
  - Respons Developer: Developer berhalusinasi menghasilkan berkas baru `module_1.py` (hash `acc738a132f1`) dan tidak mengubah `main.py`.
  - Executor mentransformasi `parse_matrix` di `module_1.py`.
  - Hasil pytest: Tetap 1 passed, 10 failed karena `test_main.py` tetap tidak mengenali `Matrix`.
- **Iterasi 2:**
  - Developer memodifikasi `main.py` (hash `f5e660d5135d`).
  - Executor mentransformasi `parse_matrix` di `main.py` (hash menjadi `33700f0b1adc`).
  - Hasil pytest: 2 passed (`test_parse_matrix` kini lulus berkat transformasi Executor + `test_parse_matrix_invalid_value`), 9 failed (seluruh operasi matriks tetap gagal `NameError: Matrix`).
- **Analisis Kritis Oracle Freeze:** Karena mode `CODE_ONLY` membekukan berkas test, bug impor di sisi Tester tidak dapat diperbaiki oleh Executor. Developer juga tidak mampu mengatasi bug yang berada di dalam berkas test, sehingga run terkunci pada status `needs_revision`.

---

## 6. ON vs CODE_ONLY vs OFF Comparison

### 6.1 Matriks Komparasi Tripartit Utama (12 Run Lintas 4 Set)

| Preset Misi | Metrik | OFF (Set 3) | CODE_ONLY (Set 4) | ON (Set 2 / Set 1) |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI CRUD** | **Final Status** | `needs_revision` | **`completed`** | **`completed`** |
| | **Test Result** | FAILED (exit 1, 2/3 fail) | **PASSED (exit 0, 2/2 pass)** | **PASSED (exit 0, 3/3 pass)** |
| | **Reviewer Result** | NOT APPROVED | **APPROVED** | **APPROVED** |
| | **Repair Loops** | 3 loops | **0 loops** | **0 loops** |
| | **Total Duration** | 179.31s | **120.94s** | 128.51s / 96.86s |
| | **Code Intervention** | 0 (Nol) | **1 file (`main.py`)** | 1 file (`main.py`) |
| | **Test Intervention** | 0 (Nol) | **0 (NOL / Freeze)** | 1 file (`test_main.py`) |
| | **Failure Type** | HTTP 422 vs assert 201 | **None (Lulus)** | None (Lulus) |
| | **Konvergensi** | Non-konvergen (stagnan) | **Konvergen instan (Iter 0)** | Konvergen instan (Iter 0) |
| **Flutter Widget** | **Final Status** | `needs_revision` | `needs_revision` | `needs_revision` / `completed`* |
| | **Test Result** | FAILED (exit 1) | FAILED (exit 1) | FAILED (exit 1) / PASSED* |
| | **Reviewer Result** | NOT APPROVED | NOT APPROVED | NOT APPROVED / APPROVED* |
| | **Repair Loops** | 3 loops | 3 loops | 3 loops / 0 loops* |
| | **Total Duration** | 192.30s | 206.77s | 184.05s / 129.17s* |
| | **Code Intervention** | 0 (Nol) | 1 file (`lib/card_metric.dart`) | 1 file (`lib/card_metric.dart`) |
| | **Test Intervention** | 0 (Nol) | **0 (NOL / Freeze)** | 0 (Nol) |
| | **Failure Type** | Compilation error | Compilation error | Compilation error / None* |
| | **Konvergensi** | Non-konvergen | Non-konvergen | Non-konvergen |
| **CLI Calculator** | **Final Status** | `needs_revision` | `needs_revision` | `needs_revision` |
| | **Test Result** | FAILED (exit 1 → exit 2) | FAILED (exit 1 persisten) | FAILED (exit 1 → exit 2) |
| | **Reviewer Result** | NOT APPROVED | NOT APPROVED | NOT APPROVED |
| | **Repair Loops** | 3 loops | 3 loops | 3 loops |
| | **Total Duration** | 233.44s | 282.25s | 211.76s / 228.99s |
| | **Code Intervention** | 0 (Nol) | 3 kali (`main.py`, `module_1.py`) | 3 kali (`main.py`) |
| | **Test Intervention** | 0 (Nol) | **0 (NOL / Freeze)** | 0 (Nol) / AST patch |
| | **Failure Type** | NameError → Collection err | NameError: Matrix di test | Assertion fail → Collection err |
| | **Konvergensi** | Non-konvergen | Non-konvergen | Non-konvergen |

*\*Catatan: Flutter ON Set 1 lulus pada iterasi 0 karena kebetulan stokastik kode awal Developer dan Tester selaras tanpa memicu deprecation.*

---

## 7. Cross-Run Patterns

1. **Pola Pembalikan Keberhasilan pada FastAPI CRUD (OFF Gagal vs CODE_ONLY Sukses):**
   - Pada mode OFF, Developer selalu gagal melewati pytest karena payload request tanpa `id` ditolak oleh model Pydantic yang mewajibkan `id: int`.
   - Pada mode CODE_ONLY, Executor memperbaiki model tersebut (`id: int | None = None`) tanpa menyentuh tes. Kode langsung lulus 100%. Ini membuktikan bahwa intervensi pada lapisan implementasi kode saja memiliki daya ubah outcome yang signifikan.
2. **Pola Kegagalan Asimetri Orakel pada CLI (Tester Bug yang Mengunci Pipeline):**
   - Pada CLI Calculator CODE_ONLY, tes yang dibuat oleh QA Tester mengandung bug fatal (`NameError: name 'Matrix' is not defined` akibat lupa import).
   - Dalam mode di mana tes dibekukan (CODE_ONLY dan OFF), kecacatan orakel pengujian ini mengunci pipeline dalam kegagalan permanen karena Developer tidak memiliki akses untuk merevisi berkas test QA Tester.
3. **Pola Ketidakberdayaan Developer Terhadap Error Kompilasi Flutter:**
   - Pada ketiga mode (ON, OFF, CODE_ONLY), Developer secara konsisten meregenerasi sintaks `headline6` dan `headline5` yang deprecated pada Flutter Material 3 meskipun berulang kali menerima feedback kompilasi terminal.
4. **Pola Penghasilan Berkas Halusinasi (`module_1.py`):**
   - Munculnya `module_1.py` saat Developer mengalami kegagalan berulang terjadi di mode OFF (`210254`, `211037`) dan terulang kembali pada mode CODE_ONLY (`220528`). Hal ini menegaskan bahwa kemunculan berkas halusinasi adalah karakteristik bawaan agen Developer saat menemui kebuntuan perbaikan, bukan artefak dari mode eksekusi.

---

## 8. Observed Facts

1. **Integritas Test Mode CODE_ONLY:** Pada ketiga run CODE_ONLY (`215919`, `220147`, `220528`), hash berkas test sebelum dan sesudah Executor identik 100% pada setiap iterasi (`test_transformations: []`). Tidak ada modifikasi atau penambahan berkas test oleh Executor.
2. **Keberhasilan Penuh FastAPI pada CODE_ONLY:** Preset FastAPI CRUD pada mode CODE_ONLY berstatus `completed` dengan 2/2 test passed pada iterasi 0, dan disetujui Reviewer, identik dengan status pada mode ON, dan berbeda kontras dengan mode OFF yang berakhir `needs_revision`.
3. **Penyebab Kelulusan FastAPI CODE_ONLY:** Perubahan kode dari `id: int` menjadi `id: int | None = None` dan mutasi list `products[:] = ...` oleh Executor pada `main.py` mendahului kelulusan pytest, tanpa ada relaksasi assertion test.
4. **Kegagalan Persisten pada Flutter dan CLI:** Preset Flutter Widget dan CLI Calculator pada mode CODE_ONLY berakhir `needs_revision` setelah menghabiskan 3 loop iterasi, konsisten dengan hasil pada mode OFF dan ON (Set 2).
5. **Defek Berkas Test pada CLI Calculator:** Berkas `test_main.py` yang dihasilkan oleh QA Tester pada run CLI CODE_ONLY memanggil `Matrix(...)` tanpa mengimpor `Matrix` dari `main.py`, memicu `NameError` pada 10 dari 11 test case.
6. **Perilaku Developer pada Feedback Loop:** Pada run Flutter dan CLI CODE_ONLY, Developer menerima objek `test_results` berisi error terminal pada setiap iterasi, namun gagal memperbaiki error tersebut pada iterasi berikutnya. Pada Flutter, Developer mencoba menghasilkan berkas `test/card_metric_test.dart` pada iterasi 1 dan 2, tetapi diabaikan oleh Executor demi menjaga pembekuan test.

---

## 9. Candidate Patterns

1. **Pola Efektivitas Intervensi Implementasi vs Intervensi Orakel:** Intervensi kode Executor terbukti sangat efektif pada kasus inkonsistensi skema data sederhana (seperti nilai default model Pydantic), tetapi tidak berdaya terhadap error arsitektur framework mendalam (seperti deprecation Flutter) atau error sintaksis impor di dalam test suite itu sendiri.
2. **Pola Stagnasi Penalaran Model 7B pada Perbaikan Sintaksis Usang:** Model `qwen2.5-coder:7b` menunjukkan *prior knowledge bias* yang sangat kuat terhadap API Flutter versi lama (`headline6`/`headline5`), sehingga feedback terminal yang secara eksplisit meminta penggantian nama getter tidak mampu mengesampingkan bias memori model tersebut.

---

## 10. Hypotheses / Interpretations

### Jawaban terhadap Tiga Pertanyaan Fokus Analisis:

#### Q1. Apakah Executor code intervention saja sudah cukup untuk mengubah outcome dibanding OFF?
- **Interpretasi Berdasarkan Bukti:** **YA, PADA DOMAIN TERTENTU.**
- **Dasar Fakta:** Pada FastAPI CRUD, mode OFF menghasilkan kegagalan total (`needs_revision`, 3 loop, exit code 1), sedangkan mode CODE_ONLY berhasil lulus sempurna (`completed`, 0 loop, exit code 0, approved). Karena pada CODE_ONLY berkas test dibekukan 100%, perubahan outcome dari FAIL menjadi PASS terbukti disebabkan semata-mata oleh intervensi kode Executor pada `main.py`.

#### Q2. Jika CODE_ONLY berhasil sementara OFF gagal, apakah keberhasilan tersebut berasal dari perubahan implementation dan bukan perubahan oracle?
- **Interpretasi Berdasarkan Bukti:** **YA, DEFINITIF BERASAL DARI PERUBAHAN IMPLEMENTATION.**
- **Dasar Fakta:** Pada run `project_20260908_215919`, hash `test_main.py` sebelum eksekusi identik dengan hash sesudah eksekusi (`8b1d69b3d4206045b157ce749cf13fb587e45f5d69561a6002a06aa317c17cdb`). Tidak ada relaksasi assertion (seperti `assert status_code in (200, 201, 400)` yang terjadi pada ON Set 2). Keberhasilan tercapai murni karena `main.py` diubah agar menerima request tanpa payload `id`, yang memenuhi kontrak asli yang diminta oleh QA Tester.

#### Q3. Jika ON berhasil tetapi CODE_ONLY gagal, apakah trace menunjukkan bahwa perubahan test/oracle berperan terhadap keberhasilan ON?
- **Interpretasi Berdasarkan Bukti:** **DATA TIDAK MENUNJUKKAN KASUS INI PADA KELOMPOK RUN YANG IDENTIK.**
- **Dasar Fakta:**
  - Pada FastAPI CRUD: Baik ON maupun CODE_ONLY sama-sama **berhasil**. Ini membuktikan bahwa relaksasi test pada mode ON sebenarnya adalah *over-intervention* (intervensi berlebih); kode yang diperbaiki saja sudah cukup untuk lulus.
  - Pada Flutter Widget dan CLI Calculator: Baik ON (Set 2) maupun CODE_ONLY sama-sama **gagal**. Pada CLI Calculator, kegagalan pada CODE_ONLY justru menyingkap fakta baru bahwa **QA Tester menghasilkan test yang cacat impor**. Pada mode ON, Executor terkadang melakukan AST patch pada test/code, namun tetap gagal berkonvergensi pada CLI. Hal ini menunjukkan bahwa kegagalan bukan akibat orakel yang terlalu ketat, melainkan diskrepansi antarmuka dan defek orakel itu sendiri.

---

## 11. Evidence Limitations

1. **Variasi Stokastik Antar Run:** Setiap run dijalankan dengan temperature model LLM standar sehingga kode yang dihasilkan QA Tester dan Developer antar set memiliki variasi redaksional (misal: jumlah tes FastAPI pada Set 2 adalah 3 item, sedangkan pada Set 4 adalah 2 item).
2. **Keterbatasan Ukuran Sampel:** Eksperimen CODE_ONLY saat ini baru mencakup 1 run per preset misi (total 3 run). Replikasi berulang disarankan untuk mengukur signifikansi statistik keberhasilan FastAPI.
3. **Ketergantungan terhadap Prompt Preset:** Preset Flutter dan CLI memiliki kompleksitas dependensi lingkungan eksternal (Flutter SDK Material 3 dan Pytest Matrix Runner) yang lebih tinggi dibandingkan endpoint REST FastAPI in-memory.

---

## 12. Raw Run References

- **FastAPI CRUD (CODE_ONLY):** `backend/output/project_20260908_215919` (`run_trace.jsonl`, `project_meta.json`)
- **Flutter Widget (CODE_ONLY):** `backend/output/project_20260908_220147` (`run_trace.jsonl`, `project_meta.json`)
- **CLI Calculator (CODE_ONLY):** `backend/output/project_20260908_220528` (`run_trace.jsonl`, `project_meta.json`)
- **Baseline Pembanding ON Set 1:** `project_20260908_175258`, `project_20260908_181146`, `project_20260908_182017`
- **Baseline Pembanding ON Set 2:** `project_20260908_195412`, `project_20260908_195655`, `project_20260908_200342`
- **Baseline Pembanding OFF Set 3:** `project_20260908_210254`, `project_20260908_210658`, `project_20260908_211037`
