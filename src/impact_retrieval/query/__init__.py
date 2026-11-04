"""Build a weighted text query from a BPMN diff."""
from .builder import DEFAULT_WEIGHTS, build_query, strip_ids

__all__ = ["DEFAULT_WEIGHTS", "build_query", "strip_ids"]
