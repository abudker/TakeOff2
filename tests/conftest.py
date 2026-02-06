"""Shared test fixtures and configuration."""
import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def evals_dir(project_root):
    """Return the evals directory."""
    return project_root / "evals"
