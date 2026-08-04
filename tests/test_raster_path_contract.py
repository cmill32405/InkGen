"""RASTER-PATH-P5 conditions for neutral linear-path raster rendering."""

from __future__ import annotations

from uuid import uuid4

import pytest

import InkGen.raster_renderer as raster_renderer
from InkGen.baird import BairdParams
from InkGen.boundary import Canvas
from InkGen.component import PathCommand
from InkGen.drawing_components import DrawingComponentGroup, PathDrawing
from InkGen.raster_renderer import render_and_degrade_drawing_group, render_drawing_group
from InkGen.style import DrawingStyle


def _style(
    *,
    stroke: str = "#000000",
    fill: str = "none",
    stroke_width: float = 0.08,
    fill_opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"raster_path_{uuid4().hex}",
        stroke=stroke,
        fill=fill,
        stroke_width=stroke_width,
        fill_opacity=fill_opacity,
    )


def _closed_path(style: DrawingStyle) -> PathDrawing:
    return PathDrawing(
        style,
        [
            PathCommand("M", [(0.5, 0.5)]),
            PathCommand("L", [(3.5, 0.5)]),
            PathCommand("V", [(0.0, 2.5)]),
            PathCommand("H", [(0.5, 0.0)]),
            PathCommand("Z"),
        ],
    )


@pytest.mark.condition("RASTER-PATH-P5")
def test_linear_path_renders_through_public_scan_path() -> None:
    """RASTER-PATH-P5: Linear paths reach clean and Baird assets."""
    result = render_and_degrade_drawing_group(
        DrawingComponentGroup("path", [_closed_path(_style(stroke="#102030"))]),
        Canvas(4, 3, "in"),
        BairdParams.clean(),
        seed=11,
        background_rgb=(255, 255, 255),
        dpi=20,
        render_supersample=2,
    )

    assert result.clean.component_count == 1
    with result.clean.asset.image() as clean:
        assert clean.getbbox() is not None
    with result.degraded.asset.image() as degraded:
        assert degraded.getbbox() == (0, 0, 80, 60)
        assert degraded.getextrema() != ((255, 255), (255, 255), (255, 255))


class _RecordingDraw:
    """Record Pillow line calls for exact path-contract assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[tuple[int, int]], tuple[int, int, int, int], int]] = []

    def line(
        self,
        points: list[tuple[int, int]],
        *,
        fill: tuple[int, int, int, int],
        width: int,
    ) -> None:
        self.calls.append((points, fill, width))


@pytest.mark.condition("RASTER-PATH-P5")
def test_linear_path_preserves_subpaths_axis_commands_and_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-PATH-P5: Subpaths render independently with exact H/V/Z geometry."""
    style = _style(stroke="#123456", stroke_width=0.5)
    path = PathDrawing(
        style,
        [
            PathCommand("M", [(1.0, 1.0)]),
            PathCommand("L", [(2.0, 1.0), (2.0, 2.0)]),
            PathCommand("Z"),
            PathCommand("M", [(3.0, 3.0)]),
            PathCommand("H", [(4.0, 99.0)]),
            PathCommand("V", [(99.0, 4.0)]),
            PathCommand("M", [(5.0, 5.0)]),
            PathCommand("L", [(6.0, 5.0)]),
        ],
    )
    recorder = _RecordingDraw()
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)

    raster_renderer._render_component(object(), path, 10.0)  # type: ignore[arg-type]

    assert recorder.calls == [
        ([(10, 10), (20, 10), (20, 20), (10, 10)], (18, 52, 86, 255), 5),
        ([(30, 30), (40, 30), (40, 40)], (18, 52, 86, 255), 5),
        ([(50, 50), (60, 50)], (18, 52, 86, 255), 5),
    ]


@pytest.mark.condition("RASTER-PATH-P5")
@pytest.mark.parametrize(
    ("commands", "expected"),
    [
        (
            [
                PathCommand("M", [(9.0, 7.0)]),
                PathCommand("L", [(3.0, 4.0), (8.0, 6.0)]),
                PathCommand("H", [(5.0, 99.0)]),
                PathCommand("V", [(99.0, 2.0)]),
            ],
            [[(9.0, 7.0), (3.0, 4.0), (8.0, 6.0), (5.0, 6.0), (5.0, 2.0)]],
        ),
        (
            [PathCommand("M", [(9.0, 9.0)]), PathCommand("L", [(1.0, 1.0)]), PathCommand("Z")],
            [[(9.0, 9.0), (1.0, 1.0), (9.0, 9.0)]],
        ),
        (
            [PathCommand("M", [(9.0, 9.0)]), PathCommand("Z")],
            [[(9.0, 9.0)]],
        ),
    ],
)
def test_linear_path_expansion_is_exact(
    commands: list[PathCommand],
    expected: list[list[tuple[float, float]]],
) -> None:
    """RASTER-PATH-P5: Minimal witnesses prove current-point and closure rules."""
    path = PathDrawing(_style(stroke="#123456"), commands)

    assert raster_renderer._sampled_path_subpaths(path) == expected


@pytest.mark.condition("RASTER-PATH-P5")
@pytest.mark.parametrize(
    "commands",
    [None, [], [PathCommand("M", [(1.0, 1.0)])]],
)
def test_empty_and_move_only_paths_are_transparent_noops(commands: list[PathCommand] | None) -> None:
    """RASTER-PATH-P5: Paths without a segment do not invent pixels."""
    result = render_drawing_group(
        DrawingComponentGroup("noop", [PathDrawing(_style(stroke="#123456"), commands)]),
        Canvas(2, 2, "in"),
        dpi=20,
    )

    assert result.component_count == 1
    with result.asset.image() as image:
        assert image.getbbox() is None


@pytest.mark.condition("RASTER-PATH-P5")
def test_unpainted_linear_path_is_transparent_noop() -> None:
    """RASTER-PATH-P5: A valid path without stroke paint remains transparent."""
    result = render_drawing_group(
        DrawingComponentGroup("unpainted", [_closed_path(_style(stroke="none", stroke_width=0.0))]),
        Canvas(4, 3, "in"),
        dpi=20,
    )

    with result.asset.image() as image:
        assert image.getbbox() is None


@pytest.mark.condition("RASTER-PATH-P5")
def test_transparent_path_fill_is_admitted() -> None:
    """RASTER-PATH-P5: Zero-opacity fill does not make a stroked path unsupported."""
    result = render_drawing_group(
        DrawingComponentGroup(
            "transparent-fill",
            [_closed_path(_style(stroke="#123456", fill="#abcdef", fill_opacity=0.0))],
        ),
        Canvas(4, 3, "in"),
        dpi=20,
    )

    with result.asset.image() as image:
        assert image.getbbox() is not None


@pytest.mark.condition("RASTER-PATH-P5")
@pytest.mark.parametrize(
    ("commands", "message"),
    [
        ([PathCommand("M")], "M requires exactly one point"),
        ([PathCommand("M", [(0.0, 0.0), (1.0, 1.0)])], "M requires exactly one point"),
        ([PathCommand("L", [(1.0, 1.0)])], "path must begin with M"),
        ([PathCommand("Z")], "path must begin with M"),
        ([PathCommand("M", [(0.0, 0.0)]), PathCommand("L")], "L requires at least one point"),
        ([PathCommand("M", [(0.0, 0.0)]), PathCommand("H")], "H requires at least one point"),
        ([PathCommand("M", [(0.0, 0.0)]), PathCommand("V")], "V requires at least one point"),
        ([PathCommand("M", [(0.0, 0.0)]), PathCommand("Z", [(1.0, 1.0)])], "Z does not accept points"),
        (
            [PathCommand("M", [(0.0, 0.0)]), PathCommand("Z"), PathCommand("L", [(1.0, 1.0)])],
            "new subpath must begin with M",
        ),
    ],
)
def test_malformed_linear_path_sequences_fail_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    commands: list[PathCommand],
    message: str,
) -> None:
    """RASTER-PATH-P5: Ambiguous or incomplete linear commands fail loudly."""
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(ValueError, match=message):
        render_drawing_group(
            DrawingComponentGroup("malformed", [PathDrawing(_style(stroke="#123456"), commands)]),
            Canvas(2, 2, "in"),
            dpi=20,
        )


@pytest.mark.condition("RASTER-PATH-P5")
def test_mutated_path_command_collection_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-PATH-P5: Mutable command lists cannot bypass the live boundary."""
    path = PathDrawing(_style(stroke="#123456"), [PathCommand("M", [(0.0, 0.0)])])
    assert path.commands is not None
    path.commands.append(object())  # type: ignore[arg-type]
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(TypeError, match="PathDrawing commands must contain only PathCommand objects"):
        render_drawing_group(DrawingComponentGroup("mutated", [path]), Canvas(2, 2, "in"), dpi=20)


@pytest.mark.condition("RASTER-PATH-P5")
@pytest.mark.parametrize("commands", ["M 0 0", 7])
def test_replaced_path_command_collection_fails_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    commands: object,
) -> None:
    """RASTER-PATH-P5: Replaced command containers cannot bypass validation."""
    path = PathDrawing(_style(stroke="#123456"), [PathCommand("M", [(0.0, 0.0)])])
    object.__setattr__(path, "commands", commands)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(TypeError, match="PathDrawing commands must be a sequence of PathCommand objects"):
        render_drawing_group(DrawingComponentGroup("replaced", [path]), Canvas(2, 2, "in"), dpi=20)
