import shutil
from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """A temporary copy of the sample files, safe to modify."""
    target = tmp_path / "samples"
    shutil.copytree(SAMPLES, target)
    return target
