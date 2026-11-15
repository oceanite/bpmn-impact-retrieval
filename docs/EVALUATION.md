# Panduan & Metodologi Evaluasi: BPMN Change Impact Retrieval (Kelompok 9)

Dokumen ini mendefinisikan metode, metrik, aturan kurasi *ground truth*, pembagian dataset, serta prosedur eksekusi evaluasi untuk proyek **BPMN Change Impact Retrieval**.

---

## 1. Tujuan Evaluasi

Sistem ini memecahkan masalah *Change Impact Analysis* (CIA) berbasis *Information Retrieval* (IR):
> Diberikan perbedaan (*diff*) antara dua versi diagram BPMN 2.0 (`old.bpmn` vs `new.bpmn`), sistem bertugas mencari dan memeringkat berkas serta fungsi pada basis kode target (`Simple-ERP`) yang wajib diubah oleh pengembang.

Tujuan utama evaluasi adalah:
1. Mengukur efektivitas ranking model retrieval (**BM25**) dibandingkan metode pembanding (**TF-IDF** dan **Keyword Matching**).
2. Menilai kualitas retrieval pada tingkat berkas (*file level*) dan fungsi/komponen (*function level*).
3. Mencegah *data leakage* dan *overfitting* selama proses tuning parameter.

---

## 2. Tingkat Granularitas Evaluasi (*Evaluation Levels*)

Evaluasi dijalankan pada dua tingkat granularitas (diimplementasikan pada [`metrics.py`](file:///mnt/c/Users/USER/a-dea/kuliah/sems%207/SE/bpmn-impact-retrieval/src/impact_retrieval/evaluation/metrics.py)):

### a. File Level (`level = "file"`)
* **Mekanisme:** Hasil perankingan dokumen diringkas (*collapsed*) menjadi daftar berkas unik berdasarkan kemunculan pertamanya (*first occurrence keeps its rank*).
* **Kriteria Relevan:** Suatu berkas dianggap relevan jika nama berkas tersebut tercantum dalam setidaknya satu baris *ground truth* untuk skenario terkait.
* **Tujuan Praktis:** Membantu pengembang mengetahui file mana saja yang perlu dibuka dan dimodifikasi.

### b. Function Level (`level = "function"`)
* **Mekanisme:** Setiap unit dokumen yang di-retrieve (fungsi/metode Go, komponen TSX, type TS, dsb.) dinilai secara independen.
* **Kriteria Relevan:** Suatu unit dianggap relevan jika:
  - `file_path` dan `function` cocok persis dengan entri *ground truth*, ATAU
  - Baris *ground truth* memiliki nilai `function` kosong (`""`), yang menandakan seluruh isi berkas tersebut terdampak (*whole-file impact*).
* **Tujuan Praktis:** Memberikan rekomendasi spesifik ke titik kode atau fungsi yang harus direvisi.

---

## 3. Kurasi Ground Truth (*Answer Key*)

Semua kunci jawaban evaluasi disimpan di [`data/ground_truth/ground_truth.csv`](file:///mnt/c/Users/USER/a-dea/kuliah/sems%207/SE/bpmn-impact-retrieval/data/ground_truth/ground_truth.csv) dengan skema:
```csv
scenario_id,file_path,function
```
* `file_path`: Alamat relatif dari root target repository (`data/target_repo/`).
* `function`: Nama fungsi Go/method, komponen TSX, atau type TS. Jika **kosong**, berarti perubahan berdampak pada keseluruhan berkas.

### Aturan Inklusi (*Inclusion Rules*)
Suatu kode **WAJIB dimasukkan** ke dalam ground truth jika dan hanya jika kode tersebut harus diedit akibat perubahan pada alur BPMN:

1. **Logika Bisnis & Transisi State:** Implementasi logika inti yang berubah (misal transisi state SQL, validasi *precondition*, perubahan batas otorisasi).
2. **API & Routing:** Handler HTTP atau registrasi rute jika *surface API* bertambah, berubah, atau dihapus.
3. **Frontend UI:** Komponen tampilan (Next.js/React TSX) yang memicu atau menampilkan tahapan proses yang diubah.
4. **Dokumentasi Kontrak API:** Berkas `api/openapi.yaml`, jika rute, parameter, enum aksi, atau skema respons berubah.
5. **Existing Tests (Fail):** Unit test atau integration test eksisting yang memverifikasi perilaku lama sehingga akan *fail* pasca-perubahan (termasuk test yang *fail* karena tahap *setup*-nya memanggil aksi yang dihapus).
6. **Existing Tests (Vacuous Pass):** Test yang tetap *pass* namun secara semu/vakum (misalnya test memeriksa penolakan order, tetapi pasca-perubahan order ditolak karena alasan/precondition lain; test tersebut harus diedit agar tetap menguji hal yang dimaksud).

### Aturan Eksklusi (*Exclusion Rules*)
Elemen berikut **sengaja tidak dimasukkan** ke ground truth:
* **Thin pass-through layers:** Method perantara yang tidak mengalami perubahan signature (misal kebanyakan method di `application/service.go` yang hanya mem-forward call ke storage layer).
* **Berkas yang harus dibuat baru:** Berkas migrasi database baru atau adapter baru yang belum ada di korpus Simple-ERP (tidak mungkin di-retrieve karena belum ada di indeks).
* **Direktori `docs/`:** Dokumentasi internal Simple-ERP sengaja diabaikan dari indeks (`config/default.yaml`) untuk mencegah *query leakage*.
* **Repositori ZIP eksternal:** Unggahan kode ZIP dari luar sistem tidak memiliki ground truth otomatis (hanya untuk pengujian fungsional).

---

## 4. Pembagian Dataset (*Splits*) & Pencegahan Kebocoran Data

| Split | Skenario | Jumlah Baris GT | Tujuan & Kebijakan |
|---|---|:---:|---|
| **dev** | `S01` – `S06` | 50 baris | Digunakan untuk eksperimen, perbaikan stopword/kamus, ablation study, dan *hyperparameter tuning*. |
| **test** | `S07` – `S10` | 19 baris | **Dibekukan (*frozen*) per 4 Nov 2026**. Dilarang dijadikan acuan saat tuning. Hanya dievaluasi **satu kali** pada Milestone 4 (M4) menggunakan konfigurasi final. |
| **real** | `data/bpmn/real/` | 0 baris | Pasangan BPMN riil dari git Simple-ERP (`bpm-haqi`, Bahasa Indonesia). Digunakan untuk demo web tanpa ground truth. |

> [!IMPORTANT]
> **Kebijakan Anti-Leakage:**
> Parameter BM25 ($k_1, b$) dan pembobotan field (`field_weights`) hanya boleh dioptimasi pada **dev set** menggunakan validasi *Leave-One-Scenario-Out* (LOSO). Jangan pernah mengubah bobot berdasarkan performa pada *test set*.

---

## 5. Metrik Evaluasi Formal

Evaluasi dihitung pada beberapa nilai ambang peringkat (*cut-off*) $k \in \{1, 3, 5, 10\}$ dengan parameter kedalaman penarikan awal `retrieve_depth = 100`:

1. **Precision@k ($P@k$):**
   $$P@k = \frac{\text{TP di Top } k}{k}$$
   *(Catatan: Tetap dibagi secara ketat dengan $k$, meskipun jumlah dokumen yang terambil kurang dari $k$)*.

2. **Recall@k ($R@k$):**
   $$R@k = \frac{\text{Item Relevan Ditemukan di Top } k}{\text{Total Item Relevan di Ground Truth}}$$

3. **F1@k:**
   $$F1@k = 2 \times \frac{P@k \times R@k}{P@k + R@k}$$
   *(Bernilai 0 jika $P@k + R@k = 0$)*.

4. **False Positive Rate@k ($FPR@k$):**
   $$FPR@k = \frac{\text{FP di Top } k}{\text{Jumlah Dokumen Negatif di Seluruh Korpus}}$$
   Menunjukkan seberapa bersih hasil retrieval dari noise terhadap keseluruhan basis kode.

5. **Mean Reciprocal Rank ($MRR$):**
   $$MRR = \frac{1}{\text{Peringkat Item Relevan Pertama}}$$
   *(Bernilai 0 jika tidak ada satu pun item relevan di dalam daftar hasil retrieval)*.

6. **Search Latency (ms):**
   Waktu komputasi yang dihabiskan untuk pembentukan query (*query building*) dan eksekusi algoritma pencarian. Tidak menghitung waktu ekstraksi kode dan pembentukan indeks (*one-time indexing*).

---

## 6. Metode Retrieval yang Dibandingkan

1. **BM25 (Metode Utama / *Proposed*):**
   - Menggunakan Okapi BM25 dengan pembobotan multi-field (misal `path: 2.0`, `name: 3.0`, `route: 2.0`, `test: 2.0`, `body: 1.0`).
   - Dilengkapi *token preprocessing*: identifer splitting (camelCase/snake_case), lowercasing, stopword removal (English + domain + code), dan Porter Stemming.
2. **TF-IDF (Baseline 1):**
   - Menghitung kemiripan dokumen menggunakan Term Frequency - Inverse Document Frequency dengan *sublinear tf scaling*.
3. **Keyword Matching (Baseline 2):**
   - Pencocokan frekuensi kemunculan token query secara langsung pada teks dokumen.

---

## 7. Prosedur Eksekusi Evaluasi

### A. Menjalankan via Terminal (CLI)
Script utama evaluasi berada di [`experiments/run_eval.py`](file:///mnt/c/Users/USER/a-dea/kuliah/sems%207/SE/bpmn-impact-retrieval/experiments/run_eval.py).

```bash
# 1. Evaluasi Dev Set (S01-S06) untuk semua metode (File & Function Level)
python experiments/run_eval.py

# 2. Evaluasi spesifik level (file atau function saja)
python experiments/run_eval.py --level file
python experiments/run_eval.py --level function

# 3. Evaluasi metode tertentu saja
python experiments/run_eval.py --methods bm25 tfidf

# 4. Evaluasi skenario tertentu
python experiments/run_eval.py --scenarios S01 S03

# 5. Evaluasi Final Test Set (Hanya untuk Milestone 4!)
python experiments/run_eval.py --split test
```

Hasil metrik per skenario akan disimpan secara otomatis ke dalam berkas CSV di `experiments/results/metrics.csv`.

### B. Menjalankan via Web Dashboard
1. Jalankan aplikasi web:
   ```bash
   uvicorn web.app:app --reload
   ```
2. Buka peramban di `http://127.0.0.1:8000/evaluation`.
3. Dashboard menampilkan:
   - Tabel ringkasan rata-rata metrik (BM25 vs TF-IDF vs Keyword).
   - Rincian per skenario beserta daftar spesifik **True Positives (TP)**, **False Positives (FP)**, dan **False Negatives (FN)**.
   - Pilihan beralih tampilan antara *File Level* dan *Function Level*.

---

## 8. Baseline Benchmark Awal (Dev Set `S01`–`S06`)

Hasil benchmark awal dengan konfigurasi default sebelum proses tuning lanjutan:

| Level | Metode | P@5 | R@5 | F1@5 | R@10 | MRR | Latency (ms) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **File** | **BM25** | **0.733** | **0.667** | **0.657** | **0.932** | **1.000** | ~2–3 ms |
| File | TF-IDF | 0.667 | 0.625 | 0.606 | 0.845 | 1.000 | ~11–12 ms |
| File | Keyword | 0.533 | 0.494 | 0.476 | 0.711 | 0.756 | ~11–12 ms |
| **Function** | **BM25** | **0.800** | **0.564** | **0.587** | **0.740** | **1.000** | ~2–3 ms |
| Function | TF-IDF | 0.500 | 0.417 | 0.399 | 0.562 | 0.764 | ~11–12 ms |
| Function | Keyword | 0.533 | 0.335 | 0.374 | 0.552 | 0.672 | ~11–12 ms |

---

## 9. *Threats to Validity* & Batasan Metodologi

Saat menyusun laporan tugas besar, cantumkan keterbatasan evaluasi berikut:
1. **Ukuran Dataset Terbatas:** Hanya terdiri atas 10 skenario dan 69 baris ground truth, sehingga perubahan pada 1 skenario berdampak signifikan pada nilai rata-rata.
2. **Kurasi Internal:** Skenario dan ground truth dirancang oleh tim yang sama yang membangun sistem, sehingga diperlukan proses verifikasi ganda (*double-review*).
3. **Blind Spot Berkas Baru:** Berkas yang harus dibuat baru pasca-perubahan arsitektur tidak dapat di-retrieve karena belum ada di korpus Simple-ERP saat proses pencarian.
4. **Tantangan Multibahasa:** Pada skenario BPMN berbahasa Indonesia (`bpm-haqi`), teks BPMN dan kode/komentar berbahasa Inggris membutuhkan kamus istilah (*domain translation*) agar matching tidak hanya bergantung pada kata sambung umum.
