"""PDF render-contract guard tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.component import ComponentGroup
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF
from InkGen.pdf_render_contract import ensure_builtin_pdf_component, ensure_pdf_group
from InkGen.style import DrawingStyle


class CustomRectanglePDF(RectanglePDF):
    """Custom PDF rectangle subclass used to test closed primitive boundaries."""


class CustomGroupPDF(ComponentGroupPDF):
    """Custom PDF group subclass used to test closed group boundaries."""

    def generate_pdf(self, context: object | None = None) -> str:
        """Return custom operators that must never pass the document guard."""
        return "custom"


def _style() -> DrawingStyle:
    """Return a unique drawing style for PDF render guard tests."""
    return DrawingStyle(name=f"pdf_guard_{uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


def _rectangle() -> RectanglePDF:
    """Return a built-in PDF rectangle component."""
    return RectanglePDF((5.0, 6.0), 10.0, 8.0, 0.0, _style())


@pytest.mark.condition("PDF-GUARD-P3")
def test_builtin_pdf_component_guard_accepts_exact_allowed_type() -> None:
    """PDF-GUARD-P3: Built-in component guard accepts exact allowed primitive types."""
    ensure_builtin_pdf_component(_rectangle(), (RectanglePDF,), message="bad component")


@pytest.mark.condition("PDF-GUARD-P3")
def test_builtin_pdf_component_guard_rejects_subclasses_and_preserves_message() -> None:
    """PDF-GUARD-P3: Built-in component guard rejects custom subclasses with caller diagnostics."""
    custom = CustomRectanglePDF((5.0, 6.0), 10.0, 8.0, 0.0, _style())

    with pytest.raises(TypeError, match="closed component"):
        ensure_builtin_pdf_component(custom, (RectanglePDF,), message="closed component")


@pytest.mark.condition("PDF-GUARD-P3")
def test_pdf_group_guard_accepts_exact_component_group_type() -> None:
    """PDF-GUARD-P3: Group guard accepts exact ComponentGroupPDF instances."""
    ensure_pdf_group(ComponentGroupPDF("ok"), ComponentGroupPDF, message="bad group")


@pytest.mark.condition("PDF-GUARD-P3")
def test_pdf_group_guard_rejects_standard_groups_and_pdf_subclasses() -> None:
    """PDF-GUARD-P3: Group guard rejects both non-PDF groups and custom PDF subclasses."""
    with pytest.raises(TypeError, match="closed group"):
        ensure_pdf_group(ComponentGroup("standard"), ComponentGroupPDF, message="closed group")
    with pytest.raises(TypeError, match="closed group"):
        ensure_pdf_group(CustomGroupPDF("custom"), ComponentGroupPDF, message="closed group")


@pytest.mark.condition("PDF-GUARD-P3")
def test_pdf_document_live_path_rejects_custom_group_subclass() -> None:
    """PDF-GUARD-P3: DocumentPDF rejects custom group subclasses before rendering custom operators."""
    document = DocumentPDF(Canvas(100.0, 80.0))
    document.add_page()
    custom = CustomGroupPDF("custom")
    custom.add_component(_rectangle())
    document.page(1).layer("base").add_component_group(custom)

    with pytest.raises(TypeError, match="DocumentPDF pages must contain ComponentGroupPDF groups"):
        document.to_pdf_bytes()


@pytest.mark.condition("PDF-GUARD-P3")
def test_pdf_render_contract_helpers_keep_keyword_only_message() -> None:
    """PDF-GUARD-P3: Guard diagnostic messages remain keyword-only."""
    with pytest.raises(TypeError, match="positional"):
        ensure_builtin_pdf_component(_rectangle(), (RectanglePDF,), "message")
    with pytest.raises(TypeError, match="positional"):
        ensure_pdf_group(ComponentGroupPDF("bad"), ComponentGroupPDF, "message")
