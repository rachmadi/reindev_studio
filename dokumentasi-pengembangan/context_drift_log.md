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

