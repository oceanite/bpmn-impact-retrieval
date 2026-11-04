import pytest

from impact_retrieval.evaluation import GroundTruthRow, evaluate_ranking, load_ground_truth

# Corpus: 4 files, 6 documents.
UNIVERSE = [("a.go", "F1"), ("a.go", "F2"), ("b.go", "G"), ("c.go", "H"), ("c.go", "H2"), ("d.go", "X")]
TRUTH = [GroundTruthRow("S", "a.go", "F1"), GroundTruthRow("S", "c.go", "")]   # c.go: whole file
RANKED = [("a.go", "F1"), ("b.go", "G"), ("a.go", "F2"), ("c.go", "H")]


def test_file_level_hand_computed():
    ev = evaluate_ranking(RANKED, TRUTH, UNIVERSE, [1, 3], "file")
    # file ranking: a, b, c   relevant: a, c   negatives: b, d
    assert ev.mrr == 1.0 and ev.first_relevant_rank == 1
    k1, k3 = ev.at(1), ev.at(3)
    assert (k1.precision, k1.recall, k1.fpr) == (1.0, 0.5, 0.0)
    assert k1.tp == ("a.go",) and k1.fn == ("c.go",)
    assert k3.precision == pytest.approx(2 / 3) and k3.recall == 1.0
    assert k3.fpr == pytest.approx(1 / 2) and k3.fp == ("b.go",)
    assert k3.f1 == pytest.approx(0.8)


def test_function_level_hand_computed():
    ev = evaluate_ranking(RANKED, TRUTH, UNIVERSE, [2, 4], "function")
    # relevant docs: a::F1, c::H, c::H2 (file row) -> 3 negatives
    k2, k4 = ev.at(2), ev.at(4)
    assert (k2.precision, k2.recall) == (0.5, 0.5)
    assert k2.tp == ("a.go::F1",) and k2.fp == ("b.go::G",) and k2.fn == ("c.go",)
    assert k2.fpr == pytest.approx(1 / 3)
    assert (k4.precision, k4.recall) == (0.5, 1.0) and k4.fn == ()
    assert k4.fpr == pytest.approx(2 / 3)


def test_mrr_uses_first_relevant_rank():
    ev = evaluate_ranking([("b.go", "G"), ("d.go", "X"), ("c.go", "H")], TRUTH, UNIVERSE, [3], "file")
    assert ev.first_relevant_rank == 3 and ev.mrr == pytest.approx(1 / 3)


def test_nothing_relevant_retrieved():
    ev = evaluate_ranking([("b.go", "G")], TRUTH, UNIVERSE, [1, 5], "file")
    assert ev.mrr == 0.0 and ev.first_relevant_rank is None
    assert ev.at(5).precision == 0.0 and ev.at(5).recall == 0.0 and ev.at(5).f1 == 0.0


def test_precision_divides_by_k_even_if_fewer_results():
    ev = evaluate_ranking([("a.go", "F1")], TRUTH, UNIVERSE, [5], "file")
    assert ev.at(5).precision == pytest.approx(1 / 5)


def test_unknown_level():
    with pytest.raises(ValueError):
        evaluate_ranking(RANKED, TRUTH, UNIVERSE, [1], "module")


def test_load_ground_truth(tmp_path):
    p = tmp_path / "gt.csv"
    p.write_text("scenario_id,file_path,function\nS1,a.go,F1\nS1, c.go ,\nS2,b.go,G\n", encoding="utf-8")
    gt = load_ground_truth(p)
    assert gt["S1"] == [GroundTruthRow("S1", "a.go", "F1"), GroundTruthRow("S1", "c.go", "")]
    assert list(gt) == ["S1", "S2"]


def test_real_ground_truth_file_loads():
    from conftest import REPO_ROOT
    gt = load_ground_truth(REPO_ROOT / "data" / "ground_truth" / "ground_truth.csv")
    assert set(gt) == {f"S{i:02d}" for i in range(1, 11)}
    assert sum(len(v) for v in gt.values()) == 69
