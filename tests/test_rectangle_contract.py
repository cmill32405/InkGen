"""Behavioral tests for the rectangle renderer contract."""

from __future__ import annotations

import uuid

import pytest

from InkGen.drawing_components import DrawingComponentGroup, OutputFormat, RectangleDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import RectanglePDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import RectangleSVG


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a unique visible drawing style."""
    return DrawingStyle(name=f"rect_{uuid.uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


def _dxf_polyline_vertices(payload: str) -> list[tuple[float, float]]:
    lines = payload.splitlines()
    vertices: list[tuple[float, float]] = []
    index = 0
    while index < len(lines) - 1:
        if lines[index] == "10":
            vertices.append((float(lines[index + 1]), float(lines[index + 3])))
            index += 4
        else:
            index += 1
    return vertices


@pytest.mark.condition("RECT-P1")
def test_rectangle_svg_validates_corner_radii_boundaries(drawing_style: DrawingStyle) -> None:
    """RECT-P1: Rectangle radii are bounded by half the rectangle dimensions."""
    rect = RectangleSVG((10.0, 20.0), 40.0, 20.0, 5.0, drawing_style)
    assert rect.corner_radii == 5.0

    rect.corner_radii = (20.0, 10.0)
    assert rect.corner_radii == (20.0, 10.0)
    RectangleSVG((10.0, 20.0), 5.0, 5.0, (2.25, 2.25), drawing_style)

    invalid_values = [
        -0.1,
        (-0.1, 1.0),
        (1.0, -0.1),
        (20.1, 10.0),
        (20.0, 10.1),
        float("inf"),
        float("nan"),
    ]
    for value in invalid_values:
        with pytest.raises(ValueError):
            RectangleSVG((10.0, 20.0), 40.0, 20.0, value, drawing_style)

    for value in ((float("nan"), 1.0), (1.0, float("inf"))):
        with pytest.raises(ValueError):
            RectangleSVG((10.0, 20.0), 40.0, 20.0, value, drawing_style)

    for value in ((2.6, 1.0), (1.0, 3.1)):
        with pytest.raises(ValueError):
            RectangleSVG((10.0, 20.0), 5.0, 6.0, value, drawing_style)

    for value in ({"rx": 1.0}, (1.0,), (1.0, 2.0, 3.0), ("1", 2.0), True):
        with pytest.raises(TypeError):
            RectangleSVG((10.0, 20.0), 40.0, 20.0, value, drawing_style)


@pytest.mark.condition("RECT-P1")
def test_rectangle_svg_emits_corner_radius_attributes(drawing_style: DrawingStyle) -> None:
    """RECT-P1: SVG rectangles preserve nonzero corner radii in markup."""
    rounded = RectangleSVG((10.0, 20.0), 40.0, 20.0, (6.0, 4.0), drawing_style).generate_svg()
    horizontal_zero = RectangleSVG((10.0, 20.0), 40.0, 20.0, (0.0, 4.0), drawing_style).generate_svg()
    vertical_zero = RectangleSVG((10.0, 20.0), 40.0, 20.0, (4.0, 0.0), drawing_style).generate_svg()
    sharp = RectangleSVG((10.0, 20.0), 40.0, 20.0, 0.0, drawing_style).generate_svg()

    assert 'rx="6.0"' in rounded
    assert 'ry="4.0"' in rounded
    assert 'width="40.0"' in rounded
    assert 'height="20.0"' in rounded
    assert 'x="10.0"' in rounded
    assert 'y="20.0"' in rounded
    assert 'rx="0.0"' in horizontal_zero
    assert 'ry="4.0"' in horizontal_zero
    assert 'rx="4.0"' in vertical_zero
    assert 'ry="0.0"' in vertical_zero
    assert 'rx="' not in sharp
    assert 'ry="' not in sharp


@pytest.mark.condition("RECT-P1")
def test_rectangle_pdf_emits_sharp_rectangle_operator_for_zero_radius(drawing_style: DrawingStyle) -> None:
    """RECT-P1: Zero-radius PDF rectangles keep the compact rectangle operator."""
    content = RectanglePDF((10.0, 20.0), 40.0, 30.0, 0.0, drawing_style).generate_pdf()

    assert "10 20 40 30 re" in content
    assert " c" not in content


@pytest.mark.condition("RECT-P1")
def test_rectangle_pdf_emits_rounded_corner_cubic_path(drawing_style: DrawingStyle) -> None:
    """RECT-P1: Nonzero PDF rectangle radii render as cubic corner arcs."""
    content = RectanglePDF((10.0, 20.0), 40.0, 30.0, (5.0, 3.0), drawing_style).generate_pdf()

    assert content == "\n".join(
        [
            "q",
            "0 0 0 RG",
            "0.2 w",
            "15 20 m",
            "45 20 l",
            "47.761424 20 50 21.343146 50 23 c",
            "50 47 l",
            "50 48.656854 47.761424 50 45 50 c",
            "15 50 l",
            "12.238576 50 10 48.656854 10 47 c",
            "10 23 l",
            "10 21.343146 12.238576 20 15 20 c",
            "h",
            "S",
            "Q",
        ]
    )


@pytest.mark.condition("RECT-P1")
def test_rectangle_pdf_rounded_path_uses_asymmetric_fractional_geometry(drawing_style: DrawingStyle) -> None:
    """RECT-P1: Rounded PDF geometry is not hidden by symmetric integer cases."""
    content = RectanglePDF((7.5, 11.25), 22.5, 18.5, (4.5, 2.5), drawing_style).generate_pdf()

    assert "12 11.25 m" in content
    assert "25.5 11.25 l" in content
    assert "27.985281 11.25 30 12.369288 30 13.75 c" in content
    assert "30 27.25 l" in content
    assert "30 28.630712 27.985281 29.75 25.5 29.75 c" in content
    assert "9.514719 29.75 7.5 28.630712 7.5 27.25 c" in content
    assert "7.5 12.369288 9.514719 11.25 12 11.25 c" in content


@pytest.mark.condition("RECT-P1")
def test_rectangle_pdf_treats_one_zero_radius_as_sharp(drawing_style: DrawingStyle) -> None:
    """RECT-P1: A zero horizontal or vertical radius renders as a sharp rectangle."""
    horizontal_zero = RectanglePDF((10.0, 20.0), 40.0, 30.0, (0.0, 3.0), drawing_style).generate_pdf()
    vertical_zero = RectanglePDF((10.0, 20.0), 40.0, 30.0, (5.0, 0.0), drawing_style).generate_pdf()

    assert "10 20 40 30 re" in horizontal_zero
    assert " c" not in horizontal_zero
    assert "10 20 40 30 re" in vertical_zero
    assert " c" not in vertical_zero


@pytest.mark.condition("RECT-P1")
def test_rectangle_pdf_rejects_invalid_corner_radii(drawing_style: DrawingStyle) -> None:
    """RECT-P1: PDF rectangle validation matches the shared rectangle contract."""
    with pytest.raises(ValueError):
        RectanglePDF((10.0, 20.0), 40.0, 30.0, -1.0, drawing_style)
    with pytest.raises(ValueError):
        RectanglePDF((10.0, 20.0), 40.0, 30.0, (21.0, 3.0), drawing_style)
    with pytest.raises(TypeError):
        RectanglePDF((10.0, 20.0), 40.0, 30.0, {"rx": 1.0}, drawing_style)


@pytest.mark.condition("RECT-P1")
def test_rectangle_drawing_materializes_svg_and_pdf_components(drawing_style: DrawingStyle) -> None:
    """RECT-P1: Neutral rectangles pass corner radii into SVG and PDF renderers."""
    drawing = RectangleDrawing((10.0, 20.0), 40.0, 30.0, (5.0, 3.0), drawing_style)

    svg = drawing.to_component(OutputFormat.SVG)
    pdf = drawing.to_component(OutputFormat.PDF)

    assert isinstance(svg, RectangleSVG)
    assert isinstance(pdf, RectanglePDF)
    assert svg.corner_radii == (5.0, 3.0)
    assert pdf.corner_radii == (5.0, 3.0)


@pytest.mark.condition("RECT-P1")
def test_dxf_rectangle_drawing_exports_rounded_closed_polyline(drawing_style: DrawingStyle) -> None:
    """RECT-P1: DXF rectangles preserve rounded corners as sampled closed polylines."""
    drawing = RectangleDrawing((10.0, 20.0), 40.0, 30.0, (5.0, 3.0), drawing_style)

    document = DXFDocument()
    neutral_group = DrawingComponentGroup("rectangles", [drawing])
    document.add_group(neutral_group)
    payload = document.to_dxf_string()
    vertices = _dxf_polyline_vertices(payload)

    assert "\nLWPOLYLINE\n" in payload
    assert "\n70\n1\n" in payload
    assert "\n90\n20\n" in payload
    expected = [
        (15.0, 20.0),
        (45.0, 20.0),
        (46.913417, 20.228361),
        (48.535534, 20.87868),
        (49.619398, 21.851949),
        (50.0, 23.0),
        (50.0, 47.0),
        (49.619398, 48.148051),
        (48.535534, 49.12132),
        (46.913417, 49.771639),
        (45.0, 50.0),
        (15.0, 50.0),
        (13.086583, 49.771639),
        (11.464466, 49.12132),
        (10.380602, 48.148051),
        (10.0, 47.0),
        (10.0, 23.0),
        (10.380602, 21.851949),
        (11.464466, 20.87868),
        (13.086583, 20.228361),
    ]
    assert len(vertices) == len(expected)
    for actual, expected_point in zip(vertices, expected, strict=True):
        assert actual == pytest.approx(expected_point)


@pytest.mark.condition("RECT-P1")
def test_dxf_rectangle_drawing_treats_one_zero_radius_as_sharp(drawing_style: DrawingStyle) -> None:
    """RECT-P1: DXF keeps one-zero radius rectangles sharp."""
    for corner_radii in ((0.0, 3.0), (5.0, 0.0)):
        document = DXFDocument()
        document.add_group(DrawingComponentGroup("rectangles", [RectangleDrawing((10.0, 20.0), 40.0, 30.0, corner_radii, drawing_style)]))
        payload = document.to_dxf_string()
        assert "\n90\n4\n" in payload
        assert _dxf_polyline_vertices(payload) == [(10.0, 20.0), (50.0, 20.0), (50.0, 50.0), (10.0, 50.0)]


@pytest.mark.condition("RECT-P1")
def test_dxf_rectangle_drawing_exports_fractional_rounded_polyline(drawing_style: DrawingStyle) -> None:
    """RECT-P1: DXF rounded rectangle sampling handles fractional asymmetric geometry."""
    document = DXFDocument()
    drawing = RectangleDrawing((7.5, 11.25), 22.5, 18.5, (4.5, 2.5), drawing_style)
    document.add_group(DrawingComponentGroup("rectangles", [drawing]))
    vertices = _dxf_polyline_vertices(document.to_dxf_string())
    expected = [
        (12.0, 11.25),
        (25.5, 11.25),
        (27.222075, 11.440301),
        (28.681981, 11.982233),
        (29.657458, 12.793291),
        (30.0, 13.75),
        (30.0, 27.25),
        (29.657458, 28.206709),
        (28.681981, 29.017767),
        (27.222075, 29.559699),
        (25.5, 29.75),
        (12.0, 29.75),
        (10.277925, 29.559699),
        (8.818019, 29.017767),
        (7.842542, 28.206709),
        (7.5, 27.25),
        (7.5, 13.75),
        (7.842542, 12.793291),
        (8.818019, 11.982233),
        (10.277925, 11.440301),
    ]

    assert len(vertices) == len(expected)
    for actual, expected_point in zip(vertices, expected, strict=True):
        assert actual == pytest.approx(expected_point)
