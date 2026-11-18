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


def test_indonesian_stopwords():
    a = Analyzer({"stemming": "none", "indonesian_stopwords": ["dan", "atau", "yang", "proses", "selesai"]})
    assert a.tokens("Master data dan konfigurasi proses selesai") == ["master", "data", "konfigurasi"]


def test_plain_words_is_grep_like():
    # lowercase, split on punctuation, English stopwords ("the", "to") removed, no stemming
    assert plain_words("Confirm the Order-to-Cash orders!") == ["confirm", "order", "cash", "orders"]
    assert plain_words("MatchSupplierInvoice") == ["matchsupplierinvoice"]   # no identifier split


# --- domain synonyms and Indonesian -> English terms (both off by default) ------------------

SYN = {"invoice": ["bill"], "confirm": ["confirmation"], "approve": ["review"]}
ID_EN = {"pengguna": "user", "penjualan": "sales", "pesanan": "order", "stok": "inventory",
         "kata": "pass word"}


def test_synonyms_off_by_default():
    a = Analyzer({"stemming": "none", "synonyms": SYN})          # use_synonyms missing -> off
    assert a.tokens("review confirmation") == ["review", "confirmation"]
    assert a.tokens("bill") == []        # "bill" is a scikit-learn English stopword ...


def test_synonyms_map_variants_to_canonical_on_both_sides():
    a = Analyzer({"stemming": "porter", "use_synonyms": True, "synonyms": SYN})
    assert a.tokens("Send bill") == a.tokens("SendInvoice") == ["send", "invoic"]   # ... unless mapped first
    assert a.tokens("Order confirmation") == ["order", "confirm"]
    assert a.tokens("reviewOrder") == ["approv", "order"]


def test_synonyms_first_canonical_wins_and_handles_yaml_values():
    from impact_retrieval.preprocessing.text import build_synonym_map
    m = build_synonym_map({"invoice": ["Bill"], "payment": ["bill", True]})
    assert m["bill"] == "invoice" and m["payment"] == "payment" and m["true"] == "payment"
    assert build_synonym_map(None) == {}


def test_translation_off_by_default():
    a = Analyzer({"stemming": "none", "id_en_terms": ID_EN})
    assert a.tokens("pesanan penjualan") == ["pesanan", "penjualan"]


def test_translation_indonesian_to_english():
    a = Analyzer({"stemming": "none", "use_translation": True, "id_en_terms": ID_EN,
                  "indonesian_stopwords": ["dan"]})
    assert a.tokens("Akses dan pengguna") == ["akses", "user"]
    assert a.tokens("Pesanan Penjualan; cek stok") == ["order", "sales", "cek", "inventory"]
    assert a.tokens("kata") == ["pass", "word"]                  # multi-word translation


def test_translation_meets_english_code():
    a = Analyzer({"stemming": "porter", "use_translation": True, "id_en_terms": ID_EN})
    assert set(a.tokens("Buat pesanan penjualan")) & set(a.tokens("CreateSalesOrder")) == {"order", "sale"}


def test_translation_then_synonyms_then_stopwords():
    a = Analyzer({"stemming": "none", "use_translation": True, "use_synonyms": True,
                  "id_en_terms": {"tagihan": "bill", "dan": "and"}, "synonyms": {"invoice": ["bill"]}})
    assert a.tokens("tagihan dan") == ["invoice"]                 # "and" is an English stopword


def test_default_config_keeps_baseline_and_has_dictionaries():
    from pathlib import Path
    import yaml
    cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "config" / "default.yaml").read_text("utf-8"))
    pre = cfg["preprocessing"]
    assert pre["use_synonyms"] is False and pre["use_translation"] is False
    for word, english in {"pengguna": "user", "penjualan": "sales", "pembelian": "purchase",
                          "stok": "inventory", "pesanan": "order"}.items():
        assert pre["id_en_terms"][word] == english
    on = Analyzer({**pre, "use_translation": True, "use_synonyms": True})
    assert on.tokens("Akses dan pengguna") == ["access", "user"]
