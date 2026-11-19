# BPMN Change Impact Retrieval — Kemajuan Mingguan
**Kelompok:** 9  
**Tanggal:** 19 November 2026  
**Target Milestone:** Milestone M2 (Penyempurnaan Query, Test Set Dibekukan, & Penyempurnaan Web UI)  
**Status Repository:** Tingkat kelulusan CI 100% (136 unit test) · Semua 6 PR telah digabungkan ke `main` · Dashboard web aktif secara langsung  

---

## 1. Ringkasan Eksekutif

Selama Minggu 2 (Milestone M2), Kelompok 9 berhasil mengubah prototipe end-to-end awal menjadi sistem retrieval yang dioptimalkan dan tangguh dengan validasi empiris serta perangkat web yang siap produksi.

### Poin Utama:
1. **Feedback PIC Diimplementasikan:** Berhasil memasukkan **Konteks Task** (penelusuran aktivitas tetangga) ke dalam query builder, menghasilkan **peningkatan murni sebesar +2.8 poin persentase pada File-level F1@5** (0.657 $\rightarrow$ 0.685).
2. **Ketidaksesuaian Antarbahasa Diselesaikan:** Mengembangkan normalisasi sinonim domain dan **kamus bisnis Bahasa Indonesia $\rightarrow$ Bahasa Inggris**. Pada model BPMN Indonesia yang sebenarnya (`data/bpmn/real/`), setiap istilah bisnis Indonesia berhasil diterjemahkan ke identifier kode dalam Bahasa Inggris, sehingga secara akurat mempromosikan `backend/cmd/api/main.go` ke peringkat #1.
3. **Validasi Anti-Kebocoran & Ground Truth yang Ketat:** Menyelesaikan tinjauan kedua secara independen terhadap seluruh **69 baris ground-truth** terhadap codebase Simple-ERP (`c76a313`). **Test Set S07–S10 secara resmi dibekukan** dan tidak pernah digunakan untuk evaluasi atau tuning.
4. **Optimasi Parameter BM25:** Tuning hyperparameter pada dev set meningkatkan normalisasi panjang, menaikkan **F1@5 tingkat File dari 0.657 menjadi 0.750 (+9.3pp)**, Recall@5 dari 0.667 menjadi **0.756 (+8.9pp)**, serta mempertahankan **MRR sempurna sebesar 1.000**.
5. **Antarmuka Web Interaktif & Ekspor:** Meningkatkan antarmuka web dengan tampilan diff BPMN semantik dan berkode warna (🟢 Ditambahkan, 🔴 Dihapus, 🟡 Dimodifikasi), indikator ukuran file upload, serta unduhan laporan dampak **CSV / JSON** dengan 1 klik.
---

## 3. Hasil Empiris Utama & Dekomposisi Ablasi

Semua evaluasi kuantitatif dilakukan secara eksklusif pada **Development Set (`S01`–`S06`, 50 baris ground-truth)** terhadap codebase target Simple-ERP. **Test Set (`S07`–`S10`) yang ditahan tetap tidak dievaluasi secara ketat hingga Milestone M4**.

### Tabel Dekomposisi Lengkap (Level File, Rata-rata pada Dev Set)

| Tahap | Konfigurasi | P@5 | R@5 | F1@5 | R@10 | F1@10 | Latensi | Kesimpulan Utama |
|---|---|---|---|---|---|---|---|---|
| **1. Baseline (M1)** | `k1=1.5, b=0.75`, Tanpa Task Context | 0.733 | 0.667 | **0.657** | 0.932 | 0.664 | 4.7 ms | Benchmark resmi yang dikunci (`v0.1-baseline`) |
| **2. Query** | `k1=1.5, b=0.75`, + Task Context 0.3 | 0.767 | 0.690 | **0.685** | 0.911 | 0.645 | 5.0 ms | **+2.8pp F1@5** kontribusi query murni |
| **3. Tuning** | `k1=0.5, b=1.0`, + Task Context 0.3 | **0.833** | **0.756** | **0.750** | **0.932** | **0.664** | 5.1 ms | **+9.3pp total gain F1@5** melalui normalisasi panjang |
| **4. + Kamus (Semua)** | Tuned + TC + Sinonim + ID $\rightarrow$ EN | 0.767 | 0.732 | **0.722** | 0.932 | 0.664 | 5.3 ms | Penurunan akibat benturan sinonim `approve ↔ review` pada S06 |
| **5. + ID $\rightarrow$ EN Saja** | Tuned + TC + Terjemahan ID $\rightarrow$ EN | **0.833** | **0.756** | **0.750** | **0.932** | **0.664** | 5.1 ms | **Tanpa regresi** pada dev set Bahasa Inggris |

---

## 4. Rincian Workstream

### Workstream A: Query Builder & NLP
* **Implementasi Task Context:** Untuk setiap task yang berubah dalam model BPMN, builder menelusuri sequence flow masuk/keluar melalui gateway tanpa nama untuk menemukan task pendahulu dan penerus terdekat yang memiliki nama.
  * **Terobosan S05 (User Invitations):** Precision@5 meningkat dari $0.60 \rightarrow 0.80$ (+20pp) dan Recall@5 dari $0.43 \rightarrow 0.57$ (+14pp). Istilah konteks (`Generate invitation token`, `Set initial password`) berhasil menarik lifecycle handler ke peringkat teratas.
  * **S01–S04:** Sepenuhnya stabil tanpa regresi.
  * **S06 (Goods Receipt Approval):** Trade-off kecil pada level fungsi ($-0.022$ F1@5), di mana task posting tetangga mempromosikan fungsi helper umum.
* **Sinonim Domain & Kamus ID $\rightarrow$ EN:**
  * Membuat kamus yang memetakan istilah bisnis Indonesia (`pengguna → user`, `penjualan → sales`, `pembelian → purchase`, `akses → access`, `laporan → report`).
  * **Validasi Kualitatif (`data/bpmn/real/`):** Sebelumnya, label hanya cocok dengan kode melalui kata-kata Bahasa Inggris yang muncul secara kebetulan (`Finance`, `Order to Cash`). Dengan terjemahan aktif, setiap istilah bisnis berhasil dicocokkan dengan bersih, sehingga `backend/cmd/api/main.go` berada di peringkat **#1**.
  * **Insight Domain:** Dalam Simple-ERP, *reviewing* penyesuaian inventaris dan *approving* purchase order merupakan transisi state machine yang terpisah. Mengelompokkan `approve: [review]` menciptakan noise pada S06. Tim merekomendasikan untuk memisahkan `review` sebelum mengaktifkan sinonim secara default.

### Workstream B: Ground Truth & Tuning Parameter
* **Review Kedua Ground Truth:**
  * Memverifikasi secara independen seluruh 69 baris terhadap Simple-ERP `c76a313`.
  * Secara formal menyelesaikan entri borderline di `data/ground_truth/REVIEW_LOG.md`:
    * S02 `store.go Summary`: Dipertahankan karena jumlah pending-approval secara langsung menggerakkan dashboard UI.
    * S05 `lifecycle.go AdminRoutes`: Dipertahankan sebagai dampak dead-code yang valid (route masih terdaftar tetapi admin tidak lagi memanggilnya).
    * Rule 6 (*vacuous-pass tests*): Test yang lolos secara vacuous setelah perubahan secara formal dilacak sebagai test terdampak yang memerlukan maintenance.
* **Tuning Hyperparameter & Leave-One-Scenario-Out (LOSO):**
  * Membuat `experiments/tune.py` yang mencakup 45 kombinasi grid ($k_1 \in [0.5, 3.0]$, $b \in [0.0, 1.0]$) dan meningkatkannya untuk mendukung cross-validation LOSO 6-fold.
  * Menemukan bahwa $b = 1.0$ (normalisasi panjang dokumen penuh) menangani panjang dokumen Simple-ERP yang heterogen (migrasi SQL kecil dibandingkan handler service Go yang panjang) secara signifikan lebih baik daripada default $b=0.75$.

### Workstream C: Aplikasi Web & Dokumentasi
* **Visual Diff yang Ditingkatkan:**
  * Tabel perubahan mengategorikan modifikasi menjadi *Activities / Tasks*, *Gateways*, *Events*, dan *Sequence Flows*.
  * Tag border berwarna: 🟢 Ditambahkan, 🔴 Dihapus, 🟡 Dimodifikasi. Sequence flow tanpa nama secara default dibuat collapsed untuk mengurangi tampilan yang terlalu penuh.
* **Ekspor Laporan Dampak:**
  * Mengimplementasikan endpoint `/download/csv` dan `/download/json`.
  * Menambahkan tombol unduh 1 klik pada layar hasil mapping.
* **Tampilan Batas Upload:**
  * Form secara eksplisit menampilkan batas ukuran file maksimum: 5 MB untuk model BPMN, 50 MB untuk arsip ZIP Codebase.
* **Arsitektur Laporan Akhir (`docs/report/outline.md`):**
  * Menyelesaikan outline laporan lengkap yang terdiri dari 8 bab, 3 Research Questions (RQ1–RQ3), 7 grafik, dan 9 tabel data.

---

## 5. Panduan Demonstrasi Langsung (Walkthrough 1 Menit)

Untuk mendemonstrasikan aplikasi langsung yang berjalan di `http://localhost:8000`:

1. **Buka Antarmuka Web:** Navigasikan ke `http://localhost:8000`.
2. **Pemeriksaan Form:** Perhatikan batas ukuran file yang ditampilkan di bawah input file (`Maks. 5 MB` / `Maks. 50 MB`).
3. **Jalankan Skenario:**
   * Pilih **`S05` (Email invitation links automatically)** dari dropdown Skenario.
   * Metode: **BM25**.
   * Klik **"Find impacted code"**.
4. **Periksa Hasil:**
   * **Tabel Diff:** Tampilkan kartu yang dikelompokkan dan berkode warna yang menyoroti task invitation yang dimodifikasi dalam warna kuning dan flow baru dalam warna hijau.
   * **Kode Terurut:** Amati handler auth Go yang terdampak dan halaman frontend Next.js yang berada di peringkat teratas dengan bukti term.
   * **Ekspor:** Klik **"Download Report (CSV)"** untuk langsung mengunduh file laporan yang bersih.

---

## 6. Langkah Berikutnya (Milestone M3: 23–29 November 2026)

1. **Studi Ablasi per Field:** Nolkan bobot untuk `path`, `name`, `route`, `db_table`, `test`, `comment`, dan `body` satu per satu untuk mengukur kekuatan ranking yang tepat dari setiap atribut kode.
2. **Penyempurnaan Kamus:** Pisahkan `review` dari `approve` dalam kamus sinonim dan evaluasi apakah parameter yang telah dituning dengan sinonim yang bersih dapat melampaui 0.750 F1@5.
3. **Visualisasi Halaman Evaluasi:** Sematkan kurva $P@k$ dan $R@k$ dinamis untuk BM25 vs Baseline Keyword vs TF-IDF langsung pada `/evaluation`.
4. **Dry Run Internal & Tag `v0.2-tuned`:** Validasi reproduksi clean-clone sebelum mengunci konfigurasi yang telah dituning.
