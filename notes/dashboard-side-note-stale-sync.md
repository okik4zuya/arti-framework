# Bug: Side note dashboard tidak sinkron dengan `.side-note.md` yang diubah dari luar

Ditulis 2026-10-01 dari sesi project "Paper Review SLR SnO2 Photocatalyst". Belum ada file yang
diubah; ini diagnosis dan usulan perbaikan untuk sesi di project ARTi Framework.

Memori terkait: `~/.arti/memory/memories/dashboard-side-note.md` (desain panel, persistensi,
keybinding), `dashboard-keybindings.md`, `dashboard-ui-conventions.md`.

## 1. Gejala

Claude Code (sesi project SLR) merapikan `.side-note.md` langsung di disk: menghapus 20 baris
duplikat, lalu menulis ulang daftar 21 paper yang belum bisa diunduh. Peneliti membuka dashboard dan:

- panel Side note masih menampilkan isi lama (dengan duplikat), padahal file di disk sudah bersih
  (diverifikasi: 21 key unik, 42 baris, tanpa baris ganda);
- duplikat yang sudah dihapus sempat muncul lagi, kemungkinan karena autosave panel menimpa file
  dengan teks lamanya (ini dugaan dari kode, belum direproduksi di browser).

## 2. Penyebab (dari `dashboard/arti-dashboard.html`, sekitar baris 3728-3830)

- `loadSideNoteForProject(projectPath)` (baris ~3765) membaca `.side-note.md` **hanya** saat
  project dimuat atau saat ganti project di Workspace picker (dipanggil dari `renderFilesPanel()`).
  Tidak ada pembacaan ulang saat panel dibuka (`openSideNote`, ~3844), saat jendela fokus kembali,
  atau secara berkala.
- `writeSideNote()` (~3798) menulis `body.value` **utuh** ke file tanpa memeriksa apakah file di
  disk berubah sejak dibaca. Itu last-writer-wins: edit dari luar (Claude Code, editor lain,
  skrip) ditimpa oleh teks panel yang basi pada autosave berikutnya (debounce 800 ms setelah
  mengetik, atau Ctrl+S).
- Desain awal memang memakai "isi selalu dibaca dari disk saat load" (lihat memori
  `dashboard-side-note.md`), tapi asumsinya hanya panel yang menulis file itu. Sekarang Claude
  Code juga sering mengedit `.side-note.md` (daftar fulltext yang gagal diunduh, catatan sementara),
  jadi asumsi itu tidak berlaku lagi.

## 3. Yang diinginkan

1. Panel menampilkan isi disk terbaru tanpa harus ganti project atau restart aplikasi.
2. Autosave tidak boleh diam-diam menimpa perubahan dari luar.
3. Perilaku yang sudah disepakati tetap: autosave diam (tanpa status "Saved", hanya error), Ctrl+S
   satu-satunya yang menampilkan "Saved", `Ctrl+Alt+N` toggle, posisi/ukuran panel di
   `localStorage` (`arti-side-note-ui`), isi tidak pernah di `localStorage`.

## 4. Usulan perbaikan (urut dari paling kecil)

- **A. Muat ulang saat panel dibuka dan saat jendela/panel kembali fokus**, hanya jika panel tidak
  "dirty" (tidak ada ketikan yang belum tersimpan). Perlu flag `sideNoteDirty` yang di-set di
  handler `input` dan di-reset setelah `writeSideNote` sukses atau setelah load.
- **B. Deteksi konflik sebelum menulis.** Simpan `mtime` (atau hash isi) file saat terakhir
  dibaca/ditulis. Sebelum `writeSideNote`, baca ulang metadata; kalau berubah dari luar:
  - panel tidak dirty: ambil isi baru (tanpa menimpa);
  - panel dirty: jangan menimpa, tampilkan status error singkat ("File diubah dari luar") dan beri
    pilihan memuat ulang atau menimpa. Ini mengikuti aturan "kegagalan selalu ditampilkan" yang
    sudah ada.
  Cek apakah endpoint `/chat/project-files/read` sudah mengembalikan `mtime`; kalau belum, tambahkan
  di `dashboard/server/chat.py` (tidak diubah di desain awal, "no server changes needed").
- **C. Polling ringan** (misal tiap 3-5 detik, hanya saat panel terbuka dan tidak dirty) sebagai
  pengganti fokus/visibility event. Lebih sederhana dari file watcher, cukup untuk skala ini.
- Rekomendasi: A + B. C hanya kalau fokus event tidak cukup (jendela native pywebview mungkin tidak
  mengirim `focus`/`visibilitychange` seperti browser, jadi uji dulu).

## 5. Uji yang perlu lolos

1. Buka panel, edit file dari luar (`echo x >> .side-note.md`), buka ulang/fokus panel: isi baru
   muncul tanpa mengetik.
2. Edit dari luar saat panel terbuka dan tidak dirty: panel ikut berubah (atau berubah saat fokus).
3. Ketik di panel, edit dari luar, tunggu autosave: file di disk **tidak** tertimpa diam-diam;
   muncul pesan konflik.
4. Tidak ada status "Saved" pada autosave biasa; Ctrl+S tetap menampilkannya.
5. Ganti project bolak-balik: tetap memuat catatan project yang benar (jaga `sideNoteLoadToken`
   untuk balapan load).
6. Uji di jendela native (pywebview), bukan hanya browser: `start-arti-dashboard.bat`.

## 6. Catatan

- Setelah diperbaiki, perbarui `dashboard-side-note.md` (bagian Persistence) dan tambahkan
  baris Change log.
- Sementara belum diperbaiki: muat ulang dashboard atau ganti project dan kembali sebelum mengetik
  di panel, supaya tidak menimpa edit dari luar.
- Belum diuji end-to-end di browser; semua di atas dari membaca kode dan memori, bukan dari
  menjalankan dashboard.
