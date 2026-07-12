"""Behavioral tests for the legacy SVG zoning contract."""

from __future__ import annotations

import math
from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.cad_component_groups import Zoning
from InkGen.component import TextComponent
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.svg_generator import ComponentGroupSVG, LineSVG, RectangleSVG, TextSVG


@pytest.fixture
def canvas() -> Canvas:
    """Return an A4-sized millimeter canvas."""
    return Canvas(210.0, 297.0, "mm")


@pytest.fixture
def line_style() -> DrawingStyle:
    """Return a unique visible line style."""
    return DrawingStyle(f"cad_zone_line_{uuid4().hex}", stroke="#111111", fill="none", stroke_width=0.2)


@pytest.fixture
def text_style() -> TextStyle:
    """Return a unique visible text style."""
    return TextStyle(f"cad_zone_text_{uuid4().hex}", Font(size=6.0))


@pytest.mark.condition("CAD-ZONING-P1")
def test_legacy_zoning_emits_only_svg_components(
    canvas: Canvas,
    line_style: DrawingStyle,
    text_style: TextStyle,
) -> None:
    """CAD-ZONING-P1: Legacy zoning intentionally emits SVG-specific components."""
    zoning = Zoning(canvas, line_style, text_style, horizontal_zones=10, vertical_zones=8)
    components = list(zoning.component_group.components())
    component_types = {type(component) for component in components}

    assert not isinstance(zoning.component_group, ComponentGroupSVG)
    assert zoning.component_group.group_label == "Zoning"
    assert component_types == {RectangleSVG, LineSVG, TextSVG}
    assert sum(type(component) is RectangleSVG for component in components) == 2
    assert sum(type(component) is LineSVG for component in components) == 32
    assert sum(type(component) is TextSVG for component in components) == 36
    assert len(components) == 70

    rectangles = [component for component in components if type(component) is RectangleSVG]
    assert rectangles[0].position == (5, 5)
    assert rectangles[0].width == pytest.approx(200.0)
    assert rectangles[0].height == pytest.approx(287.0)
    assert rectangles[1].position[0] > rectangles[0].position[0]
    assert rectangles[1].position[1] > rectangles[0].position[1]

    text_labels = [component.text for component in components if type(component) is TextSVG]
    assert text_labels[:16] == [label for character in "ABCDEFGH" for label in (character, character)]
    assert text_labels[-20:] == [label for character in "123456789:" for label in (character, character)]


@pytest.mark.condition("CAD-ZONING-P1")
def test_legacy_zoning_honors_zero_specific_margins_and_widths(
    canvas: Canvas,
    line_style: DrawingStyle,
    text_style: TextStyle,
) -> None:
    """CAD-ZONING-P1: Explicit zero values participate in CSS-like specificity."""
    zoning = Zoning(
        canvas,
        line_style,
        text_style,
        margins=9.0,
        left_margin=0.0,
        zone_width=11.0,
        left_zone_width=0.0,
        horizontal_zones=10,
        vertical_zones=8,
    )

    assert zoning._parameters["left_margin"] == 0.0
    assert zoning._parameters["top_margin"] == 9.0
    assert zoning._parameters["right_margin"] == 9.0
    assert zoning._parameters["bottom_margin"] == 9.0
    assert zoning._parameters["left_zone_width"] == 0.0
    assert zoning._parameters["top_zone_width"] == 11.0
    assert zoning._parameters["right_zone_width"] == 11.0
    assert zoning._parameters["bottom_zone_width"] == 11.0

    outer_rectangle = next(component for component in zoning.component_group.components() if isinstance(component, RectangleSVG))
    assert outer_rectangle.position == (0.0, 9.0)


@pytest.mark.condition("CAD-ZONING-P1")
def test_legacy_zoning_rejects_invalid_boundary_parameters(
    canvas: Canvas,
    line_style: DrawingStyle,
    text_style: TextStyle,
) -> None:
    """CAD-ZONING-P1: Invalid zoning parameters fail before geometry generation."""
    invalid_kwargs = [
        {"margins": "5"},
        {"margins": -0.1},
        {"horizontal_zones": 9},
        {"vertical_zones": 0},
        {"first_horizontal_char": 60},
        {"unknown": 1},
    ]

    for kwargs in invalid_kwargs:
        error_type = KeyError if "unknown" in kwargs else ValueError
        with pytest.raises(error_type):
            Zoning(canvas, line_style, text_style, **kwargs)


@pytest.mark.condition("CAD-ZONING-FINITE-P2")
@pytest.mark.parametrize(
    "kwargs",
    [
        {"margins": True},
        {"left_margin": False},
        {"top_margin": -0.5},
        {"zone_width": math.nan},
        {"right_zone_width": math.inf},
        {"bottom_zone_width": -math.inf},
        {"inner_radius": math.nan},
        {"outer_radius": math.inf},
        {"horizontal_zones": True},
        {"vertical_zones": False},
        {"horizontal_zones": -2},
        {"vertical_zones": -4},
        {"first_horizontal_char": object()},
        {"first_vertical_char": 64},
        {"first_horizontal_char": True},
        {"first_vertical_char": False},
    ],
)
def test_legacy_zoning_rejects_bool_and_nonfinite_parameters(
    canvas: Canvas,
    line_style: DrawingStyle,
    text_style: TextStyle,
    kwargs: dict[str, object],
) -> None:
    """CAD-ZONING-FINITE-P2: Zoning rejects bool and non-finite numeric overrides."""
    with pytest.raises(ValueError):
        Zoning(canvas, line_style, text_style, **kwargs)


@pytest.mark.condition("CAD-ZONING-FINITE-P2")
@pytest.mark.parametrize(
    "kwargs",
    [
        {"margins": True},
        {"left_margin": False},
        {"top_margin": -0.5},
        {"zone_width": math.nan},
        {"right_zone_width": math.inf},
        {"bottom_zone_width": -math.inf},
        {"inner_radius": math.nan},
        {"outer_radius": math.inf},
    ],
)
def test_legacy_zoning_rejects_malformed_positive_reals_at_boundary(
    canvas: Canvas,
    line_style: DrawingStyle,
    text_style: TextStyle,
    kwargs: dict[str, object],
) -> None:
    """CAD-ZONING-FINITE-P2: Positive-real failures occur at the zoning boundary."""
    with pytest.raises(ValueError, match="finite positive floating point number or integer"):
        Zoning(canvas, line_style, text_style, **kwargs)


@pytest.mark.condition("CAD-ZONING-FINITE-P2")
def test_legacy_zoning_accepts_finite_boundary_parameters(
    canvas: Canvas,
    line_style: DrawingStyle,
    text_style: TextStyle,
) -> None:
    """CAD-ZONING-FINITE-P2: Valid finite boundary values remain accepted."""
    zoning = Zoning(
        canvas,
        line_style,
        text_style,
        margins=0.0,
        zone_width=0.0,
        inner_radius=0.0,
        outer_radius=0.0,
        horizontal_zones=2,
        vertical_zones=2,
        first_horizontal_char=48,
        first_vertical_char=65,
    )

    assert zoning._parameters["left_margin"] == 0.0
    assert zoning._parameters["left_zone_width"] == 0.0
    assert zoning._parameters["horizontal_zones"] == 2
    assert zoning._parameters["vertical_zones"] == 2
    assert zoning._parameters["first_horizontal_char"] == 48
    assert zoning._parameters["first_vertical_char"] == 65


@pytest.mark.condition("CAD-ZONING-P1")
def test_legacy_zoning_round_trips_parameters_with_style_registry(
    canvas: Canvas,
    line_style: DrawingStyle,
    text_style: TextStyle,
) -> None:
    """CAD-ZONING-P1: Legacy zoning serialization preserves inputs and SVG geometry."""
    zoning = Zoning(canvas, line_style, text_style, margins=5.0, horizontal_zones=10, vertical_zones=8)
    recreated = Zoning.create_from_dict(
        zoning.parameters,
        {line_style.name: line_style, text_style.name: text_style},
    )

    assert recreated.parameters == zoning.parameters
    assert [component.parameters for component in recreated.component_group.components()] == [
        component.parameters for component in zoning.component_group.components()
    ]
    assert len(list(recreated.component_group.components())) == len(list(zoning.component_group.components()))


@pytest.mark.condition("CAD-ZONING-P1")
def test_legacy_zoning_default_width_tracks_text_outline(
    canvas: Canvas,
    line_style: DrawingStyle,
    text_style: TextStyle,
) -> None:
    """CAD-ZONING-P1: Default zone widths derive from the widest A/W/Y text outline."""
    zoning = Zoning(canvas, line_style, text_style)
    widths = []
    probe = TextComponent("_", (0.0, 0.0), text_style)
    for character in ("A", "W", "Y"):
        probe.text = character
        widths.append(probe.bbox[1][0] - probe.bbox[0][0])

    expected = pytest.approx(max(widths) + 4.0)
    assert zoning._parameters["left_zone_width"] == expected
    assert zoning._parameters["right_zone_width"] == expected
    assert zoning._parameters["top_zone_width"] == expected
    assert zoning._parameters["bottom_zone_width"] == expected
