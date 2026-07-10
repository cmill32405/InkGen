"""DXF renderer contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

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
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
)
from InkGen.dxf_generator import (
    DXFDocument,
    DXFRenderContext,
    _append_corner_arc,
    _circle_hatch_points,
    _component_to_entities,
    _format_value,
    _hatch_entity,
    _rectangle_points,
)
from InkGen.style import DrawingStyle, Font, TextStyle


def _drawing_style() -> DrawingStyle:
    return DrawingStyle(f"dxf_contract_{uuid4().hex}", stroke="#000000", fill="none")


def _text_style() -> TextStyle:
    return TextStyle(f"dxf_text_{uuid4().hex}", Font(size=9.0))


def _vertices(payload: str) -> list[tuple[float, float]]:
    lines = payload.splitlines()
    vertices: list[tuple[float, float]] = []
    index = 0
    while index < len(lines) - 1:
        if lines[index] == "10":
            x = float(lines[index + 1])
            assert lines[index + 2] == "20"
            y = float(lines[index + 3])
            vertices.append((x, y))
            index += 4
        else:
            index += 1
    return vertices


def _pair_values(payload: str, code: str) -> list[str]:
    """Return all values following a DXF group code in an artifact string."""
    lines = payload.splitlines()
    return [lines[index + 1] for index, line in enumerate(lines[:-1]) if line == code]


@pytest.mark.condition("DXF-P1")
def test_dxf_context_and_numeric_format_are_deterministic() -> None:
    """DXF-P1: Context coordinate conversion and value formatting stay deterministic."""
    default_context = DXFRenderContext()
    flipped_context = DXFRenderContext(canvas_height=100.0)

    assert default_context.point(2, 3) == (2.0, 3.0)
    assert flipped_context.point(2, 3) == (2.0, 97.0)
    assert _format_value(2.0) == "2"
    assert _format_value(2.000001) == "2.000001"
    assert _format_value(2.125000) == "2.125"
    assert _format_value("layer") == "layer"


@pytest.mark.condition("DXF-P1")
def test_dxf_context_rejects_malformed_coordinate_boundaries() -> None:
    """DXF-P1: Context coordinates and canvas heights must be finite non-boolean numbers."""
    context = DXFRenderContext(canvas_height=100.0)

    for value in [True, False, float("nan"), float("inf"), -float("inf"), "1", object()]:
        with pytest.raises((TypeError, ValueError)):
            DXFRenderContext(canvas_height=value)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            DXFDocument(canvas_height=value)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            context.point(value, 2.0)  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            context.point(1.0, value)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        DXFRenderContext(canvas_height=-0.1)
    with pytest.raises(ValueError):
        DXFDocument(canvas_height=-0.1)

    assert context.point(1.0, 2.0) == (1.0, 98.0)
    assert DXFRenderContext(canvas_height=0.0).point(1.0, 2.0) == (1.0, -2.0)
    assert DXFDocument(canvas_height=0.0).to_dxf_string().endswith("0\nEOF\n")


@pytest.mark.condition("DXF-P1")
def test_dxf_document_layers_and_ascii_text_contract() -> None:
    """DXF-P1: DXFDocument emits layer codes, flipped coordinates, and ASCII text."""
    style = _drawing_style()
    group = DrawingComponentGroup("source-layer")
    group.add_component(LineDrawing((1.0, 2.0), (3.0, 4.0), style))
    group.add_component(TextDrawing("ZONE\nA", (5.0, 6.0), _text_style()))
    document = DXFDocument(canvas_height=100.0)

    document.add_group(group, layer="override")
    payload = document.to_dxf_string()

    assert payload.count("\n8\noverride\n") == 2
    assert "\n10\n1\n20\n98\n" in payload
    assert "\n11\n3\n21\n96\n" in payload
    assert (
        _component_to_entities(TextDrawing("ZONE\nA", (5.0, 6.0), _text_style()), DXFRenderContext(canvas_height=100.0, layer="L"))[0]
        == "0\nTEXT\n8\nL\n10\n5\n20\n94\n30\n0\n40\n3.175\n1\nZONE A"
    )
    payload.encode("ascii")


@pytest.mark.condition("DXF-P1")
def test_dxf_document_layer_fallback_and_write_guard(tmp_path) -> None:
    """DXF-P1: DXFDocument uses layer fallbacks and rejects missing output directories."""
    style = _drawing_style()
    labeled = DrawingComponentGroup("source-layer")
    labeled.add_component(LineDrawing((0.0, 0.0), (1.0, 1.0), style))
    unlabeled = DrawingComponentGroup("")
    unlabeled.add_component(LineDrawing((2.0, 2.0), (3.0, 3.0), style))
    document = DXFDocument()

    document.add_group(labeled)
    document.add_group(unlabeled)
    payload = document.to_dxf_string()

    assert "\n8\nsource-layer\n" in payload
    assert "\n8\n0\n" in payload
    with pytest.raises(ValueError, match="file path does not exist"):
        document.create_dxf(str(tmp_path / "missing" / "drawing.dxf"))

    target = tmp_path / "drawing.dxf"
    document.create_dxf(str(target))
    assert target.read_text(encoding="ascii") == document.to_dxf_string()

    pathlike_target = tmp_path / "pathlike.dxf"
    document.create_dxf(pathlike_target)
    assert pathlike_target.read_text(encoding="ascii") == document.to_dxf_string()


@pytest.mark.condition("DXF-P1")
@pytest.mark.parametrize("layer", [True, False, 123, 1.5, object()])
def test_dxf_document_rejects_malformed_layer_overrides(layer: object) -> None:
    """DXF-P1: DXF layer overrides reject values that would be silently stringified."""
    style = _drawing_style()
    group = DrawingComponentGroup("source-layer")
    group.add_component(LineDrawing((0.0, 0.0), (1.0, 1.0), style))
    document = DXFDocument()

    with pytest.raises(TypeError, match="layer must be a string"):
        DXFRenderContext(layer=layer)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="layer must be a string"):
        document.add_group(group, layer=layer)  # type: ignore[arg-type]

    document.add_group(group, layer="")
    assert "\n8\nsource-layer\n" in document.to_dxf_string()


@pytest.mark.condition("DXF-P1")
@pytest.mark.parametrize(
    ("filepath", "exception_type", "message"),
    [
        (object(), TypeError, "file path must be a string or path-like object"),
        (123, TypeError, "file path must be a string or path-like object"),
        (b"drawing.dxf", TypeError, "file path must be a string or path-like object"),
        ("", ValueError, "file path must not be empty"),
    ],
)
def test_dxf_document_rejects_malformed_output_paths(
    filepath: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """DXF-P1: DXFDocument rejects malformed output paths at the writer boundary."""
    document = DXFDocument()

    with pytest.raises(exception_type, match=message):
        document.create_dxf(filepath)  # type: ignore[arg-type]


@pytest.mark.condition("DXF-P1")
def test_dxf_rectangle_and_path_closure_contracts() -> None:
    """DXF-P1: Rectangle and path exports preserve vertex counts and closure flags."""
    style = _drawing_style()
    rounded = RectangleDrawing((10.0, 20.0), 30.0, 40.0, (5.0, 8.0), style)
    rounded_points = _rectangle_points(rounded)
    closed_path = PathDrawing(
        style,
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("L", [(10.0, 0.0)]),
            PathCommand("L", [(10.0, 10.0)]),
            PathCommand("Z", []),
        ],
    )
    open_path = PathDrawing(style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(10.0, 0.0)])])

    rounded_entity = _component_to_entities(rounded, DXFRenderContext(layer="rounded"))[0]
    path_entity = _component_to_entities(closed_path, DXFRenderContext(layer="path"))[0]
    open_path_entity = _component_to_entities(open_path, DXFRenderContext(layer="path"))[0]
    expected_rounded_points = [
        (15.0, 20.0),
        (35.0, 20.0),
        (36.913417, 20.608964),
        (38.535534, 22.343146),
        (39.619398, 24.938533),
        (40.0, 28.0),
        (40.0, 52.0),
        (39.619398, 55.061467),
        (38.535534, 57.656854),
        (36.913417, 59.391036),
        (35.0, 60.0),
        (15.0, 60.0),
        (13.086583, 59.391036),
        (11.464466, 57.656854),
        (10.380602, 55.061467),
        (10.0, 52.0),
        (10.0, 28.0),
        (10.380602, 24.938533),
        (11.464466, 22.343146),
        (13.086583, 20.608964),
    ]

    assert len(rounded_points) == 20
    assert rounded_points == expected_rounded_points
    assert rounded_points[0] != rounded_points[-1]
    assert rounded_entity.startswith("0\nLWPOLYLINE\n8\nrounded\n420\n0\n370\n20\n90\n20\n70\n1\n")
    assert path_entity.startswith("0\nLWPOLYLINE\n8\npath\n420\n0\n370\n20\n90\n3\n70\n1\n")
    assert open_path_entity.startswith("0\nLWPOLYLINE\n8\npath\n420\n0\n370\n20\n90\n2\n70\n0\n")
    assert _vertices(rounded_entity) == expected_rounded_points


@pytest.mark.condition("RASTER-IMAGE-P3")
def test_dxf_polygonal_branches_emit_closed_polylines() -> None:
    """RASTER-IMAGE-P3: Polygon and regular polygon branches stay closed."""
    style = _drawing_style()
    context = DXFRenderContext(layer="closed")
    polygon = PolygonalDrawing([(0.0, 0.0), (2.0, 0.0), (1.0, 2.0)], style)
    regular = RegularPolygonDrawing((5.0, 5.0), 5, 4.0, style)

    polygon_entity = _component_to_entities(polygon, context)[0]
    regular_entity = _component_to_entities(regular, context)[0]

    assert "\n70\n1\n" in polygon_entity
    assert "\n70\n1\n" in regular_entity


@pytest.mark.condition("DXF-P1")
def test_dxf_sharp_rectangle_and_corner_duplicate_contract() -> None:
    """DXF-P1: Sharp rectangles and sampled corner arcs avoid duplicate points."""
    style = _drawing_style()
    sharp = RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, style)
    zero_y_radius = RectangleDrawing((1.0, 2.0), 3.0, 4.0, (1.0, 0.0), style)
    small_radius = RectangleDrawing((0.1234567, 0.7654321), 10.0, 10.0, (1.0, 2.0), style)
    points = [(1.0, 0.0)]
    trailing_duplicate = [(0.0, 0.0), (1.0, 0.0)]

    _append_corner_arc(points, center=(0.0, 0.0), rx=1.0, ry=1.0, start_degrees=0.0, end_degrees=0.0)
    _append_corner_arc(trailing_duplicate, center=(0.0, 0.0), rx=1.0, ry=1.0, start_degrees=0.0, end_degrees=0.0)

    assert _rectangle_points(sharp) == [(1.0, 2.0), (4.0, 2.0), (4.0, 6.0), (1.0, 6.0)]
    assert _rectangle_points(zero_y_radius) == [(1.0, 2.0), (4.0, 2.0), (4.0, 6.0), (1.0, 6.0)]
    assert _rectangle_points(small_radius)[0] == (1.123457, 0.765432)
    assert len(_rectangle_points(small_radius)) == 20
    assert points == [(1.0, 0.0)]
    assert trailing_duplicate == [(0.0, 0.0), (1.0, 0.0)]


@pytest.mark.condition("DXF-P1")
def test_dxf_circle_entity_contract() -> None:
    """DXF-P1: Circle entities preserve center, flipped y coordinate, and radius."""
    circle = CircleDrawing((10.0, 12.0), 5.0, _drawing_style())

    entity = _component_to_entities(circle, DXFRenderContext(canvas_height=100.0, layer="C"))[0]

    assert entity == "0\nCIRCLE\n8\nC\n420\n0\n370\n20\n10\n10\n20\n88\n30\n0\n40\n5"


@pytest.mark.condition("DXF-P1")
def test_dxf_entities_emit_drawing_style_color_and_lineweight() -> None:
    """DXF-P1: DXF drawing entities consume validated DrawingStyle stroke values."""
    styled = DrawingStyle(f"dxf_style_{uuid4().hex}", stroke="#112233", stroke_width=0.25)
    group = DrawingComponentGroup("styled")
    group.add_component(LineDrawing((0.0, 0.0), (1.0, 1.0), styled))
    group.add_component(RectangleDrawing((2.0, 2.0), 3.0, 4.0, 0.0, styled))
    group.add_component(CircleDrawing((8.0, 8.0), 2.0, styled))
    document = DXFDocument()

    document.add_group(group)
    payload = document.to_dxf_string()

    assert _pair_values(payload, "420") == ["1122867", "1122867", "1122867"]
    assert _pair_values(payload, "370") == ["25", "25", "25"]


@pytest.mark.condition("DXF-P1")
def test_dxf_style_lineweight_uses_standard_values_and_disabled_stroke_omits_codes() -> None:
    """DXF-P1: DXF lineweight snaps to standard values and disabled strokes stay unstyled."""
    wide = DrawingStyle(f"dxf_wide_{uuid4().hex}", stroke="#abcdef", stroke_width=0.27)
    below_threshold = DrawingStyle(f"dxf_below_{uuid4().hex}", stroke="#010203", stroke_width=0.273)
    above_threshold = DrawingStyle(f"dxf_above_{uuid4().hex}", stroke="#040506", stroke_width=0.275)
    disabled = DrawingStyle(f"dxf_none_{uuid4().hex}", stroke="none", stroke_width=0.25)
    wide_group = DrawingComponentGroup("wide")
    below_group = DrawingComponentGroup("below")
    above_group = DrawingComponentGroup("above")
    disabled_group = DrawingComponentGroup("disabled")
    wide_group.add_component(LineDrawing((0.0, 0.0), (1.0, 1.0), wide))
    below_group.add_component(LineDrawing((1.0, 1.0), (2.0, 2.0), below_threshold))
    above_group.add_component(LineDrawing((2.0, 2.0), (3.0, 3.0), above_threshold))
    disabled_group.add_component(LineDrawing((2.0, 2.0), (3.0, 3.0), disabled))

    document = DXFDocument()
    document.add_group(wide_group)
    document.add_group(below_group)
    document.add_group(above_group)
    document.add_group(disabled_group)
    payload = document.to_dxf_string()

    assert _pair_values(payload, "420") == ["11259375", "66051", "263430"]
    assert _pair_values(payload, "370") == ["25", "25", "30"]


@pytest.mark.condition("DXF-HATCH-P3")
def test_dxf_filled_closed_shapes_emit_solid_hatch_entities() -> None:
    """DXF-HATCH-P3: Closed filled drawing shapes emit deterministic solid HATCH entities."""
    fill_style = DrawingStyle(f"dxf_fill_{uuid4().hex}", stroke="none", fill="#abcdef")
    group = DrawingComponentGroup("filled")
    group.add_component(RectangleDrawing((10.0, 20.0), 30.0, 40.0, 0.0, fill_style))
    group.add_component(PolygonalDrawing([(0.0, 0.0), (2.0, 0.0), (1.0, 2.0)], fill_style))
    group.add_component(RegularPolygonDrawing((5.0, 5.0), 5, 4.0, fill_style))
    group.add_component(
        PathDrawing(
            fill_style,
            [
                PathCommand("M", [(0.0, 0.0)]),
                PathCommand("L", [(3.0, 0.0)]),
                PathCommand("L", [(3.0, 3.0)]),
                PathCommand("Z", []),
            ],
        )
    )
    group.add_component(CircleDrawing((50.0, 50.0), 5.0, fill_style))
    group.add_component(LineDrawing((0.0, 0.0), (1.0, 1.0), fill_style))
    group.add_component(PathDrawing(fill_style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(1.0, 0.0)])]))
    document = DXFDocument(canvas_height=100.0)

    document.add_group(group)
    payload = document.to_dxf_string()

    assert payload.count("\n0\nHATCH\n") == 5
    assert _pair_values(payload, "420") == ["11259375"] * 5
    assert _pair_values(payload, "93") == ["4", "3", "5", "3", "32"]
    assert "\n0\nHATCH\n8\nfilled\n420\n11259375\n100\nAcDbEntity\n100\nAcDbHatch\n" in payload
    assert "\n2\nSOLID\n" in payload
    assert "\n91\n1\n92\n7\n72\n0\n73\n1\n93\n4\n10\n10\n20\n80\n" in payload
    assert "\n98\n1\n10\n10\n20\n80\n" in payload


@pytest.mark.condition("DXF-HATCH-P3")
def test_dxf_hatch_helper_serializes_exact_boundary_codes() -> None:
    """DXF-HATCH-P3: HATCH helper preserves required group codes and converted vertices."""
    fill_style = DrawingStyle(f"dxf_fill_helper_{uuid4().hex}", stroke="none", fill="#abcdef")
    context = DXFRenderContext(canvas_height=100.0, layer="filled")
    points = [(10.0, 20.0), (40.0, 25.0), (35.0, 60.0), (12.0, 55.0)]

    entity = _hatch_entity(points, context, style=fill_style)

    assert entity == (
        "0\nHATCH\n8\nfilled\n420\n11259375\n100\nAcDbEntity\n100\nAcDbHatch\n"
        "10\n0\n20\n0\n30\n0\n210\n0\n220\n0\n230\n1\n2\nSOLID\n70\n1\n71\n0\n"
        "91\n1\n92\n7\n72\n0\n73\n1\n93\n4\n"
        "10\n10\n20\n80\n10\n40\n20\n75\n10\n35\n20\n40\n10\n12\n20\n45\n"
        "97\n0\n75\n0\n76\n1\n98\n1\n10\n10\n20\n80"
    )


@pytest.mark.condition("DXF-HATCH-P3")
def test_dxf_circle_hatch_points_are_deterministic() -> None:
    """DXF-HATCH-P3: Circle HATCH sampling preserves radius, center, and ordering."""
    circle = CircleDrawing((40.0, 50.0), 5.0, _drawing_style())

    points = _circle_hatch_points(circle)

    assert len(points) == 32
    assert points[0] == (45.0, 50.0)
    assert points[4] == (43.535534, 53.535534)
    assert points[8] == (40.0, 55.0)
    assert points[16] == (35.0, 50.0)
    assert points[24] == (40.0, 45.0)
    assert points[-1] == (44.903926, 49.024548)


@pytest.mark.condition("DXF-HATCH-P3")
def test_dxf_fill_none_omits_hatch_entities() -> None:
    """DXF-HATCH-P3: Disabled fills preserve boundary output without HATCH entities."""
    style = DrawingStyle(f"dxf_no_fill_{uuid4().hex}", stroke="#112233", fill="none")
    group = DrawingComponentGroup("outline")
    group.add_component(RectangleDrawing((0.0, 0.0), 2.0, 3.0, 0.0, style))
    group.add_component(CircleDrawing((5.0, 5.0), 2.0, style))
    document = DXFDocument()

    document.add_group(group)
    payload = document.to_dxf_string()

    assert "\n0\nLWPOLYLINE\n" in payload
    assert "\n0\nCIRCLE\n" in payload
    assert "\n0\nHATCH\n" not in payload
    assert _pair_values(payload, "420") == ["1122867", "1122867"]


@pytest.mark.condition("DXF-P1")
def test_dxf_pdf_sampled_geometry_contract_for_indirect_components() -> None:
    """DXF-P1: DXF indirect geometry branches reuse PDF-sampled points."""
    style = _drawing_style()
    context = DXFRenderContext(layer="sampled")
    components = [
        ArcDrawing((0.0, 0.0), 5.0, 3.0, 0.0, 90.0, style),
        CubicBezierDrawing((0.0, 0.0), (3.0, 6.0), (6.0, 6.0), (9.0, 0.0), style),
        RegularPolygonDrawing((5.0, 5.0), 5, 4.0, style, angle=18.0),
        PathDrawing(style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(3.0, 0.0)])]),
    ]

    for component in components:
        entity = _component_to_entities(component, context)[0]
        expected_points = [(round(float(x), 6), round(float(y), 6)) for x, y in component.to_component(OutputFormat.PDF).points]

        assert "\n8\nsampled\n" in entity
        assert f"\n90\n{len(expected_points)}\n" in entity
        assert _vertices(entity) == expected_points
