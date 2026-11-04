"""Text analysis shared by queries and code documents.

Both sides MUST go through the same Analyzer so that terms can match:
``MatchSupplierInvoice`` and "Validate invoice match" both yield ``match``, ``invoic``.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, Mapping

from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")
# camelCase / PascalCase / ACRONYMWord / trailing digits
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")

_stemmer = PorterStemmer()


@lru_cache(maxsize=200_000)
def _stem(token: str) -> str:
    return _stemmer.stem(token)


def split_identifier(token: str) -> list[str]:
    """``getHTTPResponse_code2`` -> ``['get', 'http', 'response', 'code', '2']``."""
    parts: list[str] = []
    for chunk in re.split(r"[_\-\s.$/]+", token):
        parts.extend(p.lower() for p in _CAMEL.findall(chunk))
    return parts


class Analyzer:
    """Configurable tokenizer: identifier split -> lowercase -> stopwords -> min length -> stem."""

    def __init__(self, cfg: Mapping | None = None):
        cfg = dict(cfg or {})
        self.split_identifiers = cfg.get("split_identifiers", True)
        self.lowercase = cfg.get("lowercase", True)
        self.min_len = int(cfg.get("min_token_length", 2))
        self.stem = (cfg.get("stemming") or "none").lower() == "porter"
        stop: set[str] = set()
        if cfg.get("remove_stopwords", True):
            stop |= set(ENGLISH_STOP_WORDS)
            for key in ("code_stopwords", "bpmn_stopwords", "extra_stopwords"):
                # str(): unquoted YAML words like true/false/null arrive as bool/None
                stop |= {str(w).lower() for w in cfg.get(key) or () if w is not None}
        self.stopwords = frozenset(stop)

    def tokens(self, text: str | None) -> list[str]:
        if not text:
            return []
        out: list[str] = []
        for word in _WORD.findall(text):
            pieces = split_identifier(word) if self.split_identifiers else [word]
            for piece in pieces:
                t = piece.lower() if self.lowercase else piece
                if len(t) < self.min_len or t.isdigit() or t in self.stopwords:
                    continue
                out.append(_stem(t) if self.stem else t)
        return out

    def tokens_many(self, texts: Iterable[str]) -> list[str]:
        out: list[str] = []
        for t in texts:
            out.extend(self.tokens(t))
        return out


def plain_words(text: str | None, stopwords: frozenset[str] = frozenset(ENGLISH_STOP_WORDS)) -> list[str]:
    """Baseline tokenizer: lowercase alphanumeric words, English stopwords removed.

    No identifier splitting and no stemming, i.e. what a person would type into grep.
    """
    if not text:
        return []
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1 and w not in stopwords]
