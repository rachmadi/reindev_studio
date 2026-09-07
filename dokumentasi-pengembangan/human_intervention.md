# Human Intervention Log — ReinDev Studio
Dokumen ini mencatat setiap koreksi, klarifikasi, atau intervensi langsung dari Intent Architect (Manusia) ke Agen.

---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 1a — 2026-09-07
## ═══════════════════════════════════════════════════════════════════════════

| No | Waktu | Bentuk Intervensi Intent Architect | Klasifikasi Masalah | Dampak & Tindakan Agen |
|---|---|---|---|---|
| 1 | 17:28 | Mengoreksi bahwa proyek yang dibangun adalah studio multi-agent (ReinDev Studio), bukan FDM Visual Designer (yang hanya merupakan dokumen acuan metodologi IIDD). | Salah paham intent / domain | Agen menyelaraskan kembali fokus produk ke ReinDev Studio dan meminta masukan nama produk. |
| 2 | 17:34 | Menetapkan nama resmi produk: **ReinDev Studio** (berasal dari Rekayasa Informatika). | Keputusan strategis / Branding | Agen meresmikan penamaan seluruh paket, judul dokumen, dan deskripsi produk. |
| 3 | 17:36 | Menginstruksikan penghapusan prefix `00_` pada file pra-iterasi (`estimasi_waktu.md` dan `requirement_traceability_matrix.md`). | Konvensi penamaan berkas | Agen menyesuaikan nama kedua berkas dokumentasi tanpa awalan angka 00. |
| 4 | 17:58 | Menginstruksikan bahwa pengujian pra-handoff harus dilakukan secara nyata, modul UI wajib diuji secara *headed interactive testing* dengan screenshot, analisis visual, dan penyiapan test case terstruktur bagi IA. | Tata kelola & Metodologi pengujian | Agen menambahkan protokol pengujian visual dan test case IA ke dalam spesifikasi master (`SPESIFIKASI_REINDEV_STUDIO.md`). |
| 5 | 18:02 | Menegakkan aturan tata kelola mutlak: Agen DILARANG commit ke GitHub sebelum status validasi `PASS` atau `PASS WITH NOTES` diberikan oleh IA (kecuali diminta eksplisit oleh IA). | Tata kelola rilis / Governance Gate | Agen mengunci proses commit; seluruh berkas ditahan di lingkungan lokal hingga IA menyatakan lulus. |
| 6 | 18:03 | Menegaskan bahwa seluruh berkas dokumentasi pengembangan wajib disiapkan dan dibuat secara lokal SEBELUM status validasi diberikan oleh IA. | Prosedur audit dokumentasi | Agen membuat seluruh berkas dokumentasi di lokal sebelum penyerahan handoff. |
| 7 | 18:24 | Menginstruksikan pembersihan teks obrolan pada output agen, pengukuran waktu realisasi empiris berbasis timestamp nyata (bukan angka perkiraan), dan penegakan kelengkapan 9 dokumen pengembangan. | Kualitas luaran & Akurasi empiris | 1. Agen memperbarui parser developer dengan `clean_code_content`.<br>2. Agen mengukur durasi nyata berbasis timestamp (7 menit).<br>3. Agen menyusun lengkap 9 dokumen pengembangan sesuai Bab 8.4 spesifikasi. |
---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 1b — 2026-09-07
## ═══════════════════════════════════════════════════════════════════════════

| No | Waktu | Bentuk Intervensi Intent Architect | Klasifikasi Masalah | Dampak & Tindakan Agen |
|---|---|---|---|---|
| 8 | 18:36 | Menetapkan formula baku perhitungan waktu realisasi: Pengembangan + Total Pengujian & Uji Ulang + Total Perbaikan. | Metodologi & Pengukuran Empiris | Agen merevisi total waktu realisasi di seluruh berkas dokumentasi sesuai formula IIDD. |
| 9 | 18:38 | Menginstruksikan eksekusi resmi Iterasi 1b (*Squad Pipeline & Self-Healing Loop*). | Alur Kerja / Task Authorization | Agen mengimplementasikan modul Architect, Tester, Sandbox Executor, Reviewer, dan Graph. |
| 10 | 19:03 | Menanyakan status penyelesaian eksekusi iterasi ("Belum selesai?"). | Monitoring / Query Progres | Agen melakukan investigasi mendalam, mengidentifikasi akar masalah sandbox package import, dan menerapkan perbaikan. |
---

## ═══════════════════════════════════════════════════════════════════════════
---

## ═══════════════════════════════════════════════════════════════════════════
## ITERASI 2 — 2026-09-07
## ═══════════════════════════════════════════════════════════════════════════

| No | Waktu | Bentuk Intervensi Intent Architect | Klasifikasi Masalah | Dampak & Tindakan Agen |
|---|---|---|---|---|
| 11 | 19:16 | Memberikan status PASS resmi untuk Iterasi 1b dan menginstruksikan eksekusi Iterasi 2. | Alur Kerja / Task Authorization | Agen mengunci commit Iterasi 1b ke GitHub dan langsung memulai eksekusi Iterasi 2. |
| 12 | 19:21 | Mengajukan pertanyaan verifikasi mendalam ('Sebentar. Kamu sudah menyelesaikan iterasi 2? Kamu yakin?') terkait kelengkapan bukti eksekusi real-time. | Verification Probe / Quality Assurance | Agen mengidentifikasi kebutuhan pembuktian pengujian live streaming E2E WebSocket dengan inferensi nyata Ollama, bukan sekadar unit test simulasi. |
| 13 | 19:27 | Menanyakan progres eksekusi ('Belum selesai?') saat inferensi multi-agent pipeline sedang berjalan di backend. | Monitoring / Liveness Query | Agen memverifikasi log proses LangGraph dan memastikan proses live streaming WebSocket berjalan aktif. |
| 14 | 19:32 | Mengingatkan durasi eksekusi ('Sudah lebih dari 4 menit') yang melampaui durasi respons instan awal. | SLA & Duration Awareness | Agen menjelaskan bahwa beban komputasi LLM lokal 7B dengan inferensi multi-turn dan self-healing loop membutuhkan komputasi lebih intensif dibanding unit test cepat. |
| 15 | 19:35 | Memberikan instruksi metodologis untuk memantau perulangan: 'Karena sering terjadi looping, cek dengan timer sesuai waktu estimasi yang dibuat agen'. | Governance & Safety Guardrail | Agen mengadopsi mekanisme watchdog timer terpadu untuk memantau siklus eksekusi agar tidak terjadi unmonitored loop dan menjaga batas waktu toleransi. |
