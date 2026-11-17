# To-Do List Minggu Ini (Minggu 2: 16–22 November 2026)
**Proyek:** BPMN Change Impact Retrieval (Kelompok 9)  
**Target Milestone:** M2 (Test Set Dibekukan & Peningkatan Kualitas Query / UI)  
**Tenggat PR:** Kamis, 19 November 2026 | **Checkpoint Evaluasi:** Jumat, 20 November 2026  

---

## 📌 Rekap Fokus Minggu Ini
1. Menyelesaikan tunggakan M1 (penguncian baseline dev set, tag `v0.1-baseline`, dan review silang ground truth).
2. Mengintegrasikan **saran PIC: Penambahan Task Context pada Query**.
3. Menyelesaikan kamus sinonim dan kamus istilah Indonesia $\rightarrow$ Inggris untuk menangani *multilingual mismatch*.
4. Membekukan *test set* (S07–S10) secara resmi setelah verifikasi independen.
5. Memperbarui tampilan diff, tombol download hasil (JSON/CSV), dan info batasan upload pada antarmuka web.

---

## 👤 Pembagian Tugas 4 Orang

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            PEMBAGIAN TUGAS M2                                │
├──────────────────────┬──────────────────────┬────────────────────────────────┤
│ Peran                │ Fokus Utama          │ Berkas Terkait                 │
├──────────────────────┼──────────────────────┼────────────────────────────────┤
│ Orang 1 (Lead)       │ Integrasi & Baseline │ pipeline.py, baseline.md, docs │
│ Orang 2 (Query/NLP)  │ Task Context & Kamus │ builder.py, model.py, text.py  │
│ Orang 3 (Evaluasi)   │ Review GT & Tuning   │ REVIEW_LOG.md, run_eval.py     │
│ Orang 4 (Web/Report) │ Diff View & Download │ app.py, mapping.html, outline  │
└──────────────────────┴──────────────────────┴────────────────────────────────┘
```

---

### 1. Orang 1 (Lead): Arsitektur, Baseline Lock & Integrasi
*Fokus: Mengunci angka baseline M1, me-review PR, memimpin integrasi, dan menyusun metodologi laporan.*

- [ ] **Kunci Angka Pembanding Resmi (Baseline M1):**
  - Jalankan evaluasi dev set pada branch `main`:
    ```bash
    python experiments/run_eval.py --split dev
    ```
  - Buat berkas `docs/results/baseline.md` yang memuat tabel metrik BM25, TF-IDF, dan Keyword Matching untuk level *file* dan *function* pada $k \in \{1, 3, 5, 10\}$.
  - Buat dan push tag git:
    ```bash
    git tag v0.1-baseline
    git push origin v0.1-baseline
    ```
- [ ] **Review dan Merge PR Anggota:**
  - Pastikan setiap PR menyertakan pengujian unit (`pytest`) dan tidak memecah 135+ test yang sudah lulus.
  - Pastikan tidak ada parameter yang di-hardcode (semua wajib masuk ke `config/default.yaml`).
- [ ] **Commit Pembekuan Test Set:**
  - Setelah Orang 3 menyelesaikan verifikasi S07–S10, buat commit resmi pembekuan:
    ```bash
    git commit --allow-empty -m "chore: freeze test set S07-S10 (M2 milestone)"
    ```
- [ ] **Draf Bagian Metodologi Laporan:**
  - Tulis penjelasan arsitektur sistem di `docs/report/methodology.md`: alur ekstraksi kode, pemodelan semantik BPMN, pembobotan BM25F, dan kebijakan penanganan berkas baru (*new files limitation*).

---

### 2. Orang 2: Query Builder, Task Context (Saran PIC) & Kamus Multibahasa
*Fokus: Mengimplementasikan task context, kamus sinonim, serta kamus bahasa Indonesia $\rightarrow$ Inggris.*

- [ ] **Implementasi Fitur Saran PIC — Task Context pada Query:**
  - Buka `src/impact_retrieval/bpmn/model.py` dan `src/impact_retrieval/query/builder.py`.
  - Untuk setiap elemen task yang berubah (tambah/hapus/ubah), telusuri sequence flow masuk (*incoming*) dan keluar (*outgoing*) untuk mengambil nama aktivitas tetangga (predecessor & successor tasks) sebagai token konteks.
  - Tambahkan role baru `task_context` pada query builder.
  - Tambahkan parameter bobot di `config/default.yaml`:
    ```yaml
    query:
      weights:
        task_context: 0.3  # bobot konteks aktivitas tetangga
    ```
  - Tambahkan unit test di `tests/test_query.py` untuk memastikan task context terekstrak dengan benar dan ID BPMN tetap dibersihkan (`drop_ids`).
- [ ] **Kamus Sinonim Domain:**
  - Tambahkan modul/kamus sinonim deterministik di `src/impact_retrieval/preprocessing/` (misalnya: `confirm ↔ confirmation`, `invoice ↔ bill`, `approve ↔ review`).
  - Tambahkan flag konfigurasi `preprocessing.use_synonyms: false` (default false agar baseline aman).
- [ ] **Kamus Istilah Indonesia $\rightarrow$ Inggris:**
  - Tambahkan kamus padanan istilah bisnis Simple-ERP (`pengguna → user`, `penjualan → sales`, `pembelian → purchase`, `stok → inventory`, `pesanan → order`) di konfigurasi/preprocessing.
  - Uji jalannya query pada model BPMN riil di `data/bpmn/real/` (pastikan tidak merusak hasil dev set S01–S06).
- [ ] **Laporan Pengujian Minggu 2:**
  - Simpan perbandingan metrik dev set sebelum vs sesudah penambahan fitur query ke `docs/results/week2.md`.

---

### 3. Orang 3: Evaluasi, Validasi Ground Truth & Skrip Tuning
*Fokus: Validasi ganda kunci jawaban (anti-bias), penjagaan data leakage, dan persiapan tuning.*

- [ ] **Review Kedua Ground Truth Dev Set (S01–S06):**
  - Periksa 50 baris kunci jawaban di `data/ground_truth/ground_truth.csv` terhadap kode `data/target_repo`.
  - Fokus pada baris yang ditandai *borderline* di `REVIEW_LOG.md`:
    - S02: `backend/internal/reporting/adapter/postgres/store.go` (`Summary`)
    - S05: `backend/internal/auth/adapter/http/lifecycle.go` (`AdminRoutes`)
    - S06: Pengujian yang lolos secara semu (*vacuous pass*).
  - Tulis hasil persetujuan/catatan di tabel "Still Open" pada [data/ground_truth/REVIEW_LOG.md](file:///mnt/c/Users/USER/a-dea/kuliah/sems%207/SE/bpmn-impact-retrieval/data/ground_truth/REVIEW_LOG.md).
- [ ] **Review Independen Ground Truth Test Set (S07–S10):**
  - Periksa 19 baris kunci jawaban skenario S07–S10 dengan membaca `scenario.md` dan basis kode target.
  - **Aturan Ketat Anti-Leakage:** Lakukan review **tanpa menjalankan atau melihat hasil perankingan retrieval**, agar tidak terjadi bias penyesuaian kunci jawaban.
  - Laporkan ke Lead jika ada koreksi sebelum batas waktu pembekuan test set hari Jumat.
- [ ] **Validasi Proteksi Test Set:**
  - Pastikan skrip `experiments/run_eval.py` dan halaman `/evaluation` web menggunakan `--split dev` secara default, dan opsi `--split test` tidak dipanggil sampai Milestone M4.
- [ ] **Rancang Kerangka Skrip Tuning (`experiments/tune.py`):**
  - Buat kerangka skrip untuk persiapan Milestone 3 yang akan melakukan grid search parameter BM25 ($k_1 \in [0.9, 2.0]$, $b \in [0.3, 1.0]$) dan bobot field menggunakan metode validasi silang *Leave-One-Scenario-Out* (LOSO).

---

### 4. Orang 4: Web UI, Fitur Download & Kerangka Laporan
*Fokus: Memperbaiki pengalaman pengguna di web dashboard, ekspor laporan, dan struktur dokumen akhir.*

- [ ] **Penyempurnaan Tampilan BPMN Diff (`web/templates/mapping.html`):**
  - Kelompokkan tampilan perubahan berdasarkan tipe elemen (Activities/Tasks, Gateways, Events, Sequence Flows).
  - Terapkan indikator visual warna:
    - 🟢 **Hijau:** Elemen yang ditambahkan (*Added*)
    - 🔴 **Merah:** Elemen yang dihapus (*Removed*)
    - 🟡/🔵 **Kuning/Biru:** Elemen yang diubah atributnya (*Modified*)
  - Sembunyikan sequence flow tanpa nama secara default dengan opsi collapse/expand.
- [ ] **Fitur Download Impact Report:**
  - Tambahkan fungsi ekspor pada `web/app.py`:
    - Endpoint `/download/json` (mengembalikan hasil `report.to_dict()`)
    - Endpoint `/download/csv` (kolom: `scenario_id, file_path, function, score, matched_terms`)
  - Tambahkan tombol "Download Report (CSV)" dan "Download Report (JSON)" pada halaman hasil mapping.
  - Tambahkan unit test pada `tests/test_web.py` untuk menguji kedua endpoint tersebut.
- [ ] **Indikator Batasan Upload pada Form Web:**
  - Tampilkan informasi batas ukuran berkas yang diambil dari konfigurasi `upload` (`max_bpmn_mb: 5MB`, `max_zip_mb: 50MB`) tepat di bawah input file.
- [ ] **Penyusunan Kerangka Laporan & Slide Presentasi:**
  - Buat berkas `docs/report/outline.md` yang memuat struktur bab, subbab, serta tabel/grafik yang wajib ada dalam laporan akhir tugas besar.
  - Siapkan sketsa/kerangka slide presentasi (12–15 slide).

---

## 📅 Jadwal Kerja Harian Tim (17–20 Nov 2026)

| Hari | Target Capaian | PIC Utama |
|---|---|---|
| **Selasa (17 Nov)** | Task context logic dirancang di `builder.py`; review baris borderline S01–S06 dimulai; UI diff didesain ulang. | Semua |
| **Rabu (18 Nov)** | Unit test task context selesai; kamus sinonim & ID $\rightarrow$ EN diuji; endpoint download CSV/JSON dibuat. | Orang 2, Orang 4 |
| **Kamis (19 Nov)** | **Batas Akhir Pembuatan Pull Request (PR).** Semua test lulus (`pytest`); review ground truth S07–S10 selesai. | Semua |
| **Jumat (20 Nov)** | **Checkpoint Mingguan:** Merge PR ke `main`, catat hasil di `docs/results/week2.md`, kunci test set `S07–S10`, tag `v0.1-baseline`. | Lead & Tim |

---

## ⚠️ Aturan Kualitas & Prosedur PR
1. **Branching:** Gunakan branch bertopik, misal: `feat/task-context`, `feat/web-download`, `docs/gt-review-2`.
2. **Pengujian:** Jalankan `pytest` sebelum submit PR. Semua 135+ tes wajib berstatus *PASSED*.
3. **Konfigurasi:** Jangan menaruh nilai numerik atau kata kunci langsung di kode sumber; gunakan `config/default.yaml`.
4. **Anti-Leakage:** Jangan jalankan eksperimen atau tuning pada skenario `S07`, `S08`, `S09`, atau `S10` minggu ini!
