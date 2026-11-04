"""TF-IDF + cosine similarity baseline (scikit-learn). Same analyzer as BM25, no field weights."""
from __future__ import annotations

from typing import Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..preprocessing import Analyzer
from ..types import CodeDocument, Evidence, Query, SearchResult
from .base import Retriever, analyze_corpus, rank, weighted_query_terms


class TfidfRetriever(Retriever):
    name = "tfidf"

    def __init__(self, analyzer: Analyzer, sublinear_tf: bool = True):
        self.analyzer, self.sublinear_tf = analyzer, sublinear_tf

    def index(self, docs: Sequence[CodeDocument]) -> "TfidfRetriever":
        self.docs = list(docs)
        analyzed = analyze_corpus(self.docs, self.analyzer)
        self.term_fields = [{t: sorted(f for f, c in ad.field_terms.items() if t in c)
                             for c in ad.field_terms.values() for t in c} for ad in analyzed]
        token_lists = [[t for c in ad.field_terms.values() for t, n in c.items() for _ in range(n)]
                       for ad in analyzed]
        self.vectorizer = TfidfVectorizer(analyzer=lambda tokens: tokens, lowercase=False,
                                          sublinear_tf=self.sublinear_tf, norm="l2")
        self.matrix = self.vectorizer.fit_transform(token_lists).tocsr()
        self.vocab = self.vectorizer.vocabulary_
        return self

    def search(self, query: Query, k: int = 10) -> list[SearchResult]:
        q_terms = {t: w for t, w in weighted_query_terms(query, self.analyzer).items() if t in self.vocab}
        if not q_terms:
            return []
        cols = np.array([self.vocab[t] for t in q_terms])
        q = np.array([w for w in q_terms.values()]) * self.vectorizer.idf_[cols]
        q = q / np.linalg.norm(q)
        sub = self.matrix[:, cols]                     # docs x query-terms
        contrib = sub.multiply(q).tocsr()              # cosine contribution per term
        scores = np.asarray(contrib.sum(axis=1)).ravel()
        terms = list(q_terms)
        scored = []
        for i in np.flatnonzero(scores > 0):
            row = contrib.getrow(i)
            ev = []
            for j, val in zip(row.indices, row.data):
                fields = self.term_fields[i].get(terms[j], ["body"])
                ev.extend(Evidence(terms[j], f, float(val) / len(fields)) for f in fields)
            ev.sort(key=lambda e: (-e.contribution, e.term, e.field))
            scored.append((float(scores[i]), self.docs[i], tuple(ev)))
        return rank(scored, k)
