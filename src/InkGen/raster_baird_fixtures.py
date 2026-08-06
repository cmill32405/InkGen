"""End-to-end raster, Baird, and PDF fixture composition."""

from __future__ import annotations

from dataclasses import dataclass

from InkGen.baird import BairdParams
from InkGen.boundary import Canvas
from InkGen.drawing_components import DrawingComponentGroup, ImageDrawing, LineDrawing, OutputFormat, RectangleDrawing, TextDrawing
from InkGen.extraction_truth import annotate_extraction_truth
from InkGen.grammar_truth import annotate_grammar_truth
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, ImagePDF
from InkGen.raster_renderer import RasterBairdResult, render_and_degrade_drawing_group
from InkGen.style import DrawingStyle, Font, Style, TextStyle

_CONDITION_ID = "RASTER-BAIRD-E2E-P19"
_CANVAS_WIDTH_MM = 120.0
_CANVAS_HEIGHT_MM = 80.0
_PDF_INSET_MM = 0.1
_SOURCE = "generated://inkgen/raster-baird-e2e.png"


@dataclass(frozen=True, slots=True)
class RasterBairdPDFFixture:
    """Clean/degraded raster assets paired with their image-only PDF."""

    scan: RasterBairdResult
    document: DocumentPDF

    def __post_init__(self) -> None:
        """Reject unrelated result envelopes at the public boundary."""
        if not isinstance(self.scan, RasterBairdResult):
            raise TypeError("scan must be a RasterBairdResult")
        if not isinstance(self.document, DocumentPDF):
            raise TypeError("document must be a DocumentPDF")

    @property
    def manifest(self) -> dict[str, object]:
        """Return deterministic provenance for the complete fixture chain."""
        return {
            "condition": _CONDITION_ID,
            "scan": self.scan.manifest,
            "pdf_embedding": {
                "canvas": {"width": _CANVAS_WIDTH_MM, "height": _CANVAS_HEIGHT_MM, "units": "mm"},
                "pages": 1,
                "source": _SOURCE,
                "image_pixels": [self.scan.degraded.asset.width, self.scan.degraded.asset.height],
                "inset": _PDF_INSET_MM,
            },
        }


def build_raster_baird_pdf_fixture(
    *,
    params: BairdParams | None = None,
    seed: int = 19,
    background_rgb: tuple[int, int, int] = (226, 236, 244),
    dpi: float = 72.0,
    render_supersample: int = 2,
) -> RasterBairdPDFFixture:
    """Build a deterministic drawing-to-scan image-only PDF fixture.

    The neutral drawing deliberately includes text, vector geometry,
    transparency, and geometry crossing the top-left canvas edge. Validation
    of Baird parameters, seed, substrate, DPI, and supersampling remains owned
    by the existing public composition boundary.
    """
    degradation = BairdParams() if params is None else params
    canvas = Canvas(_CANVAS_WIDTH_MM, _CANVAS_HEIGHT_MM, "mm")
    scan = render_and_degrade_drawing_group(
        _fixture_drawing_group(),
        canvas,
        degradation,
        seed=seed,
        background_rgb=background_rgb,
        dpi=dpi,
        render_supersample=render_supersample,
        source=_SOURCE,
    )

    image_component = ImageDrawing(
        scan.degraded.asset,
        (_PDF_INSET_MM, _PDF_INSET_MM),
        canvas.width - 2 * _PDF_INSET_MM,
        canvas.height - 2 * _PDF_INSET_MM,
    ).to_component(OutputFormat.PDF)
    if not isinstance(image_component, ImagePDF):
        raise TypeError("ImageDrawing PDF materialization must return ImagePDF")
    annotate_extraction_truth(
        image_component,
        "scanned_page_image",
        _CONDITION_ID,
        role="image",
        source_channel="image",
        instance_id=_CONDITION_ID,
    )
    annotate_grammar_truth(
        image_component,
        _CONDITION_ID,
        "cue",
        value={"fixture_family": "raster_baird_pdf", "rasterized_text": True, "source": _SOURCE},
        source_channel="image",
        instance_id=_CONDITION_ID,
    )

    concrete_group = ComponentGroupPDF("raster_baird_scan")
    concrete_group.add_component(image_component)
    annotate_extraction_truth(
        concrete_group,
        "scanned_page",
        _CONDITION_ID,
        role="region",
        instance_id=_CONDITION_ID,
    )
    document = DocumentPDF(canvas)
    document.add_page()
    annotate_grammar_truth(
        document,
        _CONDITION_ID,
        "assessment",
        value={"fixture_family": "raster_baird_pdf", "known_fixture": True, "extractable_text": False},
        source_channel="metadata",
        instance_id=_CONDITION_ID,
    )
    document.page(1).layer("base").add_component_group(concrete_group)
    return RasterBairdPDFFixture(scan, document)


def _fixture_drawing_group() -> DrawingComponentGroup:
    translucent = DrawingStyle(
        _unique_style_name("translucent"),
        stroke="#12384a",
        stroke_width=0.8,
        fill="#2f7da3",
        fill_opacity=0.45,
    )
    outline = DrawingStyle(_unique_style_name("outline"), stroke="#17212b", stroke_width=0.6, fill="none")
    accent = DrawingStyle(_unique_style_name("accent"), stroke="#b2342c", stroke_width=1.2, fill="none")
    text = TextStyle(_unique_style_name("text"), Font(family="sans-serif", weight="bold", size=14.0))
    text.color = "#111111"
    return DrawingComponentGroup(
        "raster_baird_source",
        [
            RectangleDrawing((-8.0, -6.0), 48.0, 30.0, (4.0, 7.0), translucent),
            RectangleDrawing((8.0, 8.0), 104.0, 64.0, 0.0, outline),
            LineDrawing((14.0, 49.0), (106.0, 49.0), accent),
            TextDrawing("INKGEN RASTER / BAIRD", (15.0, 39.0), text),
        ],
    )


def _unique_style_name(suffix: str) -> str:
    base = f"raster_baird_e2e_{suffix}"
    if base not in Style.style_names:
        return base
    index = 2
    while f"{base}_{index}" in Style.style_names:
        index += 1
    return f"{base}_{index}"
