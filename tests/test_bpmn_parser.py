import pytest

from impact_retrieval.bpmn import BpmnParseError, parse_bpmn

BPMN_HEAD = (b'<?xml version="1.0" encoding="UTF-8"?>'
             b'<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D">')
BPMN_TAIL = b"</bpmn:definitions>"


def wrap(body: bytes) -> bytes:
    return BPMN_HEAD + body + BPMN_TAIL


@pytest.fixture
def old(bpmn_fixture):
    return parse_bpmn(bpmn_fixture("order_old.bpmn"))


def test_elements_are_keyed_and_sorted_by_id(old):
    assert list(old.elements) == sorted(old.elements)
    assert {"C1", "P1", "P2", "MF1", "PROC", "L_CLERK", "L_SYS", "S", "T1", "GW", "T2", "T3", "E",
            "F1", "F2", "F3", "F4", "F5", "F6"} == set(old.elements)


def test_skips_structural_and_di_elements(old):
    # laneSet, event definitions, BPMNDI shapes/edges/plane are not elements of their own
    for skipped in ("LS1", "S_MED", "D1", "PL1", "S_di", "T1_di", "F1_di", "Defs"):
        assert skipped not in old


def test_task_fields(old):
    t1 = old.get("T1")
    assert t1.type == "userTask"
    assert t1.name == "Create order draft"          # newline + double spaces normalized
    assert t1.documentation == "Clerk enters the order lines."
    assert t1.lane == "L_CLERK"
    assert t1.parent == "PROC"
    assert t1.is_flow_node and not t1.is_flow


def test_flow_fields(old):
    f4 = old.get("F4")
    assert (f4.type, f4.source, f4.target, f4.name) == ("sequenceFlow", "GW", "T3", "No stock")
    assert f4.condition == "${stock < qty}"
    assert f4.is_flow
    mf1 = old.get("MF1")
    assert (mf1.type, mf1.source, mf1.target, mf1.parent) == ("messageFlow", "T2", "P2", "C1")


def test_gateway_default_and_event_definition(old):
    assert old.get("GW").default == "F3"
    assert old.get("S").event_definitions == ("messageEventDefinition",)


def test_lanes_and_containers(old):
    assert old.get("L_SYS").is_container
    assert old.get("L_SYS").parent == "PROC"
    assert old.get("T3").lane == "L_SYS"
    assert old.name_of("L_SYS") == "System"
    assert old.name_of("missing") == "missing"
    assert old.name_of(None) == ""


def test_nested_lane_innermost_wins():
    model = parse_bpmn(wrap(
        b'<bpmn:process id="P"><bpmn:laneSet id="LS">'
        b'<bpmn:lane id="OUTER"><bpmn:flowNodeRef>T</bpmn:flowNodeRef>'
        b'<bpmn:childLaneSet id="CLS"><bpmn:lane id="INNER"><bpmn:flowNodeRef>T</bpmn:flowNodeRef>'
        b'</bpmn:lane></bpmn:childLaneSet></bpmn:lane></bpmn:laneSet>'
        b'<bpmn:task id="T" name="x"/></bpmn:process>'))
    assert model.get("T").lane == "INNER"


def test_subprocess_is_parent_of_its_children():
    model = parse_bpmn(wrap(
        b'<bpmn:process id="P"><bpmn:subProcess id="SP" name="Sub">'
        b'<bpmn:task id="T" name="inner"/></bpmn:subProcess></bpmn:process>'))
    assert model.get("SP").parent == "P"
    assert model.get("T").parent == "SP"


def test_text_annotation_text_becomes_name():
    model = parse_bpmn(wrap(
        b'<bpmn:process id="P"><bpmn:textAnnotation id="A"><bpmn:text>Check  stock\n first</bpmn:text>'
        b'</bpmn:textAnnotation></bpmn:process>'))
    assert model.get("A").name == "Check stock first"


def test_path_and_bytes_give_same_model(bpmn_fixture):
    path = bpmn_fixture("order_old.bpmn")
    assert parse_bpmn(path) == parse_bpmn(str(path)) == parse_bpmn(path.read_bytes())


def test_parsing_is_deterministic(bpmn_fixture):
    path = bpmn_fixture("order_new.bpmn")
    assert parse_bpmn(path) == parse_bpmn(path)


@pytest.mark.parametrize("content, message", [
    (b"<bpmn:definitions", "not well-formed"),
    (b'<root id="x"/>', "expected bpmn:definitions"),
    (b'<definitions xmlns="http://example.test/not-bpmn"/>', "expected bpmn:definitions"),
    (wrap(b'<bpmn:process id="P"><bpmn:task id="T"/><bpmn:task id="T"/></bpmn:process>'),
     "duplicate element id"),
])
def test_invalid_input_raises(content, message):
    with pytest.raises(BpmnParseError, match=message):
        parse_bpmn(content)


def test_missing_file_raises(tmp_path):
    with pytest.raises(BpmnParseError, match="cannot read"):
        parse_bpmn(tmp_path / "nope.bpmn")


def test_external_entities_are_not_resolved(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET-VALUE")
    content = (
        b'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY xxe SYSTEM "' + secret.as_uri().encode() + b'">]>'
        b'<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="D">'
        b'<bpmn:process id="P"><bpmn:task id="T"><bpmn:documentation>&xxe;</bpmn:documentation>'
        b'</bpmn:task></bpmn:process></bpmn:definitions>')
    try:
        model = parse_bpmn(content)
    except BpmnParseError:
        return  # refusing the document is also safe
    assert "TOP-SECRET-VALUE" not in model.get("T").documentation
