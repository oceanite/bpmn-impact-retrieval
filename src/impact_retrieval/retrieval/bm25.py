"""BM25 over fielded documents (BM25F-style weighted term frequency).

For document d and term t::

    wtf(t, d) = sum_f  w_f * tf_f(t, d)          # field-weighted term frequency
    wdl(d)    = sum_f  w_f * len_f(d)            # field-weighted length
    idf(t)    = ln(1 + (N - df + 0.5) / (df + 0.5))
    score     = sum_t  q_t * idf(t) * wtf (k1 + 1) / (wtf + k1 (1 - b + b * wdl / avg_wdl))

``q_t`` is the summed weight of t over the query parts. With all field weights 1 and all
query weights 1 this is plain Okapi BM25. Evidence splits each term's contribution over
fields in proportion to ``w_f * tf_f``.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Mapping, Sequence

from ..preprocessing import Analyzer
from ..types import CodeDocument, Evidence, Query, SearchResult
from .base import Retriever, analyze_corpus, rank, weighted_query_terms


class BM25Retriever(Retriever):
    name = "bm25"

    def __init__(self, analyzer: Analyzer, k1: float = 1.5, b: float = 0.75,
                 field_weights: Mapping[str, float] | None = None):
        if k1 < 0 or not 0 <= b <= 1:
            raise ValueError("BM25 needs k1 >= 0 and 0 <= b <= 1")
        self.analyzer, self.k1, self.b = analyzer, float(k1), float(b)
        self.field_weights = {f: float(w) for f, w in (field_weights or {}).items()}

    def _w(self, field: str) -> float:
        return self.field_weights.get(field, 1.0)

    def index(self, docs: Sequence[CodeDocument]) -> "BM25Retriever":
        self.docs = list(docs)
        analyzed = analyze_corpus(self.docs, self.analyzer)
        self.postings: dict[str, list[tuple[int, float, dict[str, float]]]] = defaultdict(list)
        self.doc_len: list[float] = []
        for i, ad in enumerate(analyzed):
            per_term: dict[str, dict[str, float]] = defaultdict(dict)
            length = 0.0
            for field, counts in ad.field_terms.items():
                w = self._w(field)
                if w <= 0:
                    continue
                length += w * sum(counts.values())
                for term, tf in counts.items():
                    per_term[term][field] = w * tf
            self.doc_len.append(length)
            for term, by_field in per_term.items():
                self.postings[term].append((i, sum(by_field.values()), by_field))
        n = len(self.docs)
        self.avg_len = (sum(self.doc_len) / n) if n else 0.0
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}
        return self

    def search(self, query: Query, k: int = 10) -> list[SearchResult]:
        scores: dict[int, float] = defaultdict(float)
        evidence: dict[int, list[Evidence]] = defaultdict(list)
        for term, q_w in weighted_query_terms(query, self.analyzer).items():
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, wtf, by_field in self.postings[term]:
                norm = self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avg_len) if self.avg_len else 0
                s = q_w * idf * wtf * (self.k1 + 1) / (wtf + norm)
                scores[i] += s
                for field, part in sorted(by_field.items()):
                    evidence[i].append(Evidence(term, field, s * part / wtf))
        scored = [(s, self.docs[i], tuple(sorted(evidence[i], key=lambda e: (-e.contribution, e.term, e.field))))
                  for i, s in scores.items()]
        return rank(scored, k)
