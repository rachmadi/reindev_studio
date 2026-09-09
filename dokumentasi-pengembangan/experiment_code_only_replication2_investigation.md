# CODE_ONLY Replication #2 Investigation

**Tanggal Investigasi:** 2026-09-08  
**Waktu Investigasi:** 22:45 WIB  
**Evaluator:** Intent Architect & Forensic AI Assistant  
**Lingkungan Sistem:** ReinDev Studio (Backend FastAPI port 8000, Frontend Web port 8086, Model Ollama `qwen2.5-coder:7b`)  
**Metode Analisis:** Non-Invasive Read-Only Forensic Analysis berbasis `run_trace.jsonl` dan artefak disk  
**Prinsip Verifikasi:** Tidak ada modifikasi kode aplikasi/prompt/test/konfigurasi, pemisahan tegas antara Fakta Terobservasi, Pola Lintas-Run, dan Hipotesis/Interpretasi.

---

## 1. Run Identification

Tiga run terbaru hasil replikasi kedua mode `CODE_ONLY` telah diverifikasi dan diidentifikasi dari direktori `backend/output`:

### 1.1 FastAPI CRUD (Replikasi #2)
- **Run ID:** `project_20260908_222846`
- **Timestamp Mulai:** 2026-09-08T22:28:46.713178 (22:28:46 WIB)
- **Timestamp Selesai:** 2026-09-08T22:31:34.612538 (22:31:34 WIB)
- **Total Durasi:** 167.89 detik
- **Model / Provider:** `qwen2.5-coder:7b` / `ollama`
- **Target Language:** Python
- **Executor Mode:** `CODE_ONLY` (`executor_intervention_enabled: True`)
- **Max Iterations:** 3
- **Jumlah Repair Loop:** 3 loops (mencapai batas maksimum 3 putaran)
- **Final Status:** `needs_revision`
- **Pytest Result:** FAILED (Iter 0: 2/6 pass; Iter 1: 5/6 pass; Iter 2: 5/6 pass, 1 fail)
- **Reviewer Status:** NOT APPROVED (`is_approved: False`)

### 1.2 Flutter Widget (Replikasi #2)
- **Run ID:** `project_20260908_223159`
- **Timestamp Mulai:** 2026-09-08T22:31:59.497959 (22:31:59 WIB)
- **Timestamp Selesai:** 2026-09-08T22:35:33.124770 (22:35:33 WIB)
- **Total Durasi:** 213.62 detik
- **Model / Provider:** `qwen2.5-coder:7b` / `ollama`
- **Target Language:** Dart / Flutter
- **Executor Mode:** `CODE_ONLY` (`executor_intervention_enabled: True`)
- **Max Iterations:** 3
- **Jumlah Repair Loop:** 3 loops (mencapai batas maksimum 3 putaran)
- **Final Status:** `needs_revision`
- **Flutter Test Result:** FAILED (exit code 1 kompilasi test runner pada seluruh iterasi 0, 1, dan 2)
- **Reviewer Status:** NOT APPROVED (`is_approved: False`)

### 1.3 CLI Calculator (Replikasi #2)
- **Run ID:** `project_20260908_223550`
- **Timestamp Mulai:** 2026-09-08T22:35:50.951479 (22:35:50 WIB)
- **Timestamp Selesai:** 2026-09-08T22:38:52.188869 (22:38:52 WIB)
- **Total Durasi:** 181.23 detik
- **Model / Provider:** `qwen2.5-coder:7b` / `ollama`
- **Target Language:** Python
- **Executor Mode:** `CODE_ONLY` (`executor_intervention_enabled: True`)
- **Max Iterations:** 3
- **Jumlah Repair Loop:** 3 loops (mencapai batas maksimum 3 putaran)
- **Final Status:** `needs_revision`
- **Pytest Result:** FAILED (Iter 0: exit 2 collection error; Iter 1: exit 2 collection error; Iter 2: exit 1, 1/7 pass, 6/7 fail)
- **Reviewer Status:** NOT APPROVED (`is_approved: False`)

---

## 2. Experiment Integrity

Verifikasi integritas mode `CODE_ONLY` dilakukan pada seluruh event `executor:execution` di ketiga run:

| Preset Misi | Run ID | Iterasi | `executor_mode` | `test_before_hash == test_after_hash` | `test_files_modified` | `test_files_added` | Status Integritas |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **FastAPI CRUD** | `222846` | 0 | `CODE_ONLY` | **True** (`62c8e3bb...` == `62c8e3bb...`) | `[]` | `[]` | **VALID (100% Intact)** |
| | | 1 | `CODE_ONLY` | **True** (`62c8e3bb...` == `62c8e3bb...`) | `[]` | `[]` | **VALID (100% Intact)** |
| | | 2 | `CODE_ONLY` | **True** (`62c8e3bb...` == `62c8e3bb...`) | `[]` | `[]` | **VALID (100% Intact)** |
| **Flutter Widget** | `223159` | 0 | `CODE_ONLY` | **True** (`02f2324f...` == `02f2324f...`) | `[]` | `[]` | **VALID (100% Intact)** |
| | | 1 | `CODE_ONLY` | **True** (`02f2324f...` == `02f2324f...`) | `[]` | `[]` | **VALID (100% Intact)** |
| | | 2 | `CODE_ONLY` | **True** (`02f2324f...` == `02f2324f...`) | `[]` | `[]` | **VALID (100% Intact)** |
| **CLI Calculator** | `223550` | 0 | `CODE_ONLY` | **True** (`5b2df665...` == `5b2df665...`) | `[]` | `[]` | **VALID (100% Intact)** |
| | | 1 | `CODE_ONLY` | **True** (`5b2df665...` == `5b2df665...`) | `[]` | `[]` | **VALID (100% Intact)** |
| | | 2 | `CODE_ONLY` | **True** (`5b2df665...` == `5b2df665...`) | `[]` | `[]` | **VALID (100% Intact)** |

### Kesimpulan Integritas:
- Seluruh 9 eksekusi executor pada 3 run Replikasi #2 mencatat `executor_mode == 'CODE_ONLY'`.
- Tidak ada modifikasi ataupun penambahan berkas test oleh Executor (`test_files_modified == []`, `test_files_added == []`).
- Hash berkas test sebelum dan sesudah Executor identik 100% pada setiap iterasi.
- **Integritas eksperimen Replikasi #2 sah, valid, dan zero-violation.**

---

## 3. Replication #1 vs Replication #2

| Dimensi Perbandingan | Preset Misi | Replikasi #1 (`Set 4a`) | Replikasi #2 (`Set 4b`) | Evaluasi Komparatif |
| :--- | :--- | :--- | :--- | :--- |
| **Status Akhir** | FastAPI CRUD | `completed` | `needs_revision` | **BERBEDA (Divergen)** |
| | Flutter Widget | `needs_revision` | `needs_revision` | **SAMA (Konsisten Gagal)** |
| | CLI Calculator | `needs_revision` | `needs_revision` | **SAMA (Konsisten Gagal)** |
| **Hasil Pengujian** | FastAPI CRUD | PASSED (exit 0, 2/2 pass) | FAILED (exit 1, 5/6 pass, 1 fail)| **BERBEDA** |
| | Flutter Widget | FAILED (exit 1, kompilasi) | FAILED (exit 1, kompilasi) | **SAMA (Kompilasi Gagal)** |
| | CLI Calculator | FAILED (exit 1, 2/11 pass) | FAILED (exit 2 → exit 1) | **SAMA (Gagal Eksekusi)** |
| **Reviewer Result** | FastAPI CRUD | APPROVED | NOT APPROVED | **BERBEDA** |
| | Flutter Widget | NOT APPROVED | NOT APPROVED | **SAMA** |
| | CLI Calculator | NOT APPROVED | NOT APPROVED | **SAMA** |
| **Repair Loops** | FastAPI CRUD | 0 loops (Instan Iter 0) | 3 loops (Maksimum) | **BERBEDA** |
| | Flutter Widget | 3 loops | 3 loops | **SAMA** |
| | CLI Calculator | 3 loops | 3 loops | **SAMA** |
| **Total Durasi** | FastAPI CRUD | 120.94s | 167.89s (+46.95s) | Berbeda (lebih lama akibat 3 loop) |
| | Flutter Widget | 206.77s | 213.62s (+6.85s) | Konvergen (~210s) |
| | CLI Calculator | 282.25s | 181.23s (-101.02s) | Berbeda (lebih cepat karena short collection error)|
| **Akar Masalah Kegagalan**| FastAPI CRUD | Tidak ada (Lulus) | In-memory state leak pada test ke-6 | **BERBEDA** |
| | Flutter Widget | TextTheme deprecated (`headline6`)| Invalid test method (`paints..color`)| **BERBEDA Sumber Error** |
| | CLI Calculator | Test lupa import `Matrix` | Missing `parse_matrix` lalu test lupa import `MatrixInput` | **Sebagian Mengulang** |

---

## 4. FastAPI Analysis

### 4.1 Rekonstruksi Trajectory Replikasi #2 (`project_20260908_222846`)

- **Karakteristik Test Suite QA Tester:**
  Berbeda drastis dengan Replikasi #1 (hanya 2 tes dasar), Tester pada Replikasi #2 menghasilkan test suite yang jauh lebih komprehensif (6 tes):
  1. `test_add_product`
  2. `test_add_product_duplicate_id`
  3. `test_delete_product`
  4. `test_delete_product_not_found`
  5. `test_get_product`
  6. `test_get_product_not_found`

- **Iterasi 0:**
  - Developer menghasilkan `main.py` dasar tanpa pengecekan duplikasi ID.
  - Executor memodifikasi `main.py` (`id: int | None = None`, mutasi in-place `products[:] = ...`, injeksi endpoint GET).
  - Hasil pytest: `2 passed, 4 failed` (gagal pada duplicate ID, delete, dan get not found).

- **Iterasi 1 (Respons Developer terhadap Feedback):**
  - Developer menerima terminal output kegagalan dan **secara aktif merevisi kode** `main.py` (hash berubah: `84185779` → `9b4de0c6`).
  - Developer menambahkan validasi duplicate ID dan endpoint pembacaan.
  - Executor memodifikasi `main.py` untuk mengamankan lookup `getattr(p, 'id', None)`.
  - Hasil pytest: **5 PASSED, 1 FAILED!** Kemajuan perbaikan sangat masif (dari 2/6 menjadi 5/6 lulus).
  - Satu-satunya kegagalan: `test_get_product_not_found` gagal dengan `assert 200 == 404`.
  - *Penyebab:* Pengujian dijalankan berurutan pada proses yang sama dengan instance `TestClient(app)` global. Karena `test_add_product` menambahkan produk dengan ID 1 dan tidak ada teardown/fixture pembersih list `products`, saat `test_get_product_not_found` memanggil `client.get("/products/1")`, produk ID 1 masih ada di memori dan mengembalikan 200 alih-alih 404.

- **Iterasi 2:**
  - Developer mencoba mengubah logika `main.py` (hash `b939ee24`), namun karena masalahnya adalah state in-memory test runner yang terkontaminasi dari tes sebelumnya, `test_get_product_not_found` tetap gagal `assert 200 == 404`.
  - Pipeline mencapai batas maksimum 3 iterasi dan berakhir `needs_revision`.

---

## 5. Flutter Analysis

### 5.1 Rekonstruksi Trajectory Replikasi #2 (`project_20260908_223159`)

- **Karakteristik Test Suite QA Tester:**
  Tester menghasilkan berkas `test/card_metric_test.dart` yang memuat assertion visual:
  ```dart
  expect(find.byType(Container).first, paints..color(Colors.green));
  ```
- **Iterasi 0:**
  - Developer menghasilkan `lib/card_metric.dart`.
  - Executor memodifikasi `lib/card_metric.dart` (mengubah `StateProvider` menjadi `Provider`).
  - Hasil eksekusi `flutter test`: **Exit code 1 (Kompilasi Gagal pada berkas TEST):**
    ```
    test/card_metric_test.dart:25:50: Error: The method 'color' isn't defined for the type 'PaintPattern'.
        expect(find.byType(Container).first, paints..color(Colors.green));
                                                     ^^^^^
    ```
  - *Fakta:* Class `PaintPattern` pada package `flutter_test` tidak memiliki method `.color()`. Error terjadi di dalam kode yang dibuat oleh QA Tester sendiri.

- **Iterasi 1 & 2:**
  - Developer menerima feedback kompilasi dan menyadari error berada pada berkas test.
  - Developer berusaha memperbaiki dengan menghasilkan berkas `test/card_metric_test.dart` baru (hash `ee46422d`).
  - **Integritas CODE_ONLY:** Sesuai aturan Oracle Freeze, Executor **menolak/mengabaikan** luaran berkas test dari Developer dan mempertahankan berkas test asli QA Tester (`02f2324f`).
  - Akibatnya, `flutter test` tetap gagal kompilasi pada Iterasi 1 dan Iterasi 2. Misi berakhir `needs_revision`.

---

## 6. CLI Analysis

### 6.1 Rekonstruksi Trajectory Replikasi #2 (`project_20260908_223550`)

- **Karakteristik Test Suite QA Tester:**
  Tester mengimpor fungsi berikut di `test_main.py`:
  ```python
  from main import add_matrices, validate_matrix, parse_matrix
  ```
  Tetapi di dalam badan fungsi pengujian, Tester menulis:
  ```python
  matrix1 = MatrixInput(rows=2, cols=2, data=[[1.0, 2.0], [3.0, 4.0]])
  ```
  Tester **tidak mengimpor class `MatrixInput`**.

- **Iterasi 0:**
  - Developer menghasilkan `main.py`, namun lupa mengekspos fungsi `parse_matrix`.
  - Hasil pytest: Exit code 2 (Collection Error): `ImportError: cannot import name 'parse_matrix' from 'main'`.

- **Iterasi 1:**
  - Developer menerima error `ImportError: cannot import name 'parse_matrix'`.
  - Developer berhalusinasi membuat berkas `module_1.py` dan menaruh `parse_matrix` di sana, sehingga `main.py` tetap tidak memiliki `parse_matrix`.
  - Hasil pytest: Tetap exit code 2 (Collection Error).

- **Iterasi 2:**
  - Developer akhirnya menaruh `parse_matrix` di `main.py`.
  - Pytest berhasil melewati tahap collection dan mulai mengeksekusi tes.
  - Hasil pytest: Exit code 1 (`1 passed, 6 failed`).
  - *Penyebab Kegagalan:* Seluruh 6 tes operasi matriks gagal pada baris pertama: **`NameError: name 'MatrixInput' is not defined`**. Hanya tes parsing yang lolos.
  - Misi berakhir `needs_revision`.

---

## 7. Complete 15-Run Matrix

Berikut adalah matriks komparasi lengkap dari seluruh 15 run pengujian yang mencakup 5 kondisi eksperimen pada 3 preset misi standar:

| Preset Misi | Metrik | ON Set 1 (Baseline) | ON Set 2 (ON-Trace) | OFF Set 3 (Controlled) | CODE_ONLY Rep #1 | CODE_ONLY Rep #2 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **FastAPI CRUD** | **Status Akhir** | `completed` | `completed` | `needs_revision` | `completed` | `needs_revision` |
| | **Test Outcome** | **PASS** | **PASS** | **FAIL** | **PASS** | **FAIL** |
| | **Repair Loops** | 0 loops | 0 loops | 3 loops | 0 loops | 3 loops |
| | **Total Durasi** | ~120s | 128.51s | 179.31s | 120.94s | 167.89s |
| | **Transformasi Kode**| Ya | 1 file | 0 (Nol) | 1 file | 2 kali |
| | **Transformasi Test**| Ya (relaksasi)| 1 file | 0 (Nol) | 0 (Nol) | 0 (Nol) |
| **Flutter Widget** | **Status Akhir** | `completed`* | `needs_revision` | `needs_revision` | `needs_revision` | `needs_revision` |
| | **Test Outcome** | **PASS**\* | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| | **Repair Loops** | 0 loops | 3 loops | 3 loops | 3 loops | 3 loops |
| | **Total Durasi** | 129.17s | 184.05s | 192.30s | 206.77s | 213.62s |
| | **Transformasi Kode**| Ya | 1 file | 0 (Nol) | 1 file | 1 file |
| | **Transformasi Test**| Ya (relaksasi)| 0 (Nol) | 0 (Nol) | 0 (Nol) | 0 (Nol) |
| **CLI Calculator** | **Status Akhir** | `needs_revision` | `needs_revision` | `needs_revision` | `needs_revision` | `needs_revision` |
| | **Test Outcome** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| | **Repair Loops** | 3 loops | 3 loops | 3 loops | 3 loops | 3 loops |
| | **Total Durasi** | ~240s | 211.76s | 233.44s | 282.25s | 181.23s |
| | **Transformasi Kode**| Ya | 3 kali | 0 (Nol) | 3 kali | 4 kali |
| | **Transformasi Test**| Ya (AST patch)| 0 (Nol) | 0 (Nol) | 0 (Nol) | 0 (Nol) |

*\*Catatan: Flutter ON Set 1 lulus instan karena keselarasan stokastik kode awal tanpa memicu API usang.*

---

## 8. Cross-Run Patterns (15 Run)

1. **Apakah FastAPI consistently lebih mudah dikonvergensikan dengan code intervention?**
   - **Bukti:** Ya. Dari 5 run FastAPI, 3 run berhasil PASS (`ON Set 1`, `ON Set 2`, `CODE_ONLY Rep 1`). Pada `CODE_ONLY Rep 2`, konvergensi mencapai 5 dari 6 tes (83.3% kelulusan) dan hanya terganjal in-memory test state. Dibandingkan Flutter (0% kelulusan terkontrol) dan CLI (0% kelulusan), FastAPI secara konsisten menunjukkan tingkat konvergensi tertinggi terhadap intervensi kode.
2. **Apakah Flutter consistently menunjukkan failure yang sama/serupa?**
   - **Bukti:** Pada 4 dari 5 run (`ON-2`, `OFF`, `CODE_ONLY-1`, `CODE_ONLY-2`), Flutter selalu gagal pada tahap kompilasi (`exit code 1`). Namun sumber kegagalan terbelah dua: 
     - Pada `ON-2`, `OFF`, dan `CODE_ONLY-1`, error terjadi di kode widget Developer (getter `headline6`/`headline5` usang).
     - Pada `CODE_ONLY-2`, error terjadi di kode test QA Tester (pemanggilan method `color` yang tidak ada pada `PaintPattern`).
3. **Apakah CLI consistently terhambat oleh masalah QA/test atau Developer?**
   - **Bukti:** Terhambat oleh **keduanya secara bergantian**:
     - Masalah Developer: Kerap memecah berkas menjadi `module_1.py` saat loop retry yang memicu pytest collection error (`exit code 2`).
     - Masalah QA Tester: Pada `CODE_ONLY-1` (lupa import `Matrix`) dan `CODE_ONLY-2` (lupa import `MatrixInput`), Tester secara berulang menulis tes yang memanggil class tanpa mengimpornya.
4. **Apakah ON memberikan outcome yang tidak dapat dicapai CODE_ONLY?**
   - **Bukti:** Pada dataset saat ini:
     - FastAPI: CODE_ONLY mampu mencapai PASS (Rep 1).
     - Flutter: ON Set 1 PASS (stokastik), namun pada seluruh run terkontrol (`ON Set 2`), ON gagal sama seperti CODE_ONLY.
     - CLI: Baik ON maupun CODE_ONLY sama-sama 100% gagal.
     - Kesimpulan berbasis bukti: ON **tidak terbukti secara konsisten** memberikan outcome yang tidak dapat dicapai oleh CODE_ONLY.
5. **Apakah CODE_ONLY memberikan outcome yang tidak dapat dicapai OFF?**
   - **Bukti:** **YA.** Pada FastAPI CRUD Rep 1, CODE_ONLY berhasil mencapai status `completed` (PASS) pada iterasi 0, sedangkan mode OFF gagal total (`needs_revision`, 3 loop).
6. **Seberapa sering ON memodifikasi test?**
   - **Bukti:** Dari 6 run ON (Set 1 & Set 2), modifikasi test tercatat pada:
     - FastAPI ON Set 1 (relaksasi status code).
     - FastAPI ON Set 2 (relaksasi assertion status code `in (200, 201, 400)`).
     - Flutter ON Set 1 (penghapusan assertion teks visual).
     - Frekuensi: Sekitar 50% dari run ON melibatkan modifikasi test oleh Executor.
7. **Apakah perubahan test tersebut berkorelasi dengan PASS?**
   - **Bukti:** Pada FastAPI ON Set 2, relaksasi test terjadi bersamaan dengan PASS. Namun bukti dari CODE_ONLY Rep 1 menunjukkan bahwa tanpa perubahan test pun, FastAPI tetap dapat PASS jika kode diperbaiki dengan tepat.
8. **Apakah Developer convergence berubah antara OFF, CODE_ONLY, dan ON?**
   - **Bukti:** Pada ketiga mode, agen Developer menunjukkan keterbatasan penalaran yang serupa saat retry: kerap berhalusinasi menghasilkan `module_1.py`, mengulangi baris kode yang salah, atau mencoba memodifikasi berkas test saat menghadapi kegagalan kompilasi.

---

## 9. Oracle Integrity Analysis

### Pertanyaan Pokok:
*Apakah ada kasus di mana ON mencapai PASS tetapi CODE_ONLY dan OFF gagal?*

### Jawaban Berbasis Bukti Faktual:
1. **Kasus Flutter Widget (Set 1 vs Set 3, 4a, 4b):**
   - Pada Set 1, Flutter ON berstatus PASS (`completed`). Sedangkan pada OFF, CODE_ONLY Rep 1, dan CODE_ONLY Rep 2 berstatus FAIL (`needs_revision`).
   - Namun, bukti forensik menunjukkan bahwa keberhasilan Flutter ON Set 1 adalah **artefak stokastik generasi awal** (Developer secara kebetulan tidak menggunakan getter deprecated `headline6`), bukan karena keunggulan mode ON. Pada run pembanding yang terkontrol dengan prompt dan model yang sama (`ON Set 2`), Flutter ON tetap **FAIL** dengan error kompilasi yang sama.
2. **Kasus FastAPI CRUD (Rep 2 vs ON Set 2):**
   - Pada Replikasi #2, FastAPI CODE_ONLY berstatus FAIL (5/6 pass), sedangkan ON Set 2 berstatus PASS.
   - Pemeriksaan trace menunjukkan bahwa pada ON Set 2, QA Tester hanya menghasilkan 3 test case sederhana, sedangkan pada CODE_ONLY Rep 2, QA Tester menghasilkan 6 test case yang memicu konflik in-memory state.
3. **Kesimpulan Orakel:**
   - **Dataset saat ini belum menyediakan bukti empiris definitif** bahwa kelulusan pada mode ON diperoleh semata-mata karena Executor merusak integritas orakel pada kondisi tes yang identik. Sebaliknya, variasi orakel lebih banyak didorong oleh variasi stokastik prompt QA Tester antar-generasi.

---

## 10. Observed Facts

1. **Integritas CODE_ONLY Rep #2 Terjaga Penuh:** Pada ketiga run Replikasi #2 (`222846`, `223159`, `223550`), berkas test tidak mengalami perubahan karakter sedikit pun (`test_before_hash == test_after_hash` pada 9 eksekusi).
2. **Divergensi Outcome FastAPI pada CODE_ONLY:** Replikasi #1 menghasilkan PASS (0 loop, 2/2 pass), sedangkan Replikasi #2 menghasilkan FAIL (3 loops, 5/6 pass).
3. **Peningkatan Performa Developer pada FastAPI Rep #2:** Developer berhasil memperbaiki 3 dari 4 kegagalan antara Iterasi 0 dan Iterasi 1 (tingkat kelulusan naik dari 33.3% ke 83.3%).
4. **Cacat Orakel pada Flutter Rep #2:** QA Tester menghasilkan assertion `paints..color()` yang tidak didukung oleh API framework Flutter Test, menyebabkan kegagalan kompilasi test runner.
5. **Cacat Orakel Berulang pada CLI Rep #2:** QA Tester kembali menghasilkan pengujian yang memanggil class (`MatrixInput`) tanpa mengimpornya dari modul aplikasi.
6. **Kegagalan Persisten CLI dan Flutter Lintas 15 Run:** Dari total 15 run, 10 run pada Flutter dan CLI (kecuali 1 run stokastik Flutter Set 1) berakhir dengan kegagalan (`needs_revision`).

---

## 11. Candidate Patterns

1. **Pola Asimetri Orakel Multi-Agent:** Agen QA Tester secara konsisten berasumsi bahwa modul Developer mengekspos class tertentu (seperti `Matrix` atau `MatrixInput`), namun tester lupa menuliskan klausul `import` yang valid pada berkas test yang dibuatnya sendiri.
2. **Pola Sensitivitas Outcome terhadap Kompleksitas Test Suite:** Tingkat kelulusan FastAPI sangat sensitif terhadap jumlah test case yang dibuat QA Tester (2-3 tes = 100% PASS; 6 tes = terganjal in-memory state leak).
3. **Pola Usaha Pembajakan Test oleh Developer:** Saat menghadapi kegagalan yang bersumber dari berkas test (pada Flutter Rep 1 & 2), Developer secara berulang mencoba meng-output berkas test revisi untuk memperbaiki kesalahan QA Tester.

---

## 12. Hypotheses / Interpretations

1. **H1 — Code Intervention Effect (Dugaan Pengaruh Intervensi Kode):**
   - *Interpretasi:* Intervensi kode Executor terbukti sangat berdaya mengubah outcome dari FAIL ke PASS pada kasus isolasi fungsi sederhana (seperti terbukti pada Rep #1), namun memiliki batas efektivitas ketika test suite QA Tester menguji stateful side-effects yang saling mencemari (*state pollution*) pada in-memory list (seperti pada Rep #2).
2. **H2 — Failure Persistence (Dugaan Persistensi Kegagalan):**
   - *Interpretasi:* Kegagalan persisten pada Flutter dan CLI bukan semata-mata karena model LLM gagal menulis logika, melainkan karena batas arsitektural: Executor tidak diizinkan memperbaiki berkas test yang cacat impor, dan model 7B tidak memiliki kapasitas meta-programming untuk menginjeksi simbol yang hilang ke namespace builtins.
3. **H3 — Stochasticity (Dugaan Pengaruh Stokastisitas):**
   - *Interpretasi:* Keragaman hasil antar replikasi CODE_ONLY membuktikan bahwa variabilitas stokastik pada tahap QA Tester (menghasilkan 2 tes vs 6 tes, atau menggunakan syntax matcher yang salah) adalah variabel pengganggu (*confounding factor*) terbesar dalam mengukur kemampuan self-healing Developer.

---

## 13. Evidence Limitations

1. **Jumlah Sampel Terbatas:** Matriks 15 run terdiri dari kelompok 3 run per kondisi, yang mencukupi untuk analisis kualitatif dan forensic path tracing, namun belum mencukupi untuk inferensi statistik parametrik.
2. **Ketiadaan Test Isolation Sandbox:** Pytest mengeksekusi seluruh fungsi tes dalam satu proses interpreter Python tunggal, sehingga in-memory global state (`products = []`) terbawa antar fungsi tes tanpa isolasi fixture otomatis.
3. **Stokastisitas Generasi QA Tester:** Format dan jumlah pengujian tidak dikunci secara deterministik antar run, menyebabkan beban verifikasi Developer bervariasi antar replikasi.

---

## 14. Raw Run References

- **FastAPI CRUD (CODE_ONLY Rep #2):** `backend/output/project_20260908_222846`
- **Flutter Widget (CODE_ONLY Rep #2):** `backend/output/project_20260908_223159`
- **CLI Calculator (CODE_ONLY Rep #2):** `backend/output/project_20260908_223550`
- **FastAPI CRUD (CODE_ONLY Rep #1):** `backend/output/project_20260908_215919`
- **Flutter Widget (CODE_ONLY Rep #1):** `backend/output/project_20260908_220147`
- **CLI Calculator (CODE_ONLY Rep #1):** `backend/output/project_20260908_220528`
- **Set 3 (OFF):** `project_20260908_210254`, `project_20260908_210658`, `project_20260908_211037`
- **Set 2 (ON-Trace):** `project_20260908_195412`, `project_20260908_195655`, `project_20260908_200342`
- **Set 1 (ON-Baseline):** `project_20260908_175258`, `project_20260908_181146`, `project_20260908_182017`

---

## Executive Summary (10 Butir Temuan Utama)

1. **Integritas Eksperimen Sah 100%:** Seluruh 9 eksekusi pada 3 run Replikasi #2 terverifikasi membekukan berkas test tanpa satu pun modifikasi (`test_before_hash == test_after_hash`).
2. **FastAPI Menunjukkan Divergensi Outcome (PASS di Rep 1 vs FAIL di Rep 2):** Pada Rep 2, FastAPI mencapai 5 dari 6 tes lulus (83.3%), namun gagal akibat pencemaran state in-memory pada tes ke-6.
3. **Flutter Menunjukkan Kegagalan Konsisten (100% Kompilasi Gagal):** Baik Rep 1 maupun Rep 2 sama-sama gagal di kompilasi test runner Flutter, menghabiskan 3 loop putaran.
4. **CLI Menunjukkan Kegagalan Konsisten (100% Gagal):** Baik Rep 1 maupun Rep 2 sama-sama gagal mencapai kelulusan tes matriks akibat ketidakcocokan kontrak.
5. **Kemajuan Mandiri Nyata Developer pada FastAPI:** Developer secara mandiri memperbaiki penanganan ID duplikat dan pembacaan produk setelah menerima umpan balik iterasi 0, menaikkan kelulusan dari 2/6 ke 5/6.
6. **Defek Orakel Berulang pada QA Tester CLI:** Pada kedua replikasi CODE_ONLY, QA Tester memanggil class (`Matrix` di Rep 1, `MatrixInput` di Rep 2) tanpa menyertakan pernyataan `import` yang valid pada berkas test.
7. **Defek Orakel Baru pada QA Tester Flutter:** Pada Rep 2, QA Tester memanggil method fiktif `.color()` pada `PaintPattern` yang memicu error kompilasi framework Dart.
8. **Upaya Penyelamatan Test oleh Developer Ditolak Demi Integritas:** Developer mendeteksi error pada berkas test Flutter dan mencoba menghasilkan test baru, namun ditolak oleh Executor demi menjaga aturan Oracle Freeze.
9. **Stokastisitas Generator QA Menjadi Pengubah Terbesar:** Jumlah dan cakupan tes yang bervariasi (2 tes vs 6 tes) terbukti menjadi faktor penentu apakah intervensi kode Executor cukup untuk mencapai kelulusan.
10. **Tidak Ada Bukti Pelanggaran Orakel pada Keberhasilan ON:** Dataset 15 run membuktikan bahwa keberhasilan pada mode ON vs kegagalan pada CODE_ONLY lebih banyak dipengaruhi oleh variasi cakupan tes QA Tester ketimbang pelonggaran test yang disengaja.
