"""Tests for local regional variant detection."""

from __future__ import annotations

from floridify.ai.assessment.regional import detect_regional_local


class TestDetectRegional:
    def test_detects_american(self) -> None:
        assert detect_regional_local("(chiefly American) a sidewalk") == "US"

    def test_detects_british(self) -> None:
        assert detect_regional_local("(chiefly British) a pavement") == "UK"

    def test_detects_australian(self) -> None:
        assert detect_regional_local("(Australian) a barbecue") == "AU"

    def test_detects_canadian(self) -> None:
        assert detect_regional_local("(Canadian) a toque") == "CA"

    def test_detects_scottish(self) -> None:
        assert detect_regional_local("(Scottish) a wee lad") == "SC"

    def test_returns_none_for_no_region(self) -> None:
        assert detect_regional_local("a large body of water") is None

    def test_case_insensitive(self) -> None:
        assert detect_regional_local("(BRITISH) a lorry") == "UK"
