import sys
from pathlib import Path

import pytest

HELM_ROOT = Path(__file__).resolve().parents[3]
if str(HELM_ROOT) not in sys.path:
    sys.path.insert(0, str(HELM_ROOT))


@pytest.fixture
def benchmarks_root() -> Path:
    return HELM_ROOT / "benchmarks"
