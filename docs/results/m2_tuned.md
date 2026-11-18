# Hasil Evaluasi Setelah Tuning Parameter BM25 (Milestone M2)

**Tanggal:** 18 November 2026  
**Status:** Aktif  
**Split Data:** Development Set (`S01`–`S06`), 50 baris *ground truth*  
**Basis Kode Target:** Simple-ERP (Go, TypeScript, SQL, OpenAPI)  
**Konfigurasi:** `config/default.yaml` — BM25 `k1=0.5`, `b=1.0` (hasil tuning dari `experiments/tune.py`)  
**Dibandingkan dengan:** [`docs/results/baseline.md`](baseline.md) (`k1=1.5`, `b=0.75`)

---

## 1. Perubahan Konfigurasi

| Parameter | Baseline (M1) | Tuned (M2) |
|---|---|---|
| `k1` | 1.5 | **0.5** |
| `b` | 0.75 | **1.0** |

Nilai diperoleh dengan grid-search 45 kombinasi (`k1` ∈ {0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0}, `b` ∈ {0.0, 0.25, 0.5, 0.75, 1.0}) menggunakan `python experiments/tune.py`. Target optimasi: F1@5 (file level, dev set).

---

## 2. Ringkasan Metrik Tingkat Berkas (*File Level*)

Rata-rata evaluasi pada 6 skenario dev set:

| Metrik / Metode | $k$ | P@k | R@k | F1@k | FPR@k | MRR | Latensi (ms) |
|---|---|---|---|---|---|---|---|
| **BM25** | 1 | **1.000** | **0.214** | **0.335** | 0.0000 | **1.000** | 5.1 |
| **BM25** | 3 | **0.944** | **0.560** | **0.658** | 0.0010 | **1.000** | 5.1 |
| **BM25** | 5 | **0.833** | **0.756** | **0.750** | 0.0049 | **1.000** | 5.1 |
| **BM25** | 10 | **0.550** | **0.932** | **0.664** | 0.0265 | **1.000** | 5.1 |
| Keyword | 1 | 0.500 | 0.065 | 0.116 | 0.0029 | 0.672 | 28.1 |
| Keyword | 3 | 0.500 | 0.259 | 0.318 | 0.0088 | 0.672 | 28.1 |
| Keyword | 5 | 0.467 | 0.390 | 0.403 | 0.0157 | 0.672 | 28.1 |
| Keyword | 10 | 0.367 | 0.667 | 0.449 | 0.0374 | 0.672 | 28.1 |
| TF-IDF | 1 | 1.000 | 0.214 | 0.335 | 0.0000 | 1.000 | 33.7 |
| TF-IDF | 3 | 0.667 | 0.348 | 0.432 | 0.0059 | 1.000 | 33.7 |
| TF-IDF | 5 | 0.700 | 0.649 | 0.634 | 0.0088 | 1.000 | 33.7 |
| TF-IDF | 10 | 0.500 | 0.866 | 0.607 | 0.0295 | 1.000 | 33.7 |

---

## 3. Ringkasan Metrik Tingkat Fungsi (*Function Level*)

Rata-rata evaluasi pada 6 skenario dev set:

| Metrik / Metode | $k$ | P@k | R@k | F1@k | FPR@k | MRR | Latensi (ms) |
|---|---|---|---|---|---|---|---|
| **BM25** | 1 | **1.000** | **0.186** | **0.289** | 0.0000 | **1.000** | 5.1 |
| **BM25** | 3 | **0.889** | **0.459** | **0.539** | 0.0005 | **1.000** | 5.1 |
| **BM25** | 5 | **0.700** | **0.532** | **0.538** | 0.0022 | **1.000** | 5.1 |
| **BM25** | 10 | **0.600** | **0.772** | **0.618** | 0.0059 | **1.000** | 5.1 |
| Keyword | 1 | 0.333 | 0.029 | 0.053 | 0.0010 | 0.589 | 28.1 |
| Keyword | 3 | 0.444 | 0.187 | 0.230 | 0.0025 | 0.589 | 28.1 |
| Keyword | 5 | 0.533 | 0.335 | 0.374 | 0.0034 | 0.589 | 28.1 |
| Keyword | 10 | 0.383 | 0.468 | 0.392 | 0.0091 | 0.589 | 28.1 |
| TF-IDF | 1 | 0.667 | 0.154 | 0.231 | 0.0005 | 0.756 | 33.7 |
| TF-IDF | 3 | 0.389 | 0.201 | 0.234 | 0.0027 | 0.756 | 33.7 |
| TF-IDF | 5 | 0.500 | 0.401 | 0.382 | 0.0037 | 0.756 | 33.7 |
| TF-IDF | 10 | 0.350 | 0.520 | 0.373 | 0.0096 | 0.756 | 33.7 |

---

## 4. Mean Reciprocal Rank (MRR) per Skenario (*File Level*)

| Metode | S01 | S02 | S03 | S04 | S05 | S06 | Rata-rata |
|---|---|---|---|---|---|---|---|
| **BM25** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **1.000** |
| Keyword | 0.20 | 1.00 | 1.00 | 0.50 | 0.33 | 1.00 | 0.672 |
| TF-IDF | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.000 |

---

## 5. Perbandingan BM25 vs Baseline M1

| Metrik | Baseline M1 (`k1=1.5, b=0.75`) | Tuned M2 (`k1=0.5, b=1.0`) | Delta |
|---|---|---|---|
| F1@3 (file) | 0.625 | **0.658** | **+0.033** |
| F1@5 (file) | 0.657 | **0.750** | **+0.093** |
| F1@10 (file) | 0.664 | 0.664 | 0.000 |
| R@5 (file) | 0.667 | **0.756** | **+0.089** |
| R@10 (file) | 0.932 | 0.932 | 0.000 |
| MRR (file) | 1.000 | 1.000 | 0.000 |
| F1@5 (function) | 0.587 | **0.538** | −0.049 |
| F1@10 (function) | 0.585 | **0.618** | **+0.033** |

Peningkatan signifikan pada metrik *file level* F1@5 (+9.3pp) dan R@5 (+8.9pp). MRR tetap sempurna.
Penurunan kecil pada F1@5 *function level* (−4.9pp) karena `b=1.0` menghukum dokumen panjang lebih
agresif; pada `k=10` function level justru naik.

---

## 6. Catatan

- Tuning hanya dilakukan pada dev set (S01–S06); test set (S07–S10) tetap beku untuk M4.
- Detail semua 45 kombinasi tersimpan di `experiments/results/tune_results.csv`.
- `b=1.0` = normalisasi panjang penuh; cocok karena dokumen Simple-ERP bervariasi panjangnya
  (file SQL/migration vs file domain Go).
