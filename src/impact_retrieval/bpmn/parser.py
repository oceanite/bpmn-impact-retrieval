"""Parse BPMN 2.0 XML into a :class:`BpmnModel`.

Only semantic content is kept. Diagram interchange (BPMNDI: shapes, edges,
waypoints) and the derived ``incoming``/``outgoing`` references are ignored, so
moving a shape on the canvas never shows up as a change.

The XML parser refuses DTD loading, entity expansion and network access, because
the web page parses user uploads.
"""
from __future__ import annotations

from pathlib import Path

from lxml import etree

from .model import BpmnElement, BpmnModel

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"

#: Tags that carry an id but are not elements of their own (or are folded into a parent).
_SKIP_TAGS = frozenset({
    "definitions", "incoming", "outgoing", "flowNodeRef", "laneSet", "childLaneSet",
    "extensionElements", "documentation", "text", "conditionExpression",
})
_PARENT_TAGS = frozenset({"process", "subProcess", "transaction", "adHocSubProcess", "collaboration"})


class BpmnParseError(ValueError):
    """The input is not well-formed XML or not a BPMN 2.0 definitions document."""


def _parser() -> etree.XMLParser:
    return etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True,
                           remove_comments=True, remove_pis=True, huge_tree=False)


def _local(tag: object) -> str | None:
    """Local name for BPMN-namespace tags; None for anything else (DI, comments, extensions)."""
    if not isinstance(tag, str):
        return None
    qn = etree.QName(tag)
    return qn.localname if qn.namespace == BPMN_NS else None


def _norm(text: str | None) -> str:
    return " ".join(text.split()) if text else ""


def _text_of(el: etree._Element, child: str) -> str:
    parts = [_norm("".join(c.itertext())) for c in el if _local(c.tag) == child]
    return " ".join(p for p in parts if p)


def parse_bpmn(source: str | Path | bytes) -> BpmnModel:
    """Parse a BPMN file.

    ``source`` is a filesystem path (``str``/``Path``) or the raw file content (``bytes``).
    Raises :class:`BpmnParseError` for malformed XML, a non-BPMN root, or duplicate ids.
    """
    try:
        if isinstance(source, bytes):
            root = etree.fromstring(source, _parser())
        else:
            root = etree.parse(str(source), _parser()).getroot()
    except etree.XMLSyntaxError as exc:
        raise BpmnParseError(f"not well-formed XML: {exc}") from exc
    except OSError as exc:
        raise BpmnParseError(f"cannot read {source!r}: {exc}") from exc

    if _local(root.tag) != "definitions":
        raise BpmnParseError(f"root element is {root.tag!r}, expected bpmn:definitions ({BPMN_NS})")

    # Lane membership. Outer lanes are visited before their child lanes, so the innermost wins.
    lane_of: dict[str, str] = {}
    for lane in root.iter(f"{{{BPMN_NS}}}lane"):
        for ref in lane.iterfind(f"{{{BPMN_NS}}}flowNodeRef"):
            if ref.text and ref.text.strip():
                lane_of[ref.text.strip()] = lane.get("id")

    elements: dict[str, BpmnElement] = {}
    for el in root.iter():
        tag = _local(el.tag)
        el_id = el.get("id")
        if tag is None or not el_id or tag in _SKIP_TAGS or tag.endswith("EventDefinition"):
            continue
        if el_id in elements:
            raise BpmnParseError(f"duplicate element id {el_id!r}")

        name = _norm(el.get("name"))
        if not name and tag == "textAnnotation":
            name = _text_of(el, "text")

        elements[el_id] = BpmnElement(
            id=el_id,
            type=tag,
            name=name,
            documentation=_text_of(el, "documentation"),
            lane=lane_of.get(el_id),
            parent=_parent_id(el),
            source=el.get("sourceRef"),
            target=el.get("targetRef"),
            condition=_text_of(el, "conditionExpression"),
            event_definitions=tuple(sorted(
                t for t in (_local(c.tag) for c in el) if t and t.endswith("EventDefinition"))),
            default=el.get("default"),
            called_element=el.get("calledElement"),
        )

    return BpmnModel(elements=dict(sorted(elements.items())))


def _parent_id(el: etree._Element) -> str | None:
    node = el.getparent()
    while node is not None:
        if _local(node.tag) in _PARENT_TAGS:
            return node.get("id")
        node = node.getparent()
    return None
