"""Tests for renderer-neutral synthetic drawing component recipes."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.cad_component_groups import Zoning
from InkGen.component import PathCommand
from InkGen.drawing_components import (
    ArcDrawing,
    CircleDrawing,
    CubicBezierDrawing,
    DrawingComponentGroup,
    LineDrawing,
    OutputFormat,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
    ZoningDrawing,
)
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.svg_generator import ComponentGroupSVG


def _name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _styles() -> tuple[DrawingStyle, TextStyle]:
    line_style = DrawingStyle(_name("neutral_line"), stroke="#111111", fill="none", stroke_width=0.2)
    text_style = TextStyle(_name("neutral_text"), Font(size=6))
    return line_style, text_style


@pytest.mark.condition("PDF-P3")
def test_neutral_zoning_recipe_materializes_svg_components() -> None:
    """PDF-P3: ZoningDrawing can emit an SVG component group without PDF coupling."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()
    zoning = ZoningDrawing(
        canvas,
        line_style,
        text_style,
        horizontal_zones=10,
        vertical_zones=8,
        first_horizontal_char=48,
    )

    group = zoning.to_group(OutputFormat.SVG)
    component_types = {type(component).__name__ for component in group.components()}

    assert isinstance(group, ComponentGroupSVG)
    assert component_types == {"LineSVG", "RectangleSVG", "TextSVG"}
    assert all(hasattr(component, "generate_svg") for component in group.components())


@pytest.mark.condition("PDF-P3")
def test_neutral_zoning_recipe_materializes_pdf_components() -> None:
    """PDF-P3: ZoningDrawing can emit a PDF component group that renders in DocumentPDF."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()
    zoning = ZoningDrawing(
        canvas,
        line_style,
        text_style,
        horizontal_zones=10,
        vertical_zones=8,
        first_horizontal_char=48,
    )

    group = zoning.to_group("pdf")
    document = DocumentPDF(canvas)
    document.add_page()
    document.page(1).layer("base").add_component_group(group)
    payload = document.to_pdf_bytes()
    component_types = {type(component).__name__ for component in group.components()}

    assert isinstance(group, ComponentGroupPDF)
    assert component_types == {"LinePDF", "RectanglePDF", "TextPDF"}
    assert payload.startswith(b"%PDF-1.4\n")
    assert b"/Count 1" in payload


@pytest.mark.condition("PDF-P3")
def test_neutral_group_preserves_geometry_across_svg_and_pdf_outputs() -> None:
    """PDF-P3: The same neutral recipe produces equivalent SVG and PDF group geometry."""
    line_style, text_style = _styles()
    recipe = DrawingComponentGroup("portable")
    recipe.add_component(RectangleDrawing((10.0, 20.0), 30.0, 40.0, 0.0, line_style))
    recipe.add_component(LineDrawing((0.0, 0.0), (5.0, 5.0), line_style))
    recipe.add_component(TextDrawing("A1", (12.0, 22.0), text_style))

    svg_group = recipe.to_group(OutputFormat.SVG)
    pdf_group = recipe.to_group(OutputFormat.PDF)

    assert svg_group.bbox == pdf_group.bbox
    assert svg_group.convex_hull == pdf_group.convex_hull


@pytest.mark.condition("PDF-P3")
def test_neutral_primitives_materialize_to_svg_and_pdf_components() -> None:
    """PDF-P3: Drawing primitives support only the drawing renderers SVG and PDF."""
    line_style, text_style = _styles()
    primitives = [
        RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, line_style),
        LineDrawing((0.0, 0.0), (5.0, 5.0), line_style),
        TextDrawing("A", (2.0, 3.0), text_style),
        ArcDrawing((10.0, 10.0), 4.0, 2.0, 0.0, 90.0, line_style),
        QuadraticBezierDrawing((0.0, 0.0), (3.0, 6.0), (6.0, 0.0), line_style),
        CubicBezierDrawing((0.0, 0.0), (2.0, 6.0), (4.0, 6.0), (6.0, 0.0), line_style),
        PathDrawing(line_style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(3.0, 0.0)]), PathCommand("Z")]),
        RegularPolygonDrawing((8.0, 8.0), 5, 3.0, line_style),
        PolygonalDrawing([(0.0, 0.0), (4.0, 0.0), (2.0, 3.0)], line_style),
        CircleDrawing((5.0, 5.0), 2.0, line_style),
    ]

    for primitive in primitives:
        svg_component = primitive.to_component(OutputFormat.SVG)
        pdf_component = primitive.to_component(OutputFormat.PDF)

        assert svg_component.__class__.__name__.endswith("SVG")
        assert pdf_component.__class__.__name__.endswith("PDF")
        assert hasattr(svg_component, "generate_svg")
        assert hasattr(pdf_component, "generate_pdf")


@pytest.mark.condition("PDF-P3")
def test_neutral_recipes_fail_loudly_for_unsupported_output_format() -> None:
    """PDF-P3: Unsupported render targets fail before a mixed renderer group is created."""
    recipe = DrawingComponentGroup("bad_target")

    with pytest.raises(TypeError, match="to_component"):
        recipe.add_component(object())

    with pytest.raises(ValueError, match="Unsupported output format"):
        recipe.to_group("png")


@pytest.mark.condition("PDF-P3")
def test_zoning_recipe_round_trips_without_renderer_specific_components() -> None:
    """PDF-P3: ZoningDrawing serialization stores recipe inputs, not SVG/PDF classes."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()
    zoning = ZoningDrawing(
        canvas,
        line_style,
        text_style,
        margins=5,
        horizontal_zones=10,
        vertical_zones=8,
        first_horizontal_char=48,
    )

    recreated = ZoningDrawing.create_from_dict(
        zoning.parameters,
        {line_style.name: line_style, text_style.name: text_style},
    )

    assert recreated.parameters == zoning.parameters
    assert "SVG" not in repr(zoning.parameters)
    assert "PDF" not in repr(zoning.parameters)


@pytest.mark.condition("ZONING-DRAWING-FINITE-P2")
@pytest.mark.parametrize(
    "kwargs",
    [
        {"margins": True},
        {"margins": object()},
        {"margins": -0.01},
        {"margins": float("nan")},
        {"margins": float("inf")},
        {"zone_width": float("-inf")},
        {"inner_radius": True},
        {"outer_radius": -1.0},
    ],
)
def test_zoning_drawing_rejects_invalid_dimension_parameters(kwargs: dict[str, object]) -> None:
    """ZONING-DRAWING-FINITE-P2: Zoning dimensions must be finite non-negative numbers."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()

    with pytest.raises((TypeError, ValueError), match="finite non-negative number"):
        ZoningDrawing(canvas, line_style, text_style, **kwargs)


@pytest.mark.condition("ZONING-DRAWING-FINITE-P2")
def test_zoning_drawing_preserves_zero_dimension_overrides() -> None:
    """ZONING-DRAWING-FINITE-P2: Zero is a valid explicit zoning dimension."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()

    zoning = ZoningDrawing(
        canvas,
        line_style,
        text_style,
        margins=5.0,
        left_margin=0.0,
        zone_width=3.0,
        left_zone_width=0.0,
        horizontal_zones=10,
        vertical_zones=8,
        first_horizontal_char=48,
    )

    params = zoning.parameters["ZoningDrawing"]["parameters"]
    assert params["left_margin"] == 0.0
    assert params["left_zone_width"] == 0.0
    assert params["right_margin"] == 5.0
    assert params["right_zone_width"] == 3.0


@pytest.mark.condition("ZONING-DRAWING-FINITE-P2")
def test_zoning_drawing_hydration_rejects_invalid_dimensions() -> None:
    """ZONING-DRAWING-FINITE-P2: Serialized zoning dimensions cannot bypass validation."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()
    payload = {
        "ZoningDrawing": {
            "canvas": canvas.parameters,
            "line_style": line_style.parameters,
            "text_style": text_style.parameters,
            "parameters": {"zone_width": float("nan")},
        }
    }

    with pytest.raises(ValueError, match="finite non-negative number"):
        ZoningDrawing.create_from_dict(payload, {line_style.name: line_style, text_style.name: text_style})


@pytest.mark.condition("ZONING-DRAWING-LAYOUT-P2")
@pytest.mark.parametrize(
    ("canvas", "kwargs", "message"),
    [
        (Canvas(20.0, 20.0, "mm"), {}, "inner drawing area must be positive"),
        (Canvas(40.0, 60.0, "mm"), {"left_margin": 25.0, "right_margin": 20.0}, "outer drawing area must be positive"),
        (Canvas(40.0, 60.0, "mm"), {"left_margin": 20.0, "right_margin": 20.0}, "outer drawing area must be positive"),
        (Canvas(80.0, 40.0, "mm"), {"top_margin": 25.0, "bottom_margin": 20.0}, "outer drawing area must be positive"),
        (Canvas(60.0, 40.0, "mm"), {"top_margin": 20.0, "bottom_margin": 20.0}, "outer drawing area must be positive"),
        (
            Canvas(80.0, 80.0, "mm"),
            {"margins": 5.0, "left_zone_width": 40.0, "right_zone_width": 40.0},
            "inner drawing area must be positive",
        ),
        (
            Canvas(80.0, 80.0, "mm"),
            {"margins": 5.0, "left_zone_width": 35.0, "right_zone_width": 35.0},
            "inner drawing area must be positive",
        ),
        (
            Canvas(80.0, 80.0, "mm"),
            {"margins": 5.0, "top_zone_width": 35.0, "bottom_zone_width": 35.0},
            "inner drawing area must be positive",
        ),
        (
            Canvas(80.0, 80.0, "mm"),
            {"margins": 5.0, "top_zone_width": 45.0, "bottom_zone_width": 30.0},
            "inner drawing area must be positive",
        ),
    ],
)
def test_zoning_drawing_rejects_impossible_layouts_before_primitive_construction(
    canvas: Canvas,
    kwargs: dict[str, object],
    message: str,
) -> None:
    """ZONING-DRAWING-LAYOUT-P2: Impossible layouts fail at the zoning boundary."""
    line_style, text_style = _styles()

    with pytest.raises(ValueError, match=message):
        ZoningDrawing(canvas, line_style, text_style, **kwargs)


@pytest.mark.condition("ZONING-DRAWING-LAYOUT-P2")
def test_zoning_drawing_hydration_rejects_impossible_layouts_before_primitive_construction() -> None:
    """ZONING-DRAWING-LAYOUT-P2: Serialized impossible layouts use the same boundary."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()
    zoning = ZoningDrawing(
        canvas,
        line_style,
        text_style,
        margins=5.0,
        horizontal_zones=10,
        vertical_zones=8,
        first_horizontal_char=48,
    )
    payload = deepcopy(zoning.parameters)
    payload["ZoningDrawing"]["canvas"] = Canvas(20.0, 20.0, "mm").parameters

    with pytest.raises(ValueError, match="inner drawing area must be positive"):
        ZoningDrawing.create_from_dict(payload, {line_style.name: line_style, text_style.name: text_style})


@pytest.mark.condition("ZONING-DRAWING-LABEL-RANGE-P2")
@pytest.mark.parametrize(
    ("parameters", "valid"),
    [
        ({"first_horizontal_char": 48, "horizontal_zones": 10, "first_vertical_char": 65, "vertical_zones": 8}, True),
        ({"first_horizontal_char": 49, "horizontal_zones": 8, "first_vertical_char": 65, "vertical_zones": 26}, True),
        ({"first_horizontal_char": 56, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, True),
        ({"first_horizontal_char": 65, "horizontal_zones": 26, "first_vertical_char": 65, "vertical_zones": 2}, True),
        ({"first_horizontal_char": 89, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, True),
        ({"first_horizontal_char": 97, "horizontal_zones": 26, "first_vertical_char": 65, "vertical_zones": 2}, True),
        ({"first_horizontal_char": 121, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, True),
        ({"first_horizontal_char": 47, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, False),
        ({"first_horizontal_char": 58, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, False),
        ({"first_horizontal_char": 64, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, False),
        ({"first_horizontal_char": 91, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, False),
        ({"first_horizontal_char": 96, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, False),
        ({"first_horizontal_char": 123, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, False),
        ({"first_horizontal_char": 49, "horizontal_zones": 10, "first_vertical_char": 65, "vertical_zones": 8}, False),
        ({"first_horizontal_char": 57, "horizontal_zones": 4, "first_vertical_char": 65, "vertical_zones": 8}, False),
        ({"first_horizontal_char": 90, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, False),
        ({"first_horizontal_char": 122, "horizontal_zones": 2, "first_vertical_char": 65, "vertical_zones": 2}, False),
        ({"first_horizontal_char": 48, "horizontal_zones": 10, "first_vertical_char": 122, "vertical_zones": 8}, False),
        ({"first_horizontal_char": 48, "horizontal_zones": 10, "first_vertical_char": 89, "vertical_zones": 4}, False),
    ],
)
def test_zoning_drawing_label_range_validator_partitions(parameters: dict[str, object], valid: bool) -> None:
    """ZONING-DRAWING-LABEL-RANGE-P2: Label range partitions are explicit."""
    zoning = object.__new__(ZoningDrawing)
    zoning._parameters = parameters

    if valid:
        zoning._validate_zone_label_ranges()
    else:
        with pytest.raises(ValueError, match="alphanumeric ASCII labels"):
            zoning._validate_zone_label_ranges()


@pytest.mark.condition("ZONING-DRAWING-LABEL-RANGE-P2")
def test_zoning_drawing_preserves_alphanumeric_label_sequences() -> None:
    """ZONING-DRAWING-LABEL-RANGE-P2: Valid zoning labels stay alphanumeric."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()

    zoning = ZoningDrawing(
        canvas,
        line_style,
        text_style,
        horizontal_zones=10,
        vertical_zones=8,
        first_horizontal_char=48,
        first_vertical_char=65,
    )
    labels = [component.text for component in zoning.drawing_group.components if isinstance(component, TextDrawing)]

    assert set("0123456789").issubset(labels)
    assert set("ABCDEFGH").issubset(labels)
    assert all(label.isalnum() and len(label) == 1 for label in labels)


@pytest.mark.condition("ZONING-DRAWING-LABEL-RANGE-P2")
@pytest.mark.parametrize(
    "kwargs",
    [
        {"horizontal_zones": 10},
        {"horizontal_zones": 4, "first_horizontal_char": 57},
        {"horizontal_zones": 8, "first_horizontal_char": 52},
        {"vertical_zones": 4, "first_vertical_char": 89},
        {"vertical_zones": 8, "first_vertical_char": 122},
        {"vertical_zones": 4, "first_vertical_char": 121},
    ],
)
def test_zoning_drawing_rejects_label_sequences_that_leave_ascii_ranges(kwargs: dict[str, object]) -> None:
    """ZONING-DRAWING-LABEL-RANGE-P2: Label ranges fail before text generation."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()

    with pytest.raises(ValueError, match="alphanumeric ASCII labels"):
        ZoningDrawing(canvas, line_style, text_style, **kwargs)


@pytest.mark.condition("ZONING-DRAWING-LABEL-RANGE-P2")
def test_zoning_drawing_hydration_rejects_label_ranges_that_leave_ascii_ranges() -> None:
    """ZONING-DRAWING-LABEL-RANGE-P2: Serialized label ranges cannot bypass validation."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()
    zoning = ZoningDrawing(
        canvas,
        line_style,
        text_style,
        horizontal_zones=10,
        vertical_zones=8,
        first_horizontal_char=48,
    )
    payload = deepcopy(zoning.parameters)
    payload["ZoningDrawing"]["parameters"]["first_horizontal_char"] = 49

    with pytest.raises(ValueError, match="alphanumeric ASCII labels"):
        ZoningDrawing.create_from_dict(payload, {line_style.name: line_style, text_style.name: text_style})


@pytest.mark.condition("PDF-P3")
def test_neutral_zoning_svg_output_matches_legacy_zoning_geometry() -> None:
    """PDF-P3: ZoningDrawing keeps the existing SVG zoning geometry while removing backend coupling."""
    canvas = Canvas(210.0, 297.0, "mm")
    line_style, text_style = _styles()
    kwargs = {"margins": 5, "horizontal_zones": 10, "vertical_zones": 8, "first_horizontal_char": 48}

    legacy_components = list(Zoning(canvas, line_style, text_style, **kwargs).component_group.components())
    neutral_components = list(ZoningDrawing(canvas, line_style, text_style, **kwargs).to_group(OutputFormat.SVG).components())

    assert [component.parameters for component in neutral_components] == [component.parameters for component in legacy_components]
