"""Top-level package public API contract tests."""

from __future__ import annotations

import pytest

import InkGen
from InkGen import (
    Canvas,
    ComponentGroupPDF,
    DocumentOutputFormat,
    DocumentPDF,
    DXFDocument,
    DXFRenderContext,
    ExtractionTruthRecord,
    FlowDocument,
    GrammarTruthRecord,
    ImageDrawing,
    ImagePDF,
    ImageSVG,
    ParserStressBOMRow,
    ParserStressFixtureSpec,
    RasterImageAsset,
    RasterImageComponent,
    RectanglePDF,
    ScannedParserStressFixtureSpec,
    Table,
    ZoningDrawing,
    build_parser_stress_pdf,
    build_scanned_parser_stress_pdf,
)
from InkGen.document_outputs import DocumentOutputFormat as ModuleDocumentOutputFormat
from InkGen.document_outputs import FlowDocument as ModuleFlowDocument
from InkGen.drawing_components import ImageDrawing as ModuleImageDrawing
from InkGen.dxf_generator import DXFDocument as ModuleDXFDocument
from InkGen.dxf_generator import DXFRenderContext as ModuleDXFRenderContext
from InkGen.extraction_truth import ExtractionTruthRecord as ModuleExtractionTruthRecord
from InkGen.grammar_truth import GrammarTruthRecord as ModuleGrammarTruthRecord
from InkGen.image_assets import RasterImageAsset as ModuleRasterImageAsset
from InkGen.image_assets import RasterImageComponent as ModuleRasterImageComponent
from InkGen.parser_stress_fixtures import ParserStressBOMRow as ModuleParserStressBOMRow
from InkGen.parser_stress_fixtures import ParserStressFixtureSpec as ModuleParserStressFixtureSpec
from InkGen.parser_stress_fixtures import ScannedParserStressFixtureSpec as ModuleScannedParserStressFixtureSpec
from InkGen.parser_stress_fixtures import build_parser_stress_pdf as module_build_parser_stress_pdf
from InkGen.parser_stress_fixtures import build_scanned_parser_stress_pdf as module_build_scanned_parser_stress_pdf
from InkGen.pdf_generator import ComponentGroupPDF as ModuleComponentGroupPDF
from InkGen.pdf_generator import DocumentPDF as ModuleDocumentPDF
from InkGen.pdf_generator import ImagePDF as ModuleImagePDF
from InkGen.pdf_generator import RectanglePDF as ModuleRectanglePDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import ImageSVG as ModuleImageSVG
from InkGen.table import Table as ModuleTable

DOCUMENTED_PUBLIC_SYMBOLS = {
    "ArcPDF",
    "CirclePDF",
    "ComponentGroupPDF",
    "DocumentPDF",
    "ExtractionTruthAnnotation",
    "ExtractionTruthRecord",
    "FlattenedPath",
    "FlattenedSVG",
    "LinePDF",
    "PDFGeneratorInterface",
    "PDFRenderContext",
    "ParserStressBOMRow",
    "ParserStressFixtureSpec",
    "PathPDF",
    "RectanglePDF",
    "Row",
    "Column",
    "Cell",
    "Table",
    "DocumentOutputFormat",
    "DXFDocument",
    "DXFRenderContext",
    "FlowDocument",
    "GrammarTruthAnnotation",
    "GrammarTruthRecord",
    "ImageDrawing",
    "ImagePDF",
    "ImageSVG",
    "ZoningDrawing",
    "build_parser_stress_pdf",
    "RasterImageAsset",
    "RasterImageComponent",
    "ScannedParserStressFixtureSpec",
    "annotate_extraction_truth",
    "annotate_grammar_truth",
    "build_scanned_parser_stress_pdf",
    "extraction_truth_json",
    "flatten_svg",
    "grammar_truth_json",
}


@pytest.mark.condition("PUBLIC-API-P1")
def test_package_all_exports_are_bound_and_public() -> None:
    """PUBLIC-API-P1: Every __all__ symbol is importable and public."""
    assert len(InkGen.__all__) == len(set(InkGen.__all__))
    assert not any(name.startswith("_") for name in InkGen.__all__)

    for name in InkGen.__all__:
        assert getattr(InkGen, name) is not None


@pytest.mark.condition("PUBLIC-API-P1")
def test_documented_public_symbols_are_exported_from_package_root() -> None:
    """PUBLIC-API-P1: Documented public APIs are available from the package root."""
    missing = DOCUMENTED_PUBLIC_SYMBOLS.difference(InkGen.__all__)

    assert missing == set()
    for name in DOCUMENTED_PUBLIC_SYMBOLS:
        assert hasattr(InkGen, name)


@pytest.mark.condition("PUBLIC-API-P1")
def test_root_exports_match_submodule_identities() -> None:
    """PUBLIC-API-P1: Top-level exports are aliases to the canonical submodule objects."""
    assert DocumentPDF is ModuleDocumentPDF
    assert ComponentGroupPDF is ModuleComponentGroupPDF
    assert RectanglePDF is ModuleRectanglePDF
    assert ExtractionTruthRecord is ModuleExtractionTruthRecord
    assert GrammarTruthRecord is ModuleGrammarTruthRecord
    assert FlowDocument is ModuleFlowDocument
    assert DocumentOutputFormat is ModuleDocumentOutputFormat
    assert DXFDocument is ModuleDXFDocument
    assert DXFRenderContext is ModuleDXFRenderContext
    assert Table is ModuleTable
    assert RasterImageAsset is ModuleRasterImageAsset
    assert RasterImageComponent is ModuleRasterImageComponent
    assert ImageDrawing is ModuleImageDrawing
    assert ImageSVG is ModuleImageSVG
    assert ImagePDF is ModuleImagePDF
    assert ParserStressBOMRow is ModuleParserStressBOMRow
    assert ParserStressFixtureSpec is ModuleParserStressFixtureSpec
    assert build_parser_stress_pdf is module_build_parser_stress_pdf
    assert ScannedParserStressFixtureSpec is ModuleScannedParserStressFixtureSpec
    assert build_scanned_parser_stress_pdf is module_build_scanned_parser_stress_pdf


@pytest.mark.condition("PUBLIC-API-P1")
def test_root_exports_work_in_pdf_authoring_path() -> None:
    """PUBLIC-API-P1: Root-imported PDF classes work in a minimal authoring path."""
    canvas = Canvas(40.0, 30.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroupPDF("panel")
    group.add_component(RectanglePDF((5.0, 6.0), 10.0, 8.0, 0.0, DrawingStyle("public_api_pdf", fill="none")))
    document.page(1).layer("base").add_component_group(group)

    payload = document.to_pdf_bytes()

    assert payload.startswith(b"%PDF-1.4")
    assert b"5 6 10 8 re" in payload


@pytest.mark.condition("PUBLIC-API-P1")
def test_renderer_neutral_zoning_recipe_is_exported() -> None:
    """PUBLIC-API-P1: Renderer-neutral drawing recipes include top-level zoning access."""
    assert ZoningDrawing.__name__ == "ZoningDrawing"
