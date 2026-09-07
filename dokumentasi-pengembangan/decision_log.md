# Decision Log — ReinDev Studio
Dokumen ini mencatat seluruh keputusan arsitektur, teknis, dan metodologis yang diambil selama pengembangan.

---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 1a — 2026-09-07 18:10
## ═══════════════════════════════════════════════════════════════════════════

1. **Keputusan Arsitektur State Management (LangGraph TypedDict):**
   - *Konteks:* Dibutuhkan wadah state yang ringan dan kompatibel dengan LangGraph StateGraph untuk membawa konteks antar-node agen.
   - *Keputusan:* Menggunakan `SquadState(TypedDict)` di `backend/state.py`.
   - *Rasional:* TypedDict memberikan validasi tipe statis di IDE tanpa overhead komputasi serialisasi Pydantic yang berat di setiap siklus node.

2. **Strategi Single Resident Model di VRAM 6GB:**
   - *Konteks:* Laptop pengembang memiliki batas hardware VRAM 6GB. Menjalankan dua model lokal berbeda memicu *model-swapping* yang memakan waktu 5–8 detik tiap pergantian giliran.
   - *Keputusan:* Mengunci model default Ollama ke satu model resident: `qwen2.5-coder:7b` dengan parameter `num_ctx: 8192` dan `temperature: 0.2`.
   - *Rasional:* Model tetap berada di memori GPU secara permanen, inferensi berjalan pada kecepatan 35–45 token/detik, dan suhu laptop tetap stabil.

3. **Format Blok Penanda File Khusus (`=== FILE: [nama] ===`) & Sanitasi Ketat:**
   - *Konteks:* Model LLM lokal sering kali menyertakan teks obrolan pembuka atau penutup di luar blok kode markdown.
   - *Keputusan:* Mewajibkan Developer Agent membungkus setiap file dalam format blok penanda `=== FILE: ... ===` dan memproses output melalui `clean_code_content` untuk membuang segala teks percakapan.
   - *Rasional:* Menjamin keandalan ekstraksi file kode ke dalam dictionary secara deterministik dan bersih dari teks pengganggu.
4. **Standardisasi Formula Perhitungan Waktu Realisasi IIDD:**
   - *Konteks:* Dalam metodologi IIDD, waktu realisasi sering kali keliru disederhanakan hanya sebagai waktu penulisan kode awal (coding time).
   - *Keputusan:* Menetapkan formula baku perhitungan waktu realisasi:
     \\text{Total Waktu Realisasi} = \\text{Waktu Pengembangan} + \\text{Total Waktu Pengujian \\& Uji Ulang} + \\text{Total Waktu Perbaikan} + \\text{Waktu Dokumentasi}
   - *Rasional:* Mencerminkan beban kerja rekayasa perangkat lunak yang komprehensif dan akurat untuk studi empiris IIDD.
---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 1b — 2026-09-07 19:11
## ═══════════════════════════════════════════════════════════════════════════

| ID | Keputusan | Alternatif yang Dipertimbangkan | Alasan Dipilih | Diubah? |
|---|---|---|---|---|
| D-005 | Auto-scaffold `__init__.py` pada setiap folder sandbox | Mewajibkan LLM membuat sendiri `__init__.py` | Model LLM sering mengabaikan pembuatan file kosong `__init__.py`, menyebabkan `ModuleNotFoundError` pada test runner | Tidak |
| D-006 | Penyuntikan Rencana Arsitektur ke Prompt Developer | Hanya memberikan spesifikasi PM ke Developer | Menjaga konsistensi struktur folder dan kontrak interface antar modul yang telah ditetapkan Architect | Tidak |
| D-007 | Batas Maksimal Self-Healing Loop: 3 Putaran | Loop tanpa batas (infinite loop) / 1 kali loop | 3 putaran memberikan kesempatan cukup bagi LLM untuk memperbaiki bug tanpa risiko kehabisan kuota/VRAM tak berujung | Tidak |
| D-008 | Logging Streaming per Node pada StateGraph | Menunggu seluruh graph selesai (`invoke`) | Memberikan transparansi real-time atas progres tiap agen dan memudahkan debugging jika salah satu agen mengalami kendala | Tidak |
---

## ═══════════════════════════════════════════════════════════════════════════
---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 2 — 2026-09-07 19:41
## ═══════════════════════════════════════════════════════════════════════════

| ID | Keputusan | Alternatif yang Dipertimbangkan | Alasan Dipilih | Diubah? |
|---|---|---|---|---|
| D-009 | Arsitektur Decoupled FastAPI + WebSocket Hub | Long-polling HTTP / Server-Sent Events (SSE) | WebSocket bersifat dua arah (full-duplex) sehingga klien Flutter dapat mengirim interupsi/perintah dan menerima streaming event dalam koneksi tunggal | Tidak |
| D-010 | Asynchronous Thread Executor untuk StateGraph Stream | Menjalankan stream langsung secara sinkron di event loop | Mencegah event loop asyncio terblokir saat LangGraph melakukan inferensi LLM atau eksekusi sandbox | Tidak |
| D-011 | Penyimpanan Output Proyek Berbasis Timestamp Slug (output/project_YYYYMMDD_HHMMSS) | Menimpa folder output tunggal | Menjaga riwayat hasil generate proyek agar tidak hilang dan dapat diinspeksi kembali di File Explorer | Tidak |
| D-012 | Protokol Watchdog Timer untuk Monitoring Inferensi & Loop Multi-Agent | Membiarkan eksekusi berjalan tanpa timer eksternal | Menghindari kondisi loop tak terpantau (unmonitored looping) dan memastikan agen memberikan laporan berkala sesuai batas estimasi | Tidak |

---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 3 — 2026-09-07 20:08
## ═══════════════════════════════════════════════════════════════════════════

| ID | Keputusan | Alternatif yang Dipertimbangkan | Alasan Dipilih | Diubah? |
|---|---|---|---|---|
| D-013 | Penerapan Riverpod 3 dengan Pola Notifier & NotifierProvider | StateProvider (legacy/deprecated di Riverpod 3) atau ChangeNotifier | Notifier adalah standar resmi Riverpod 3 yang menawarkan *type-safety*, manajemen siklus hidup objek yang lebih bersih, dan performa reaktif optimal | Tidak |
| D-014 | Layout Scaffold Studio 3-Panel Responsif (330px Left Hub + Flexible Workspace) | Tata letak satu kolom / wizard step-by-step | Memberikan visibilitas terpadu bagi software engineer untuk mengontrol parameter di kiri sambil memantau timeline dan hasil kode di kanvas utama | Tidak |
| D-015 | Desain Tema Ganda Material Design 3 (Slate Dark #0B0F19 & Slate Light #F8FAFC) | Tema tunggal tanpa opsi toggle | Mengakomodasi preferensi visual developer dalam sesi coding panjang sekaligus memenuhi standar aksesibilitas kontras MD3 | Tidak |
| D-016 | Protokol Headed Interactive Testing Langsung di Layar Desktop Pengguna | Pengujian headless murni di background | Memastikan Intent Architect dapat menginspeksi secara visual, berinteraksi langsung (klik tombol, toggle tema), dan menguji responsivitas antarmuka di layar riil | Tidak |

---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 4 — 2026-09-07 21:19
## ═══════════════════════════════════════════════════════════════════════════

| ID | Keputusan | Alternatif yang Dipertimbangkan | Alasan Dipilih | Diubah? |
|---|---|---|---|---|
| D-017 | Multiline TextField dengan Live Character Counter & Validasi Visual Bersih | Pop-up modal dialog alert saat string kosong | Validasi teks merah inline di bawah field lebih bersahabat (*developer-friendly*), tidak menginterupsi alur kerja, dan memberikan kejelasan batasan konteks LLM (0–1000 karakter) | Tidak |
| D-018 | Dynamic Badge 'LOCAL RESIDENT' (Emerald) vs 'CLOUD OPENROUTER' (Indigo) pada Engine Selector Card | Dropdown polos tanpa indikator visual | Memberikan penegasan visual instan kepada Intent Architect mengenai lingkungan inferensi yang sedang aktif (efisiensi VRAM 6GB lokal vs latensi cloud) | Tidak |
| D-019 | Penggunaan ChoiceChips untuk Bahasa Target & Slider untuk Max QA Loops | Dropdown teks konvensional / input angka teks bebas | ChoiceChips dan Slider memberikan feedback taktil cepat, mencegah input di luar rentang (1–5 loop), dan mengeliminasi kesalahan pengetikan nama bahasa | Tidak |
| D-020 | Otomasi Sistem Izin Terfokus via PreToolUse Lifecycle Hook (`.agents/hooks.json`) | Mengandalkan dialog izin berulang default Antigravity / menonaktifkan seluruh izin | Mengeliminasi dialog izin yang berulang untuk aksi yang telah disetujui sebelumnya (git, flutter, python, inspeksi) khusus pada workspace ReinDev Studio tanpa mengorbankan keamanan sistem global | Tidak |
| D-021 | Tombol Clear Prompt Ganda (SuffixIcon 'x' di TextField & Tombol '✕ Hapus' di Header) | Hanya mengandalkan seleksi teks manual / backspace | Fleksibilitas interaksi tingkat tinggi; merespon intervensi IA No. 28 (TC-IA-03) agar pengguna dapat mereset teks prompt panjang dan counter karakter kembali ke 0 dalam satu klik | Tidak |
| D-022 | Injeksi Anti-Cache Script di `web/index.html` & Peluncuran Profil Bersih `--disable-cache` | Meminta pengguna membersihkan cache browser secara manual setiap rilis baru | Menghilangkan friksi penyerahan build web yang diakibatkan CacheStorage Service Worker Flutter Web yang agresif; memastikan layar monitor fisik IA selalu menerima kompilasi teraktual | Tidak |

