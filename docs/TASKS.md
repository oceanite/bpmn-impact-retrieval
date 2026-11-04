# Pembagian tugas (Kelompok 9)

Status per 2026-11-04: **seluruh pipeline sudah jalan dari ujung ke ujung**, termasuk website
dan evaluasi, plus upload source code berbentuk ZIP (135 test lulus). Pekerjaan yang tersisa adalah *memperbaiki, menguji dan melaporkan*,
bukan membangun dari nol. Baca `docs/ARCHITECTURE.md` dulu.

## Cara mulai (semua anggota)

```bash
git clone https://github.com/oceanite/bpmn-impact-retrieval.git
cd bpmn-impact-retrieval
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .                         # supaya `impact_retrieval` bisa di-import
git clone https://github.com/AbimanyuDA/Simple-ERP.git data/target_repo

pytest                                   # semua test harus lulus
python -m impact_retrieval.pipeline S03
python experiments/run_eval.py           # tabel BM25 vs baseline
uvicorn web.app:app --reload             # buka http://127.0.0.1:8000
```

Aturan kerja:
* Satu branch per tugas (`feat/...`, `fix/...`), masuk ke `main` lewat Pull Request, di-review lead.
* Setiap PR menyertakan test; `pytest` wajib lulus.
* Tidak ada angka di-hardcode. Parameter masuk `config/default.yaml`.
* Website hanya memanggil `pipeline.py` / `evaluation/`, tidak menghitung ranking sendiri.
* Kalau mengubah skenario atau ground truth, jalankan ulang `experiments/run_eval.py` dan catat hasilnya.

---

## Lead (bagian paling teknis): ekstraksi, retrieval, integrasi

Sudah selesai: `code/` (termasuk `archive.py` untuk upload ZIP yang aman), `retrieval/`, `pipeline.py`, `types.py`.

- [ ] Review dan merge PR anggota lain.
- [ ] **Ablation study per field:** jalankan evaluasi dengan satu field dimatikan (`field_weights.<field>: 0`)
      untuk tiap field, catat dampaknya pada F1@5 dan MRR. Ini bahan bagus untuk laporan.
- [ ] (Opsional, nilai tambah) **Propagasi call graph:** fungsi yang memanggil hasil teratas ikut naik
      skornya. Harus tetap deterministik dan bisa dimatikan lewat config.
- [ ] (Opsional) Ekstraksi Go: hubungkan method `Service` ↔ `Store` dengan nama sama, supaya
      pass-through layer bisa diberi label "terkait" di report.

## Orang 2: preprocessing & query builder

File: `src/impact_retrieval/preprocessing/`, `src/impact_retrieval/query/`, bagian `preprocessing` dan `query` di config.
Versi dasar sudah jalan. Tugasnya memperbaiki kualitas query.

- [ ] **Audit stopwords:** buat script di `experiments/` yang menampilkan 50 term dengan document frequency
      tertinggi di korpus. Term yang muncul hampir di semua dokumen tapi tidak bermakna masuk `code_stopwords`.
      Ukur dampaknya dengan `run_eval.py`.
- [ ] **Kamus sinonim domain** (opsional di config, default mati), misalnya `confirm ↔ confirmation`
      (stemming sudah menangani sebagian), `invoice ↔ bill`, `approve ↔ review`. Harus deterministik.
- [ ] **Stopwords bahasa Indonesia** (`dan`, `atau`, `yang`, `di`, `ke`, `dari`, ...) di config. Ini temuan nyata:
      pada pasangan asli `data/bpmn/real/`, BPMN dan UI Simple-ERP cocok terutama lewat kata "dan"
      (lihat `data/bpmn/real/README.md`). Pastikan angka S01–S06 tidak berubah.
- [ ] **Kamus Indonesia → Inggris** untuk model `docs/bpm-haqi` (misalnya `pengguna → user`, `penjualan → sales`).
      Dengan ini model berbahasa Indonesia juga bisa dipakai. Uji dengan pasangan di `data/bpmn/real/`.
- [ ] **Eksperimen bobot query** (`query.weights`): misalnya apakah `documentation: 1.0` lebih baik dari 0.5.
      Catat hasilnya, dan hati-hati overfitting (lihat Orang 3).
- [ ] Test untuk setiap fitur baru (`tests/test_preprocessing.py`, `tests/test_query.py`).

Kriteria selesai: semua fitur bisa dinyalakan/dimatikan lewat config, ada test, dan ada tabel
perbandingan sebelum/sesudah di PR.

## Orang 3: evaluasi & ground truth

File: `data/`, `experiments/`, `src/impact_retrieval/evaluation/`.

- [x] Review pertama ground truth S01–S06 (41 → 50 baris, alasan di `data/ground_truth/REVIEW_LOG.md`).
- [x] Skenario S07–S10 (test set, 19 baris ground truth): kondisi gateway, message flow, pindah lane, multi-perubahan.
- [ ] **Review kedua** ground truth S01–S06 dan S07–S10 oleh anggota tim, terutama baris *borderline*.
      Isi tabel di `REVIEW_LOG.md`. Untuk S07–S10: review **tanpa** melihat hasil ranking.
- [ ] Jangan evaluasi atau tuning pada test set sebelum M4. `run_eval.py` dan halaman Evaluation memakai
      split `dev` secara default; `--split test` hanya untuk run final.
- [ ] **Script tuning parameter** (`experiments/tune.py`): grid k1 ∈ {0.9, 1.2, 1.5, 2.0}, b ∈ {0.3, 0.5, 0.75, 1.0},
      plus beberapa variasi bobot field. Pakai **leave-one-scenario-out**: tuning di 5 skenario, uji di 1,
      ulangi 6 kali. Laporkan hasil di skenario uji, bukan di skenario tuning.
- [ ] Tabel dan grafik untuk laporan: P@k/R@k untuk k = 1..10, BM25 vs keyword vs TF-IDF, file vs function level.

Kriteria selesai: ground truth sudah direview, minimal 10 skenario, dan hasil tuning dilaporkan tanpa overfitting.

## Orang 4: website, laporan, presentasi

File: `web/`, `docs/`, README.

Versi dasar sudah jalan: halaman Mapping (termasuk upload ZIP source code opsional), Evaluation, Settings,
dan JSON API.

- [ ] **Tampilan diff yang lebih jelas:** kelompokkan per elemen, warna added/removed/modified, sembunyikan
      flow tanpa nama secara default.
- [ ] (Opsional) Render diagram BPMN dengan **bpmn-js** dan sorot elemen yang berubah.
- [ ] **Download hasil:** tombol unduh impact report sebagai JSON/CSV (`report.to_dict()` sudah tersedia).
- [ ] **Upload ZIP:** tampilkan batas ukuran (`config.upload`) di form, dan cantumkan nama codebase di file download.
      Ingat: halaman Evaluation selalu memakai Simple-ERP, karena ground truth hanya ada untuk Simple-ERP.
- [ ] Halaman Evaluation: grafik P@k/R@k untuk k = 1..10, dan pilihan subset skenario.
- [ ] Test untuk setiap halaman atau fitur baru di `tests/test_web.py`.
- [ ] **Laporan akhir** (gunakan "Threats to validity" di `docs/ARCHITECTURE.md`), **slide**, dan screenshot di README.

Kriteria selesai: demo bisa dijalankan dari clone bersih mengikuti README, dan semua halaman punya test.

---

## Hal yang sengaja belum dikerjakan (diskusikan dulu sebelum menambah)
* Dampak berupa **file baru** (migration/adapter baru) tidak bisa di-retrieve; sudah dikecualikan dari ground truth.
* Teks UI Simple-ERP berbahasa Indonesia; query dari model berbahasa Inggris tidak cocok dengannya.
* Codebase dari upload ZIP tidak punya ground truth, jadi hanya bisa dipakai di halaman Mapping, tidak dievaluasi.
* ID elemen yang berganti dianggap remove + add, bukan rename.
