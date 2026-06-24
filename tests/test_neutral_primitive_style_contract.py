"""Behavioral tests for neutral drawing primitive style boundaries."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest

from InkGen.component import PathCommand
from InkGen.drawing_components import (
    ArcDrawing,
    CircleDrawing,
    CubicBezierDrawing,
    LineDrawing,
    OutputFormat,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
)
from InkGen.style import DrawingStyle, Font, TextStyle


def _drawing_style() -> DrawingStyle:
    """Return a unique drawing style for neutral primitive style tests."""
    return DrawingStyle(f"neutral_primitive_draw_{uuid4().hex}", stroke="#111111", fill="none", stroke_width=0.2)


def _text_style() -> TextStyle:
    """Return a unique text style for neutral primitive style tests."""
    return TextStyle(f"neutral_primitive_text_{uuid4().hex}", Font(size=8.0))


@pytest.mark.condition("NEUTRAL-PRIMITIVE-STYLE-P2")
@pytest.mark.parametrize(
    ("factory", "owner"),
    [
        (lambda style: RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, style), "RectangleDrawing"),
        (lambda style: LineDrawing((0.0, 0.0), (5.0, 5.0), style), "LineDrawing"),
        (lambda style: ArcDrawing((10.0, 10.0), 4.0, 2.0, 0.0, 90.0, style), "ArcDrawing"),
        (
            lambda style: QuadraticBezierDrawing((0.0, 0.0), (3.0, 6.0), (6.0, 0.0), style),
            "QuadraticBezierDrawing",
        ),
        (
            lambda style: CubicBezierDrawing((0.0, 0.0), (2.0, 6.0), (4.0, 6.0), (6.0, 0.0), style),
            "CubicBezierDrawing",
        ),
        (lambda style: PathDrawing(style, [PathCommand("M", [(0.0, 0.0)])]), "PathDrawing"),
        (lambda style: RegularPolygonDrawing((8.0, 8.0), 5, 3.0, style), "RegularPolygonDrawing"),
        (lambda style: PolygonalDrawing([(0.0, 0.0), (4.0, 0.0), (2.0, 3.0)], style), "PolygonalDrawing"),
        (lambda style: CircleDrawing((5.0, 5.0), 2.0, style), "CircleDrawing"),
    ],
)
@pytest.mark.parametrize("invalid_style", [object(), None])
def test_neutral_drawing_primitives_reject_invalid_drawing_styles(
    factory: Callable[[object], object],
    owner: str,
    invalid_style: object,
) -> None:
    """NEUTRAL-PRIMITIVE-STYLE-P2: Drawing primitives require DrawingStyle."""
    with pytest.raises(TypeError, match=f"{owner} style must be a DrawingStyle"):
        factory(invalid_style)


@pytest.mark.condition("NEUTRAL-PRIMITIVE-STYLE-P2")
def test_neutral_drawing_primitives_reject_text_style_kind() -> None:
    """NEUTRAL-PRIMITIVE-STYLE-P2: TextStyle cannot stand in for drawing style."""
    with pytest.raises(TypeError, match="RectangleDrawing style must be a DrawingStyle"):
        RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, _text_style())  # type: ignore[arg-type]


@pytest.mark.condition("NEUTRAL-PRIMITIVE-STYLE-P2")
@pytest.mark.parametrize("invalid_style", [object(), None, _drawing_style()])
def test_neutral_text_primitive_rejects_invalid_text_styles(invalid_style: object) -> None:
    """NEUTRAL-PRIMITIVE-STYLE-P2: TextDrawing requires TextStyle."""
    with pytest.raises(TypeError, match="TextDrawing style must be a TextStyle"):
        TextDrawing("A", (1.0, 2.0), invalid_style)  # type: ignore[arg-type]


@pytest.mark.condition("NEUTRAL-PRIMITIVE-STYLE-P2")
def test_neutral_primitives_with_valid_styles_still_materialize() -> None:
    """NEUTRAL-PRIMITIVE-STYLE-P2: Valid styles preserve SVG/PDF materialization."""
    drawing_style = _drawing_style()
    text_style = _text_style()
    primitives = [
        RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, drawing_style),
        LineDrawing((0.0, 0.0), (5.0, 5.0), drawing_style),
        TextDrawing("A", (2.0, 3.0), text_style),
        PathDrawing(drawing_style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(3.0, 0.0)])]),
    ]

    for primitive in primitives:
        svg_component = primitive.to_component(OutputFormat.SVG)
        pdf_component = primitive.to_component(OutputFormat.PDF)

        assert svg_component.__class__.__name__.endswith("SVG")
        assert pdf_component.__class__.__name__.endswith("PDF")
