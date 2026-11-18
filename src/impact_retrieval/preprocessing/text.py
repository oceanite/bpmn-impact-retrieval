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


def build_synonym_map(groups: Mapping | None) -> dict[str, str]:
    """``{canonical: [variant, ...]}`` -> ``{variant: canonical}`` (all lowercase).

    Mapping every variant to one canonical word is deterministic and symmetric: query and code
    go through the same Analyzer, so ``bill`` in a BPMN label and ``Invoice`` in code meet as
    ``invoice``. A word listed under two canonicals keeps the first (config order).
    """
    out: dict[str, str] = {}
    for canonical, variants in (groups or {}).items():
        canon = str(canonical).lower()
        for v in [canonical, *(variants or ())]:
            out.setdefault(str(v).lower(), canon)
    return out


def build_translation_map(terms: Mapping | None) -> dict[str, tuple[str, ...]]:
    """``{indonesian: "english words"}`` -> ``{indonesian: ("english", "words")}`` (lowercase)."""
    return {str(k).lower(): tuple(str(v).lower().split()) for k, v in (terms or {}).items() if v}


class Analyzer:
    """Configurable tokenizer.

    identifier split -> lowercase -> Indonesian->English -> synonyms -> stopwords -> min length -> stem.
    Translation and synonyms are off unless ``use_translation`` / ``use_synonyms`` is true.
    """

    def __init__(self, cfg: Mapping | None = None):
        cfg = dict(cfg or {})
        self.split_identifiers = cfg.get("split_identifiers", True)
        self.lowercase = cfg.get("lowercase", True)
        self.min_len = int(cfg.get("min_token_length", 2))
        self.stem = (cfg.get("stemming") or "none").lower() == "porter"
        stop: set[str] = set()
        if cfg.get("remove_stopwords", True):
            stop |= set(ENGLISH_STOP_WORDS)
            for key in ("code_stopwords", "bpmn_stopwords", "extra_stopwords", "indonesian_stopwords"):
                # str(): unquoted YAML words like true/false/null arrive as bool/None
                stop |= {str(w).lower() for w in cfg.get(key) or () if w is not None}
        self.stopwords = frozenset(stop)
        self.translations = build_translation_map(cfg.get("id_en_terms")) if cfg.get("use_translation") else {}
        self.synonyms = build_synonym_map(cfg.get("synonyms")) if cfg.get("use_synonyms") else {}

    def _normalize(self, token: str) -> list[str]:
        """Translate and canonicalize one token; may return several words (multi-word translation)."""
        key = token.lower()
        words = self.translations.get(key) or (token,)
        if self.synonyms:
            words = tuple(self.synonyms.get(w.lower(), w) for w in words)
        return list(words)

    def tokens(self, text: str | None) -> list[str]:
        if not text:
            return []
        out: list[str] = []
        for word in _WORD.findall(text):
            pieces = split_identifier(word) if self.split_identifiers else [word]
            for piece in pieces:
                piece = piece.lower() if self.lowercase else piece
                for t in self._normalize(piece) if (self.translations or self.synonyms) else (piece,):
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
