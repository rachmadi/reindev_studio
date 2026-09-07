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
