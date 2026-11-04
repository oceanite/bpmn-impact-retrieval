from pathlib import Path

import pytest

from impact_retrieval.config import load_config

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCENARIOS = REPO_ROOT / "data" / "bpmn" / "scenarios"
FIXTURE_REPO = FIXTURES / "code"


@pytest.fixture
def bpmn_fixture():
    """Path to a file in tests/fixtures/bpmn/."""
    return lambda name: FIXTURES / "bpmn" / name


@pytest.fixture
def cfg():
    """The real default config, pointed at the small fixture repo."""
    return load_config(overrides={"paths": {"target_repo": str(FIXTURE_REPO)}})


@pytest.fixture
def fixture_docs(cfg):
    from impact_retrieval.code import extract_corpus
    return extract_corpus(FIXTURE_REPO, cfg["code_extraction"])
