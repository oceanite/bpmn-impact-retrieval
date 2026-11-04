"""Diff two BPMN models by element id."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .model import COMPARED_FIELDS, BpmnElement, BpmnModel
from .parser import parse_bpmn


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


_ORDER = {ChangeType.ADDED: 0, ChangeType.REMOVED: 1, ChangeType.MODIFIED: 2}


@dataclass(frozen=True)
class FieldChange:
    field: str
    old: object
    new: object


@dataclass(frozen=True)
class ElementChange:
    change_type: ChangeType
    old: BpmnElement | None
    new: BpmnElement | None
    fields: tuple[FieldChange, ...] = ()   # MODIFIED only

    @property
    def element(self) -> BpmnElement:
        """The current version of the element (the old one if it was removed)."""
        return self.new if self.new is not None else self.old  # type: ignore[return-value]

    @property
    def element_id(self) -> str:
        return self.element.id

    @property
    def changed_fields(self) -> tuple[str, ...]:
        return tuple(f.field for f in self.fields)

    def to_dict(self) -> dict:
        return {
            "change_type": self.change_type.value,
            "element_id": self.element_id,
            "element_type": self.element.type,
            "old": self.old.to_dict() if self.old else None,
            "new": self.new.to_dict() if self.new else None,
            "fields": [{"field": f.field, "old": _plain(f.old), "new": _plain(f.new)}
                       for f in self.fields],
        }


@dataclass(frozen=True)
class BpmnDiff:
    """Ordered changes: added, then removed, then modified; each group sorted by element id."""

    changes: tuple[ElementChange, ...]

    def __len__(self) -> int:
        return len(self.changes)

    def __iter__(self):
        return iter(self.changes)

    @property
    def is_empty(self) -> bool:
        return not self.changes

    def of_type(self, change_type: ChangeType) -> tuple[ElementChange, ...]:
        return tuple(c for c in self.changes if c.change_type is change_type)

    @property
    def added(self) -> tuple[ElementChange, ...]:
        return self.of_type(ChangeType.ADDED)

    @property
    def removed(self) -> tuple[ElementChange, ...]:
        return self.of_type(ChangeType.REMOVED)

    @property
    def modified(self) -> tuple[ElementChange, ...]:
        return self.of_type(ChangeType.MODIFIED)

    def to_dict(self) -> dict:
        return {"changes": [c.to_dict() for c in self.changes]}


def diff_models(old: BpmnModel, new: BpmnModel) -> BpmnDiff:
    """Compare two models. Elements are matched by id; same input always gives the same order."""
    changes: list[ElementChange] = []
    for el_id in new.elements.keys() - old.elements.keys():
        changes.append(ElementChange(ChangeType.ADDED, None, new.elements[el_id]))
    for el_id in old.elements.keys() - new.elements.keys():
        changes.append(ElementChange(ChangeType.REMOVED, old.elements[el_id], None))
    for el_id in old.elements.keys() & new.elements.keys():
        a, b = old.elements[el_id], new.elements[el_id]
        diffs = tuple(FieldChange(f, getattr(a, f), getattr(b, f))
                      for f in COMPARED_FIELDS if getattr(a, f) != getattr(b, f))
        if diffs:
            changes.append(ElementChange(ChangeType.MODIFIED, a, b, diffs))
    changes.sort(key=lambda c: (_ORDER[c.change_type], c.element_id))
    return BpmnDiff(tuple(changes))


def diff_files(old: str | Path | bytes, new: str | Path | bytes) -> BpmnDiff:
    """Parse and diff two BPMN sources (paths or raw bytes)."""
    return diff_models(parse_bpmn(old), parse_bpmn(new))


def _plain(value: object) -> object:
    return list(value) if isinstance(value, tuple) else value
