"""Data contracts shared between pipeline stages.

Every stage talks to the next only through these types:

    bpmn.diff  ->  BpmnDiff
    query      ->  Query            (raw, weighted text parts; each retriever analyzes them itself)
    code       ->  CodeDocument     (one per function / component / route / file)
    retrieval  ->  SearchResult     (ranked document + evidence)
    pipeline   ->  ImpactReport     (everything the website and evaluation need)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

#: Fields a CodeDocument may carry. Field weights in config/default.yaml use these names.
FIELDS: tuple[str, ...] = ("path", "name", "route", "db_table", "comment", "config", "test", "body")


@dataclass(frozen=True)
class CodeDocument:
    """One retrievable unit of the target codebase."""

    doc_id: str                 # "<path>::<function>" or "<path>" for file-level documents
    path: str                   # POSIX path relative to the target repo root
    function: str               # function / method / component / type / route; "" = whole file
    kind: str                   # function | method | type | component | test | route | migration | config | file
    language: str               # go | typescript | sql | yaml | json
    start_line: int
    end_line: int
    fields: Mapping[str, str]   # raw (unprocessed) text per field name in FIELDS

    def text(self) -> str:
        """All field text joined; used by the plain keyword baseline."""
        return "\n".join(v for v in self.fields.values() if v)


@dataclass(frozen=True)
class QueryPart:
    """A piece of query text with a weight and where it came from."""

    text: str
    weight: float
    role: str                   # name_new | name_old | documentation | flow_endpoint | lane | process
    element_id: str             # BPMN element that produced it


@dataclass(frozen=True)
class Query:
    parts: tuple[QueryPart, ...]

    @property
    def text(self) -> str:
        return " ".join(p.text for p in self.parts)

    @property
    def is_empty(self) -> bool:
        return not any(p.text.strip() for p in self.parts)


@dataclass(frozen=True)
class Evidence:
    """Why a document matched: one query term in one field."""

    term: str
    field: str
    contribution: float         # share of the document score from this term/field


@dataclass(frozen=True)
class SearchResult:
    rank: int                   # 1-based
    score: float
    document: CodeDocument
    evidence: tuple[Evidence, ...] = ()

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "score": round(self.score, 6),
            "file": self.document.path,
            "function": self.document.function,
            "kind": self.document.kind,
            "lines": [self.document.start_line, self.document.end_line],
            "evidence": [{"term": e.term, "field": e.field, "contribution": round(e.contribution, 6)}
                         for e in self.evidence],
        }


@dataclass(frozen=True)
class ImpactReport:
    method: str
    query: Query
    results: tuple[SearchResult, ...]
    changes: object                  # bpmn.BpmnDiff (kept untyped to avoid an import cycle)
    latency_ms: float                # query building + search; excludes one-time indexing
    params: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "latency_ms": round(self.latency_ms, 3),
            "params": dict(self.params),
            "query": [{"text": p.text, "weight": p.weight, "role": p.role, "element_id": p.element_id}
                      for p in self.query.parts],
            "changes": self.changes.to_dict() if hasattr(self.changes, "to_dict") else None,
            "results": [r.to_dict() for r in self.results],
        }
