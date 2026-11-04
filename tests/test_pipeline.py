import json

import pytest

from impact_retrieval.evaluation import split_scenarios
from impact_retrieval.pipeline import ImpactPipeline, main
from impact_retrieval.retrieval import METHODS


@pytest.fixture
def pipe(cfg):
    return ImpactPipeline(cfg=cfg)


@pytest.mark.parametrize("method", METHODS)
def test_end_to_end_on_fixture_repo(pipe, bpmn_fixture, method):
    report = pipe.run(bpmn_fixture("order_old.bpmn"), bpmn_fixture("order_new.bpmn"), method=method, k=5)
    assert report.method == method and len(report.changes) == 9
    assert 0 < len(report.results) <= 5 and report.latency_ms >= 0
    # the removed task "Confirm order" must surface the code that confirms orders
    assert "ConfirmOrder" in {r.document.function for r in report.results[:3]}
    again = pipe.run(bpmn_fixture("order_old.bpmn"), bpmn_fixture("order_new.bpmn"), method=method, k=5)
    assert [r.document.doc_id for r in again.results] == [r.document.doc_id for r in report.results]


def test_bytes_input_same_as_paths(pipe, bpmn_fixture):
    a = pipe.run(bpmn_fixture("order_old.bpmn"), bpmn_fixture("order_new.bpmn"), "bm25")
    b = pipe.run(bpmn_fixture("order_old.bpmn").read_bytes(), bpmn_fixture("order_new.bpmn").read_bytes(), "bm25")
    assert [r.to_dict() for r in a.results] == [r.to_dict() for r in b.results]


def test_report_is_json_serializable(pipe, bpmn_fixture):
    data = json.loads(json.dumps(pipe.run(bpmn_fixture("order_old.bpmn"), bpmn_fixture("order_new.bpmn")).to_dict()))
    assert data["method"] == "bm25" and data["params"]["k1"] == 1.5
    assert {"rank", "score", "file", "function", "evidence"} <= set(data["results"][0])
    assert data["changes"]["changes"] and data["query"]


def test_identical_models_give_no_results(pipe, bpmn_fixture):
    report = pipe.run(bpmn_fixture("order_old.bpmn"), bpmn_fixture("order_old.bpmn"))
    assert report.query.is_empty and report.results == ()


def test_overrides_reach_the_retriever(cfg, bpmn_fixture):
    from impact_retrieval.config import deep_merge
    p = ImpactPipeline(cfg=deep_merge(cfg, {"retrieval": {"bm25": {"k1": 0.9, "b": 0.3}}}))
    assert p.retriever("bm25").k1 == 0.9 and p.retriever("bm25").b == 0.3


def test_errors(pipe, bpmn_fixture):
    with pytest.raises(ValueError):
        pipe.run(bpmn_fixture("order_old.bpmn"), bpmn_fixture("order_new.bpmn"), method="nope")
    with pytest.raises(FileNotFoundError):
        pipe.run_scenario("S99")


DEV = ["S01", "S02", "S03", "S04", "S05", "S06"]
TEST = ["S07", "S08", "S09", "S10"]


def test_real_scenarios_are_listed():
    assert ImpactPipeline().scenarios() == DEV + TEST


def test_dev_and_test_splits():
    pipe = ImpactPipeline()
    assert split_scenarios(pipe) == DEV                    # default_split: dev keeps the test set out
    assert split_scenarios(pipe, "dev") == DEV
    assert split_scenarios(pipe, "test") == TEST
    assert split_scenarios(pipe, "all") == DEV + TEST
    assert not set(split_scenarios(pipe, "dev")) & set(split_scenarios(pipe, "test"))
    with pytest.raises(ValueError, match="unknown split"):
        split_scenarios(pipe, "train")


def test_cli_with_two_files(bpmn_fixture, capsys, monkeypatch, cfg):
    import impact_retrieval.pipeline as mod
    monkeypatch.setattr(mod, "ImpactPipeline", lambda: ImpactPipeline(cfg=cfg))
    assert main([str(bpmn_fixture("order_old.bpmn")), str(bpmn_fixture("order_new.bpmn")), "-k", "3"]) == 0
    out = capsys.readouterr().out
    assert "method=bm25" in out and "ConfirmOrder" in out
