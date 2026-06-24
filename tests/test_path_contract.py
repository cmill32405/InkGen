"""PATH-P1 behavioral tests for generic path renderer contracts."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import Path, PathCommand
from InkGen.drawing_components import DrawingComponentGroup, OutputFormat, PathDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.pdf_generator import PathPDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import PathSVG


def _style() -> DrawingStyle:
    """Return a unique visible drawing style."""
    return DrawingStyle(f"path_{uuid4().hex}", stroke="#000000", fill="none")


def _dxf_entity_pairs(payload: str) -> list[tuple[str, str]]:
    """Parse DXF code/value pairs from an ASCII DXF payload."""
    lines = payload.splitlines()
    assert len(lines) % 2 == 0
    return list(zip(lines[0::2], lines[1::2], strict=True))


def _dxf_polyline_vertices(payload: str) -> list[tuple[float, float]]:
    """Read LWPOLYLINE vertices from a single-polyline DXF payload."""
    pairs = _dxf_entity_pairs(payload)
    vertices: list[tuple[float, float]] = []
    index = 0
    while index < len(pairs):
        code, value = pairs[index]
        if code == "10":
            next_code, y = pairs[index + 1]
            assert next_code == "20"
            vertices.append((float(value), float(y)))
            index += 2
        else:
            index += 1
    return vertices


@pytest.mark.condition("PATH-P1")
def test_path_command_normalizes_and_rejects_invalid_inputs() -> None:
    """PATH-P1: PathCommand normalizes valid commands and rejects invalid data."""
    command = PathCommand(" m ", [(1.1114, 2.5555)])

    assert command.type == "M"
    assert command.points == [(1.111, 2.555)]

    command.add_point((3, 4))
    assert command.points[-1] == (3.0, 4.0)

    with pytest.raises(TypeError, match="Command type must be a string"):
        PathCommand(3, [])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="R is not a supported path command"):
        PathCommand("R", [])
    with pytest.raises(ValueError, match="Points must contain two numeric values"):
        PathCommand("L", [(1.0,)])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="Points must contain two numeric values"):
        PathCommand("L", [(1.0, 2.0, 3.0)])  # type: ignore[list-item]


@pytest.mark.condition("PATH-P1")
def test_path_collects_command_points_and_rejects_bad_additions() -> None:
    """PATH-P1: Path collects command points and rejects non-command additions."""
    path = Path(_style(), [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(1.0, 1.0)])])
    path.add_command({"type": "L", "points": [(2.0, 2.0)]})

    assert [command.type for command in path.commands] == ["M", "L", "L"]
    assert path.points == [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]

    with pytest.raises(TypeError, match="Command must be a PathCommand or a dictionary"):
        path.add_command(object())  # type: ignore[arg-type]


@pytest.mark.condition("PATH-P1")
def test_path_pdf_emits_supported_commands_as_exact_operators() -> None:
    """PATH-P1: PathPDF maps supported SVG-style commands to exact PDF operators."""
    path = PathPDF(
        _style(),
        commands=[
            PathCommand("M", [(0.0, 0.0), (1.0, 2.0)]),
            PathCommand("L", [(3.0, 4.0), (4.0, 5.0)]),
            PathCommand("H", [(7.0, 0.0)]),
            PathCommand("V", [(0.0, 6.0)]),
            PathCommand("Q", [(7.0, 8.0), (9.0, 10.0), (10.0, 11.0), (12.0, 13.0)]),
            PathCommand("C", [(11.0, 12.0), (13.0, 14.0), (15.0, 16.0), (16.0, 17.0), (18.0, 19.0), (20.0, 21.0)]),
            PathCommand("A", [(17.0, 18.0), (19.0, 20.0), (21.0, 22.0)]),
            PathCommand("Z", []),
        ],
    )

    lines = path.generate_pdf().splitlines()

    assert "1 2 m" in lines
    assert "3 4 l" in lines
    assert "4 5 l" in lines
    assert "7 5 l" in lines
    assert "7 6 l" in lines
    assert "7 7.333333 7.666667 8.666667 9 10 c" in lines
    assert "9.666667 10.666667 10.666667 11.666667 12 13 c" in lines
    assert "11 12 13 14 15 16 c" in lines
    assert "16 17 18 19 20 21 c" in lines
    assert "21 22 l" in lines
    assert "h" in lines
    assert lines[-2:] == ["S", "Q"]


@pytest.mark.condition("PATH-P1")
def test_path_pdf_uses_origin_for_initial_axis_commands() -> None:
    """PATH-P1: Initial H/V commands start from the PDF path origin."""
    horizontal = PathPDF(_style(), commands=[PathCommand("H", [(5.0, 9.0)])])
    vertical = PathPDF(_style(), commands=[PathCommand("V", [(8.0, 6.0)])])

    assert "5 0 l" in horizontal.generate_pdf().splitlines()
    assert "0 6 l" in vertical.generate_pdf().splitlines()


@pytest.mark.condition("PATH-P1")
def test_path_pdf_renders_single_endpoint_arc_fallback() -> None:
    """PATH-P1: PDF arc fallback accepts a single endpoint."""
    path = PathPDF(_style(), commands=[PathCommand("A", [(7.0, 8.0)])])

    assert "7 8 l" in path.generate_pdf().splitlines()


@pytest.mark.condition("PATH-P1")
def test_path_pdf_rejects_commands_it_cannot_render() -> None:
    """PATH-P1: PathPDF fails instead of silently dropping unsupported commands."""
    for command_type in ("S", "T"):
        path = PathPDF(
            _style(),
            commands=[
                PathCommand("M", [(0.0, 0.0)]),
                PathCommand(command_type, [(1.0, 1.0), (2.0, 2.0)]),
            ],
        )

        with pytest.raises(ValueError, match=f"PathPDF does not support path command {command_type}"):
            path.generate_pdf()


@pytest.mark.condition("PATH-P1")
@pytest.mark.parametrize(
    ("command", "message"),
    [
        (PathCommand("C", [(1.0, 1.0), (2.0, 2.0)]), "groups of three"),
        (PathCommand("Q", [(1.0, 1.0)]), "groups of two"),
        (PathCommand("A", []), "requires an endpoint"),
    ],
)
def test_path_pdf_rejects_incomplete_curve_segments(command: PathCommand, message: str) -> None:
    """PATH-P1: PathPDF fails on incomplete path commands instead of truncating."""
    path = PathPDF(_style(), commands=[PathCommand("M", [(0.0, 0.0)]), command])

    with pytest.raises(ValueError, match=message):
        path.generate_pdf()


@pytest.mark.condition("PATH-P1")
def test_path_svg_preserves_smooth_commands_that_pdf_rejects() -> None:
    """PATH-P1: SVG keeps valid smooth commands even when PDF cannot render them."""
    path = PathSVG(
        _style(),
        commands=[
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("S", [(1.0, 1.0), (2.0, 2.0)]),
            PathCommand("T", [(3.0, 3.0)]),
        ],
    )

    assert 'd="M 0.0,0.0 S 1.0,1.0 2.0,2.0 T 3.0,3.0"' in path.generate_svg()


@pytest.mark.condition("PATH-P1")
def test_path_svg_formats_axis_and_default_arc_commands() -> None:
    """PATH-P1: SVG path formatting preserves axis commands and default arc flags."""
    partial_arc = PathCommand("A", [(7.0, 8.0), (9.0, 10.0)])
    partial_arc.flags = {"radii": (2.0, 3.0)}
    empty_flag_arc = PathCommand("A", [(11.0, 12.0)])
    empty_flag_arc.flags = {}
    path = PathSVG(
        _style(),
        commands=[
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("H", [(5.0, 9.0)]),
            PathCommand("V", [(8.0, 6.0)]),
            PathCommand("A", [(7.0, 8.0)]),
            partial_arc,
            empty_flag_arc,
        ],
    )

    assert (
        'd="M 0.0,0.0 H 5.0 V 6.0 A 0.0,0.0 0.0 0 0 7.0,8.0 A 2.0,3.0 0.0 0 0 9.0,10.0 A 0.0,0.0 0.0 0 0 11.0,12.0"' in path.generate_svg()
    )


@pytest.mark.condition("PATH-P1")
def test_path_drawing_materializes_svg_and_pdf_components() -> None:
    """PATH-P1: Neutral path drawings materialize to requested concrete renderers."""
    commands = [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(1.0, 1.0)])]
    drawing = PathDrawing(_style(), commands)

    svg_component = drawing.to_component(OutputFormat.SVG)
    pdf_component = drawing.to_component(OutputFormat.PDF)

    assert isinstance(svg_component, PathSVG)
    assert isinstance(pdf_component, PathPDF)
    assert svg_component.commands == commands
    assert pdf_component.commands == commands


@pytest.mark.condition("PATH-DRAWING-COMMANDS-P2")
def test_path_drawing_accepts_command_sequences_before_materialization() -> None:
    """PATH-DRAWING-COMMANDS-P2: PathDrawing normalizes valid command sequences."""
    commands = (PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(2.0, 3.0)]))
    drawing = PathDrawing(_style(), commands)

    svg_component = drawing.to_component(OutputFormat.SVG)
    pdf_component = drawing.to_component(OutputFormat.PDF)

    assert drawing.commands == list(commands)
    assert isinstance(svg_component, PathSVG)
    assert isinstance(pdf_component, PathPDF)
    assert svg_component.commands == list(commands)
    assert pdf_component.commands == list(commands)


@pytest.mark.condition("PATH-DRAWING-COMMANDS-P2")
@pytest.mark.parametrize(
    "commands",
    [
        "M",
        b"M",
        object(),
        [object()],
        [{"type": "M", "points": []}],
    ],
)
def test_path_drawing_rejects_malformed_command_collections(commands: object) -> None:
    """PATH-DRAWING-COMMANDS-P2: PathDrawing rejects malformed command collections."""
    with pytest.raises(TypeError, match="PathDrawing commands must"):
        PathDrawing(_style(), commands)  # type: ignore[arg-type]


@pytest.mark.condition("PATH-P1")
def test_dxf_path_drawing_reuses_pdf_points_and_closure_flag() -> None:
    """PATH-P1: DXF path output uses neutral path points and Z closure state."""
    style = _style()
    open_path = PathDrawing(style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(3.0, 0.0)])])
    closed_path = PathDrawing(
        style,
        [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(3.0, 0.0)]), PathCommand("Z", [])],
    )

    open_group = DrawingComponentGroup("open_path")
    open_group.add_component(open_path)
    open_document = DXFDocument()
    open_document.add_group(open_group)
    open_payload = open_document.to_dxf_string()

    closed_group = DrawingComponentGroup("closed_path")
    closed_group.add_component(closed_path)
    closed_document = DXFDocument()
    closed_document.add_group(closed_group)
    closed_payload = closed_document.to_dxf_string()

    assert "\n70\n0\n" in open_payload
    assert "\n70\n1\n" in closed_payload
    assert _dxf_polyline_vertices(open_payload) == open_path.to_component(OutputFormat.PDF).points
    assert _dxf_polyline_vertices(closed_payload) == closed_path.to_component(OutputFormat.PDF).points
