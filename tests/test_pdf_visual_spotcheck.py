"""Tests for the SVG/PDF visual spot-check artifact generator."""

from __future__ import annotations

import pytest

from examples.pdf_visual_spotcheck import create_spotcheck_artifacts


@pytest.mark.condition("PDF-P1")
def test_pdf_visual_spotcheck_generates_svg_and_pdf_pair(tmp_path) -> None:
    """PDF-P1: The visual spot-check generator emits matched SVG/PDF artifacts."""
    paths = create_spotcheck_artifacts(tmp_path)

    assert paths["svg"].read_text(encoding="utf-8").startswith("<?xml")
    assert paths["pdf"].read_bytes().startswith(b"%PDF-1.6\n")
