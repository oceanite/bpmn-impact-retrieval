"""Turn a BpmnDiff into a weighted Query.

What goes in (roles; weights come from config ``query.weights``):

* ``name``          name of each changed node: new name, or old name if the node was removed
* ``name_old``      previous name of a renamed node (the code still uses the old words)
* ``documentation`` documentation of a changed node
* ``flow``          name of a changed flow ("Approved", "Order confirmation")
* ``flow_endpoint`` names of the nodes a changed flow connects (old and new endpoints)
* ``lane``          lane of a changed node (both lanes if it moved)
* ``process``       process / sub-process containing the change
* ``task_context``  names of the nodes right before / after a changed activity along sequence
                    flows (predecessor and successor tasks). Unnamed nodes such as a plain
                    gateway are walked through; neighbours that changed themselves are skipped
                    because they are already in the query with a higher weight.

Element ids such as ``SAL-SO-001`` are removed from all text so retrieval cannot
match on trace ids alone. The query is raw text; each retriever analyzes it itself.
"""
from __future__ import annotations

import re
from typing import Mapping

from ..bpmn import BpmnDiff, BpmnElement, BpmnModel, ChangeType
from ..types import Query, QueryPart

DEFAULT_WEIGHTS = {"name": 1.0, "name_old": 1.0, "documentation": 0.5, "flow": 0.3,
                   "flow_endpoint": 0.3, "lane": 0.2, "process": 0.1, "task_context": 0.3}
_ACTIVITY_TYPES = frozenset({"task", "callActivity", "subProcess", "transaction", "adHocSubProcess"})
_ID_LIKE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b")


def strip_ids(text: str) -> str:
    return " ".join(_ID_LIKE.sub(" ", text).split())


def is_activity(el: BpmnElement) -> bool:
    """Tasks of any kind (userTask, serviceTask, ...), call activities and sub-processes."""
    return el.type in _ACTIVITY_TYPES or el.type.endswith("Task")


def neighbour_names(model: BpmnModel, element_id: str, flow_types: frozenset[str] = frozenset({"sequenceFlow"}),
                    skip: frozenset[str] = frozenset()) -> list[str]:
    """Names of the nearest named predecessors and successors of ``element_id``.

    Follows flows of ``flow_types`` one step in each direction; an unnamed node (e.g. a
    gateway without a label) is walked through until a named node is reached. Nodes in
    ``skip`` are neither returned nor walked through. Output order is deterministic.
    """
    incoming: dict[str, list[str]] = {}
    outgoing: dict[str, list[str]] = {}
    for el in model:
        if el.type in flow_types and el.source and el.target:
            outgoing.setdefault(el.source, []).append(el.target)
            incoming.setdefault(el.target, []).append(el.source)

    names: list[str] = []
    for edges in (incoming, outgoing):          # predecessors first, then successors
        seen = {element_id}
        frontier = sorted(edges.get(element_id, ()))
        while frontier:
            nxt: list[str] = []
            for node_id in frontier:
                if node_id in seen or node_id in skip:
                    continue
                seen.add(node_id)
                node = model.get(node_id)
                if node is None or node.is_container:
                    continue
                if node.name:
                    names.append(node.name)
                else:
                    nxt.extend(sorted(edges.get(node_id, ())))
            frontier = nxt
    return names


def build_query(diff: BpmnDiff, old: BpmnModel, new: BpmnModel, cfg: Mapping | None = None) -> Query:
    cfg = dict(cfg or {})
    weights = {**DEFAULT_WEIGHTS, **(cfg.get("weights") or {})}
    drop_ids = cfg.get("drop_ids", True)
    context_flows = frozenset(cfg.get("task_context_flow_types") or ("sequenceFlow",))
    changed = frozenset(c.element_id for c in diff)
    parts: dict[tuple[str, str], QueryPart] = {}   # (role, text) -> part; keeps first-seen order

    def add(text: str | None, role: str, element_id: str) -> None:
        text = strip_ids(text or "") if drop_ids else " ".join((text or "").split())
        w = float(weights.get(role, 0.0))
        if not text or w <= 0:
            return
        key = (role, text.lower())
        if key not in parts:
            parts[key] = QueryPart(text=text, weight=w, role=role, element_id=element_id)

    for change in diff:
        el, prev = change.element, change.old
        model = old if change.change_type is ChangeType.REMOVED else new
        if el.is_container and el.type not in ("lane", "participant", "subProcess"):
            add(el.name, "process", el.id)
            continue

        if el.is_flow:
            add(el.name, "flow", el.id)
            if prev is not None and change.change_type is ChangeType.MODIFIED and prev.name != el.name:
                add(prev.name, "flow", el.id)
            ends = {el.source, el.target}
            if prev is not None:
                ends |= {prev.source, prev.target}
            for end in sorted(e for e in ends if e):
                add(new.name_of(end) if end in new else old.name_of(end), "flow_endpoint", el.id)
            continue

        add(el.name, "lane" if el.type == "lane" else "name", el.id)
        if change.change_type is ChangeType.MODIFIED and prev is not None and prev.name != el.name:
            add(prev.name, "name_old", el.id)
        add(el.documentation, "documentation", el.id)
        for lane in dict.fromkeys(x for x in (el.lane, prev.lane if prev else None) if x):
            add((new if lane in new else old).name_of(lane), "lane", el.id)
        if el.parent:
            add(model.name_of(el.parent), "process", el.id)
        if is_activity(el):
            # removed -> old neighbours, added -> new ones, modified -> both (it may have been rewired)
            sides = (old,) if change.change_type is ChangeType.REMOVED else                 (new,) if change.change_type is ChangeType.ADDED else (old, new)
            for side in sides:
                for name in neighbour_names(side, el.id, context_flows, changed):
                    add(name, "task_context", el.id)

    return Query(tuple(parts.values()))
