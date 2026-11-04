import io
import stat
import zipfile

import pytest

from conftest import FIXTURE_REPO
from impact_retrieval.code import ArchiveError, extract_corpus, safe_extract_zip
from impact_retrieval.pipeline import ImpactPipeline, corpus_fingerprint, documents_from_zip


def make_zip(entries: dict[str, bytes], symlink: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "/etc/passwd")
    return buf.getvalue()


def zip_fixture_repo(top: str = "shop-main/") -> bytes:
    """The fixture repo zipped like GitHub's 'Download ZIP' (one top-level folder)."""
    return make_zip({top + p.relative_to(FIXTURE_REPO).as_posix(): p.read_bytes()
                     for p in sorted(FIXTURE_REPO.rglob("*")) if p.is_file()})


def test_extracts_and_unwraps_single_top_folder(tmp_path):
    root = safe_extract_zip(zip_fixture_repo(), tmp_path)
    assert root == (tmp_path / "shop-main").resolve()
    assert (root / "backend/internal/shop/adapter/postgres/store.go").is_file()


def test_no_unwrap_when_several_top_entries(tmp_path):
    root = safe_extract_zip(make_zip({"a/x.go": b"package a", "b.go": b"package b"}), tmp_path)
    assert root == tmp_path.resolve()


@pytest.mark.parametrize("name", [
    "../evil.go", "a/../../evil.go", "/etc/evil.go", "C:/evil.go", "C:evil.go",
    "..\\evil.go", "\\\\server\\share\\evil.go",
])
def test_rejects_paths_that_escape(tmp_path, name):
    with pytest.raises(ArchiveError, match="unsafe path"):
        safe_extract_zip(make_zip({name: b"x"}), tmp_path / "out")
    assert not (tmp_path / "evil.go").exists()


def test_rejects_symlinks(tmp_path):
    with pytest.raises(ArchiveError, match="symbolic links"):
        safe_extract_zip(make_zip({"a.go": b"package a"}, symlink="link"), tmp_path)


def test_rejects_too_many_files(tmp_path):
    with pytest.raises(ArchiveError, match="limit is 2"):
        safe_extract_zip(make_zip({f"f{i}.go": b"x" for i in range(3)}), tmp_path, max_files=2)


def test_rejects_zip_bomb(tmp_path):
    bomb = make_zip({"big.go": b"0" * 2_000_000})       # compresses to a few KB
    assert len(bomb) < 50_000
    with pytest.raises(ArchiveError, match="more than"):
        safe_extract_zip(bomb, tmp_path, max_total_bytes=1_000_000)


@pytest.mark.parametrize("data, message", [(b"not a zip", "not a valid ZIP"), (make_zip({}), "empty")])
def test_rejects_bad_archives(tmp_path, data, message):
    with pytest.raises(ArchiveError, match=message):
        safe_extract_zip(data, tmp_path)


def test_documents_from_zip_match_extracting_the_folder(cfg):
    from_zip = documents_from_zip(zip_fixture_repo(), cfg)
    from_dir = extract_corpus(FIXTURE_REPO, cfg["code_extraction"])
    assert from_zip == from_dir                      # same paths: top folder is unwrapped


def test_zip_without_supported_files(cfg):
    with pytest.raises(ArchiveError, match="no supported source files"):
        documents_from_zip(make_zip({"README.txt": b"hello", "main.rb": b"puts 1"}), cfg)


def test_zip_size_limit_from_config(cfg):
    small = {**cfg, "upload": {**cfg["upload"], "max_zip_mb": 0}}
    with pytest.raises(ArchiveError, match="larger than 0 MB"):
        documents_from_zip(zip_fixture_repo(), small)


def test_pipeline_from_zip_end_to_end(cfg, bpmn_fixture):
    pipe = ImpactPipeline.from_zip(zip_fixture_repo(), cfg, label="shop.zip")
    report = pipe.run(bpmn_fixture("order_old.bpmn"), bpmn_fixture("order_new.bpmn"), "bm25", k=5)
    assert report.params["corpus"] == "shop.zip" and report.params["documents"] == len(pipe.documents)
    assert "ConfirmOrder" in {r.document.function for r in report.results[:3]}


def test_different_codebases_never_share_an_index(cfg):
    a = ImpactPipeline.from_zip(zip_fixture_repo(), cfg)
    b = ImpactPipeline.from_zip(make_zip({"x/pay.go": b"package x\nfunc PayInvoice() {}\n"}), cfg)
    assert corpus_fingerprint(a.documents) != corpus_fingerprint(b.documents)
    assert a.retriever("bm25") is not b.retriever("bm25")
    assert a.retriever("bm25") is ImpactPipeline.from_zip(zip_fixture_repo(), cfg).retriever("bm25")  # cached
