"""Turn the target repository into CodeDocuments.

Units
-----
* Go       : one document per function, method and type declaration (tests -> kind "test").
             Files without declarations become one file-level document.
* TS / TSX : one document per top-level function, arrow-function const, class, interface and
             type alias (PascalCase function in .tsx -> kind "component"). Test/spec files become
             one file-level document whose ``test`` field lists the test titles.
* OpenAPI  : one document per path (kind "route") plus one for ``components``.
* SQL      : one document per migration file (kind "migration").
* YAML/JSON: one file-level document (kind "config").

Fields (raw text, analyzed later): path, name, route, db_table, comment, config, test, body.
Output order is deterministic: files sorted by path, units by position.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterator, Mapping

import tree_sitter_go
import tree_sitter_typescript
import yaml
from tree_sitter import Language, Node, Parser

from ..types import CodeDocument

_GO = Language(tree_sitter_go.language())
_TS = Language(tree_sitter_typescript.language_typescript())
_TSX = Language(tree_sitter_typescript.language_tsx())

_SQL_TABLE = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE(?:\s+IF\s+(?:NOT\s+)?EXISTS)?|ON)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE)
_SQL_NOT_TABLES = {"select", "set", "where", "only", "conflict", "delete", "update", "true", "false",
                   "now", "lateral", "unnest", "a", "b", "c", "d", "g", "l", "p", "t", "u", "s"}
_GO_ROUTE = re.compile(
    r"\.(Get|Post|Put|Patch|Delete|Head|Options)\(\s*[\"`]([^\"`]+)[\"`]\s*,\s*\w+\.(\w+)\s*\)")
_TS_TEST_CALL = re.compile(r"\b(?:test|it|describe)(?:\.\w+)?\(\s*[\"'`]([^\"'`]+)[\"'`]")
_TEMPLATE_SUB = re.compile(r"\$\{[^}]*\}")

_GO_IDENT = {"identifier", "field_identifier", "type_identifier", "package_identifier"}
_TS_IDENT = {"identifier", "property_identifier", "type_identifier", "shorthand_property_identifier",
             "shorthand_property_identifier_pattern"}


@dataclass
class _Unit:
    """Mutable document under construction."""
    path: str
    function: str
    kind: str
    language: str
    start_line: int
    end_line: int
    fields: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add(self, name: str, *texts: str) -> None:
        self.fields[name].extend(t for t in texts if t)

    def freeze(self, doc_id: str) -> CodeDocument:
        return CodeDocument(
            doc_id=doc_id, path=self.path, function=self.function, kind=self.kind,
            language=self.language, start_line=self.start_line, end_line=self.end_line,
            fields={k: " ".join(v) for k, v in sorted(self.fields.items()) if v})


# --------------------------------------------------------------------------- public API

def extract_corpus(repo_root: str | Path, cfg: Mapping) -> list[CodeDocument]:
    """Walk ``repo_root`` according to ``cfg`` (the ``code_extraction`` section) and extract documents."""
    root = Path(repo_root)
    if not root.is_dir():
        raise FileNotFoundError(f"target repository not found: {root}")
    include = {e.lower() for e in cfg.get("include_extensions", [])}
    exclude_dirs = set(cfg.get("exclude_dirs", []))
    exclude_files = set(cfg.get("exclude_files", []))
    openapi = cfg.get("openapi_spec")

    openapi_names = {n.lower() for n in cfg.get("openapi_filenames", [])}
    units: list[_Unit] = []
    for file in _walk(root, include, exclude_dirs, exclude_files):
        rel = file.relative_to(root).as_posix()
        is_openapi = rel == openapi or file.name.lower() in openapi_names
        units.extend(extract_file(rel, file.read_bytes(), is_openapi=is_openapi))

    _attach_go_routes(units)
    return _freeze_all(units)


def extract_file(rel_path: str, content: bytes, is_openapi: bool = False) -> list[_Unit]:
    """Extract the units of one file. ``rel_path`` is POSIX and relative to the repo root."""
    suffix = PurePosixPath(rel_path).suffix.lower()
    if suffix == ".go":
        units = _extract_go(rel_path, content)
    elif suffix in (".ts", ".tsx"):
        units = _extract_ts(rel_path, content, tsx=(suffix == ".tsx"))
    elif suffix == ".sql":
        units = [_extract_sql(rel_path, content)]
    elif suffix in (".yaml", ".yml") and is_openapi:
        units = _extract_openapi(rel_path, content)
    elif suffix in (".yaml", ".yml", ".json"):
        units = [_extract_config(rel_path, content)]
    else:
        units = []
    for u in units:
        u.add("path", _path_words(rel_path))
    return units


# --------------------------------------------------------------------------- walking / helpers

def _walk(root: Path, include: set[str], exclude_dirs: set[str], exclude_files: set[str]) -> Iterator[Path]:
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
        rel_parts = path.relative_to(root).parts
        if any(part in exclude_dirs for part in rel_parts[:-1]):
            continue
        if path.is_file() and path.suffix.lower() in include and path.name not in exclude_files:
            yield path


def _path_words(rel_path: str) -> str:
    p = PurePosixPath(rel_path)
    return " ".join([*p.parts[:-1], p.stem])


def _freeze_all(units: list[_Unit]) -> list[CodeDocument]:
    docs, seen = [], set()
    for u in units:
        doc_id = f"{u.path}::{u.function}" if u.function else u.path
        if doc_id in seen:  # e.g. two receivers with the same method name in one file
            doc_id = f"{doc_id}@{u.start_line}"
        seen.add(doc_id)
        docs.append(u.freeze(doc_id))
    return docs


def _walk_nodes(node: Node) -> Iterator[Node]:
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def _text(node: Node | None) -> str:
    return node.text.decode("utf-8", "replace") if node is not None and node.text else ""


def _sql_tables(text: str) -> list[str]:
    tables = []
    for m in _SQL_TABLE.finditer(text):
        name = m.group(1).lower()
        if name not in _SQL_NOT_TABLES and name not in tables:
            tables.append(name)
    return tables


def _strip_comment(text: str) -> str:
    return re.sub(r"^\s*(//+|/\*+|\*+/?|--+|#)\s?", "", text, flags=re.MULTILINE).replace("*/", " ")


def _leading_comments(node: Node) -> list[str]:
    """Comments directly above ``node`` (no blank line in between)."""
    out, prev, line = [], node.prev_sibling, node.start_point[0]
    while prev is not None and prev.type == "comment" and prev.end_point[0] >= line - 1:
        out.insert(0, _strip_comment(_text(prev)))
        line, prev = prev.start_point[0], prev.prev_sibling
    return out


def _fill_body(unit: _Unit, node: Node, idents: set[str], string_types: set[str]) -> None:
    for n in _walk_nodes(node):
        if n.type in idents:
            unit.add("body", _text(n))
        elif n.type in string_types:
            s = _text(n)
            unit.add("body", s)
            unit.add("db_table", *_sql_tables(s))
        elif n.type == "comment":
            unit.add("comment", _strip_comment(_text(n)))


# --------------------------------------------------------------------------- Go

def _extract_go(rel: str, content: bytes) -> list[_Unit]:
    tree = Parser(_GO).parse(content)
    is_test_file = rel.endswith("_test.go")
    units: list[_Unit] = []
    strings = {"interpreted_string_literal_content", "raw_string_literal_content"}
    for node in tree.root_node.children:
        specs: list[tuple[Node, str, str]] = []
        if node.type == "function_declaration":
            name = _text(node.child_by_field_name("name"))
            kind = "test" if is_test_file and name.startswith(("Test", "Benchmark", "Fuzz")) else "function"
            specs.append((node, name, kind))
        elif node.type == "method_declaration":
            specs.append((node, _text(node.child_by_field_name("name")), "method"))
        elif node.type == "type_declaration":
            for spec in node.children:
                if spec.type in ("type_spec", "type_alias"):
                    specs.append((spec, _text(spec.child_by_field_name("name")), "type"))
        for decl, name, kind in specs:
            u = _Unit(rel, name, kind, "go", decl.start_point[0] + 1, decl.end_point[0] + 1)
            u.add("test" if kind == "test" else "name", name)
            if node.type == "method_declaration":
                recv = node.child_by_field_name("receiver")
                u.add("name", *[_text(n) for n in _walk_nodes(recv) if n.type == "type_identifier"])
            u.add("comment", *_leading_comments(node))
            _fill_body(u, decl, _GO_IDENT, strings)
            units.append(u)
    if not units:
        u = _Unit(rel, "", "file", "go", 1, tree.root_node.end_point[0] + 1)
        _fill_body(u, tree.root_node, _GO_IDENT, strings)
        units.append(u)
    # Route registrations are resolved after all files are read (see _attach_go_routes).
    text = content.decode("utf-8", "replace")
    for u in units:
        u.fields["_routes"] = [f"{m.group(1).upper()} {m.group(2)}|{m.group(3)}"
                               for m in _GO_ROUTE.finditer(text)
                               if u.start_line <= text.count("\n", 0, m.start()) + 1 <= u.end_line]
    return units


def _attach_go_routes(units: list[_Unit]) -> None:
    """``r.Post("/x", h.create)`` -> route "POST /x" on both the registering function and ``create``."""
    by_pkg: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for u in units:
        for entry in u.fields.pop("_routes", []) if u.language == "go" else []:
            route, handler = entry.split("|")
            u.add("route", route)
            by_pkg[str(PurePosixPath(u.path).parent)][handler].append(route)
    for u in units:
        if u.language == "go" and u.kind == "method":
            for route in by_pkg.get(str(PurePosixPath(u.path).parent), {}).get(u.function, []):
                u.add("route", route)


# --------------------------------------------------------------------------- TypeScript / TSX

def _is_ts_test(rel: str) -> bool:
    name = PurePosixPath(rel).name
    return (".test." in name or ".spec." in name or "/tests/" in f"/{rel}" or "/e2e/" in f"/{rel}")


def _extract_ts(rel: str, content: bytes, tsx: bool) -> list[_Unit]:
    tree = Parser(_TSX if tsx else _TS).parse(content)
    strings = {"string_fragment", "jsx_text"}
    end = tree.root_node.end_point[0] + 1

    if _is_ts_test(rel):
        u = _Unit(rel, "", "test", "typescript", 1, end)
        u.add("test", *_TS_TEST_CALL.findall(content.decode("utf-8", "replace")))
        _fill_body(u, tree.root_node, _TS_IDENT, strings)
        _add_ts_routes(u, tree.root_node)
        return [u]

    units: list[_Unit] = []
    for top in tree.root_node.children:
        decl = top.child_by_field_name("declaration") if top.type == "export_statement" else top
        if decl is None:
            continue
        found: list[tuple[Node, str, str]] = []
        if decl.type in ("function_declaration", "generator_function_declaration", "class_declaration"):
            name = _text(decl.child_by_field_name("name"))
            kind = "component" if tsx and name[:1].isupper() and decl.type != "class_declaration" else (
                "type" if decl.type == "class_declaration" else "function")
            found.append((decl, name, kind))
        elif decl.type in ("interface_declaration", "type_alias_declaration", "enum_declaration"):
            found.append((decl, _text(decl.child_by_field_name("name")), "type"))
        elif decl.type == "lexical_declaration":
            for d in decl.children:
                value = d.child_by_field_name("value") if d.type == "variable_declarator" else None
                if value is not None and value.type in ("arrow_function", "function_expression", "function"):
                    name = _text(d.child_by_field_name("name"))
                    found.append((d, name, "component" if tsx and name[:1].isupper() else "function"))
        for node, name, kind in found:
            u = _Unit(rel, name, kind, "typescript", node.start_point[0] + 1, node.end_point[0] + 1)
            u.add("name", name)
            u.add("comment", *_leading_comments(top))
            _fill_body(u, node, _TS_IDENT, strings)
            _add_ts_routes(u, node)
            units.append(u)
    if not units:
        u = _Unit(rel, "", "file", "typescript", 1, end)
        _fill_body(u, tree.root_node, _TS_IDENT, strings)
        _add_ts_routes(u, tree.root_node)
        units.append(u)
    return units


def _add_ts_routes(unit: _Unit, node: Node) -> None:
    """API paths used in fetch helpers, e.g. `/sales-orders/${id}/confirm` -> /sales-orders/{}/confirm."""
    for n in _walk_nodes(node):
        if n.type in ("string", "template_string"):
            s = _TEMPLATE_SUB.sub("{}", _text(n)[1:-1])
            if re.match(r"^/[a-z][\w\-{}]*(/[\w\-{}]*)*$", s):
                unit.add("route", s)


# --------------------------------------------------------------------------- SQL / OpenAPI / config

def _extract_sql(rel: str, content: bytes) -> _Unit:
    text = content.decode("utf-8", "replace")
    u = _Unit(rel, "", "migration", "sql", 1, text.count("\n") + 1)
    u.add("db_table", *_sql_tables(text))
    u.add("comment", *[m.strip() for m in re.findall(r"--(.*)$", text, flags=re.MULTILINE)])
    u.add("body", re.sub(r"--.*$", "", text, flags=re.MULTILINE))
    return u


def _flatten(value: object) -> Iterator[str]:
    if isinstance(value, Mapping):
        for k, v in value.items():
            yield str(k)
            yield from _flatten(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _flatten(v)
    elif value is not None and not isinstance(value, bool):
        yield str(value)


def _extract_openapi(rel: str, content: bytes) -> list[_Unit]:
    text = content.decode("utf-8", "replace")
    spec = yaml.safe_load(text) or {}
    lines = text.splitlines()

    def line_of(key: str) -> int:
        for i, line in enumerate(lines, 1):
            if line.strip().startswith(f"{key}:") or line.strip().startswith(f"'{key}':"):
                return i
        return 1

    units = []
    path_items = list((spec.get("paths") or {}).items())
    starts = [line_of(p) for p, _ in path_items]
    for i, (path, item) in enumerate(path_items):
        end = (starts[i + 1] - 1) if i + 1 < len(starts) else len(lines)
        u = _Unit(rel, path, "route", "yaml", starts[i], end)
        methods = [m for m in (item or {}) if m.lower() in
                   ("get", "post", "put", "patch", "delete", "head", "options")]
        u.add("route", path, *[f"{m.upper()} {path}" for m in methods])
        u.add("body", *_flatten(item))
        units.append(u)
    rest = {k: v for k, v in spec.items() if k != "paths"}
    if rest:
        u = _Unit(rel, "#/components", "config", "yaml", 1, len(lines))
        u.add("config", *_flatten(rest))
        units.append(u)
    return units


def _extract_config(rel: str, content: bytes) -> _Unit:
    text = content.decode("utf-8", "replace")
    u = _Unit(rel, "", "config", PurePosixPath(rel).suffix.lstrip(".").replace("yml", "yaml"),
              1, text.count("\n") + 1)
    try:
        data = yaml.safe_load(text)  # JSON is valid YAML
        u.add("config", *_flatten(data))
    except yaml.YAMLError:
        u.add("config", text)
    return u
