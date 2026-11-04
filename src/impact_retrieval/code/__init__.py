"""Extract retrievable documents (functions, components, routes, migrations, config) from the target repo."""
from .extractor import extract_corpus, extract_file

__all__ = ["extract_corpus", "extract_file"]
