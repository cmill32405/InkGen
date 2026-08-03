"""Condition tests for canonical rounded regular-polygon rendering."""

from __future__ import annotations

import math
import re
from uuid import uuid4

import pytest
from PIL import Image

import InkGen.dxf_generator as dxf_module
import InkGen.pdf_generator as pdf_module
import InkGen.raster_renderer as raster_module
import InkGen.svg_generator as svg_module
from InkGen.baird import BairdParams
from InkGen.boundary import Canvas
from InkGen.component import RoundedPolygonCorner, regular_polygon_corner_geometry, sample_rounded_polygon_path
from InkGen.drawing_components import DrawingComponentGroup, RegularPolygonDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import RegularPolygonPDF, _rounded_polygon_path
from InkGen.raster_renderer import render_and_degrade_drawing_group, render_drawing_group
from InkGen.style import DrawingStyle
from InkGen.svg_generator import RegularPolygonSVG


def _style(*, fill: str = "none", stroke: str = "#000000", stroke_width: float = 0.2) -> DrawingStyle:
    return DrawingStyle(
        name=f"rounded_regular_polygon_{uuid4().hex}",
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
    )


def _vertices(sides: int, radius: float = 10.0, angle: float = 0.0) -> list[tuple[float, float]]:
    return [
        (
            radius * math.cos(math.radians(angle + 90.0 + index * 360.0 / sides)),
            radius * math.sin(math.radians(angle + 90.0 + index * 360.0 / sides)),
        )
        for index in range(sides)
    ]


def _dxf_polyline_vertices(payload: str) -> list[tuple[float, float]]:
    lines = payload.splitlines()
    polyline_start = lines.index("LWPOLYLINE")
    count_index = lines.index("90", polyline_start)
    expected_count = int(lines[count_index + 1])
    vertices: list[tuple[float, float]] = []
    index = count_index + 2
    while index < len(lines) - 3 and len(vertices) < expected_count:
        if lines[index] == "10" and lines[index + 2] == "20":
            vertices.append((float(lines[index + 1]), float(lines[index + 3])))
            index += 4
        else:
            index += 1
    return vertices


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
@pytest.mark.parametrize("sides", [3, 4, 5, 8, 17])
def test_corner_geometry_is_circular_tangent_and_nonoverlapping(sides: int) -> None:
    """P9: Every corner is tangent to both edges and has the requested radius."""
    radius = 10.0
    corner_radius = radius / 2.0
    points = _vertices(sides, radius, angle=13.0)
    corners = regular_polygon_corner_geometry(points, corner_radius)

    assert len(corners) == sides
    assert all(corner.sweep_radians == pytest.approx(math.tau / sides) for corner in corners)
    for index, corner in enumerate(corners):
        vertex = points[index]
        previous = points[index - 1]
        following = points[(index + 1) % sides]
        incoming = (vertex[0] - previous[0], vertex[1] - previous[1])
        outgoing = (following[0] - vertex[0], following[1] - vertex[1])
        entry_radius = (corner.entry[0] - corner.center[0], corner.entry[1] - corner.center[1])
        exit_radius = (corner.exit[0] - corner.center[0], corner.exit[1] - corner.center[1])

        assert math.hypot(*entry_radius) == pytest.approx(corner_radius)
        assert math.hypot(*exit_radius) == pytest.approx(corner_radius)
        assert entry_radius[0] * incoming[0] + entry_radius[1] * incoming[1] == pytest.approx(0.0, abs=1e-10)
        assert exit_radius[0] * outgoing[0] + exit_radius[1] * outgoing[1] == pytest.approx(0.0, abs=1e-10)
        assert math.dist(corner.exit, corners[(index + 1) % sides].entry) >= -1e-12

    reversed_corners = regular_polygon_corner_geometry(list(reversed(points)), corner_radius)
    assert all(corner.sweep_radians == pytest.approx(-math.tau / sides) for corner in reversed_corners)


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_corner_geometry_and_sampling_reject_malformed_domains() -> None:
    """P9: Shared geometry rejects malformed radii, points, overlap, and arc steps."""
    square = _vertices(4)
    for value, error in [
        (True, TypeError),
        ("1", TypeError),
        (0.0, ValueError),
        (-1.0, ValueError),
        (float("nan"), ValueError),
        (float("inf"), ValueError),
    ]:
        with pytest.raises(error):
            regular_polygon_corner_geometry(square, value)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="at least three"):
        regular_polygon_corner_geometry(square[:2], 1.0)
    with pytest.raises(ValueError, match="overlap"):
        regular_polygon_corner_geometry(square, 8.0)
    with pytest.raises(ValueError, match="nonzero area"):
        regular_polygon_corner_geometry([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)], 0.1)

    corners = regular_polygon_corner_geometry(square, 1.0)
    with pytest.raises(ValueError, match="at least one"):
        sample_rounded_polygon_path([])
    for value, error in [
        (True, TypeError),
        ("1", TypeError),
        (-0.1, ValueError),
        (0.0, ValueError),
        (math.pi, ValueError),
        (math.tau, ValueError),
        (float("nan"), ValueError),
        (float("inf"), ValueError),
    ]:
        with pytest.raises(error):
            sample_rounded_polygon_path(corners, value)  # type: ignore[arg-type]


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
@pytest.mark.parametrize(
    ("points", "error", "message"),
    [
        ([(0.0, 0.0), (1.0, 0.0), object()], TypeError, "coordinate pairs"),
        ([(0.0, 0.0), (1.0,), (0.0, 1.0)], TypeError, "coordinate pairs"),
        ([(0.0, 0.0), (1.0, 0.0, 2.0), (0.0, 1.0)], TypeError, "coordinate pairs"),
        ([(False, 0.0), (1.0, 0.0), (0.0, 1.0)], TypeError, "numeric"),
        ([(0.0, 0.0), (1.0, "0"), (0.0, 1.0)], TypeError, "numeric"),
        ([(float("inf"), 0.0), (1.0, 0.0), (0.0, 1.0)], ValueError, "finite"),
        ([(0.0, float("-inf")), (1.0, 0.0), (0.0, 1.0)], ValueError, "finite"),
        ([(1e308, 1e308), (-1e308, 1e308), (-1e308, -1e308), (1e308, -1e308)], ValueError, "nonzero area"),
        ([(0.0, 0.0), (0.0, 0.0), (1.0, 0.0), (0.0, 1.0)], ValueError, "positive length"),
        ([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.0, 0.0)], ValueError, "positive length"),
        ([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (2.0, 1.0), (2.0, 0.0)], ValueError, "convex corners"),
        ([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)], ValueError, "convex corners"),
        (
            [
                (0.0, 0.0),
                (0.927608825462488, 0.6735717093285103),
                (0.0, 2.0),
                (-0.927608825462488, -0.6735717093285103),
            ],
            ValueError,
            "convex corners",
        ),
        (
            [
                (0.0, 0.0),
                (-1.855217650924976, -1.3471434186570206),
                (0.0, 2.0),
                (-0.927608825462488, -0.6735717093285103),
            ],
            ValueError,
            "convex corners",
        ),
        ([(0.0, 0.0), (2.0, 0.0), (1.0, 1.0), (2.0, 2.0), (0.0, 2.0)], ValueError, "sweep"),
    ],
)
def test_corner_geometry_rejects_each_malformed_point_partition(
    points: object,
    error: type[Exception],
    message: str,
) -> None:
    """P9: Point validation distinguishes every malformed geometry partition."""
    with pytest.raises(error, match=message):
        regular_polygon_corner_geometry(points, 0.1)  # type: ignore[arg-type]


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_small_orientations_and_exact_overlap_boundary_preserve_geometry() -> None:
    """P9: Orientation is sign-based and an exact tangent midpoint is allowed."""
    square = [(0.0, 2.0), (0.0, 0.0), (2.0, 0.0), (2.0, 2.0)]
    boundary = regular_polygon_corner_geometry(square, 1.0)
    assert all(corner.sweep_radians == pytest.approx(math.pi / 2.0) for corner in boundary)

    tiny = [(x * 0.1, y * 0.1) for x, y in square]
    forward = regular_polygon_corner_geometry(tiny, 0.02)
    reverse = regular_polygon_corner_geometry(list(reversed(tiny)), 0.02)
    assert all(corner.sweep_radians > 0.0 for corner in forward)
    assert all(corner.sweep_radians < 0.0 for corner in reverse)


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_sampled_outline_has_bounded_steps_and_exact_corner_endpoints() -> None:
    """P9: Sampling includes tangent endpoints and never exceeds 22.5 degrees."""
    corners = regular_polygon_corner_geometry(_vertices(4), 2.0)
    sampled = sample_rounded_polygon_path(corners)

    assert len(sampled) == 20
    for index, corner in enumerate(corners):
        offset = index * 5
        assert sampled[offset] == pytest.approx(corner.entry)
        assert sampled[offset + 4] == pytest.approx(corner.exit)
        for point in sampled[offset : offset + 5]:
            assert math.dist(point, corner.center) == pytest.approx(2.0)

    triangle = regular_polygon_corner_geometry(_vertices(3), 2.0)
    assert len(sample_rounded_polygon_path(triangle)) == 21

    tiny_sweep = (
        RoundedPolygonCorner(
            (1.0, 0.0),
            (math.cos(1e-15), math.sin(1e-15)),
            (0.0, 0.0),
            1e-15,
        ),
    )
    assert len(sample_rounded_polygon_path(tiny_sweep)) == 2


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_axis_aligned_square_has_exact_canonical_corner_records_and_samples() -> None:
    """P9: A fixed square witnesses every shared geometry coordinate and sweep."""
    points = [(9.0, 11.0), (9.0, 9.0), (11.0, 9.0), (11.0, 11.0)]
    corners = regular_polygon_corner_geometry(points, 0.5)
    expected = [
        ((9.5, 11.0), (9.0, 10.5), (9.5, 10.5)),
        ((9.0, 9.5), (9.5, 9.0), (9.5, 9.5)),
        ((10.5, 9.0), (11.0, 9.5), (10.5, 9.5)),
        ((11.0, 10.5), (10.5, 11.0), (10.5, 10.5)),
    ]

    for corner, (entry, exit_point, center) in zip(corners, expected, strict=True):
        assert corner.entry == pytest.approx(entry)
        assert corner.exit == pytest.approx(exit_point)
        assert corner.center == pytest.approx(center)
        assert corner.sweep_radians == pytest.approx(math.pi / 2.0)

    assert sample_rounded_polygon_path(corners, math.pi / 2.0) == pytest.approx(
        [
            (9.5, 11.0),
            (9.0, 10.5),
            (9.0, 9.5),
            (9.5, 9.0),
            (10.5, 9.0),
            (11.0, 9.5),
            (11.0, 10.5),
            (10.5, 11.0),
        ]
    )


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_svg_path_and_pdf_cubics_match_fixed_tangent_geometry() -> None:
    """P9: Serialized arc endpoints and PDF tangent controls are exact witnesses."""
    style = _style()
    svg = RegularPolygonSVG((10.0, 10.0), 4, math.sqrt(2.0), style, angle=45.0, corner_radius=0.5).generate_svg()
    path_data = re.search(r'd="([^"]+)"', svg)
    assert path_data is not None
    assert path_data.group(1) == (
        "M 9.5,11 A 0.5,0.5 0 0 1 9,10.5 L 9,9.5 A 0.5,0.5 0 0 1 9.5,9 L 10.5,9 A 0.5,0.5 0 0 1 11,9.5 L 11,10.5 A 0.5,0.5 0 0 1 10.5,11 Z"
    )

    corners = (
        RoundedPolygonCorner((0.0, 1.0), (1.0, 0.0), (1.0, 1.0), math.pi / 2.0),
        RoundedPolygonCorner((3.0, 0.0), (4.0, 1.0), (3.0, 1.0), math.pi / 2.0),
        RoundedPolygonCorner((4.0, 3.0), (3.0, 4.0), (3.0, 3.0), math.pi / 2.0),
        RoundedPolygonCorner((1.0, 4.0), (0.0, 3.0), (1.0, 3.0), math.pi / 2.0),
    )
    assert _rounded_polygon_path(corners) == [
        "0 1 m",
        "0 0.447715 0.447715 0 1 0 c",
        "3 0 l",
        "3.552285 0 4 0.447715 4 1 c",
        "4 3 l",
        "4 3.552285 3.552285 4 3 4 c",
        "1 4 l",
        "0.447715 4 0 3.552285 0 3 c",
        "h",
    ]
    clockwise = (RoundedPolygonCorner((1.0, 0.0), (0.0, 1.0), (1.0, 1.0), -math.pi / 2.0),)
    assert _rounded_polygon_path(clockwise) == [
        "1 0 m",
        "0.447715 0 0 0.447715 0 1 c",
        "h",
    ]

    root_three = math.sqrt(3.0)
    rotated = (
        RoundedPolygonCorner(
            (2.0 + root_three, 4.0),
            (3.0, 3.0 - root_three),
            (2.0, 3.0),
            -math.pi / 2.0,
        ),
    )
    controls = [float(value) for value in _rounded_polygon_path(rotated)[1].removesuffix(" c").split()]
    control_distance = 2.0 * (4.0 / 3.0) * math.tan(math.pi / 8.0)
    assert controls == pytest.approx(
        [
            2.0 + root_three + 0.5 * control_distance,
            4.0 - root_three * control_distance / 2.0,
            3.0 + root_three * control_distance / 2.0,
            3.0 - root_three + 0.5 * control_distance,
            3.0,
            3.0 - root_three,
        ],
        abs=1e-6,
    )

    for sweep in (0.5, -0.5):
        small_sweep = (
            RoundedPolygonCorner(
                (2.0, 0.0),
                (2.0 * math.cos(sweep), 2.0 * math.sin(sweep)),
                (0.0, 0.0),
                sweep,
            ),
        )
        small_controls = [float(value) for value in _rounded_polygon_path(small_sweep)[1].removesuffix(" c").split()]
        small_distance = 2.0 * (4.0 / 3.0) * math.tan(abs(sweep) / 4.0)
        assert small_controls[0] == pytest.approx(2.0)
        assert small_controls[1] == pytest.approx(math.copysign(small_distance, sweep), abs=1e-6)


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_svg_and_pdf_emit_closed_rounded_paths_while_sharp_paths_stay_linear() -> None:
    """P9: SVG uses circular arcs and PDF uses tangent cubic arc segments."""
    style = _style()
    rounded_svg = RegularPolygonSVG((10.0, 10.0), 5, 8.0, style, angle=11.0, corner_radius=2.0).generate_svg()
    sharp_svg = RegularPolygonSVG((10.0, 10.0), 5, 8.0, style, angle=11.0).generate_svg()
    rounded_pdf = RegularPolygonPDF((10.0, 10.0), 5, 8.0, style, angle=11.0, corner_radius=2.0).generate_pdf()
    sharp_pdf = RegularPolygonPDF((10.0, 10.0), 5, 8.0, style, angle=11.0).generate_pdf()

    assert rounded_svg.count(" A ") == 5
    assert rounded_svg.count(" L ") == 4
    assert " A " not in sharp_svg
    assert rounded_pdf.count(" c\n") == 5
    assert rounded_pdf.count(" l\n") == 4
    assert " c\n" not in sharp_pdf
    assert "\nh\n" in rounded_pdf
    sharp_path_data = re.search(r'd="([^"]+)"', RegularPolygonSVG((10.0, 10.0), 4, math.sqrt(2.0), style, angle=45.0).generate_svg())
    assert sharp_path_data is not None
    assert sharp_path_data.group(1) == "M 9.0, 11.0 9.0, 9.0 11.0, 9.0 11.0, 11.0  Z"


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_high_cardinality_polygon_closes_without_identity_based_indexing() -> None:
    """P9: Corner joining remains numeric when side counts exceed cached integers."""
    style = _style()
    rounded_svg = RegularPolygonSVG((10.0, 10.0), 300, 8.0, style, corner_radius=0.5).generate_svg()
    rounded_pdf = RegularPolygonPDF((10.0, 10.0), 300, 8.0, style, corner_radius=0.5).generate_pdf()
    assert rounded_svg.count(" A ") == 300
    assert rounded_svg.count(" L ") == 299
    assert rounded_pdf.count(" c\n") == 300
    assert rounded_pdf.count(" l\n") == 299


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_sharp_backends_bypass_rounded_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    """P9: Radius zero preserves every established sharp backend path."""
    style = _style(fill="#225588")
    polygon = RegularPolygonDrawing((5.0, 5.0), 4, 3.0, style)

    def unexpected(*args: object, **kwargs: object) -> object:
        raise AssertionError("sharp polygon must not construct rounded geometry")

    monkeypatch.setattr(svg_module, "regular_polygon_corner_geometry", unexpected)
    monkeypatch.setattr(pdf_module, "regular_polygon_corner_geometry", unexpected)
    assert " A " not in RegularPolygonSVG((5.0, 5.0), 4, 3.0, style).generate_svg()
    assert " c\n" not in RegularPolygonPDF((5.0, 5.0), 4, 3.0, style).generate_pdf()

    group = DrawingComponentGroup("sharp_polygon")
    group.add_component(polygon)
    monkeypatch.setattr(dxf_module, "regular_polygon_corner_geometry", unexpected)
    document = DXFDocument()
    document.add_group(group)
    assert "LWPOLYLINE" in document.to_dxf_string()
    monkeypatch.setattr(raster_module, "regular_polygon_corner_geometry", unexpected)
    assert render_drawing_group(group, Canvas(10.0, 10.0), dpi=25.4).asset.width == 10


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_subunit_radius_dispatches_rounded_dxf_and_raster_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    """P9: Any positive radius, including values below one, selects rounding."""
    polygon = RegularPolygonDrawing((5.0, 5.0), 4, 3.0, _style(fill="#225588"), corner_radius=0.5)
    group = DrawingComponentGroup("subunit_rounded_polygon")
    group.add_component(polygon)
    calls: list[str] = []

    dxf_geometry = dxf_module.regular_polygon_corner_geometry
    raster_geometry = raster_module.regular_polygon_corner_geometry

    def capture_dxf(*args: object, **kwargs: object) -> object:
        calls.append("dxf")
        return dxf_geometry(*args, **kwargs)  # type: ignore[arg-type]

    def capture_raster(*args: object, **kwargs: object) -> object:
        calls.append("raster")
        return raster_geometry(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(dxf_module, "regular_polygon_corner_geometry", capture_dxf)
    document = DXFDocument()
    document.add_group(group)
    document.to_dxf_string()
    monkeypatch.setattr(raster_module, "regular_polygon_corner_geometry", capture_raster)
    render_drawing_group(group, Canvas(10.0, 10.0), dpi=25.4)
    assert calls.count("dxf") == 1
    assert calls.count("raster") == 2


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_dxf_and_raster_share_the_canonical_sampled_outline(monkeypatch: pytest.MonkeyPatch) -> None:
    """P9: DXF and raster consume the same bounded shared sample points."""
    style = _style(fill="#225588", stroke="#000000", stroke_width=0.5)
    polygon = RegularPolygonDrawing((12.0, 12.0), 4, 8.0, style, angle=0.0, corner_radius=2.0)
    points = _vertices(4, 8.0)
    points = [(x + 12.0, y + 12.0) for x, y in points]
    expected = sample_rounded_polygon_path(regular_polygon_corner_geometry(points, 2.0))

    group = DrawingComponentGroup("rounded_polygon")
    group.add_component(polygon)
    document = DXFDocument()
    document.add_group(group)
    actual_dxf = _dxf_polyline_vertices(document.to_dxf_string())
    assert len(actual_dxf) == len(expected)
    for actual, wanted in zip(actual_dxf, expected, strict=True):
        assert actual == pytest.approx(wanted, abs=1e-6)

    captured: list[tuple[float, float]] = []
    original = raster_module._draw_polygon

    def capture(*args: object, **kwargs: object) -> None:
        captured.extend(args[1])  # type: ignore[arg-type]
        original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(raster_module, "_draw_polygon", capture)
    result = render_drawing_group(group, Canvas(24.0, 24.0), dpi=25.4, supersample=2)
    assert captured == pytest.approx(expected)
    with result.asset.image() as image:
        assert image.getpixel((12, 12))[3] > 0
        assert image.getpixel((12, 20))[3] == 0


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_public_rounded_polygon_clean_to_baird_path() -> None:
    """P9: Rounded polygon RGBA output feeds the standalone Baird pipeline."""
    group = DrawingComponentGroup("rounded_polygon_baird")
    group.add_component(RegularPolygonDrawing((12.0, 12.0), 5, 8.0, _style(fill="#225588"), corner_radius=2.0))

    result = render_and_degrade_drawing_group(
        group,
        Canvas(24.0, 24.0),
        BairdParams(blur=0.2, binarize=False, sensitivity=0.03, jitter=0.0),
        seed=17,
        background_rgb=(255, 255, 255),
        dpi=25.4,
        render_supersample=2,
    )

    assert result.clean.asset.width == result.degraded.asset.width == 24
    assert result.clean.asset.height == result.degraded.asset.height == 24
    assert result.clean.asset.mode == "RGBA"


@pytest.mark.condition("RASTER-ROUNDED-POLYGON-P9")
def test_live_corner_mutation_fails_before_raster_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """P9: Renderer revalidation rejects hostile live mutation before allocation."""
    polygon = RegularPolygonDrawing((5.0, 5.0), 4, 4.0, _style(fill="#000000"), corner_radius=1.0)
    object.__setattr__(polygon, "corner_radius", 3.0)
    group = DrawingComponentGroup("mutated_rounded_polygon")
    group.add_component(polygon)
    allocations: list[object] = []

    monkeypatch.setattr(Image, "new", lambda *args, **kwargs: allocations.append((args, kwargs)))
    with pytest.raises(ValueError, match="half the radius"):
        render_drawing_group(group, Canvas(10.0, 10.0), dpi=25.4)
    assert allocations == []
