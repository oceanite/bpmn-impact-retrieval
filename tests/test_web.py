"""Website smoke tests (run against the real Simple-ERP clone; skipped if it is missing)."""
import pytest

from conftest import FIXTURES, REPO_ROOT

pytest.importorskip("httpx2")
if not (REPO_ROOT / "data" / "target_repo" / "backend").is_dir():
    pytest.skip("Simple-ERP clone not present in data/target_repo", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

from web.app import app  # noqa: E402

client = TestClient(app)
OLD = (FIXTURES / "bpmn" / "order_old.bpmn").read_bytes()
NEW = (FIXTURES / "bpmn" / "order_new.bpmn").read_bytes()


def test_mapping_form_lists_scenarios():
    r = client.get("/")
    assert r.status_code == 200 and "S01" in r.text and "S06" in r.text


def test_mapping_with_scenario():
    r = client.post("/", data={"scenario": "S03", "method": "bm25"})
    assert r.status_code == 200 and "Detected changes" in r.text and "CreateDelivery" in r.text


def test_mapping_with_upload():
    r = client.post("/", data={"method": "keyword"},
                    files={"old_file": ("old.bpmn", OLD), "new_file": ("new.bpmn", NEW)})
    assert r.status_code == 200 and "Ranked impact" in r.text


def test_bad_upload_shows_error():
    r = client.post("/", data={"method": "bm25"},
                    files={"old_file": ("old.bpmn", b"<broken"), "new_file": ("new.bpmn", NEW)})
    assert r.status_code == 200 and "not well-formed" in r.text


def test_nothing_chosen_shows_error():
    r = client.post("/", data={"method": "bm25"})
    assert "Choose a scenario" in r.text


def test_settings_are_applied():
    r = client.post("/", data={"scenario": "S01", "method": "bm25", "k1": "0.9", "b": "0.4", "w_name": "5"})
    assert r.status_code == 200 and 'value="0.9"' in r.text and 'value="5.0"' in r.text


@pytest.mark.parametrize("level", ["file", "function"])
def test_evaluation_page(level):
    r = client.get(f"/evaluation?k=5&level={level}")
    assert r.status_code == 200 and "bm25" in r.text and "tfidf" in r.text and "S06" in r.text


def test_mapping_with_source_code_zip():
    from test_archive import zip_fixture_repo
    r = client.post("/", data={"method": "bm25"},
                    files={"old_file": ("old.bpmn", OLD), "new_file": ("new.bpmn", NEW),
                           "code_zip": ("shop.zip", zip_fixture_repo())})
    assert r.status_code == 200 and "shop.zip" in r.text and "ConfirmOrder" in r.text


def test_scenario_against_uploaded_zip():
    from test_archive import zip_fixture_repo
    r = client.post("/", data={"scenario": "S03", "method": "bm25"},
                    files={"code_zip": ("shop.zip", zip_fixture_repo())})
    assert r.status_code == 200 and "shop.zip" in r.text


def test_bad_zip_shows_error():
    r = client.post("/", data={"scenario": "S01", "method": "bm25"},
                    files={"code_zip": ("code.zip", b"not a zip")})
    assert r.status_code == 200 and "not a valid ZIP" in r.text


def test_api():
    r = client.get("/api/scenarios/S01?k=3")
    assert r.status_code == 200 and len(r.json()["results"]) == 3
    assert client.get("/api/scenarios/S99").status_code == 404
