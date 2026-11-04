"""Shared retriever interface and the analyzed corpus all methods index from."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from ..preprocessing import Analyzer
from ..types import CodeDocument, Query, SearchResult


@dataclass(frozen=True)
class AnalyzedDoc:
    document: CodeDocument
    field_terms: dict[str, Counter]   # field -> term counts after analysis


def analyze_corpus(docs: Sequence[CodeDocument], analyzer: Analyzer) -> list[AnalyzedDoc]:
    return [AnalyzedDoc(d, {f: Counter(analyzer.tokens(text)) for f, text in d.fields.items()})
            for d in docs]


def weighted_query_terms(query: Query, analyzer: Analyzer) -> dict[str, float]:
    """term -> summed weight over all query parts (insertion order = first appearance)."""
    weights: dict[str, float] = {}
    for part in query.parts:
        for term in analyzer.tokens(part.text):
            weights[term] = weights.get(term, 0.0) + part.weight
    return weights


class Retriever(ABC):
    """All methods: build once with ``index(docs)``, then ``search(query, k)``."""

    name: str = "base"

    @abstractmethod
    def index(self, docs: Sequence[CodeDocument]) -> "Retriever":
        ...

    @abstractmethod
    def search(self, query: Query, k: int = 10) -> list[SearchResult]:
        ...


def rank(scored: list[tuple[float, CodeDocument, tuple]], k: int) -> list[SearchResult]:
    """Sort by score desc, then doc_id asc (deterministic ties); keep positive scores only."""
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda s: (-s[0], s[1].doc_id))
    return [SearchResult(rank=i + 1, score=s, document=d, evidence=ev)
            for i, (s, d, ev) in enumerate(scored[:k])]
