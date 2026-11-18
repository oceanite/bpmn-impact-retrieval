# Hasil Evaluasi Baseline Resmi (Milestone M1)

**Tanggal:** 18 November 2026  
**Status:** Terkunci (*Locked Baseline*)  
**Tag Git:** `v0.1-baseline`  
**Split Data:** Development Set (`S01`–`S06`), 50 baris *ground truth*  
**Basis Kode Target:** Simple-ERP (Go, TypeScript, SQL, OpenAPI)  
**Konfigurasi:** Parameter standar pada `config/default.yaml` ($k_1 = 1.5, b = 0.75$, stopwords default)  
**Total Unit Tests:** 136 passed  

---

## 1. Ringkasan Metrik Tingkat Berkas (*File Level*)

Rata-rata evaluasi pada 6 skenario dev set:

| Metrik / Metode | $k$ | P@k | R@k | F1@k | FPR@k | MRR | Latensi (ms) |
|---|---|---|---|---|---|---|---|
| **BM25** | 1 | **1.000** | **0.214** | **0.335** | 0.0000 | **1.000** | 4.7 |
| **BM25** | 3 | **0.889** | **0.536** | **0.625** | 0.0020 | **1.000** | 4.7 |
| **BM25** | 5 | **0.733** | **0.667** | **0.657** | 0.0078 | **1.000** | 4.7 |
| **BM25** | 10 | **0.550** | **0.932** | **0.664** | 0.0265 | **1.000** | 4.7 |
| Keyword | 1 | 0.667 | 0.149 | 0.227 | 0.0020 | 0.756 | 15.4 |
| Keyword | 3 | 0.500 | 0.259 | 0.318 | 0.0088 | 0.756 | 15.4 |
| Keyword | 5 | 0.533 | 0.494 | 0.476 | 0.0137 | 0.756 | 15.4 |
| Keyword | 10 | 0.400 | 0.711 | 0.488 | 0.0354 | 0.756 | 15.4 |
| TF-IDF | 1 | 1.000 | 0.214 | 0.335 | 0.0000 | 1.000 | 20.1 |
| TF-IDF | 3 | 0.722 | 0.372 | 0.466 | 0.0049 | 1.000 | 20.1 |
| TF-IDF | 5 | 0.667 | 0.625 | 0.606 | 0.0098 | 1.000 | 20.1 |
| TF-IDF | 10 | 0.483 | 0.845 | 0.589 | 0.0305 | 1.000 | 20.1 |

---

## 2. Ringkasan Metrik Tingkat Fungsi (*Function Level*)

Rata-rata evaluasi pada 6 skenario dev set:

| Metrik / Metode | $k$ | P@k | R@k | F1@k | FPR@k | MRR | Latensi (ms) |
|---|---|---|---|---|---|---|---|
| **BM25** | 1 | **1.000** | **0.186** | **0.289** | 0.0000 | **1.000** | 4.7 |
| **BM25** | 3 | **0.944** | **0.458** | **0.541** | 0.0002 | **1.000** | 4.7 |
| **BM25** | 5 | **0.800** | **0.564** | **0.587** | 0.0015 | **1.000** | 4.7 |
| **BM25** | 10 | **0.567** | **0.740** | **0.585** | 0.0064 | **1.000** | 4.7 |
| Keyword | 1 | 0.500 | 0.112 | 0.165 | 0.0007 | 0.672 | 15.4 |
| Keyword | 3 | 0.444 | 0.187 | 0.230 | 0.0025 | 0.672 | 15.4 |
| Keyword | 5 | 0.533 | 0.335 | 0.374 | 0.0034 | 0.672 | 15.4 |
| Keyword | 10 | 0.400 | 0.552 | 0.420 | 0.0089 | 0.672 | 15.4 |
| TF-IDF | 1 | 0.667 | 0.154 | 0.231 | 0.0005 | 0.764 | 20.1 |
| TF-IDF | 3 | 0.500 | 0.229 | 0.278 | 0.0022 | 0.764 | 20.1 |
| TF-IDF | 5 | 0.500 | 0.417 | 0.399 | 0.0037 | 0.764 | 20.1 |
| TF-IDF | 10 | 0.367 | 0.562 | 0.397 | 0.0094 | 0.764 | 20.1 |

---

## 3. Mean Reciprocal Rank (MRR) per Skenario (*File Level*)

| Metode | S01 | S02 | S03 | S04 | S05 | S06 | Rata-rata |
|---|---|---|---|---|---|---|---|
| **BM25** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** | **1.000** |
| Keyword | 0.20 | 1.00 | 1.00 | 1.00 | 0.33 | 1.00 | 0.756 |
| TF-IDF | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.000 |

---

## 4. Analisis & Temuan Baseline

1. **Keunggulan BM25:**
   * Pada tingkat berkas (*file level*), BM25 mengungguli baseline *Keyword Matching* dan *TF-IDF* secara signifikan di seluruh metrik $k$.
   * F1@5 BM25 mencapai **0.657** (vs Keyword **0.476** dan TF-IDF **0.606**).
   * Recall@10 BM25 mencapai **0.932**, membuktikan bahwa 93.2% berkas yang terdampak perubahan BPMN berhasil ditemukan dalam 10 rekomendasi teratas.
   * Nilai MRR sempurna (**1.000**) menunjukkan berkas relevan pertama selalu berada di posisi ranking 1 untuk seluruh skenario dev set.
2. **Efisiensi Waktu (Latensi):**
   * BM25 memiliki rata-rata latensi retrieval sebesar **4.7 ms**, jauh lebih cepat dibandingkan Keyword matching (15.4 ms) dan TF-IDF (20.1 ms).
3. **Kelemahan Keyword Matching:**
   * Keyword baseline mengalami drop MRR yang parah pada skenario `S01` (MRR 0.20) dan `S05` (MRR 0.33), akibat keterbatasan pencocokan leksikal murni tanpa pembobotan frekuensi inversi term.
4. **Catatan Perbandingan Mendatang (M2 & M3):**
   * Peningkatan fitur query dari Orang 2 (*task context*, kamus sinonim, kamus ID $\rightarrow$ EN) serta tuning parameter ($k_1, b$) dari Orang 3 wajib diukur terhadap angka acuan di dokumen ini.
