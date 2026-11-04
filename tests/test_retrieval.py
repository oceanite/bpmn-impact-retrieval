import pytest

from impact_retrieval.preprocessing import Analyzer
from impact_retrieval.retrieval import (BM25Retriever, KeywordRetriever, Retriever, TfidfRetriever,
                                        make_retriever)
from impact_retrieval.types import CodeDocument, Query, QueryPart


def doc(doc_id, **fields):
    return CodeDocument(doc_id=doc_id, path=f"{doc_id}.go", function=doc_id, kind="function",
                        language="go", start_line=1, end_line=1, fields=fields)


def q(text, weight=1.0):
    return Query((QueryPart(text, weight, "name", "X"),))


ANALYZER = Analyzer({"stemming": "porter"})
DOCS = [
    doc("confirm_order", name="ConfirmOrder", body="UPDATE sales_orders SET confirmed_at"),
    doc("create_delivery", name="CreateDelivery", body="confirm order before delivery"),
    doc("list_users", name="ListUsers", body="users email invite"),
]


def all_methods():
    return [BM25Retriever(ANALYZER), KeywordRetriever(), TfidfRetriever(ANALYZER)]


@pytest.mark.parametrize("retriever", all_methods(), ids=lambda r: r.name)
def test_common_interface(retriever):
    assert isinstance(retriever, Retriever)
    results = retriever.index(DOCS).search(q("confirm order"), k=10)
    assert [r.rank for r in results] == list(range(1, len(results) + 1))
    assert [r.score for r in results] == sorted((r.score for r in results), reverse=True)
    assert results[0].document.doc_id in {"confirm_order", "create_delivery"}
    assert "list_users" not in {r.document.doc_id for r in results}
    assert all(r.evidence for r in results)
    assert retriever.search(q("confirm order"), k=10) == results      # deterministic
    assert len(retriever.search(q("confirm order"), k=1)) == 1           # k cut-off
    assert retriever.search(q("zzzunknown"), k=10) == []


def test_bm25_field_weights_change_the_ranking():
    docs = [doc("x", name="Approve", body="invoice"), doc("y", name="Invoice", body="approve")]
    by_name = BM25Retriever(ANALYZER, field_weights={"name": 3, "body": 1}).index(docs)
    by_body = BM25Retriever(ANALYZER, field_weights={"name": 1, "body": 3}).index(docs)
    assert by_name.search(q("invoice"))[0].document.doc_id == "y"
    assert by_body.search(q("invoice"))[0].document.doc_id == "x"


def test_bm25_zero_weight_field_is_ignored():
    r = BM25Retriever(ANALYZER, field_weights={"body": 0}).index([doc("x", name="Other", body="invoice")])
    assert r.search(q("invoice")) == []


def test_bm25_evidence_adds_up_to_score():
    r = BM25Retriever(ANALYZER, field_weights={"name": 3}).index(DOCS)
    for res in r.search(q("confirm order delivery")):
        assert sum(e.contribution for e in res.evidence) == pytest.approx(res.score)
    top = r.search(q("confirm"))[0]
    assert {(e.term, e.field) for e in top.evidence} <= {("confirm", "name"), ("confirm", "body")}


def test_bm25_query_weights_matter():
    r = BM25Retriever(ANALYZER).index(DOCS)
    heavy = Query((QueryPart("delivery", 5.0, "name", "A"), QueryPart("confirm", 0.1, "name", "B")))
    assert r.search(heavy)[0].document.doc_id == "create_delivery"


def test_ties_are_broken_by_doc_id():
    docs = [doc("b", name="Invoice"), doc("a", name="Invoice")]
    for retriever in all_methods():
        assert [x.document.doc_id for x in retriever.index(docs).search(q("invoice"))] == ["a", "b"]


def test_bm25_rejects_bad_parameters():
    with pytest.raises(ValueError):
        BM25Retriever(ANALYZER, b=1.5)
    with pytest.raises(ValueError):
        BM25Retriever(ANALYZER, k1=-1)


def test_keyword_is_substring_without_stemming():
    r = KeywordRetriever().index([doc("x", body="purchase_order_lines"), doc("y", body="ordering")])
    assert [x.document.doc_id for x in r.search(q("order"))] == ["x", "y"]   # both contain "order"
    assert r.search(q("orders")) == []                                         # no stemming


def test_keyword_ranks_by_distinct_words_first():
    r = KeywordRetriever().index([doc("many", body="order order order order"), doc("both", body="order invoice")])
    assert r.search(q("order invoice"))[0].document.doc_id == "both"


def test_make_retriever_from_config(cfg):
    assert isinstance(make_retriever("bm25", cfg), BM25Retriever)
    assert make_retriever("bm25", cfg).k1 == cfg["retrieval"]["bm25"]["k1"]
    assert isinstance(make_retriever("keyword", cfg), KeywordRetriever)
    assert isinstance(make_retriever("tfidf", cfg), TfidfRetriever)
    with pytest.raises(ValueError):
        make_retriever("nope", cfg)
