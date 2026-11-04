"""Semantic model of a BPMN 2.0 file: elements keyed by id, layout (DI) excluded."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Iterator

FLOW_TYPES = frozenset({"sequenceFlow", "messageFlow", "association", "dataInputAssociation",
                        "dataOutputAssociation"})
CONTAINER_TYPES = frozenset({"definitions", "collaboration", "process", "subProcess", "transaction",
                             "adHocSubProcess", "laneSet", "lane", "participant"})


@dataclass(frozen=True)
class BpmnElement:
    """One BPMN element with an id. Only semantic attributes; never diagram geometry."""

    id: str
    type: str                          # BPMN local tag name, e.g. "userTask", "sequenceFlow"
    name: str = ""                     # whitespace-normalized
    documentation: str = ""            # all <documentation> children, whitespace-normalized
    lane: str | None = None            # id of the innermost lane holding this node
    parent: str | None = None          # id of the enclosing process / subProcess / collaboration
    source: str | None = None          # flows only
    target: str | None = None          # flows only
    condition: str = ""                # sequenceFlow conditionExpression text
    event_definitions: tuple[str, ...] = ()  # e.g. ("timerEventDefinition",)
    default: str | None = None         # gateway / activity default flow id
    called_element: str | None = None  # callActivity

    @property
    def is_flow(self) -> bool:
        return self.type in FLOW_TYPES

    @property
    def is_container(self) -> bool:
        return self.type in CONTAINER_TYPES

    @property
    def is_flow_node(self) -> bool:
        return not self.is_flow and not self.is_container

    def to_dict(self) -> dict:
        d = {f.name: getattr(self, f.name) for f in fields(self)}
        d["event_definitions"] = list(self.event_definitions)
        return d


#: Fields compared by the diff, in report order. ``id`` is the match key, so it is not listed.
COMPARED_FIELDS: tuple[str, ...] = tuple(f.name for f in fields(BpmnElement) if f.name != "id")


@dataclass(frozen=True)
class BpmnModel:
    """All id-bearing semantic elements of one BPMN file, sorted by id."""

    elements: dict[str, BpmnElement]

    def __len__(self) -> int:
        return len(self.elements)

    def __iter__(self) -> Iterator[BpmnElement]:
        return iter(self.elements.values())

    def __contains__(self, element_id: object) -> bool:
        return element_id in self.elements

    def get(self, element_id: str) -> BpmnElement | None:
        return self.elements.get(element_id)

    def name_of(self, element_id: str | None) -> str:
        """Display name of an element (falls back to its id); used for lane/flow context."""
        if element_id is None:
            return ""
        el = self.elements.get(element_id)
        return (el.name or el.id) if el else element_id
