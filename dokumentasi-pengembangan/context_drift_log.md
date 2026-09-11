# Context Drift Log — ReinDev Studio
Dokumen ini melacak perbedaan antara intensi awal dan implementasi teknis aktual (Drift Terencana vs Drift Inisiatif Agen).

---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 1a — 2026-09-07 18:10
## ═══════════════════════════════════════════════════════════════════════════

### Bagian A: Perubahan Scope dan Pendekatan
| Deskripsi Perubahan | Dampak terhadap Scope | Sumber |
|---|---|---|
| Penambahan fungsi pembersih teks obrolan `clean_code_content()` | Positif (Menjamin kemurnian file kode tanpa artefak markdown) | Intent Architect |
| Penyediaan mode pengujian deterministik (`MOCK_LLM=true`) di config | Positif (Mendukung pengujian CI/CD instan di samping mode live Ollama) | Agen |

### Bagian B: Keputusan Mandiri Agen
- **B1 (Penambahan di luar spesifikasi):**
  - Implementasi fungsi sanitasi `clean_code_content` untuk mengeliminasi potensi kebocoran teks obrolan LLM ke dalam kode sumber.
- **B2 (Keputusan Teknis):**
  - Mengunci parameter `num_ctx: 8192` dan `temperature: 0.2` pada `ChatOllama` untuk mempertahankan efisiensi VRAM 6GB tanpa memicu swapping.
  - Menerapkan mekanisme impor adaptif `try: from ..state ... except (ImportError, ValueError): from state ...` pada package `agents`.

### Ringkasan Distribusi Sumber Drift:
- **Intent Architect:** 33.3% (Instruksi pembersihan obrolan & penegakan tata kelola)
- **Agen:** 66.7% (Penyesuaian teknis parser dan impor adaptif)
- **Eksternal:** 0.0%

### Severity Drift Keseluruhan:
**Minor** — Seluruh perubahan memperkuat keandalan kode tanpa mengubah fungsi dasar State, PM, dan Developer.
---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 1b — 2026-09-07 19:10
## ═══════════════════════════════════════════════════════════════════════════

### Bagian A: Perubahan Scope dan Pendekatan
| Deskripsi Perubahan | Dampak terhadap Scope | Sumber |
|---|---|---|
| Penambahan auto-scaffold `__init__.py` dan konfigurasi dinamis `PYTHONPATH` di sandbox | Positif (Menjamin seluruh subpackage Python dapat diimpor tanpa error) | Agen (Micro Loop) |
| Mode streaming real-time per node pada eksekusi StateGraph | Positif (Memungkinkan pemantauan log seketika tanpa penundaan buffering) | Agen |

### Bagian B: Keputusan Mandiri Agen
- **B1 (Penambahan di luar spesifikasi):**
  - Menerapkan parameter `errors='replace'` dan `sys.stdout.reconfigure(encoding='utf-8')` untuk mencegah crash `cp1252` pada terminal Windows saat mencetak karakter Unicode/emoji log status.
- **B2 (Keputusan Teknis):**
  - Mengintegrasikan masukan `architecture_plan` secara langsung ke dalam prompt `developer_agent` agar kode yang dihasilkan selalu mematuhi modul dan kontrak interface dari System Architect.

### Ringkasan Distribusi Sumber Drift Iterasi 1b:
- **Intent Architect:** 0.0%
- **Agen:** 100.0% (Resolusi impor modul sandbox, streaming logging, pencegahan crash terminal Windows)
- **Eksternal:** 0.0%

### Severity Drift Keseluruhan:
**Minor** — Peningkatan robustitas eksekutor dan logging tanpa mengubah arsitektur 5 agen squad.
---

## ═══════════════════════════════════════════════════════════════════════════
---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 2 — 2026-09-07 19:41
## ═══════════════════════════════════════════════════════════════════════════

### Bagian A: Perubahan Scope dan Pendekatan
| Deskripsi Perubahan | Dampak terhadap Scope | Sumber |
|---|---|---|
| Penambahan REST Endpoint GET /api/projects/{name} untuk membaca konten file proyek | Positif (Memudahkan File Explorer frontend membaca isi file tanpa akses disk langsung) | Agen |
| Dukungan aksi ping-pong pada protokol WebSocket | Positif (Menjaga liveness heartbeat koneksi antara Flutter dan FastAPI) | Agen |
| Konfigurasi root pytest.ini untuk mengisolasi folder sandbox dan output | Positif (Mencegah collision modul saat running full test suite) | Agen |
| Protokol Watchdog Timer untuk pemantauan looping inferensi multi-agent | Positif (Mencegah unmonitored execution loop sesuai batas estimasi agen) | Intent Architect |

### Bagian B: Keputusan Mandiri Agen
- **B1 (Penambahan di luar spesifikasi):**
  - Menyimpan metadata proyek hasil eksekusi dalam format project_meta.json di setiap folder output untuk riwayat histori.
- **B2 (Keputusan Teknis):**
  - Menggunakan syncio.get_event_loop().run_in_executor untuk generator stream LangGraph agar loop asinkron WebSocket tidak terblokir selama komputasi LLM.
  - Menambahkan argumen isolasi -o python_files=test_*.py *_test.py pada invocation subprocess sandbox test runner.

### Ringkasan Distribusi Sumber Drift Iterasi 2:
- **Intent Architect:** 25.0% (Arahan watchdog timer untuk monitoring looping)
- **Agen:** 75.0% (Peningkatan kapabilitas REST, heartbeat websocket, non-blocking stream executor, isolasi pytest)
- **Eksternal:** 0.0%

### Severity Drift Keseluruhan:
**Minor** — Penguatan reliabilitas server web, pengujian end-to-end terisolasi, dan guardrail runtime tanpa mengubah arsitektur inti.

---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 3 — 2026-09-07 20:08
## ═══════════════════════════════════════════════════════════════════════════

### Bagian A: Perubahan Scope dan Pendekatan
| Deskripsi Perubahan | Dampak terhadap Scope | Sumber |
|---|---|---|
| Penambahan 5 Kartu Topologi Agen pada Workspace Tab Timeline | Positif (Memberikan representasi visual instan atas struktur squad multi-agent sebelum Iterasi 5) | Agen |
| Peluncuran browser headed Chrome interaktif dan build Windows Desktop bersamaan | Positif (Memenuhi arahan IA bahwa pengujian headed harus tampak di layar pengguna) | Intent Architect |

### Bagian B: Keputusan Mandiri Agen
- **B1 (Penambahan di luar spesifikasi):**
  - Menyediakan bottom status bar pada workspace untuk menampilkan status squad loop dan siklus IIDD saat ini.
- **B2 (Keputusan Teknis):**
  - Mengadopsi pola Riverpod 3 Notifier dan NotifierProvider secara menyeluruh untuk kompatibilitas jangka panjang.

### Ringkasan Distribusi Sumber Drift Iterasi 3:
- **Intent Architect:** 50.0% (Penegasan pengujian headed tampak langsung di layar IA)
- **Agen:** 50.0% (Topologi kartu agen visual, bottom status bar, migrasi Riverpod 3)
- **Eksternal:** 0.0%

### Severity Drift Keseluruhan:
**Minor** — Pengayaan antarmuka visual dan kepatuhan pengujian visual tanpa mengubah kontrak sistem.

---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 4 — 2026-09-07 21:19
## ═══════════════════════════════════════════════════════════════════════════

### Bagian A: Perubahan Scope dan Pendekatan
| Deskripsi Perubahan | Dampak terhadap Scope | Sumber |
|---|---|---|
| Penambahan Tombol Clear Text & Live Character Counter (`0 / 1000`) pada input prompt | Positif (Meningkatkan usability dan mencegah luapan konteks teks LLM) | Agen |
| Otomasi pendaftaran izin workspace terpadu ke `config.json` dan hook | Positif (Menghilangkan prompt izin berulang pada dokumen dan tooling proyek) | Intent Architect |

### Bagian B: Keputusan Mandiri Agen
- **B1 (Penambahan di luar spesifikasi):**
  - Menyediakan chip info performa dinamis ('Fast • Resident 6GB' vs 'High Accuracy • Cloud API') pada kartu Engine Selector.
- **B2 (Keputusan Teknis):**
  - Menyelaraskan timing asinkron `tester.pump(const Duration(seconds: 2))` pada pengujian widget Flutter untuk menangani transisi state simulasi deploy tanpa error.

### Ringkasan Distribusi Sumber Drift Iterasi 4:
- **Intent Architect:** 50.0% (Instruksi penghapusan konfirmasi izin berulang pada berkas yang sama)
- **Agen:** 50.0% (Penambahan counter karakter, tombol clear, chip info performa engine)
- **Eksternal:** 0.0%

### Severity Drift Keseluruhan:
**Minor** — Peningkatan kenyamanan pengguna (*developer experience*) dan proteksi batasan konteks tanpa deviasi dari spesifikasi fungsional REQ-019 s.d. REQ-022.
---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 5 — 2026-09-07 22:45
## ═══════════════════════════════════════════════════════════════════════════

### Bagian A: Perubahan Scope dan Pendekatan
| Deskripsi Perubahan | Dampak terhadap Scope | Sumber |
|---|---|---|
| Penambahan Visual Thought Stream dengan Collapsible Card & Filter | Positif (Memungkinkan pemantauan penalaran internal agen per peran secara transparan) | Agen |
| Otomasi Eksekusi Toolchain Nyata Dart/Flutter di Backend | Positif (Menggantikan tiruan mock Python dengan eksekusi compiler `dart test` subproses aktual) | Intent Architect |
| Penerapan Role-Based Token Budget (`num_predict: 300-1000`) | Positif (Memangkas latensi PM/Architect dari >120s menjadi ~24s, mencegah timeout browser) | Intent Architect |

### Bagian B: Keputusan Mandiri Agen
- **B1 (Penambahan di luar spesifikasi):**
  - Menerapkan mekanisme agent heartbeat interval 2.5 detik pada WebSocket untuk mencegah timeout UI saat LLM berpikir panjang.
  - Memotong `OLLAMA_NUM_CTX` dari 8192 ke 2048 agar 100% layer model berjalan di VRAM GPU 6GB tanpa thrashing PCIe.
- **B2 (Keputusan Teknis):**
  - Mengintegrasikan paket `flutter_markdown` adaptif untuk merender teks pemikiran Markdown secara kaya (*rich text*).

### Ringkasan Distribusi Sumber Drift Iterasi 5:
- **Intent Architect:** 50.0% (Otorisasi real toolchain execution, batasan token latensi)
- **Agen:** 50.0% (Thought stream collapsible, heartbeat interval, optimasi VRAM GPU)
- **Eksternal:** 0.0%

### Severity Drift Keseluruhan:
**Minor** — Peningkatan drastis integritas eksekusi dan responsivitas UI tanpa mengubah spesifikasi REQ-023 s.d. REQ-026.

---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 6 — 2026-09-08 s.d. 2026-09-10
## ═══════════════════════════════════════════════════════════════════════════

### Bagian A: Perubahan Scope dan Pendekatan
| Deskripsi Perubahan | Dampak terhadap Scope | Sumber |
|---|---|---|
| Protokol Pengujian Frozen Oracle Terkunci (Phase 0, 1, 2) | Positif (Mengeliminasi bias evaluasi semu dan mengisolasi variabel intervensi secara ilmiah) | Intent Architect |
| Eliminasi Total Mode ON (Oracle Dilution) dari Protokol Utama | Positif (Menjamin test suite acuan tidak dapat dimutasi atau direlaksasi oleh runtime) | Intent Architect |
| Arsitektur Pre-Freeze Contract Integrity Gate P0-2.1 | Positif (Mencegah kontrak antarmuka ompong atau menyimpang sebelum diserahkan ke Developer) | Intent Architect |
| Developer Gateway Abstraction Layer (OpenRouter Cloud/Frontier Support) | Positif (Mendukung pengujian komparatif frontier tanpa mengubah 100% squad pipeline lokal) | Intent Architect |
| Universal Environment Grounding Framework (D-074 & D-075) | Positif (Mencegah halusinasi API usang/deprecated secara proaktif sejak hulu PM & Architect) | Intent Architect & Agen |
| Generic Static Architect Blueprint Validator AST (D-078) | Positif (Menjamin konsistensi internal blueprint sintaksis dan parameter sebelum contract gate) | Intent Architect & Agen |
| Decoupled Dynamic Repair-Depth Budgets (A5/D5) | Positif (Memisahkan counter revisi AST dan Contract Gate, membuka pemulihan slow-convergent Loop 4) | Intent Architect |
| Improved Repentance Guidance (7-Step) & Rehabilitation State Memory (D10) | Positif (Menyediakan umpan balik diagnostik preskriptif dan melacak strategi gagal guna memutus perulangan error) | Intent Architect & Agen |

### Bagian B: Keputusan Mandiri Agen
- **B1 (Penambahan di luar spesifikasi):**
  - Implementasi sensor sintaksis resolusi tinggi `analyze_dart_bracket_balance()` di `diagnostic_parser.py` (P0-1.1) untuk mendiagnosis baris akar cascade compiler Dart.
  - Implementasi struktur memori rehabilitasi multi-loop (`repair_history`, `failed_strategies`, `known_good_constraints`) pada `SquadState`.
- **B2 (Keputusan Teknis):**
  - Merancang Executor v2 (`backend/executor_v2.py`) dengan mode baru `SAFE` sebagai kandidat default, menggantikan 9 aturan global regex destruktif dengan AST pre-flight linter murni dan rollback otomatis.
  - Menerapkan fallback semantik yang aman (`val if val is not None else default`) pada graph routing dan agent state.
  - Penegakan proteksi Blueprint Validator terhadap halusinasi lintas-task (mencegah impor `@app` FastAPI pada tugas kalkulator CLI Run 6).

### Ringkasan Distribusi Sumber Drift Iterasi 6:
- **Intent Architect:** 68.0% (Desain eksperimen terkontrol, arsitektur kontrak, grounding, batasan independen, repentance work order)
- **Agen:** 32.0% (Sensor kurung P0-1.1, implementasi AST validator, repentance guidance 7-step, memori rehabilitasi, fallback semantik safe)
- **Eksternal:** 0.0%

### Severity Drift Keseluruhan:
**Major (Positive Architectural Hardening)** — Transformasi arsitektural substansial yang mengalihkan sistem dari manipulasi runtime reaktif (regex rewriting) menuju pertahanan deterministik proaktif berbasis kontrak, AST validator, bimbingan preskriptif 7-elemen, dan isolasi kriptografis murni.

---

## ═══════════════════════════════════════════════════════════════════════════
## SESI LANJUTAN ITERASI 6 (DETERMINISTIC CEP, ENGINEERING DOCTRINE & RUN 4) — 2026-09-11
## ═══════════════════════════════════════════════════════════════════════════
*Catatan Status: Iterasi 6 tetap OPEN / ONGOING menunggu hasil peninjauan dan validasi akhir oleh Intent Architect.*

### Bagian A: Perubahan Scope dan Pendekatan
| Deskripsi Perubahan | Dampak terhadap Scope | Sumber |
|---|---|---|
| Perumusan Formal Engineering Doctrine 5 Poin (Authoritative Contract, Exception Compatibility, Behavioral Invariant, Causal Scope, Deterministic Verification) | Positif (Menetapkan doktrin rekayasa generik berbasis kontrak publik dan subtyping `issubclass` tanpa istilah non-formal) | Intent Architect |
| Penguncian Behavioral Invariant (`behavior lock > source-code lock`) | Positif (Mengunci perilaku/tes yang lulus tanpa melarang penambahan validasi pada fungsi yang sama) | Intent Architect |
| Dual-Evidence Ground Truth untuk Exception Compatibility (Traceback + AST Class Hierarchy Audit) | Positif (Memastikan resep `RX-B5-EXC-COMPAT-001` diverifikasi ganda via runtime pytest dan deklarasi AST) | Intent Architect |
| Pelacakan Riwayat Regresi Permanen (`ever_regressed: True`, strict transparency) | Positif (Mencegah penghapusan bukti historis jika invarian sempat regresi lalu pulih) | Intent Architect |
| Top-Ordering Canonical Prioritization & Budget Expansion pada Repair Directive | Positif (Mengeliminasi Silent Context Truncation dengan memastikan urutan kanonikal `failure → causal evidence → prescription → invariant → doctrine → verification` masuk sebelum info sekunder) | Intent Architect & Agen |
| Penerapan Prinsip Evidence Density | Positif (Menghapus `current_code_excerpt` redundan di CEP demi menghemat budget konteks untuk hal yang sudah ada di prompt utama) | Intent Architect |
| Identifikasi Function Boundary Blind Spot & Module-Level Validation Misattribution (E-057, D-082) | Positif (Membuka kebutuhan evolusi B5 dari module-level symbol binding menuju function-level symbol binding untuk menuntaskan 5/5 PASS) | Agen & Intent Architect |

### Bagian B: Keputusan Mandiri Agen
- **B1 (Penambahan di luar spesifikasi):**
  - Implementasi fungsi inspeksi deterministik `inspect_ast_exception_hierarchy()` di `backend/context_assembler.py` untuk membuktikan relasi pewarisan kelas target tanpa bergantung pada output LLM.
  - Audit komparatif AST dan trace telemetri Run 4 yang membuktikan pencapaian Zero Functional Regression (0.0% regresi pada 30 peluang).
- **B2 (Keputusan Teknis):**
  - Penataan ulang urutan seksi pada `render_repair_directive` mengikuti urutan kanonikal linier penentu tindakan.
  - Eliminasi cuplikan kode redundan di Authoritative Context dan ekspansi kuota render `_MAX_RENDER_CHARS` ke 4.500 karakter sebagai parameter engineering terukur.
  - Analisis forensik penempatan validasi `parse_matrix` vs fungsi aljabar murni `add_matrices`/`multiply_matrices` sebagai akar kebuntuan 2 tes dimensi.

### Ringkasan Distribusi Sumber Drift Sesi 2026-09-11:
- **Intent Architect:** 72.0% (Engineering Doctrine, Behavioral Invariant Lock, Dual-Evidence AST, Canonical Sequence, Evidence Density, Otorisasi Run 4)
- **Agen:** 28.0% (Deteksi Silent Context Truncation, AST hierarchy inspector, Top-Ordering Directive Prioritization, Identifikasi Function Boundary Blind Spot)
- **Eksternal:** 0.0%

### Severity Drift Keseluruhan:
**Major (Positive Semantic Hardening)** — Penyempurnaan arsitektural dari sekadar pengawasan sintaksis menuju pengawalan semantik hierarki tipe objek, jaminan keterbacaan instruksi tindakan (*actionable transparency*), dan pembuktian empiris preservasi invarian perilaku pada model lokal.


