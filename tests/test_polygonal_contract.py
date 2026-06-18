"""Behavioral tests for the irregular polygon renderer contract."""

from __future__ import annotations

import uuid

import pytest

import InkGen.component as component_module
from InkGen.drawing_components import DrawingComponentGroup, OutputFormat, PolygonalDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.errors import InvalidPolygonError
from InkGen.pdf_generator import PolygonalPDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import PolygonalSVG


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a unique visible drawing style."""
    return DrawingStyle(name=f"polygon_{uuid.uuid4().hex}", stroke="#000000", stroke_width=0.2, fill="none")


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


@pytest.mark.condition("POLYGON-P1")
def test_polygonal_component_preserves_valid_irregular_geometry(drawing_style: DrawingStyle) -> None:
    """POLYGON-P1: Valid irregular polygons preserve point order and geometry."""
    points = [(1.0, 1.0), (5.0, 1.0), (4.0, 3.0), (2.0, 4.0), (0.5, 2.0)]
    polygon = PolygonalSVG(points, drawing_style)

    assert polygon.points == points
    assert polygon.bbox == ((0.5, 1.0), (5.0, 4.0))
    assert polygon.polygon.area == pytest.approx(8.75)
    assert set(polygon.convex_hull) == {(0.5, 2.0), (1.0, 1.0), (5.0, 1.0), (4.0, 3.0), (2.0, 4.0)}


@pytest.mark.condition("POLYGON-P1")
def test_polygonal_component_rejects_invalid_inputs(drawing_style: DrawingStyle) -> None:
    """POLYGON-P1: Invalid polygon inputs fail at the component boundary."""
    invalid_values = [
        [(0.0, 0.0), (1.0, 1.0)],
        [(0.0, 0.0), (1.0, 1.0), (2.0,)],
        [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0, 3.0)],
        [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0, 99.0)],
        [(0.0, 0.0), (1.0, 1.0), ("x", 2.0)],
        [(0.0, 0.0), (1.0, 1.0), (float("nan"), 2.0)],
        [(0.0, 0.0), (1.0, 1.0), (2.0, float("nan"))],
        [(0.0, 0.0), (1.0, 1.0), (float("inf"), 2.0)],
        [(0.0, 0.0), (1.0, 1.0), (2.0, float("inf"))],
        [(0.0, 0.0), (1.0, 1.0), (True, 2.0)],
        [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)],
        [(0.0, 0.0), (2.0, 2.0), (0.0, 2.0), (2.0, 0.0)],
        "not-points",
    ]

    for points in invalid_values:
        with pytest.raises(InvalidPolygonError):
            PolygonalSVG(points, drawing_style)

    polygon = PolygonalSVG([(0.0, 0.0), (2.0, 0.0), (1.0, 2.0)], drawing_style)
    assert polygon._polygon_check([(0.0, 0.0), (2.0, 0.0), (1.0, 2.0)]) is True
    assert polygon._polygon_check([(0.0, 0.0), (1.0, 1.0)]) is False
    with pytest.raises(InvalidPolygonError):
        polygon.points = [(0.0, 0.0), (1.0, 1.0)]


@pytest.mark.condition("POLYGON-P1")
def test_polygonal_validation_rejects_before_shapely_for_nonfinite(monkeypatch: pytest.MonkeyPatch) -> None:
    """POLYGON-P1: Non-finite coordinates are rejected before Shapely construction."""

    def fail_polygon(_points):
        raise AssertionError("Polygon should not be constructed for non-finite coordinates")

    monkeypatch.setattr(component_module, "Polygon", fail_polygon)
    checker = object.__new__(PolygonalSVG)

    assert checker._create_valid_polygon([(0.0, 0.0), (1.0, 0.0), (float("nan"), 1.0)]) is None
    assert checker._create_valid_polygon([(0.0, 0.0), (1.0, 0.0), (1.0, float("inf"))]) is None


@pytest.mark.condition("POLYGON-P1")
def test_polygonal_validation_rejects_each_invalid_shapely_predicate(monkeypatch: pytest.MonkeyPatch) -> None:
    """POLYGON-P1: Empty, invalid, and zero-area Shapely polygons fail independently."""
    checker = object.__new__(PolygonalSVG)
    points = [(0.0, 0.0), (2.0, 0.0), (0.0, 0.5)]

    class FakePolygon:
        is_empty = False
        is_valid = True
        area = 0.5

        def __init__(self, _points):
            pass

    monkeypatch.setattr(component_module, "Polygon", FakePolygon)
    assert checker._create_valid_polygon(points) is not None

    FakePolygon.is_empty = True
    FakePolygon.is_valid = True
    FakePolygon.area = 0.5
    assert checker._create_valid_polygon(points) is None

    FakePolygon.is_empty = False
    FakePolygon.is_valid = False
    FakePolygon.area = 0.5
    assert checker._create_valid_polygon(points) is None

    FakePolygon.is_empty = False
    FakePolygon.is_valid = True
    FakePolygon.area = 0.0
    assert checker._create_valid_polygon(points) is None


@pytest.mark.condition("POLYGON-P1")
def test_polygonal_svg_emits_exact_closed_path(drawing_style: DrawingStyle) -> None:
    """POLYGON-P1: SVG polygon output preserves vertex order and closure."""
    polygon = PolygonalSVG([(1.0, 1.0), (5.0, 1.0), (4.0, 3.0), (2.0, 4.0)], drawing_style)

    assert (
        polygon.generate_svg()
        == f"""<path
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0;stroke-linecap:butt;stroke-linejoin:miter"
            d="M 1.0,1.0 5.0,1.0 4.0,3.0 2.0,4.0 Z"
            id="path{polygon.id}" />"""
    )


@pytest.mark.condition("POLYGON-P1")
def test_polygonal_pdf_emits_exact_closed_path(drawing_style: DrawingStyle) -> None:
    """POLYGON-P1: PDF polygon output preserves vertex order and closure."""
    polygon = PolygonalPDF([(1.0, 1.0), (5.0, 1.0), (4.0, 3.0), (2.0, 4.0)], drawing_style)

    assert polygon.generate_pdf() == "\n".join(
        [
            "q",
            "0 0 0 RG",
            "0.2 w",
            "1 1 m",
            "5 1 l",
            "4 3 l",
            "2 4 l",
            "h",
            "S",
            "Q",
        ]
    )


@pytest.mark.condition("POLYGON-P1")
def test_polygonal_primitives_round_trip_parameters(drawing_style: DrawingStyle) -> None:
    """POLYGON-P1: SVG and PDF polygon primitives preserve serialized parameters."""
    svg = PolygonalSVG([(1.0, 1.0), (5.0, 1.0), (4.0, 3.0)], drawing_style)
    pdf = PolygonalPDF([(1.0, 1.0), (5.0, 1.0), (4.0, 3.0)], drawing_style)

    assert PolygonalSVG.create_from_dict(svg.parameters, drawing_style).parameters == svg.parameters
    assert PolygonalPDF.create_from_dict(pdf.parameters, drawing_style).parameters == pdf.parameters


@pytest.mark.condition("POLYGON-P1")
def test_polygonal_drawing_materializes_svg_and_pdf_components(drawing_style: DrawingStyle) -> None:
    """POLYGON-P1: Neutral polygon recipes materialize to matching SVG/PDF polygons."""
    points = [(1.0, 1.0), (5.0, 1.0), (4.0, 3.0), (2.0, 4.0)]
    drawing = PolygonalDrawing(points, drawing_style)

    svg = drawing.to_component(OutputFormat.SVG)
    pdf = drawing.to_component(OutputFormat.PDF)

    assert isinstance(svg, PolygonalSVG)
    assert isinstance(pdf, PolygonalPDF)
    assert svg.points == points
    assert pdf.points == points


@pytest.mark.condition("POLYGON-P1")
def test_dxf_polygonal_drawing_exports_closed_polyline(drawing_style: DrawingStyle) -> None:
    """POLYGON-P1: DXF exports neutral polygon drawings as closed polylines."""
    points = [(1.0, 1.0), (5.0, 1.0), (4.0, 3.0), (2.0, 4.0)]
    document = DXFDocument()
    document.add_group(DrawingComponentGroup("polygons", [PolygonalDrawing(points, drawing_style)]))
    payload = document.to_dxf_string()

    assert "\nLWPOLYLINE\n" in payload
    assert "\n8\npolygons\n" in payload
    assert "\n90\n4\n" in payload
    assert "\n70\n1\n" in payload
    assert _dxf_polyline_vertices(payload) == points
