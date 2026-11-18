# Hasil Pengujian Fitur Query Minggu 2 (Orang 2)

**Tanggal:** 18 November 2026  
**Split Data:** Development Set (`S01`–`S06`) saja. Test set (`S07`–`S10`) **tidak** dijalankan.  
**Metode:** BM25 (field weights default)  
**Dibandingkan dengan:** [`baseline.md`](baseline.md) (`k1=1.5`, `b=0.75`, tanpa task context)  
**Fitur yang diuji:**

* `task_context` (saran PIC): nama aktivitas tetangga (predecessor/successor) dari task yang berubah,
  bobot `query.weights.task_context: 0.3` (`src/impact_retrieval/query/builder.py`)
* Kamus sinonim domain: `preprocessing.use_synonyms` (default `false`)
* Kamus istilah Indonesia → Inggris: `preprocessing.use_translation` (default `false`)

Semua angka dihasilkan lewat `ImpactPipeline(overrides=...)` + `evaluate_all(..., split="dev")`
dengan config `main` saat ini; hanya parameter di kolom "Konfigurasi" yang diubah.
Baris A mereproduksi angka `baseline.md` persis (F1@5 file 0.657, function 0.587).

---

## 1. Kontribusi murni task context (`k1=1.5`, `b=0.75`)

Parameter BM25 sama dengan baseline M1, sehingga selisihnya murni dari task context
(tidak tercampur efek tuning Orang 3).

| Level | Varian | P@5 | R@5 | F1@5 | P@10 | R@10 | F1@10 | MRR |
|---|---|---|---|---|---|---|---|---|
| File | A. Baseline M1 (tanpa TC) | 0.733 | 0.667 | 0.657 | 0.550 | 0.932 | 0.664 | 1.000 |
| File | B. + task context 0.3 | **0.767** | **0.690** | **0.685** | 0.533 | 0.911 | 0.645 | 1.000 |
| File | Delta B − A | +0.034 | +0.023 | **+0.028** | −0.017 | −0.021 | −0.019 | 0.000 |
| Function | A. Baseline M1 (tanpa TC) | 0.800 | 0.564 | 0.587 | 0.567 | 0.740 | 0.585 | 1.000 |
| Function | B. + task context 0.3 | 0.767 | 0.547 | 0.565 | 0.550 | 0.726 | 0.570 | 1.000 |
| Function | Delta B − A | −0.033 | −0.017 | **−0.022** | −0.017 | −0.014 | −0.015 | 0.000 |

### Delta per skenario (@5)

| Skenario | File ΔP@5 | File ΔR@5 | Function ΔP@5 | Function ΔR@5 |
|---|---|---|---|---|
| S01 | 0.00 | 0.00 | 0.00 | 0.00 |
| S02 | 0.00 | 0.00 | 0.00 | 0.00 |
| S03 | 0.00 | 0.00 | 0.00 | 0.00 |
| S04 | 0.00 | 0.00 | 0.00 | 0.00 |
| S05 | **+0.20** (0.60 → 0.80) | **+0.14** (0.43 → 0.57) | 0.00 | 0.00 |
| S06 | 0.00 | 0.00 | −0.20 (1.00 → 0.80) | −0.10 (0.40 → 0.30) |

**Temuan:**
1. Task context hanya mengubah 2 dari 6 skenario. Kenaikan file-level seluruhnya berasal dari **S05**
   (konteks "Generate invitation token", "Set initial password";
   satu berkas relevan tambahan masuk top-5).
2. Pada **S06** function level, nama task tetangga ("Receive goods", "Post goods receipt and stock") mendorong fungsi
   posting yang sudah ada ke atas, menggeser satu fungsi relevan keluar dari top-5.
3. Pada k=10 task context sedikit menurunkan recall file level (0.932 → 0.911).
4. MRR tetap 1.000. Dengan hanya 6 skenario, selisih ±0.02–0.03 setara satu dokumen di satu
   skenario, jadi efeknya **kecil dan belum bisa disebut signifikan**.

---

## 2. Kamus sinonim & terjemahan ID → EN

### 2a. Dev set S01–S06 (cek regresi)

| Level | Varian (`k1=1.5`, `b=0.75`, + TC 0.3) | P@5 | R@5 | F1@5 | R@10 | F1@10 | MRR |
|---|---|---|---|---|---|---|---|
| File | B. Tanpa kamus | 0.767 | 0.690 | 0.685 | 0.911 | 0.645 | 1.000 |
| File | C. + sinonim | 0.767 | 0.690 | 0.685 | 0.932 | 0.664 | 1.000 |
| File | D. + ID → EN | 0.767 | 0.690 | 0.685 | 0.911 | 0.645 | 1.000 |
| File | E. + sinonim + ID → EN | 0.767 | 0.690 | 0.685 | 0.932 | 0.664 | 1.000 |
| Function | B. Tanpa kamus | 0.767 | 0.547 | 0.565 | 0.726 | 0.570 | 1.000 |
| Function | E. + sinonim + ID → EN | 0.767 | 0.547 | 0.565 | 0.741 | 0.586 | 1.000 |

Dengan parameter baseline **tidak ada regresi** pada S01–S06: angka @5 identik, dan sinonim sedikit
menaikkan @10 (R@10 file 0.911 → 0.932). Ini wajar karena seluruh BPMN dev set berbahasa Inggris,
sehingga kamus ID → EN praktis tidak terpakai.

**Catatan regresi pada parameter hasil tuning (`k1=0.5`, `b=1.0`):** sinonim menurunkan F1@5 file
dari 0.750 → 0.722. Penyebabnya satu skenario, **S06** (P@5 1.0 → 0.8, R@5 0.71 → 0.57). Grup sinonim
`approve: [review, ...]` membuat kata "review/reviews" di kode dihitung sebagai "approve", sehingga
`purchasing/adapter/postgres/store.go` naik dan satu berkas relevan tergeser. Kamus ID → EN sendiri
tidak mengubah angka (0.750 tetap). **Rekomendasi:** keluarkan `review` dari grup `approve` sebelum
sinonim dinyalakan; approve dan review adalah langkah berbeda di Simple-ERP.

### 2b. Model BPMN riil berbahasa Indonesia (`data/bpmn/real/`)

Pasangan `l0-simple-erp_old/new.bpmn` tidak punya ground truth (perubahannya hanya merapikan diagram),
jadi pengujian ini **kualitatif**.

| | Kamus mati | Sinonim + ID → EN aktif |
|---|---|---|
| Term query Indonesia yang tidak cocok dengan kode | `aks`, `pengguna`, `laporan`, `pemilik`, `kebutuhan`, `konfigurasi`, `pengendalian` | tidak ada (kecuali `keseluruhan`) |
| Term hasil terjemahan | – | `access`, `user`, `report`, `owner`, `requir`, `configur`, `control` |
| Top-1 | `frontend/features/finance/finance-workspace.tsx` | `backend/cmd/api/main.go` |
| Term yang cocok di top-1 | ap, ar, data, financ, order, role | access, ap, ar, data, financ, inventori, master, report, requir, role, user |

**Temuan:**
1. Kamus ID → EN berhasil: istilah bisnis Indonesia kini cocok dengan identifier berbahasa Inggris di
   kode Simple-ERP (`user`, `access`, `report`). Tanpa kamus, kecocokan hanya lewat kata Inggris yang
   kebetulan ada di label (Finance, Order to Cash, Procure to Pay).
2. Hasil teratas berpindah ke `backend/cmd/api/main.go` (wiring semua modul), yang memang paling
   relevan untuk perubahan di model level-0 yang mencakup semua modul.
3. Risiko: `kebutuhan → requirement` menghasilkan term `requir`, yang juga cocok dengan kata umum
   "required" di kode (mis. `migration_contract_test.go` naik ke #2). Perlu dipertimbangkan untuk dihapus
   atau dipetakan ke istilah lain.

---

## 3. Tabel dekomposisi (ablation), file level, dev set

| Tahapan | Konfigurasi | F1@5 (File) | Recall@5 (File) | MRR | Keterangan |
|---|---|---|---|---|---|
| Baseline (M1) | `k1=1.5`, `b=0.75`, tanpa task context | 0.657 | 0.667 | 1.000 | Baseline resmi M1 |
| + Fitur Orang 2 | `k1=1.5`, `b=0.75`, + task context 0.3 | **0.685** | **0.690** | 1.000 | Kontribusi fitur query (+0.028 F1@5) |
| + Tuning Orang 3 | `k1=0.5`, `b=1.0`, + task context 0.3 | 0.750 | 0.756 | 1.000 | Hasil gabungan M2 (dihitung ulang, sama dengan `m2_tuned.md`) |
| + Kamus (eksperimen) | `k1=0.5`, `b=1.0`, + task context + sinonim + ID → EN | 0.722 | 0.732 | 1.000 | Eksperimen M3; turun karena sinonim `approve ↔ review` (S06) |
| + Kamus (hanya ID → EN) | `k1=0.5`, `b=1.0`, + task context + ID → EN | 0.750 | 0.756 | 1.000 | Tidak ada regresi |

> **Catatan untuk Orang 3:** header `m2_tuned.md` menulis `k1=0.9`, `b=0.5`, tetapi angka F1@5 0.750
> hanya terreproduksi dengan `k1=0.5`, `b=1.0`. Dengan `k1=0.9`, `b=0.5` (+ TC) F1@5 file = 0.685.
> `config/default.yaml` di `main` masih `k1=1.5`, `b=0.75`.

---

## 4. Kesimpulan & rekomendasi

1. **Task context** memberi kenaikan kecil di file level (+0.028 F1@5, dari S05) dan penurunan kecil di
   function level (−0.022, dari S06). Tetap aktif dengan bobot 0.3; bobotnya bisa ikut di-tuning
   bersama `k1`/`b` di LOSO (M3).
2. **Kamus ID → EN** aman (tidak ada regresi di S01–S06) dan jelas membantu model berbahasa Indonesia.
   Layak dinyalakan untuk demo dengan model `docs/bpm-haqi`.
3. **Kamus sinonim** sebaiknya tetap `false` sampai `review` dikeluarkan dari grup `approve`.
4. Test set S07–S10 tidak disentuh; seluruh angka di dokumen ini hanya dari dev set.
