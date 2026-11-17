# Panduan Alur Kerja Git Bebas Konflik (Kelompok 9)

Panduan ini wajib diikuti oleh seluruh anggota tim (**Orang 1, Orang 2, Orang 3, dan Orang 4**) agar tidak terjadi tabrakan kode (*merge conflict*), perbedaan baris baru (*line ending mismatch*), atau penimpaan pekerjaan rekan satu tim.

---

## 1. Golden Rules (Aturan Emas Tim)

1. 🚫 **JANGAN PERNAH `git commit` / `git push` langsung ke branch `main`!**
   * Branch `main` **dilindungi (*protected*)**. Semua kode baru hanya boleh masuk melalui Pull Request (PR) yang telah di-review dan lolos test.
2. 🔄 **Satu Fitur = Satu Branch.**
   * Setiap tugas dibuatkan branch terpisah yang dicabangkan dari `main` terbaru.
3. 🧪 **Wajib Lolos `pytest` Sebelum Buka PR.**
   * PR yang menyebabkan tes gagal (`failed`) **tidak akan di-merge**.
4. ⏱️ **Pull Sering-Sering (*Sync Early, Sync Often*).**
   * Sebelum mulai ngoding di hari baru, selalu tarik versi terbaru dari `origin main`.

---

## 2. Pencegahan Masalah Line Ending (Windows vs WSL/Linux)

Karena anggota tim ada yang memakai Windows (PowerShell/CMD) dan ada yang memakai WSL/Linux, Git sering mendeteksi ribuan baris berubah semu akibat perbedaan karakter enter (`CRLF` vs `LF`).

### Langkah Wajib Setiap Anggota (Jalankan sekali di terminal masing-masing):

* **Jika Anda menggunakan Windows (PowerShell / CMD / Git Bash):**
  ```bash
  git config --global core.autocrlf true
  ```
* **Jika Anda menggunakan WSL / Linux / macOS:**
  ```bash
  git config --global core.autocrlf input
  ```
*(Proyek ini sudah dilengkapi file `.gitattributes` untuk memastikan semua file teks disimpan dalam format `LF` secara otomatis).*

---

## 3. Matriks Pembagian File (*File Ownership*)

Konflik Git terjadi jika **dua orang mengedit baris yang sama di file yang sama**. Untuk mencegahnya, patuhi pembagian wilayah berkas berikut:

| Peran | Wilayah Kerja Eksklusif (Bebas Edit) | Berkas Bersama (*Shared*) | Aturan Khusus |
|---|---|---|---|
| **Orang 1 (Lead)** | `experiments/run_eval.py`, `docs/results/baseline.md`, `docs/report/methodology.md` | `config/default.yaml` | Menjaga `retrieval:` & `evaluation:` di config. |
| **Orang 2 (Query)** | `src/impact_retrieval/query/`, `src/impact_retrieval/preprocessing/`, `tests/test_query.py`, `tests/test_preprocessing.py` | `config/default.yaml` | **Hanya edit bagian `query:` dan `preprocessing:`** di config. Dilarang merapikan/mengubah urutan section lain! |
| **Orang 3 (Evaluasi)** | `data/ground_truth/`, `experiments/tune.py`, `docs/results/` | `config/default.yaml` | Hanya mengisi `REVIEW_LOG.md` dan skrip tuning. |
| **Orang 4 (Web & UI)** | `web/`, `tests/test_web.py`, `docs/report/outline.md` | `config/default.yaml` | **Hanya edit bagian `upload:`** di config. |

> [!WARNING]
> **Aturan Khusus untuk `config/default.yaml`:**
> Berkas ini dibaca bersama. Jangan pernah memformat ulang (*reformat / auto-indent whole file*), jangan menghapus komentar orang lain, dan **hanya sentuh blok konfigurasi milik modul Anda sendiri**.

---

## 4. Alur Kerja Standar (Langkah demi Langkah)

Ikuti alur 6 langkah ini setiap kali Anda akan mengerjakan tugas baru:

```
[1. Checkout main & Pull] ──► [2. Buat Branch Baru] ──► [3. Ngoding & Commit Atomik]
                                                                  │
[6. Review & Merge Lead] ◄── [5. Buka PR di GitHub] ◄── [4. Rebase / Sync main & Pytest]
```

### Langkah 1: Pastikan branch `main` lokal Anda adalah yang paling mutakhir
```bash
git checkout main
git pull origin main
```

### Langkah 2: Buat branch baru dari `main`
Gunakan konvensi penamaan branch:
* Fitur baru: `feat/<nama-fitur-singkat>`
* Perbaikan bug: `fix/<nama-bug>`
* Dokumentasi / GT: `docs/<nama-dokumen>`

*Contoh:*
```bash
# Orang 2 (Task Context):
git checkout -b feat/task-context

# Orang 4 (Download feature):
git checkout -b feat/web-download

# Orang 3 (Ground truth review):
git checkout -b docs/gt-review-2
```

### Langkah 3: Bekerja dan commit secara bertahap (Atomik)
Buat commit yang kecil dan bermakna. Jangan menunggu semua selesai baru 1 kali commit raksasa.
```bash
# Cek file apa saja yang Anda ubah (pastikan tidak ada file sampah seperti .venv atau cache)
git status

# Tambahkan file spesifik (hindari `git add .` jika ada file yang tidak sengaja terubah)
git add src/impact_retrieval/query/builder.py tests/test_query.py

# Commit dengan pesan yang jelas
git commit -m "feat(query): extract predecessor and successor task context"
```

### Langkah 4: Sebelum membuka PR, sinkronkan branch Anda dengan `main` terbaru
Sebelum Anda mengajukan PR, teman Anda mungkin sudah me-merge kodenya ke `main`. Tarik update tersebut ke branch Anda:
```bash
# 1. Ambil update terbaru dari GitHub
git fetch origin

# 2. Gabungkan perubahan main ke branch Anda
git merge origin/main

# 3. Jalankan pengujian wajib
pytest
```
*Jika `pytest` lulus dan tidak ada error, Anda siap mengirim kode ke GitHub.*

### Langkah 5: Push branch ke GitHub dan buat Pull Request
```bash
git push -u origin feat/task-context
```
1. Buka repositori di browser: [github.com/oceanite/bpmn-impact-retrieval](https://github.com/oceanite/bpmn-impact-retrieval)
2. Klik tombol hijau **"Compare & pull request"**.
3. Isi deskripsi PR:
   * Apa yang diubah?
   * Apakah ada parameter baru di config?
   * Sertakan screenshot atau bukti `pytest` lulus.
4. Assign **Lead (Orang 1)** sebagai *Reviewer*.

### Langkah 6: Review & Merge oleh Lead
* Lead membaca diff kode dan memverifikasi pengujian.
* Jika disetujui, Lead memilih **"Squash and merge"** atau **"Rebase and merge"** di GitHub agar riwayat git tetap rapi.
* Setelah di-merge, hapus branch fitur di GitHub.

---

## 5. Pertolongan Pertama: Jika Terjadi Merge Conflict

Jika GitHub mengatakan *"This branch has conflicts that must be resolved"*, jangan panik! Lakukan langkah ini di laptop Anda:

1. Di branch Anda, jalankan:
   ```bash
   git fetch origin
   git merge origin/main
   ```
2. Git akan memberi tahu file mana yang konflik (misalnya: `CONFLICT in config/default.yaml`).
3. Buka file tersebut di VS Code. Anda akan melihat penanda konflik:
   ```yaml
   <<<<<<< HEAD (Perubahan Anda)
     task_context: 0.3
   =======
     indonesian_stopwords: [dan, atau, ...]
   >>>>>>> origin/main (Perubahan di main)
   ```
4. **Pilih solusi yang benar:**
   * Di VS Code, gunakan tombol pembantu: `Accept Current Change`, `Accept Incoming Change`, atau **`Accept Both Changes`** (paling sering untuk file konfigurasi).
   * Bersihkan tanda `<<<<<<<`, `=======`, dan `>>>>>>>`.
5. Simpan file, lalu uji ulang:
   ```bash
   pytest
   ```
6. Commit penyelesaian konflik dan push kembali:
   ```bash
   git add config/default.yaml
   git commit -m "fix: resolve merge conflict with main"
   git push origin <nama-branch-anda>
   ```

> [!TIP]
> **Ingin membatalkan merge saat bingung/panik?**  
> Jalankan perintah ini untuk kembali ke kondisi sebelum merge dimulai:
> ```bash
> git merge --abort
> ```

---

## 6. Cheatsheet Perintah Penting Harian

| Perintah | Fungsi |
|---|---|
| `git status` | Melihat status file (apakah ada perubahan yang belum di-commit). |
| `git diff` | Melihat detail baris kode yang Anda ubah sebelum di-commit. |
| `git checkout main && git pull` | Memperbarui branch utama lokal Anda dari server. |
| `git branch` | Melihat sedang berada di branch mana. |
| `git restore <nama_file>` | Membatalkan perubahan lokal pada file yang belum di-commit. |
| `git checkout -b <nama_branch>` | Membuat branch baru dan langsung berpindah ke sana. |
| `pytest` | Menjalankan seluruh test suite (wajib 100% lulus!). |
