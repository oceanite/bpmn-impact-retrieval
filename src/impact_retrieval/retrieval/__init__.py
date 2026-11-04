"""Retrieval methods. Every method implements ``index(docs)`` and ``search(query, k)``."""
from __future__ import annotations

from typing import Mapping

from ..preprocessing import Analyzer
from .base import Retriever
from .bm25 import BM25Retriever
from .keyword import KeywordRetriever
from .tfidf import TfidfRetriever

METHODS = ("bm25", "keyword", "tfidf")


def make_retriever(method: str, cfg: Mapping) -> Retriever:
    """Build an (unindexed) retriever from the full config."""
    analyzer = Analyzer(cfg.get("preprocessing"))
    r = cfg.get("retrieval", {})
    if method == "bm25":
        bm = r.get("bm25", {})
        return BM25Retriever(analyzer, k1=bm.get("k1", 1.5), b=bm.get("b", 0.75),
                             field_weights=r.get("field_weights"))
    if method == "keyword":
        return KeywordRetriever()
    if method == "tfidf":
        return TfidfRetriever(analyzer, sublinear_tf=r.get("tfidf", {}).get("sublinear_tf", True))
    raise ValueError(f"unknown method {method!r}; choose one of {METHODS}")


__all__ = ["BM25Retriever", "KeywordRetriever", "METHODS", "Retriever", "TfidfRetriever", "make_retriever"]
