"""Quality test fixtures and configuration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.quality.models import GoldenFixture

GOLDEN_DIR = Path(__file__).parent / "golden_fixtures"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --live-api option for tests that hit real AI APIs."""
    parser.addoption(
        "--live-api",
        action="store_true",
        default=False,
        help="Run tests that require real AI API calls",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "live_api: tests that hit real AI APIs (deselect by default)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip live_api tests unless --live-api is passed."""
    if config.getoption("--live-api"):
        return
    skip_live = pytest.mark.skip(reason="need --live-api option to run")
    for item in items:
        if "live_api" in item.keywords:
            item.add_marker(skip_live)


def _load_golden(name: str) -> GoldenFixture:
    """Load and validate a golden fixture by name."""
    path = GOLDEN_DIR / f"{name}.json"
    if not path.exists():
        pytest.skip(f"Golden fixture not found: {path}. Run record_fixtures.py first.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return GoldenFixture.model_validate(raw)


@pytest.fixture
def golden_bank() -> GoldenFixture:
    """Golden fixture for 'bank' (polysemous English word)."""
    return _load_golden("bank_en")


@pytest.fixture
def golden_fork() -> GoldenFixture:
    """Golden fixture for 'fork' (polysemous English word with synonyms)."""
    return _load_golden("fork_en")


@pytest.fixture
def golden_fr() -> GoldenFixture:
    """Golden fixture for 'en coulisses' (enriched French phrase)."""
    return _load_golden("en_coulisses_fr")
