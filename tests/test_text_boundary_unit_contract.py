"""Behavioral proof for drawing-text canvas-unit consistency."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen import component as component_module
from InkGen.boundary import Canvas
from InkGen.component import ComponentGroup
from InkGen.document import Layer
from InkGen.drawing_components import DrawingComponentGroup, TextDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.errors import ComponentGroupOffCanvas
from InkGen.pdf_generator import TextPDF
from InkGen.style import Font, TextStyle
from InkGen.svg_generator import TextSVG
from InkGen.text_outline import outline_for_text

CONDITION = "TEXT-BOUNDARY-UNITS-P1"
PROBE_TEXT = "A email@yourbusinessname.co.nz"
PROBE_SIZE = 6.75


def _style(*, size: float = PROBE_SIZE) -> TextStyle:
    """Return a uniquely registered DejaVu Sans text style."""
    return TextStyle(
        name=f"text_boundary_units_{uuid4().hex}",
        font=Font(family="DejaVu Sans", size=size),
    )


def _dxf_text_height(payload: str) -> float:
    """Return group-code 40 from the first DXF TEXT entity."""
    lines = payload.splitlines()
    entity_start = lines.index("TEXT") - 1
    for index in range(entity_start, len(lines) - 1, 2):
        if lines[index] == "40":
            return float(lines[index + 1])
        if index > entity_start and lines[index] == "0":
            break
    raise AssertionError("DXF TEXT height was not emitted")


@pytest.mark.condition(CONDITION)
def test_text_outline_matches_canvas_units_and_layer_rejects_only_real_overflow() -> None:
    """Drawing text bounds match rendered size and preserve true overflow rejection."""
    style = _style()
    component = TextPDF(PROBE_TEXT, (0.0, 20.0), style)
    expected = outline_for_text(
        PROBE_TEXT,
        style.font.font_file,
        PROBE_SIZE,
        x=0.0,
        y=20.0,
        units="mm",
        dpi=96.0,
        add_one_pixel_margin=False,
    )
    expected_width = expected["path_bbox"][2] - expected["path_bbox"][0]
    actual_width = max(x for x, _ in component.points) - min(x for x, _ in component.points)

    assert actual_width == pytest.approx(expected_width)

    svg_component = TextSVG(PROBE_TEXT, (0.0, 20.0), style)
    svg_expected = outline_for_text(
        PROBE_TEXT,
        style.font.font_file,
        PROBE_SIZE * 96.0 / 72.0,
        x=0.0,
        y=20.0,
        units="mm",
        dpi=96.0,
        add_one_pixel_margin=False,
    )
    svg_expected_width = svg_expected["path_bbox"][2] - svg_expected["path_bbox"][0]
    svg_actual_width = max(x for x, _ in svg_component.points) - min(x for x, _ in svg_component.points)
    assert svg_actual_width == pytest.approx(svg_expected_width)

    fitting_group = ComponentGroup(f"text_fits_{uuid4().hex}")
    fitting_group.add_component(component)
    fitting_layer = Layer(
        f"text_fits_layer_{uuid4().hex}",
        Canvas(expected_width + 0.5, 40.0, "mm"),
    )
    fitting_layer.add_component_group(fitting_group)

    overflowing_group = ComponentGroup(f"text_overflows_{uuid4().hex}")
    overflowing_group.add_component(TextPDF(PROBE_TEXT, (0.0, 20.0), _style()))
    overflowing_layer = Layer(
        f"text_overflows_layer_{uuid4().hex}",
        Canvas(expected_width - 0.5, 40.0, "mm"),
    )
    with pytest.raises(ComponentGroupOffCanvas):
        overflowing_layer.add_component_group(overflowing_group)


@pytest.mark.condition(CONDITION)
def test_text_fallback_outline_uses_canvas_units(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF fallback uses canvas units while generic fallback retains points."""

    def fail_outline(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("outline unavailable")

    monkeypatch.setattr(component_module, "outline_for_text", fail_outline)
    component = TextPDF("AB", (0.0, 10.0), _style())

    assert component.bbox == (
        (0.0, 3.25),
        (8.1, 10.0),
    )
    empty = TextPDF("", (0.0, 10.0), _style())
    assert empty.bbox == (
        (0.0, 3.25),
        (3.375, 10.0),
    )
    minimum = TextPDF("", (0.0, 10.0), _style(size=1.0))
    assert minimum.bbox == (
        (0.0, 9.0),
        (0.5, 10.0),
    )

    generic_size = PROBE_SIZE * 25.4 / 72.0
    generic = TextSVG("AB", (0.0, 10.0), _style())
    assert generic.bbox == (
        (0.0, 10.0 - generic_size),
        (2.0 * generic_size * 0.6, 10.0),
    )
    generic_empty = TextSVG("", (0.0, 10.0), _style())
    assert generic_empty.bbox == (
        (0.0, 10.0 - generic_size),
        (generic_size * 0.5, 10.0),
    )


@pytest.mark.condition(CONDITION)
def test_pdf_outline_fix_preserves_svg_and_dxf_font_size_contracts() -> None:
    """PDF uses page canvas units without changing SVG or DXF point semantics."""
    style = _style()
    svg = TextSVG("Ink", (1.0, 2.0), style).generate_svg()
    pdf = TextPDF("Ink", (1.0, 2.0), style).generate_pdf()
    group = DrawingComponentGroup(f"text_units_{uuid4().hex}")
    group.add_component(TextDrawing("Ink", (1.0, 2.0), style))
    dxf_document = DXFDocument(canvas_height=20.0)
    dxf_document.add_group(group)

    assert "font-size:9.000000px" in svg
    assert "/F1 6.75 Tf" in pdf
    assert _dxf_text_height(dxf_document.to_dxf_string()) == pytest.approx(PROBE_SIZE * 25.4 / 72.0)
