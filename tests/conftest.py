from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCENARIOS = REPO_ROOT / "data" / "bpmn" / "scenarios"


@pytest.fixture
def bpmn_fixture():
    """Path to a file in tests/fixtures/bpmn/."""
    return lambda name: FIXTURES / "bpmn" / name
