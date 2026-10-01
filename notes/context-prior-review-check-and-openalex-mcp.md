# Konteks: Prior-Review Check di ARTi-SLR + upgrade arti-ref-search-mcp

Ditulis 2026-10-01 dari sesi project "Paper Review SLR SnO2 Photocatalyst", lalu dipindahkan ke
`~/.arti/notes/` (proyek ARTi Framework, tempat tool dan skill-nya berada; bukan proyek "ARTi
Workflow" yang hanya menyimpan diagram/ebook). Belum ada file skill/tool yang diubah; semua di
bawah ini baru diagnosis dan usulan.

Memori terkait di proyek ini: `memory/memories/arti-ref-search-mcp-build.md` (riwayat build MCP,
termasuk catatan `~/.claude.json` "belum diverifikasi restart"; sesi 2026-10-01 berhasil memuat
dan memanggil tool-nya, jadi sudah terbukti jalan) dan `memory/memories/arti-slr-build.md`
(riwayat build skill ARTi-SLR). Draf plan: `notes/plan-prior-review-check-draft.md` (salinan dari
`C:\Users\user\.claude\plans\elegant-finding-wren.md`).

## 1. Asal masalah

Proyek SLR SnO2 untuk fotoreduksi CO2 sudah sampai Stage 2 (35 paper lolos Gate 1, protokol terkunci
sejak 2026-09-27). Saat peneliti bertanya "kapan menganalisis novelty topiknya", ternyata **tidak ada
langkah pengecekan review terdahulu** di workflow:

- `arti-slr-workflow.png`: alurnya Topik awal → RQ + PICO(C) → Protokol → Search → Screening → ...
  → Matriks Sintesis → Idea Canvas (+Novelty). Tidak ada kotak untuk mengecek apakah review serupa
  sudah ada.
- `~/.arti/skills/ARTi-SLR/SKILL.md`, Key Principle 9: novelty scoring (Idea Canvas) hanya untuk
  celah studi empiris di masa depan, bukan untuk novelty review itu sendiri.
- `references/slr-manuscript-blueprint-template.md`, Introduction paragraf 2 ("why a review is
  needed now — prior reviews' scope/date gap") tidak punya langkah hulu yang menghasilkan isinya.
- Efeknya: pengecekan paling cepat baru terjadi di Stage 4 atau saat menulis Introduction. Kalau
  ternyata sudah ada review yang hampir sama, ekstraksi puluhan paper sudah terlanjur dikerjakan.

## 2. Usulan perubahan workflow ("Cek Review Terdahulu")

- **Posisi:** satu kotak putih (dibuat model) di antara "RQ + PICO(C)" dan "Protokol". Alasannya:
  hasilnya bisa mengubah RQ/PICO(C) dan harus ada sebelum protokol terkunci. Posisi setelah
  Protokol ditolak (verdict "mirip" akan membuka protokol yang sudah terkunci); posisi di Idea
  Canvas ditolak (terlalu terlambat dan menilai hal berbeda).
- **Output:** `slr/prior-reviews.md`: tabel review (tahun, sistematis/naratif, cakupan SnO2 vs
  oksida umum, cakupan CO2, strategi modifikasi, jendela tahun) + verdict + kalimat pembeda untuk
  Introduction paragraf 2.
- **Verdict:** `clear` / `partial overlap` (tulis pembeda) / `near-duplicate` (rekomendasi
  reframing RQ/PICO(C), diperlakukan sebagai membuka keputusan yang sudah "confirmed").
- **Titik sentuh di skill** (edit hanya di `~/.arti/skills/ARTi-SLR/`, bukan symlink
  `~/.claude/skills/`):
  1. `references/stage1-question-and-protocol.md`: tambah Part C antara Part A dan Part B.
  2. File baru `references/prior-review-check-template.md`.
  3. `SKILL.md`: daftar Core Documents (jumlah dokumen berubah), diagram Workflow Stages, stub
     Stage 1, Key Principles (tambah prinsip baru, perjelas Principle 9), catatan "Not this skill".
  4. `references/slr-manuscript-blueprint-template.md`: paragraf 2 menunjuk ke `prior-reviews.md`.
  5. `references/stage4-synthesis-and-handoff.md` + `slr-handoff-template.md`: catatan ulang
     pencarian review sebelum submit + pointer ke `prior-reviews.md`.
- **Diagram PNG** dimiliki peneliti dan digambar manual di draw.io. Perubahan: satu kotak putih
  baru, panah vertikal masuk dan keluar, geser kotak Protokol dst. ke bawah (jarak saat ini hanya
  ~30 px). Berlaku juga untuk salinan sederhana di `figures/arti-slr-workflow.png` milik skill.
- Draf plan lengkap (Part A untuk proyek SnO2, Part B untuk skill): `notes/plan-prior-review-check-draft.md`.
  Plan itu **belum disetujui**; peneliti meminta diskusi dulu. Part A dijalankan di proyek SnO2,
  bukan di sini; Part B (skill) dikerjakan di sini setelah MCP siap.

## 3. Cara menjalankan pengecekan: kesimpulan diskusi

- Volumenya kecil (puluhan hit, bukan ratusan), jadi **tidak memakai alur RIS** seperti SLR utama.
  Tabel yang dibaca langsung sudah cukup.
- **Review terdahulu jangan masuk `arti-lit`** (rekomendasi, belum dikonfirmasi peneliti). Baris di
  sana ikut terhitung di PRISMA Flow dan mengacaukan angka SLR. Simpan di `slr/prior-reviews.md`.
- Pencari utama: Claude lewat `arti-ref-search-mcp` (OpenAlex) dan scite, query sempit berfrasa
  satu per angle (sesuai `working-preferences.md`).
- Opsional: peneliti menjalankan satu query Scopus `DOCTYPE(re)` dan menempel hasilnya di chat,
  karena SLR-nya Scopus-only. RIS hanya kalau hit di atas ~50 dan butuh dedup.
- **Dua keputusan masih terbuka untuk peneliti:** (a) review terdahulu tetap di luar `arti-lit`
  atau disimpan di sana dengan penanda khusus; (b) query Scopus `DOCTYPE(re)` wajib atau opsional.

## 4. Hambatan teknis yang memicu upgrade MCP

Server di `~/.arti/tools/arti-ref-search-mcp/` (didaftarkan di `~/.claude.json` user scope dan
`~/.arti/.mcp.json`). Struktur: `server.py` (satu `@mcp.tool()` tipis), `paper.py`, `http_client.py`,
`sources/base.py`, `sources/openalex.py`, `README.md`.

Tool tunggal saat ini:

```
search_openalex_works(query, max_results=10, year_from=None, year_to=None,
                      open_access_only=False, sort_by_citations=False)
```

Yang dipakai dari OpenAlex hanya `search` (full-text sederhana), `from/to_publication_date`,
`open_access.is_oa`, dan `sort=cited_by_count:desc`. Akibatnya untuk pengecekan review:

- **Tidak ada filter tipe dokumen** (`type:review`). Review tidak bisa dipisahkan dari artikel
  biasa; harus menebak lewat kata "review" di query lalu menyaring manual.
- Tidak bisa membatasi pencarian ke judul/abstrak saja (`title_and_abstract.search`), padahal
  `search` biasa mencocokkan teks lebih luas dan menambah noise.
- Tidak ada pagination (cursor) dan batas `per_page` 200, jadi hasil di atas 200 tidak terjangkau.
- Tidak ada filter `is_retracted:false`, bahasa, ambang sitasi, topik/konsep, atau sumber/jurnal.
- Tidak ada penelusuran sitasi (siapa mengutip / dikutip paper X) dan tidak ada `group_by`
  (misalnya hitung hit per tahun atau per tipe tanpa menarik semua record).
- Field yang dikembalikan tetap (abstrak penuh ikut terbawa), tidak bisa dipangkas dengan `select`.
  Untuk pengecekan puluhan hit ini memboroskan konteks.
- `Paper` tidak menyimpan `type`, `is_retracted`, `language`, atau nama jurnal, jadi hasil tidak
  bisa difilter atau diurutkan di sisi Claude setelah diterima.

## 5. Arah upgrade yang diusulkan

Tujuan peneliti: lebih fleksibel, memakai fitur filter bawaan OpenAlex. Daftar filter di bawah
berasal dari pengetahuan umum tentang OpenAlex API dan **belum diverifikasi ke dokumentasi saat
ini**; cek dulu sebelum implementasi (mis. `https://docs.openalex.org/api-entities/works/filter-works`).

Kandidat:

1. **Parameter filter eksplisit** pada tool: `work_type` (`review`, `article`, ...),
   `search_in` (default / judul / judul+abstrak), `language`, `exclude_retracted` (default true),
   `min_citations`, `has_abstract`, `source_issn` atau nama jurnal, `topic_id`/`concept_id`.
2. **Parameter `filters` bebas** (string atau dict OpenAlex mentah) sebagai jalan keluar untuk filter
   yang belum dibungkus parameter sendiri, tanpa perlu mengubah server tiap kali.
3. **Pagination:** `cursor` / pengambilan berhalaman sampai `max_results`, sambil tetap melaporkan
   total hit (`meta.count`) agar pengecekan "berapa banyak hit" bisa dicatat di search log.
4. **Tool terpisah untuk agregasi:** `count_openalex_works(query, filters, group_by)` untuk melihat
   jumlah hit per tahun/tipe tanpa menarik record (cocok untuk mengukur sempit-lebarnya query).
5. **Tool penelusuran sitasi:** works yang mengutip / dikutip sebuah DOI atau OpenAlex ID
   (`cites:`, `referenced_works`, `related_works`).
6. **Kontrol keluaran:** `select`/`fields` dan opsi `include_abstract` supaya hasil ringkas;
   tambahkan `type`, `is_retracted`, `language`, `venue` ke `Paper`.
7. **Operator boolean dalam query** (AND/OR/NOT dan frasa berkutip) diteruskan apa adanya; dokumentasikan
   perilakunya agar sesuai gaya query sempit di `working-preferences.md`.
8. Pertahankan: error dilempar (`SourceFetchError`) bukan mengembalikan `[]` diam-diam; `mailto` dan
   `OPENALEX_API_KEY` opsional; struktur tambah-sumber lewat `PaperSource`; README dan
   `notes/openalex-api.md` ikut diperbarui.

Setelah upgrade selesai, langkah "Cek Review Terdahulu" di skill bisa menyebut tool dan parameter
yang tepat (`work_type="review"`), dan Part C di skill ditulis mengacu ke tool itu.

## 6. Status proyek SnO2 SLR (untuk konteks, tidak perlu dikerjakan di sesi baru)

- Stage 1 dan pencarian Stage 2 selesai; Gate 1 selesai (35 lolos, 50 ditolak).
- Fulltext: 23 dari 35 sudah ada di `literature/fulltext/`; 12 belum bisa diunduh (daftar di
  `.side-note.md` proyek itu). `memory/todo-list.md` proyek itu masih menandai pengambilan fulltext
  belum dimulai, jadi perlu dikoreksi di sesi proyek itu.
- Gate 2 (eligibilitas) menunggu hasil pengecekan review terdahulu, yang menunggu upgrade MCP atau
  dikerjakan dengan tool yang ada.
- Dua artikel review sudah ada di korpus tetapi ditolak di Gate 1: `pinto-2022`, `lu-2014`.

## 7. Titik awal yang disarankan untuk sesi ini

1. Verifikasi daftar filter OpenAlex ke dokumentasi terbaru.
2. Putuskan paket parameter (poin 5.1-5.2) dan apakah agregasi/sitasi (5.4-5.5) masuk tahap ini.
3. Implementasi di `~/.arti/tools/arti-ref-search-mcp/`, uji dengan query nyata (SnO2 + CO2
   photoreduction, `work_type="review"`), lalu perbarui README.
4. Baru setelah itu, ubah skill ARTi-SLR sesuai bagian 2.
