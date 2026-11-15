# Proposal Audit Stopwords & Daftar Stopwords Bahasa Indonesia

Dokumen ini disusun sebagai *deliverable* Milestone 1 (M1) untuk peran **Orang 2 (Preprocessing & Query Builder)**, berdasarkan hasil audit menggunakan skrip [`experiments/term_stats.py`](file:///mnt/c/Users/USER/a-dea/kuliah/sems%207/SE/bpmn-impact-retrieval/experiments/term_stats.py).

---

## 1. Temuan Masalah & Latar Belakang

Berdasarkan analisis frekuensi kata pada basis kode target (`Simple-ERP`) dan model BPMN riil di `data/bpmn/real/`:

1. **Kecocokan Semu (*Accidental Matches*) pada Model Bahasa Indonesia:**
   Pada pasangan BPMN asli (`data/bpm-haqi/level-0/l0-simple-erp.bpmn`), label sequence flow dan proses ditulis dalam Bahasa Indonesia (contoh: *"Master data dan konfigurasi"*, *"Finance AP dan AR"*, *"Kebutuhan apa?"*). 
   Sistem saat ini mencocokkan teks tersebut dengan komponen UI Simple-ERP (`frontend/app/*/page.tsx`) **terutama karena kata sambung `"dan"` (DF = 11 dokumen / 6.2%) dan kata `"yang"` (DF = 7 dokumen)**. Tanpa stopword bahasa Indonesia, pencarian menghasilkan *false positive* yang tinggi hanya karena partikel/kata hubung umum.

2. **Kata Boilerplate Pemrograman dengan DF Sangat Tinggi:**
   Audit frekuensi dokumen (*Document Frequency / DF*) menunjukkan beberapa istilah teknis umum muncul di sebagian besar berkas Simple-ERP tanpa membawa makna spesifik proses bisnis:
   - `id`: Muncul di **106 dari 176 dokumen (60.2%)**, dengan total 2.952 kemunculan.
   - `github`, `com`: Muncul di **53 dokumen (30.1%)**, berasal dari baris import Go package (`github.com/AbimanyuDA/Simple-ERP/...`).
   - `status`: Muncul di **75 dokumen (42.6%)**, 816 kemunculan.
   - `request`: Muncul di **67 dokumen (38.1%)**, 563 kemunculan.
   - `application`: Muncul di **53 dokumen (30.1%)**, 449 kemunculan.

---

## 2. Draft Usulan: Stopwords Bahasa Indonesia (`indonesian_stopwords`)

Daftar kata berikut diusulkan untuk ditambahkan ke konfigurasi preprocessing sistem. Kata-kata ini dikelompokkan berdasarkan kategori tata bahasa:

### A. Konjungsi (Kata Sambung)
```yaml
dan, atau, serta, tetapi, tapi, melainkan, sedangkan, namun, padahal,
karena, sebab, sehingga, maka, agar, supaya, untuk, jika, kalau, jikalau,
bila, apabila, asalkan, walaupun, meskipun, kendatipun, biarpun, bahwa,
setelah, sesudah, sebelum, ketika, saat, sewaktu, sementara, lalu, kemudian
```

### B. Preposisi (Kata Depan)
```yaml
di, ke, dari, pada, dalam, bagi, kepada, daripada, oleh, dengan,
tentang, tanpa, antara, hingga, sampai, atas, bawah, depan, belakang
```

### C. Pronomina, Partikel, & Penunjuk
```yaml
ini, itu, yang, ada, adalah, ialah, merupakan, yaitu, yakni, tersebut,
suatu, para, setiap, tiap, masing, per, pun, lah, kah, dong
```

### D. Modalitas, Negasi, & Tanya
```yaml
apa, apakah, bagaimana, bagaimanakah, kapan, mana, di mana, ke mana, dari mana,
siapa, siapakah, mengapa, kenapa, bisa, dapat, boleh, harus, wajib,
akan, telah, sudah, sedang, lagi, belum, tidak, tak, bukan, jangan
```

### E. Istilah Alur & Elemen Umum BPMN
```yaml
alur, tahap, tahapan, langkah, proses, kegiatan, aktivitas,
mulai, selesai, aksi, hasil, diterima, sistem, pengguna
```

---

## 3. Usulan Penambahan pada `code_stopwords`

Berdasarkan hasil pemindaian `term_stats.py`, berikut istilah kode yang diusulkan untuk ditambahkan ke daftar `code_stopwords`:

| Istilah | DF | DF % | Alasan |
|---|:---:|:---:|---|
| `id` | 106 | 60.2% | Identifier generik Go/TS/SQL yang muncul hampir di semua struct, query, dan komponen UI. |
| `github` | 53 | 30.1% | Bagian dari URL path package import Go (`github.com/...`). |
| `com` | 54 | 30.7% | Domain suffix dari import package Go. |
| `request` | 67 | 38.1% | Istilah generik HTTP request/DTO di handler dan controller. |
| `status` | 75 | 42.6% | Properti status umum (HTTP status atau model status) yang ada di hampir semua modul. |

---

## 4. Rencana Integrasi Teknis

### A. Konfigurasi (`config/default.yaml`)
Tambahkan field `indonesian_stopwords` pada blok `preprocessing`:

```yaml
preprocessing:
  split_identifiers: true
  lowercase: true
  remove_stopwords: true
  stemming: porter
  min_token_length: 2
  code_stopwords: [func, return, err, nil, ctx, context, string, int, bool, error, var, const,
                   type, struct, interface, package, import, if, else, for, range, defer, go,
                   tx, "true", "false", "null", undefined, async, await, export, default, let,
                   new, http, json, api, internal, adapter, backend, frontend, src, ts, tsx,
                   app, features, lib, fmt, errors, len, make, append, map, chi, pgx,
                   use, div, span, props,
                   # Usulan baru M1:
                   id, github, com, request, status]
  bpmn_stopwords: [task, process, start, end, event, gateway, flow, lane, level, completed,
                   requested, identified, ready, merge]
  indonesian_stopwords: [dan, atau, serta, tetapi, tapi, melainkan, sedangkan, namun,
                         karena, sebab, sehingga, agar, supaya, jika, kalau, bila, apabila,
                         walaupun, meskipun, bahwa, setelah, sesudah, sebelum, ketika, saat,
                         lalu, kemudian, di, ke, dari, pada, dalam, untuk, bagi, kepada, oleh,
                         dengan, tentang, tanpa, antara, hingga, sampai, atas, bawah, ini,
                         itu, yang, ada, adalah, ialah, tersebut, suatu, para, setiap, masing,
                         per, pun, apa, apakah, bagaimana, kapan, mana, siapa, mengapa, kenapa,
                         bisa, dapat, akan, telah, sudah, belum, tidak, bukan, alur, tahap,
                         langkah, proses, kegiatan, mulai, selesai, aksi, hasil, diterima]
```

### B. Modifikasi Parser Token (`src/impact_retrieval/preprocessing/text.py`)
Pada class `Analyzer`, cukup tambahkan `"indonesian_stopwords"` ke dalam tuple pengecekan stopword:
```python
if cfg.get("remove_stopwords", True):
    stop |= set(ENGLISH_STOP_WORDS)
    for key in ("code_stopwords", "bpmn_stopwords", "extra_stopwords", "indonesian_stopwords"):
        stop |= {str(w).lower() for w in cfg.get(key) or () if w is not None}
```

---

## 5. Analisis Risiko & Evaluasi Dampak (Safety Check)

1. **Dev Set (S01–S06):**
   - Seluruh model BPMN skenario S01–S06 menggunakan Bahasa Inggris.
   - Penambahan `indonesian_stopwords` **tidak akan mengubah nilai metrik dev set sama sekali ($P@k, R@k, F1@k, MRR$)**, sehingga aman dari risiko regresi.
2. **Evaluasi Penambahan `code_stopwords` (`id`, `github`, `com`, dll.):**
   - Sebelum di-merge permanen pada Milestone 2 (M2), jalankan `python experiments/run_eval.py` di branch terpisah.
   - Bandingkan tabel metrik sebelum dan sesudah untuk memastikan $F1@5$ dan $MRR$ pada S01–S06 tidak mengalami penurunan.
