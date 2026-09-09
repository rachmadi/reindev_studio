# Laporan Validasi Frozen Oracle (Phase 0) — Research Experiment Protocol v1

Dokumen ini menyajikan hasil pelaksanaan **Phase 0 — Frozen Oracle Validation** secara komprehensif untuk ReinDev Studio sebelum pelaksanaan pilot comparison *Executor OFF vs. CODE_ONLY vs. ON*.

---

## 1. Objective

Tujuan dari Phase 0 adalah memvalidasi, menstandardisasi, dan membekukan (*freeze*) tiga test suite artefak (**FastAPI T1**, **CLI T1**, dan **Flutter T1**) sebagai **Experimental Ground Truth** (Frozen Oracle). 

Pengujian eksperimental terdahulu membuktikan bahwa variabilitas stokastik dan cacat bawaan pada test suite yang digenerasi oleh QA Tester LLM (*moving goalposts*, assertion keliru, `input()` pada stdin tertutup, dan getter fiktif) merupakan **confounding factor** utama yang mendistorsi evaluasi efektivitas Executor. Dengan membekukan test suite menjadi oracle yang valid dan immutable (SHA-256 terkunci), pengaruh intervensi Executor dapat diisolasi secara objektif dan deterministik.

---

## 2. Existing FastAPI Oracle Audit (`fastapi_t1`)

### 2.1 Lokasi & Identitas Artefak
- **Direktori:** `dokumentasi-pengembangan/experiments/frozen_oracle/fastapi_t1/`
- **Berkas Test:** `test_main.py`
- **SHA-256 Hash:** `a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63`
- **Checksum File:** `checksums.sha256` (Terverifikasi identik)

### 2.2 Audit Rinci Kasus Uji & Assertion
| Kasus Uji | Target Requirement | Assertion yang Divalidasi | Rasional & Bukti Objektif |
|---|---|---|---|
| `test_create_product` | POST `/products` (Pydantic validation, status 201) | `status_code == 201`, payload dict keys `name`, `quantity`, `"id" in data` | Sesuai spesifikasi REST CRUD: pembuatan entitas baru wajib menghasilkan HTTP 201 Created dan mengembalikan objek dengan atribut ID. |
| `test_get_all_products` | GET `/products` (Collection listing) | `status_code == 200`, `isinstance(data, list)`, `len(data) >= 1` | Memverifikasi pembacaan koleksi inventaris. Menggunakan `len >= 1` alih-alih angka eksak untuk mencegah kerapuhan terhadap state in-memory sebelumnya. |
| `test_get_product_by_id` | GET `/products/{id}` (Single item retrieval) | `status_code == 200`, `data["name"] == "Wireless Mouse"`, `data["quantity"] == 30` | Membuat produk terlebih dahulu secara dinamis, mengambil ID aktual yang dihasilkan (`prod_id = res.json()["id"]`), lalu melakukan GET by ID. Bebas dari asumsi ID statis `id == 1`. |
| `test_delete_product` | DELETE `/products/{id}` (status 204 & subsequent 404) | `status_code == 204`, kemudian GET `/products/{prod_id}` menghasilkan `status_code == 404` | Sesuai kontrak HTTP DELETE: berhasil menghapus entitas tanpa payload kembalian (204 No Content), dan entitas terbukti hilang saat dicari kembali (404 Not Found). |
| `test_delete_nonexistent_product` | DELETE `/products/{id}` (404 on missing entity) | `status_code == 404` pada ID `999999` | Menguji penanganan galat saat menghapus ID yang tidak pernah ada tanpa tabrakan dengan ID in-memory yang valid. |

### 2.3 Status Validasi FastAPI T1
- **Status:** **VALIDATED**
- **Integritas:** Tidak ditemukan cacat objektif. Test suite 100% mematuhi spesifikasi REST API FastAPI, tidak memiliki dependensi urutan eksekusi (*order-independent*), dan bebas dari asersi status code ganda yang ambigu.

---

## 3. CLI Oracle Validation (`cli_t1`)

### 3.1 Lokasi & Identitas Artefak
- **Direktori:** `dokumentasi-pengembangan/experiments/frozen_oracle/cli_t1/`
- **Berkas Test:** `test_main.py`
- **SHA-256 Hash:** `0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124`
- **Task Requirement:** *"Bangun kalkulator CLI Python dengan operasi matematika matriks dan penanganan error komprehensif."*

### 3.2 Desain & Isolasi Uji Deterministik
Pada eksperimen terdahulu (Set 5), QA Tester menghasilkan 17 kasus uji interaktif yang memanggil fungsi `main()` atau `input()`, memicu kegagalan deterministik `EOFError: EOF when reading a line` pada lingkungan sandbox headless. 

Oracle `cli_t1` dirancang untuk menguji **kemampuan inti matematis matriks dan penanganan kesalahan** secara deterministik dan programatis tanpa bergantung pada terminal, `sys.stdin`, atau `input()`. Oracle menyediakan adaptor interface non-intrusif (`_get_matrix`, `_to_list`, `_add`, `_sub`, `_mul`) yang kompatibel baik terhadap implementasi berbasis `class Matrix` maupun fungsi prosedural (`add_matrices`, dsb.).

### 3.3 Audit Rinci Kasus Uji & Assertion
| Kasus Uji | Target Operasi | Nilai Masukan & Ekspektasi | Rasional & Bukti Matematis |
|---|---|---|---|
| `test_matrix_addition` | Penjumlahan Matriks 2x2 | $A = \begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}, B = \begin{pmatrix} 5 & 6 \\ 7 & 8 \end{pmatrix} \rightarrow A+B = \begin{pmatrix} 6 & 8 \\ 10 & 12 \end{pmatrix}$ | Penjumlahan elemen demi elemen: $1+5=6, 2+6=8, 3+7=10, 4+8=12$. Matematis benar. |
| `test_matrix_subtraction` | Pengurangan Matriks 2x2 | $A = \begin{pmatrix} 5 & 6 \\ 7 & 8 \end{pmatrix}, B = \begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix} \rightarrow A-B = \begin{pmatrix} 4 & 4 \\ 4 & 4 \end{pmatrix}$ | Pengurangan elemen demi elemen: $5-1=4, 6-2=4, 7-3=4, 8-4=4$. Matematis benar. |
| `test_matrix_multiplication` | Perkalian Matriks 2x2 | $A = \begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}, B = \begin{pmatrix} 5 & 6 \\ 7 & 8 \end{pmatrix} \rightarrow A \cdot B = \begin{pmatrix} 19 & 22 \\ 43 & 50 \end{pmatrix}$ | Dot product baris-kolom: $(1\cdot 5 + 2\cdot 7 = 19)$, $(1\cdot 6 + 2\cdot 8 = 22)$, $(3\cdot 5 + 4\cdot 7 = 43)$, $(3\cdot 6 + 4\cdot 8 = 50)$. Matematis benar. |
| `test_matrix_addition_incompatible_dimensions` | Validasi Dimensi Penjumlahan | $A_{2\times 2} + B_{2\times 3} \rightarrow$ raises `ValueError` | Penjumlahan matriks dengan ordo berbeda tidak terdefinisi secara aljabar linier; wajib memicu penanganan galat. |
| `test_matrix_multiplication_incompatible_dimensions` | Validasi Dimensi Perkalian | $A_{2\times 3} \cdot B_{2\times 3} \rightarrow$ raises `ValueError` | Perkalian matriks mensyaratkan jumlah kolom matriks pertama sama dengan jumlah baris matriks kedua ($\text{cols}(A) = 3 \neq \text{rows}(B) = 2$); wajib memicu penanganan galat. |

### 3.4 Status Validasi CLI T1
- **Status:** **VALIDATED**
- **Integritas:** 100% bebas dari `input()`, `sys.stdin`, dan dependensi terminal. Teruji dan terbukti lulus 5/5 pada implementasi referensi matriks.

---

## 4. Flutter Oracle Validation (`flutter_t1`)

### 4.1 Lokasi & Identitas Artefak
- **Direktori:** `dokumentasi-pengembangan/experiments/frozen_oracle/flutter_t1/`
- **Berkas Test:** `card_metric_test.dart`
- **SHA-256 Hash:** `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528`
- **Task Requirement:** *"Bangun komponen widget kartu metrik modern responsif Flutter dengan Material Design 3 dan Riverpod state."*

### 4.2 Audit Kompatibilitas Environment & Dependensi Aktual
Pemeriksaan langsung terhadap `frontend/pubspec.lock` dan toolchain sistem:
- **Flutter Version:** Flutter 3.47.2 (channel stable, tools Dart 3.13.2)
- **Riverpod Version:** `flutter_riverpod: ^3.4.3` (Riverpod 3 resmi)
- **Eliminasi Cacat Terdahulu:**
  1. *Fictitious Getter Elimination:* Tidak lagi mengakses properti non-eksisten seperti `element.backgroundColor` atau `card.color` yang memicu crash pada `Element`.
  2. *API Deprecation Protection:* Tidak menggunakan `StateProvider` atau `StateNotifierProvider` peninggalan Riverpod 1/2 yang dihapus di Riverpod 3; menggunakan `Provider<T>` standar.
  3. *Naming Convention:* Nama berkas menggunakan standar resmi toolchain Dart: `card_metric_test.dart` (pola `*_test.dart` di bawah folder `test/`).

### 4.3 Audit Rinci Kasus Uji & Assertion
| Kasus Uji | Target Requirement | Assertion yang Divalidasi | Rasional & Bukti Objektif |
|---|---|---|---|
| `renders CardMetric with Material 3 Card and Riverpod state` | Rendering Komponen, MD3 Card, & Riverpod | `find.byType(CardMetric)` (findsOneWidget), `find.byType(Card)` (findsOneWidget), `find.text('Revenue')` (findsOneWidget), `find.text('1000')` (findsOneWidget) | Memverifikasi widget `CardMetric` terpasang dalam `ProviderScope`, merender widget `Card` bertema Material Design 3, dan menampilkan nilai metrik yang diberikan melalui model data `MetricData`. |
| `renders responsively inside constrained box without overflow` | Desain Responsif & Integritas Tata Letak | `find.byType(CardMetric)` (findsOneWidget), `expect(tester.takeException(), isNull)` di dalam box `300x200` | Memverifikasi komponen kartu metrik dapat dirender dalam container berukuran terbatas tanpa memicu `RenderFlex overflowed by ... pixels` (menjawab syarat *responsif*). |

### 4.4 Status Validasi Flutter T1
- **Status:** **VALIDATED**
- **Integritas:** 100% kompatibel dengan Flutter 3.47.2 dan `flutter_riverpod 3.4.3`. Teruji dan terbukti lulus 2/2 pada runner subproses `flutter test` di lingkungan sandbox.

---

## 5. Verifikasi Frozen Oracle Runtime

Verifikasi runtime dilakukan menggunakan skrip automasi observabilitas [`verify_all_oracles.py`](file:///C:/Users/rachm/.gemini/antigravity/brain/ea3a040b-4b12-431a-a775-9723c5ac5063/scratch/verify_all_oracles.py) terhadap implementasi referensi yang valid:

```
Alur Eksekusi:
Developer (Initial Fixture) ──> [route_after_developer] ──> Frozen Oracle ──> Executor (Sandbox Runner) ──> Reviewer
                                         │
                                         └── (Loop > 0) ──> Executor (Bypass QA Tester Selamanya)
```

### Hasil Verifikasi Runtime per Oracle:
1. **FastAPI T1 (`verify_fastapi_t1`):**
   - Routing Loop 0: `frozen_oracle` (QA Tester berhasil dilewati).
   - Event Trace: `frozen_oracle:loaded` tercatat dengan hash `a1db9bb1...` (match 100%).
   - Eksekusi Sandbox: **PASS (5/5 tests passed, exit code 0)**.
   - Routing Pasca-Eksekusi: `reviewer` (lulus langsung).
   - Trace Audit: `tester_events = 0`, `frozen_oracle_events = 1`.
2. **CLI T1 (`verify_cli_t1`):**
   - Routing Loop 0: `frozen_oracle` (QA Tester berhasil dilewati).
   - Event Trace: `frozen_oracle:loaded` tercatat dengan hash `0bd5b598...` (match 100%).
   - Eksekusi Sandbox: **PASS (5/5 tests passed, exit code 0)**.
   - Routing Pasca-Eksekusi: `reviewer` (lulus langsung).
   - Trace Audit: `tester_events = 0`, `frozen_oracle_events = 1`.
3. **Flutter T1 (`verify_flutter_t1`):**
   - Routing Loop 0: `frozen_oracle` (QA Tester berhasil dilewati).
   - Event Trace: `frozen_oracle:loaded` tercatat dengan hash `4589e15c...` (match 100%).
   - Pemetaan Path Sandbox: Dimetakan secara tepat ke `test/card_metric_test.dart`.
   - Eksekusi Sandbox: **PASS (2/2 tests passed, exit code 0)**.
   - Routing Pasca-Eksekusi: `reviewer` (lulus langsung).
   - Trace Audit: `tester_events = 0`, `frozen_oracle_events = 1`.

### Verifikasi Jalur Perbaikan (Repair Path Routing):
Pada simulasi kegagalan iterasi 1 (`iteration_count = 1, passed = False`), alur routing dievaluasi:
- Transisi dari Executor: `route_after_executor` $\rightarrow$ `"developer"`.
- Transisi dari Developer (Loop 1): `route_after_developer` $\rightarrow$ `"executor"`.
- **Hasil:** Terkonfirmasi secara absolut bahwa pada siklus perbaikan (*repair loop*), alur **TIDAK PERNAH KEMBALI KE TESTER**, sehingga test suite tetap 100% beku dan *immutable*.

---

## 6. SHA-256 Integrity Audit

| Oracle | Direktori Artefak | Berkas Test | SHA-256 (Frozen Reference) | Validated | Executable | Tester Bypassed |
|---|---|---|---|---|---|---|
| **FastAPI T1** | `experiments/frozen_oracle/fastapi_t1/` | `test_main.py` | `a1db9bb1f6eaf47d5cf56e102c4a0f6e1f49d757e9faa1485b36f2972a152d63` | **YES** | **YES** (5/5) | **YES** (0 event) |
| **CLI T1** | `experiments/frozen_oracle/cli_t1/` | `test_main.py` | `0bd5b598afa7ae4c9cdf0e269d13136b51d35a4e0b1ac6548f0a2cf8a8eba124` | **YES** | **YES** (5/5) | **YES** (0 event) |
| **Flutter T1** | `experiments/frozen_oracle/flutter_t1/` | `card_metric_test.dart` | `4589e15cfb8f37ba70642e70623ca143bceee1a44175aefd072f441d9e8a9528` | **YES** | **YES** (2/2) | **YES** (0 event) |

Setiap direktori telah dilengkapi berkas `metadata.json` dan `checksums.sha256` untuk verifikasi integritas kriptografis sebelum eksekusi eksperimen berikutnya.

---

## 7. Regression Test

Eksekusi regresi menyeluruh pada test suite internal backend:
- **Perintah:** `backend/.venv/Scripts/python.exe -m pytest backend/`
- **Hasil Baseline:** 33 passed
- **Hasil Terkini:** **34 passed, 0 failed, 1 warning (10.00s)**
- **Delta:** **+1 test baru** (`test_frozen_oracle_node_dart_prefix` pada `backend/test_frozen_oracle.py`), 0 regresi.

---

## 8. Anomalies / Limitations

1. **Batasan Kontrak Konstruktor Flutter pada Iterasi Awal (Loop 0):**
   - *Observasi:* Pada Iterasi 0, Developer menulis implementasi berdasarkan rancangan Architect tanpa melihat test suite. Jika Architect merancang konstruktor yang berbeda (misal `CardMetric({required this.title, required this.unit})`), kompilasi Dart pada Iterasi 0 akan gagal.
   - *Mitigasi Eksperimental:* Ini adalah perilaku yang sah dan diharapkan dari sebuah test oracle. Pada Iterasi 1 (self-healing), Developer menerima compiler error dan test oracle Frozen, lalu menyesuaikan konstruktor agar selaras dengan kontrak `MetricData(title, value, color)`.
2. **Isolasi CLI dari Interactive Stdin:**
   - *Observasi:* CLI Matrix Calculator tidak lagi menguji parsing argumen baris perintah melalui `sys.argv` atau input interaktif konsol.
   - *Justifikasi Ilmiah:* Pengujian interaktif pada subproses non-TTY secara deterministik memicu `EOFError`. Memfokuskan oracle pada operasi matematika matriks dan penanganan error dimensi menguji kompetensi rekayasa perangkat lunak sesungguhnya tanpa bias I/O konsol.
3. **Persistensi State In-Memory FastAPI:**
   - *Observasi:* Karena FastAPI menggunakan store in-memory global, penghapusan entitas pada test sebelumnya dapat mempengaruhi ukuran list.
   - *Mitigasi:* Kasus uji `test_get_all_products` menggunakan asersi fleksibel `len(data) >= 1` dan kasus uji delete membuat produk tersendiri secara atomik.

---

## 9. Final Readiness Assessment

Berdasarkan kriteria evaluasi protokol riset:
- **FastAPI T1:** **VALIDATED**
- **CLI T1:** **VALIDATED**
- **Flutter T1:** **VALIDATED**

### Kesimpulan Kesiapan:
Ketiga Frozen Oracle (**FastAPI T1**, **CLI T1**, dan **Flutter T1**) berada dalam status **READY FOR PILOT**. Lingkungan eksperimen, mekanisme `frozen_oracle_path`, *routing bypass*, dan verifikasi kriptografis SHA-256 telah 100% siap untuk eksperimen komparasi pilot (OFF vs. CODE_ONLY vs. ON).

---
*Laporan ini disusun secara otomatis oleh Agen Antigravity pada 2026-09-09 07:05 WIB.*
