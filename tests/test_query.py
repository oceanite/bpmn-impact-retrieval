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
