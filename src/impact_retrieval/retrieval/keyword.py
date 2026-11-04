"""Plain keyword baseline: what ``grep -i -F`` with the query words would find.

No identifier splitting, no stemming, no field weights. Score = number of distinct query
words found in the document text (case-insensitive substring); ties are broken by the total
number of occurrences, then by doc_id.
"""
from __future__ import annotations

from typing import Sequence

from ..preprocessing import plain_words
from ..types import CodeDocument, Evidence, Query, SearchResult
from .base import Retriever, rank


class KeywordRetriever(Retriever):
    name = "keyword"

    def index(self, docs: Sequence[CodeDocument]) -> "KeywordRetriever":
        self.docs = list(docs)
        self.fields_lower = [{f: t.lower() for f, t in d.fields.items()} for d in self.docs]
        return self

    def search(self, query: Query, k: int = 10) -> list[SearchResult]:
        words = list(dict.fromkeys(plain_words(query.text)))
        scored = []
        for doc, fields in zip(self.docs, self.fields_lower):
            matched, total, ev = 0, 0, []
            for w in words:
                hits = {f: t.count(w) for f, t in fields.items() if w in t}
                if hits:
                    matched += 1
                    total += sum(hits.values())
                    ev.extend(Evidence(w, f, 1.0 / len(hits)) for f in sorted(hits))
            if matched:
                # occurrences only break ties between equal distinct-match counts
                scored.append((matched + total / (total + 1) * 0.999, doc, tuple(ev)))
        return rank(scored, k)
