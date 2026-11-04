from conftest import FIXTURE_REPO
from impact_retrieval.code import extract_corpus


def by_id(docs):
    return {d.doc_id: d for d in docs}


def test_documents_and_kinds(fixture_docs):
    got = {(d.path, d.function, d.kind) for d in fixture_docs}
    assert got == {
        ("api/openapi.yaml", "/orders/{id}/confirm", "route"),
        ("api/openapi.yaml", "/deliveries", "route"),
        ("api/openapi.yaml", "#/components", "config"),
        ("backend/internal/shop/adapter/http/handler.go", "Handler", "type"),
        ("backend/internal/shop/adapter/http/handler.go", "Register", "method"),
        ("backend/internal/shop/adapter/http/handler.go", "confirm", "method"),
        ("backend/internal/shop/adapter/http/handler.go", "listDeliveries", "method"),
        ("backend/internal/shop/adapter/postgres/store.go", "Store", "type"),
        ("backend/internal/shop/adapter/postgres/store.go", "ConfirmOrder", "method"),
        ("backend/internal/shop/adapter/postgres/store.go", "CreateDelivery", "method"),
        ("backend/internal/shop/adapter/postgres/store.go", "exec", "method"),
        ("backend/internal/shop/store_test.go", "TestConfirmOrderSetsTimestamp", "test"),
        ("backend/internal/shop/store_test.go", "helperForTests", "function"),
        ("backend/migrations/000001_orders.up.sql", "", "migration"),
        ("frontend/features/shop/order-panel.tsx", "OrderDetail", "type"),
        ("frontend/features/shop/order-panel.tsx", "OrderPanel", "component"),
        ("frontend/features/shop/order-panel.tsx", "formatTotal", "function"),
        ("frontend/package.json", "", "config"),
        ("frontend/tests/order-panel.test.tsx", "", "test"),
    }


def test_excluded_directories_are_skipped(fixture_docs):
    assert not any(d.path.startswith("docs/") for d in fixture_docs)


def test_go_method_fields(fixture_docs):
    d = by_id(fixture_docs)["backend/internal/shop/adapter/postgres/store.go::ConfirmOrder"]
    assert (d.start_line, d.end_line, d.language) == (10, 13, "go")   # func line; doc comment is 8-9
    assert d.fields["name"] == "ConfirmOrder Store"                 # method + receiver type
    assert "marks an approved order as confirmed" in d.fields["comment"]
    assert "transaction" in d.fields["comment"]                     # multi-line doc comment
    assert d.fields["db_table"] == "sales_orders"
    assert "confirmed_at" in d.fields["body"]                       # SQL string content
    assert d.fields["path"] == "backend internal shop adapter postgres store"


def test_sql_tables_from_insert_and_select(fixture_docs):
    d = by_id(fixture_docs)["backend/internal/shop/adapter/postgres/store.go::CreateDelivery"]
    assert d.fields["db_table"].split() == ["deliveries", "sales_orders"]
    assert "deliveries need a confirmed order" in d.fields["comment"]   # comment inside body


def test_go_routes_attach_to_handler_and_register(fixture_docs):
    docs = by_id(fixture_docs)
    assert docs["backend/internal/shop/adapter/http/handler.go::confirm"].fields["route"] == "POST /orders/{id}/confirm"
    assert docs["backend/internal/shop/adapter/http/handler.go::listDeliveries"].fields["route"] == "GET /deliveries"
    assert docs["backend/internal/shop/adapter/http/handler.go::Register"].fields["route"] == \
        "POST /orders/{id}/confirm GET /deliveries"


def test_go_test_name_goes_to_test_field(fixture_docs):
    d = by_id(fixture_docs)["backend/internal/shop/store_test.go::TestConfirmOrderSetsTimestamp"]
    assert d.fields["test"] == "TestConfirmOrderSetsTimestamp" and "name" not in d.fields


def test_tsx_component(fixture_docs):
    d = by_id(fixture_docs)["frontend/features/shop/order-panel.tsx::OrderPanel"]
    assert d.language == "typescript"
    assert d.fields["route"] == "/orders/{}/confirm"                # template literal normalized
    assert "Confirm order" in d.fields["body"]                      # JSX text
    assert "Shows one order" in d.fields["comment"]


def test_ts_test_file_lists_test_titles(fixture_docs):
    d = by_id(fixture_docs)["frontend/tests/order-panel.test.tsx"]
    assert d.fields["test"] == "order panel shows the confirm button"


def test_openapi_and_migration_and_config(fixture_docs):
    docs = by_id(fixture_docs)
    route = docs["api/openapi.yaml::/orders/{id}/confirm"]
    assert route.fields["route"] == "/orders/{id}/confirm POST /orders/{id}/confirm"
    assert "Confirm an approved order" in route.fields["body"]
    assert route.start_line == 4 and route.end_line == 7
    mig = docs["backend/migrations/000001_orders.up.sql"]
    assert mig.fields["db_table"].split() == ["sales_orders", "deliveries"]
    assert mig.fields["comment"] == "sales orders and deliveries"
    assert "vitest" in docs["frontend/package.json"].fields["config"]


def test_extraction_is_deterministic_and_ids_unique(cfg):
    a = extract_corpus(FIXTURE_REPO, cfg["code_extraction"])
    b = extract_corpus(FIXTURE_REPO, cfg["code_extraction"])
    assert a == b
    assert len({d.doc_id for d in a}) == len(a)
    assert [d.path for d in a] == sorted(d.path for d in a)


def test_missing_repo_raises(cfg, tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        extract_corpus(tmp_path / "nope", cfg["code_extraction"])
