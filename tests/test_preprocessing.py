import pytest

from impact_retrieval.preprocessing import Analyzer, plain_words, split_identifier


@pytest.mark.parametrize("token, expected", [
    ("MatchSupplierInvoice", ["match", "supplier", "invoice"]),
    ("matchSupplierInvoice", ["match", "supplier", "invoice"]),
    ("purchase_order_lines", ["purchase", "order", "lines"]),
    ("sales-order-panel", ["sales", "order", "panel"]),
    ("getHTTPResponse", ["get", "http", "response"]),
    ("HTTPServer", ["http", "server"]),
    ("code2", ["code", "2"]),
    ("ID", ["id"]),
])
def test_split_identifier(token, expected):
    assert split_identifier(token) == expected


def test_analyzer_full_pipeline():
    a = Analyzer({"stemming": "porter", "code_stopwords": ["ctx"]})
    assert a.tokens("func (s Store) MatchSupplierInvoice(ctx Context) matched invoices") == [
        "func", "store", "match", "supplier", "invoic", "context", "match", "invoic"]


def test_stopwords_lists_and_min_length():
    a = Analyzer({"stemming": "none", "code_stopwords": ["func"], "bpmn_stopwords": ["Task"], "min_token_length": 3})
    # "the" English stopword, "func" code, "task" bpmn (case-insensitive), "id" too short, "42" digits
    assert a.tokens("the func Task id 42 approve") == ["approve"]


def test_yaml_booleans_in_stopword_list_are_accepted():
    a = Analyzer({"stemming": "none", "code_stopwords": [True, False, None, "nil"]})
    assert a.tokens("true false nil approve") == ["approve"]


def test_options_can_be_disabled():
    a = Analyzer({"split_identifiers": False, "lowercase": False, "remove_stopwords": False,
                  "stemming": "none", "min_token_length": 1})
    assert a.tokens("MatchInvoice the") == ["MatchInvoice", "the"]


def test_empty_text():
    assert Analyzer().tokens("") == [] and Analyzer().tokens(None) == []


def test_query_and_code_terms_meet():
    a = Analyzer({"stemming": "porter"})
    assert set(a.tokens("Validate invoice match")) & set(a.tokens("MatchSupplierInvoice")) == {"match", "invoic"}


def test_plain_words_is_grep_like():
    # lowercase, split on punctuation, English stopwords ("the", "to") removed, no stemming
    assert plain_words("Confirm the Order-to-Cash orders!") == ["confirm", "order", "cash", "orders"]
    assert plain_words("MatchSupplierInvoice") == ["matchsupplierinvoice"]   # no identifier split
