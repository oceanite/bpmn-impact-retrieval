import pytest

from impact_retrieval.bpmn import diff_models, parse_bpmn
from impact_retrieval.query import build_query, strip_ids


@pytest.fixture
def models(bpmn_fixture):
    old, new = parse_bpmn(bpmn_fixture("order_old.bpmn")), parse_bpmn(bpmn_fixture("order_new.bpmn"))
    return old, new, diff_models(old, new)


def parts(query):
    return {(p.text, p.role): p for p in query.parts}


def test_roles_from_fixture_diff(models):
    old, new, diff = models
    got = parts(build_query(diff, old, new))
    assert ("Confirm order", "name") in got                 # removed task -> its (old) name
    assert ("Approve order", "name") in got                 # added task
    assert ("Create sales order", "name") in got            # renamed: new name ...
    assert ("Create order draft", "name_old") in got        # ... and old name
    assert ("Clerk enters customer and order lines.", "documentation") in got
    assert ("Reserve stock", "name") in got                 # retyped + moved task
    assert ("Clerk", "lane") in got and ("System", "lane") in got   # both lanes of the move
    assert ("Order confirmation", "flow") in got            # removed message flow
    assert ("Customer", "flow_endpoint") in got
    assert ("Stock available?", "flow_endpoint") in got     # source of retargeted F3
    assert ("Order handling", "process") in got


def test_weights_come_from_config(models):
    old, new, diff = models
    query = build_query(diff, old, new, {"weights": {"name": 2.0, "lane": 0.0}})
    assert all(p.weight == 2.0 for p in query.parts if p.role == "name")
    assert not any(p.role == "lane" for p in query.parts)   # weight 0 -> dropped


def test_no_duplicate_parts(models):
    old, new, diff = models
    q = build_query(diff, old, new)
    keys = [(p.role, p.text.lower()) for p in q.parts]
    assert len(keys) == len(set(keys))


def test_empty_diff_gives_empty_query(bpmn_fixture):
    m = parse_bpmn(bpmn_fixture("order_old.bpmn"))
    q = build_query(diff_models(m, m), m, m)
    assert q.is_empty and q.parts == ()


def test_deterministic(models):
    old, new, diff = models
    assert build_query(diff, old, new) == build_query(diff, old, new)


@pytest.mark.parametrize("text, expected", [
    ("Audit SAL-SO-001; commit", "Audit ; commit"),
    ("Review PUR-PR-003 now", "Review now"),
    ("Order-to-Cash Level 2", "Order-to-Cash Level 2"),     # normal hyphenated words are kept
])
def test_strip_ids(text, expected):
    assert strip_ids(text) == expected


def test_ids_can_be_kept(models):
    old, new, diff = models
    assert build_query(diff, old, new, {"drop_ids": False}).parts  # still builds


# --- task context (predecessor / successor tasks of a changed task) -------------------------

def test_task_context_from_fixture(models):
    old, new, diff = models
    ctx = {p.text for p in build_query(diff, old, new).parts if p.role == "task_context"}
    # T4 "Approve order" (added): between gateway and end event in the new model
    # T2 "Confirm order" (removed): same neighbours in the old model; T1 renamed: start event + gateway
    assert ctx == {"Stock available?", "Done", "Order received"}


def test_task_context_skips_changed_neighbours(models):
    old, new, diff = models
    ctx = {p.text for p in build_query(diff, old, new).parts if p.role == "task_context"}
    # T1 and T3 changed themselves, so they are not context of each other or of T4
    assert not ctx & {"Create sales order", "Reserve stock", "Approve order", "Confirm order"}


def test_task_context_weight_from_config(models):
    old, new, diff = models
    q = build_query(diff, old, new, {"weights": {"task_context": 0.7}})
    assert {p.weight for p in q.parts if p.role == "task_context"} == {0.7}
    off = build_query(diff, old, new, {"weights": {"task_context": 0.0}})
    assert not any(p.role == "task_context" for p in off.parts)


def _chain(*nodes, flows):
    from impact_retrieval.bpmn import BpmnElement, BpmnModel
    els = [BpmnElement(id=i, type=t, name=n, parent="P") for i, t, n in nodes]
    els += [BpmnElement(id=f"F{k}", type="sequenceFlow", source=s, target=t, parent="P")
            for k, (s, t) in enumerate(flows)]
    els.append(BpmnElement(id="P", type="process", name="Sales"))
    return BpmnModel({e.id: e for e in els})


def test_task_context_walks_through_unnamed_nodes_and_drops_ids():
    nodes = [("A", "userTask", "SAL-SO-001 Check credit"), ("G", "exclusiveGateway", ""),
             ("B", "serviceTask", "Ship goods"), ("C", "userTask", "Send invoice")]
    old = _chain(*nodes, flows=[("A", "G"), ("G", "C")])
    new = _chain(*nodes, ("X", "userTask", "Pack items"), flows=[("A", "G"), ("G", "X"), ("X", "C")])
    q = build_query(diff_models(old, new), old, new)
    ctx = [p for p in q.parts if p.role == "task_context"]
    # X's predecessor is the unnamed gateway G -> walked through to A; trace id removed
    assert [p.text for p in ctx] == ["Check credit", "Send invoice"]
    assert all(p.element_id == "X" for p in ctx)
    kept = build_query(diff_models(old, new), old, new, {"drop_ids": False})
    assert "SAL-SO-001 Check credit" in {p.text for p in kept.parts if p.role == "task_context"}


def test_task_context_ignores_message_flows_by_default():
    nodes = [("A", "userTask", "Check credit"), ("B", "userTask", "Notify customer")]
    from impact_retrieval.bpmn import BpmnElement, BpmnModel
    old = _chain(*nodes, flows=[])
    els = dict(old.elements)
    els["M"] = BpmnElement(id="M", type="messageFlow", source="B", target="A2")
    els["A2"] = BpmnElement(id="A2", type="userTask", name="Approve credit", parent="P")
    new = BpmnModel(els)
    q = build_query(diff_models(old, new), old, new)
    assert not any(p.role == "task_context" for p in q.parts)
    q2 = build_query(diff_models(old, new), old, new, {"task_context_flow_types": ["sequenceFlow", "messageFlow"]})
    assert "Notify customer" in {p.text for p in q2.parts if p.role == "task_context"}
