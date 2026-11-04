import json

import pytest

from conftest import SCENARIOS
from impact_retrieval.bpmn import ChangeType, diff_files, diff_models, parse_bpmn

A, R, M = ChangeType.ADDED, ChangeType.REMOVED, ChangeType.MODIFIED


def summary(diff):
    """{element_id: (change_type, changed_fields)} for compact assertions."""
    return {c.element_id: (c.change_type, c.changed_fields) for c in diff}


@pytest.fixture
def order_diff(bpmn_fixture):
    return diff_files(bpmn_fixture("order_old.bpmn"), bpmn_fixture("order_new.bpmn"))


def test_fixture_diff_detects_every_change(order_diff):
    assert summary(order_diff) == {
        "F7": (A, ()),
        "T4": (A, ()),
        "F5": (R, ()),
        "MF1": (R, ()),
        "T2": (R, ()),
        "F3": (M, ("target",)),
        "F4": (M, ("condition",)),
        "T1": (M, ("name", "documentation")),
        "T3": (M, ("type", "lane")),
    }


def test_order_is_added_removed_modified_then_id(order_diff):
    assert [c.element_id for c in order_diff] == ["F7", "T4", "F5", "MF1", "T2", "F3", "F4", "T1", "T3"]
    assert [c.element_id for c in order_diff.added] == ["F7", "T4"]
    assert [c.element_id for c in order_diff.removed] == ["F5", "MF1", "T2"]
    assert [c.element_id for c in order_diff.modified] == ["F3", "F4", "T1", "T3"]


def test_field_change_values(order_diff):
    t3 = next(c for c in order_diff.modified if c.element_id == "T3")
    assert [(f.field, f.old, f.new) for f in t3.fields] == [
        ("type", "serviceTask", "userTask"), ("lane", "L_SYS", "L_CLERK")]
    t1 = next(c for c in order_diff.modified if c.element_id == "T1")
    assert t1.fields[0].old == "Create order draft" and t1.fields[0].new == "Create sales order"


def test_added_and_removed_carry_the_right_side(order_diff):
    t4 = next(c for c in order_diff.added if c.element_id == "T4")
    assert t4.old is None and t4.new.name == "Approve order" and t4.element is t4.new
    t2 = next(c for c in order_diff.removed if c.element_id == "T2")
    assert t2.new is None and t2.old.name == "Confirm order" and t2.element is t2.old


def test_identical_models_give_empty_diff(bpmn_fixture):
    diff = diff_files(bpmn_fixture("order_old.bpmn"), bpmn_fixture("order_old.bpmn"))
    assert diff.is_empty and len(diff) == 0


def test_layout_only_change_is_ignored(bpmn_fixture):
    content = bpmn_fixture("order_old.bpmn").read_bytes()
    moved = content.replace(b'x="100" y="100"', b'x="400" y="300"')
    assert moved != content
    assert diff_files(content, moved).is_empty


def test_whitespace_only_name_change_is_ignored():
    def doc(name: bytes) -> bytes:
        return (b'<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D">'
                b'<bpmn:process id="P"><bpmn:task id="T" name="' + name + b'"/></bpmn:process>'
                b'</bpmn:definitions>')
    assert diff_files(doc(b"Post  stock"), doc(b"Post&#10;stock")).is_empty


def test_diff_is_deterministic(bpmn_fixture):
    old, new = parse_bpmn(bpmn_fixture("order_old.bpmn")), parse_bpmn(bpmn_fixture("order_new.bpmn"))
    assert diff_models(old, new) == diff_models(old, new)


def test_reverse_diff_swaps_added_and_removed(order_diff, bpmn_fixture):
    reverse = diff_files(bpmn_fixture("order_new.bpmn"), bpmn_fixture("order_old.bpmn"))
    assert {c.element_id for c in reverse.added} == {c.element_id for c in order_diff.removed}
    assert {c.element_id for c in reverse.removed} == {c.element_id for c in order_diff.added}
    assert {c.element_id for c in reverse.modified} == {c.element_id for c in order_diff.modified}


def test_to_dict_is_json_serializable(order_diff):
    data = json.loads(json.dumps(order_diff.to_dict()))
    first = data["changes"][0]
    assert first["change_type"] == "added" and first["element_id"] == "F7"
    t3 = next(c for c in data["changes"] if c["element_id"] == "T3")
    assert t3["fields"] == [{"field": "type", "old": "serviceTask", "new": "userTask"},
                            {"field": "lane", "old": "L_SYS", "new": "L_CLERK"}]


# --- regression against the committed evaluation scenarios --------------------------------

EXPECTED_SCENARIOS = {
    "S01": {
        "GW-P2P-MATCHED": (M, ("name",)),
        "PUR-INV-002": (M, ("name", "documentation")),
    },
    "S02": {
        "FLOW-INV-004": (R, ()), "FLOW-INV-005": (R, ()), "FLOW-INV-006": (R, ()),
        "GW-INV-APPROVED": (R, ()), "INV-ADJ-003": (R, ()), "INV-END-REJECTED": (R, ()),
        "FLOW-INV-003": (M, ("target",)),
        "INV-ADJ-002": (M, ("documentation",)),
    },
    "S03": {
        "FLOW-O2C-010": (R, ()), "MSG-O2C-002": (R, ()), "SAL-SO-005": (R, ()),
        "FLOW-O2C-008": (M, ("target",)),
        "SAL-DLV-001": (M, ("documentation",)),
    },
    "S04": {
        "AUTH-PWD-005": (M, ("name", "documentation")),
    },
    "S05": {
        "AUTH-USR-003": (M, ("type", "name", "documentation", "lane")),
    },
    "S06": {
        "FLOW-P2P-009A": (A, ()), "PUR-GR-003": (A, ()),
        "FLOW-P2P-009": (M, ("target",)),
    },
}


@pytest.mark.parametrize("scenario_id", sorted(EXPECTED_SCENARIOS))
def test_scenario_diffs(scenario_id):
    folder = SCENARIOS / scenario_id
    diff = diff_files(folder / "old.bpmn", folder / "new.bpmn")
    assert summary(diff) == EXPECTED_SCENARIOS[scenario_id]
