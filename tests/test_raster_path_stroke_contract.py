"""RASTER-PATH-STROKE-P17 conditions for semantic raster path strokes."""

from __future__ import annotations

from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

import InkGen.raster_renderer as raster_renderer
from InkGen.boundary import Canvas
from InkGen.component import PathCommand
from InkGen.drawing_components import DrawingComponentGroup, PathDrawing
from InkGen.raster_renderer import render_drawing_group
from InkGen.style import DrawingStyle


def _style(
    *,
    linecap: str = "butt",
    linejoin: str = "miter",
    miterlimit: float = 10.0,
    fill: str = "none",
    stroke_opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"raster_path_stroke_{uuid4().hex}",
        stroke="#102030",
        fill=fill,
        stroke_width=0.4,
        stroke_opacity=stroke_opacity,
        stroke_linecap=linecap,
        stroke_linejoin=linejoin,
        stroke_miterlimit=miterlimit,
    )


def _render(path: PathDrawing) -> bytes:
    result = render_drawing_group(
        DrawingComponentGroup("path-stroke", [path]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )
    return result.asset.data


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_sampling_records_source_endpoints_without_promoting_curve_samples() -> None:
    """RASTER-PATH-STROKE-P17: Only source segment ends become semantic vertices."""
    path = PathDrawing(
        _style(),
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("Q", [(0.5, 1.0), (1.0, 0.0)]),
            PathCommand("L", [(2.0, 0.0)]),
            PathCommand("C", [(2.5, 1.0), (3.5, 1.0), (4.0, 0.0)]),
        ],
    )

    subpath = raster_renderer._sampled_path_geometry(path)[0]

    assert len(subpath.points) == 66
    assert subpath.endpoint_indices == (0, 32, 33, 65)
    assert subpath.segment_count == 3
    assert subpath.closed is False


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_open_path_has_one_join_per_interior_source_endpoint() -> None:
    """RASTER-PATH-STROKE-P17: Curve samples provide tangents but not extra joins."""
    path = PathDrawing(
        _style(linejoin="round"),
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("Q", [(1.0, 1.0), (2.0, 0.0)]),
            PathCommand("L", [(2.0, 2.0)]),
        ],
    )
    subpath = raster_renderer._sampled_path_geometry(path)[0]

    assert raster_renderer._semantic_path_join_triples(subpath) == [(subpath.points[31], subpath.points[32], subpath.points[33])]


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_closed_path_joins_the_seam_once_without_endpoint_caps() -> None:
    """RASTER-PATH-STROKE-P17: Z creates seam joins and suppresses caps."""
    commands = [
        PathCommand("M", [(1.0, 1.0)]),
        PathCommand("L", [(4.0, 1.0), (2.5, 4.0)]),
        PathCommand("Z"),
    ]
    subpath = raster_renderer._sampled_path_geometry(PathDrawing(_style(), commands))[0]

    assert subpath.closed is True
    assert subpath.points[-1] == subpath.points[0]
    assert len(raster_renderer._semantic_path_join_triples(subpath)) == 3
    assert _render(PathDrawing(_style(linecap="butt"), commands)) == _render(PathDrawing(_style(linecap="round"), commands))
    assert _render(PathDrawing(_style(linecap="butt"), commands)) == _render(PathDrawing(_style(linecap="square"), commands))


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
@pytest.mark.parametrize("linecap", ["round", "square"])
def test_open_caps_extend_beyond_butt_path_support(linecap: str) -> None:
    """RASTER-PATH-STROKE-P17: Open paths cap only their two semantic ends."""
    commands = [PathCommand("M", [(1.0, 2.0)]), PathCommand("L", [(4.0, 2.0)])]
    butt = render_drawing_group(
        DrawingComponentGroup("butt", [PathDrawing(_style(), commands)]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )
    capped = render_drawing_group(
        DrawingComponentGroup("capped", [PathDrawing(_style(linecap=linecap), commands)]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )

    with butt.asset.image() as butt_image, capped.asset.image() as capped_image:
        assert butt_image.getpixel((17, 40))[3] == 0
        assert capped_image.getpixel((17, 40))[3] > 0
        assert butt_image.getpixel((83, 40))[3] == 0
        assert capped_image.getpixel((83, 40))[3] > 0


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_curve_cap_uses_local_endpoint_tangent_instead_of_endpoint_chord() -> None:
    """RASTER-PATH-STROKE-P17: Square curve caps follow sampled endpoint tangents."""
    path = PathDrawing(
        _style(linecap="square"),
        [PathCommand("M", [(1.0, 3.0)]), PathCommand("Q", [(1.0, 1.0), (3.0, 1.0)])],
    )
    subpath = raster_renderer._sampled_path_geometry(path)[0]

    start_tangent, end_tangent = raster_renderer._open_path_endpoint_tangents(subpath)

    assert start_tangent[0] == pytest.approx(0.0, abs=0.1)
    assert start_tangent[1] < -0.9
    assert end_tangent[0] > 0.9
    assert end_tangent[1] == pytest.approx(0.0, abs=0.1)


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_endpoint_tangents_use_the_nearest_distinct_samples_exactly() -> None:
    """RASTER-PATH-STROKE-P17: Tangents cannot skip curve samples."""
    subpath = raster_renderer._sampled_path_geometry(
        PathDrawing(
            _style(linecap="square"),
            [PathCommand("M", [(1.0, 3.0)]), PathCommand("Q", [(1.0, 1.0), (3.0, 1.0)])],
        )
    )[0]

    assert raster_renderer._open_path_endpoint_tangents(subpath) == (
        raster_renderer._unit_tangent(subpath.points[0], subpath.points[1]),
        raster_renderer._unit_tangent(subpath.points[-2], subpath.points[-1]),
    )


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_diagonal_square_cap_satisfies_all_four_support_coordinates() -> None:
    """RASTER-PATH-STROKE-P17: Both tangent axes and normal signs define a cap."""

    class RecordingDraw:
        def __init__(self) -> None:
            self.calls: list[list[tuple[float, float]]] = []

        def polygon(self, points: list[tuple[float, float]], *, fill: object) -> None:
            del fill
            self.calls.append(list(points))

    draw = RecordingDraw()

    tangent = raster_renderer._unit_tangent((0.0, 0.0), (3.0, 4.0))
    raster_renderer._draw_path_endpoint_cap(
        draw,
        (10.0, 10.0),
        tangent,
        (16, 32, 48, 255),
        10,
        "square",
        at_start=False,
    )

    assert draw.calls == [
        [
            (6.0, 13.0),
            (9.0, 17.0),
            (17.0, 11.0),
            (14.0, 7.0),
        ]
    ]


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_multiple_open_subpaths_receive_independent_caps() -> None:
    """RASTER-PATH-STROKE-P17: M boundaries cannot join or cap across subpaths."""
    path = PathDrawing(
        _style(linecap="round"),
        [
            PathCommand("M", [(1.0, 1.0)]),
            PathCommand("L", [(2.0, 1.0)]),
            PathCommand("M", [(3.0, 3.0)]),
            PathCommand("L", [(4.0, 3.0)]),
        ],
    )

    geometry = raster_renderer._sampled_path_geometry(path)

    assert [subpath.segment_count for subpath in geometry] == [1, 1]
    assert all(not subpath.closed for subpath in geometry)
    assert all(raster_renderer._semantic_path_join_triples(subpath) == [] for subpath in geometry)


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
@pytest.mark.parametrize(
    ("commands", "expected_segments"),
    [
        ([PathCommand("H", [(1.0, 9.0), (2.0, 9.0)]), PathCommand("V", [(9.0, 1.0)])], 3),
        ([PathCommand("S", [(1.0, 1.0), (2.0, 0.0), (3.0, 1.0), (4.0, 0.0)])], 2),
        ([PathCommand("T", [(1.0, 1.0), (2.0, 0.0)])], 2),
    ],
)
def test_every_grouped_source_segment_records_one_endpoint(
    commands: list[PathCommand],
    expected_segments: int,
) -> None:
    """RASTER-PATH-STROKE-P17: Grouped H/V/S/T segments retain topology."""
    subpath = raster_renderer._sampled_path_geometry(PathDrawing(_style(), [PathCommand("M", [(0.0, 0.0)]), *commands]))[0]

    assert subpath.segment_count == expected_segments
    assert len(subpath.endpoint_indices) == expected_segments + 1


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_equal_endpoint_arc_remains_a_semantic_noop() -> None:
    """RASTER-PATH-STROKE-P17: SVG equal-endpoint A cannot invent caps or joins."""
    command = PathCommand("A", [(1.0, 1.0)])
    command.flags = {"radii": (2.0, 1.0), "rotation": 0.0, "large_arc": 0, "sweep": 1}
    subpath = raster_renderer._sampled_path_geometry(PathDrawing(_style(linecap="round"), [PathCommand("M", [(1.0, 1.0)]), command]))[0]

    assert subpath.points == ((1.0, 1.0),)
    assert subpath.endpoint_indices == (0,)
    assert subpath.segment_count == 0


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_degenerate_semantic_join_has_no_invented_tangent() -> None:
    """RASTER-PATH-STROKE-P17: All-equal vertices cannot create a join wedge."""
    path = PathDrawing(
        _style(linejoin="bevel"),
        [PathCommand("M", [(1.0, 1.0)]), PathCommand("L", [(1.0, 1.0), (1.0, 1.0)])],
    )
    subpath = raster_renderer._sampled_path_geometry(path)[0]

    assert raster_renderer._semantic_path_join_triples(subpath) == []
    assert raster_renderer._distinct_path_neighbor(subpath, 0, -1) is None


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_closed_custom_join_paints_the_explicit_closure_segment(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-PATH-STROKE-P17: Custom closed strokes retain the Z body and seam joins."""
    path = PathDrawing(
        _style(linejoin="round"),
        [
            PathCommand("M", [(1.0, 1.0)]),
            PathCommand("L", [(3.0, 1.0), (2.0, 3.0)]),
            PathCommand("Z"),
        ],
    )
    calls: list[list[tuple[float, float]]] = []
    original = raster_renderer._draw_curve

    def capture(
        draw: object,
        points: list[tuple[float, float]] | tuple[tuple[float, float], ...],
        scale: float,
        stroke: tuple[int, int, int, int],
        stroke_width: int,
    ) -> None:
        calls.append(list(points))
        original(draw, points, scale, stroke, stroke_width)

    monkeypatch.setattr(raster_renderer, "_draw_curve", capture)

    _render(path)

    assert calls[-1] == [(2.0, 3.0), (1.0, 1.0)]
    assert len(calls) == 3


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_filled_path_composites_semantic_stroke_after_fill() -> None:
    """RASTER-PATH-STROKE-P17: P12 paint order also applies to custom strokes."""
    path = PathDrawing(
        _style(linecap="round", linejoin="bevel", fill="#80A0C0"),
        [
            PathCommand("M", [(1.0, 1.0)]),
            PathCommand("L", [(4.0, 1.0), (2.5, 4.0)]),
        ],
    )
    result = render_drawing_group(
        DrawingComponentGroup("filled-custom-stroke", [path]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        assert image.getpixel((50, 40))[:3] == (128, 160, 192)
        assert image.getpixel((20, 20))[:3] == (16, 32, 48)


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_translucent_semantic_stroke_source_over_composites_after_fill() -> None:
    """RASTER-PATH-STROKE-P17: The separate stroke layer preserves alpha."""
    path = PathDrawing(
        _style(linejoin="bevel", fill="#80A0C0", stroke_opacity=0.5),
        [
            PathCommand("M", [(1.0, 1.0)]),
            PathCommand("L", [(4.0, 1.0), (2.5, 4.0)]),
        ],
    )
    result = render_drawing_group(
        DrawingComponentGroup("translucent-custom-stroke", [path]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        assert image.getpixel((20, 20)) == (72, 96, 120, 255)


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_sampler_defensive_invariants_fail_explicitly() -> None:
    """RASTER-PATH-STROKE-P17: Impossible internal states do not fail ambiguously."""
    sampler = raster_renderer._PathSampler(PathDrawing(_style()))

    with pytest.raises(AssertionError, match="close requires"):
        sampler._close([])
    with pytest.raises(AssertionError, match="segment requires"):
        sampler._append_segment([(0.0, 0.0), (1.0, 1.0)])
    with pytest.raises(AssertionError, match="command requires"):
        sampler._current_point()
    with pytest.raises(AssertionError, match="finish requires"):
        sampler._finish(closed=False)


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_move_only_subpath_remains_transparent_with_nonbutt_cap() -> None:
    """RASTER-PATH-STROKE-P17: M alone does not invent a stroked segment."""
    for linecap in ("round", "square"):
        path = PathDrawing(_style(linecap=linecap), [PathCommand("M", [(2.0, 2.0)])])
        result = render_drawing_group(
            DrawingComponentGroup("move-only", [path]),
            Canvas(5.0, 5.0, "in"),
            dpi=20,
            supersample=1,
        )
        with result.asset.image() as image:
            assert image.getbbox() is None


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
@pytest.mark.parametrize("linecap", ["round", "square"])
def test_zero_length_source_segment_paints_one_bounded_cap(linecap: str) -> None:
    """RASTER-PATH-STROKE-P17: A degenerate open segment retains cap semantics."""
    path = PathDrawing(
        _style(linecap=linecap),
        [PathCommand("M", [(2.0, 2.0)]), PathCommand("L", [(2.0, 2.0)])],
    )
    result = render_drawing_group(
        DrawingComponentGroup("zero-segment", [path]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        assert image.getbbox() is not None
        assert image.getpixel((40, 40))[3] > 0
        assert image.getpixel((30, 30))[3] == 0


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_default_path_uses_exact_established_curve_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-PATH-STROKE-P17: Default cap/join/limit retain the legacy route."""
    path = PathDrawing(
        _style(),
        [PathCommand("M", [(1.0, 1.0)]), PathCommand("L", [(2.0, 1.0), (2.0, 2.0)])],
    )
    calls: list[tuple[list[tuple[float, float]], float]] = []

    def capture(
        draw: object,
        points: list[tuple[float, float]],
        scale: float,
        stroke: tuple[int, int, int, int],
        stroke_width: int,
    ) -> None:
        del draw, stroke, stroke_width
        calls.append((list(points), scale))

    monkeypatch.setattr(raster_renderer, "_draw_curve", capture)
    render_drawing_group(
        DrawingComponentGroup("legacy", [path]),
        Canvas(3.0, 3.0, "in"),
        dpi=20,
        supersample=2,
    )

    assert calls == [([(1.0, 1.0), (2.0, 1.0), (2.0, 2.0)], 40.0)]


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
@pytest.mark.parametrize("linejoin", ["round", "bevel"])
def test_path_nonmiter_joins_render_through_public_api(linejoin: str) -> None:
    """RASTER-PATH-STROKE-P17: Round and bevel source joins reach PNG output."""
    path = PathDrawing(
        _style(linejoin=linejoin),
        [PathCommand("M", [(1.0, 4.0)]), PathCommand("L", [(2.5, 1.0), (4.0, 4.0)])],
    )

    result = render_drawing_group(
        DrawingComponentGroup("join", [path]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=2,
    )

    with result.asset.image() as image:
        assert image.getbbox() is not None


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_nondefault_path_miter_limit_changes_acute_corner_support() -> None:
    """RASTER-PATH-STROKE-P17: Path miters use the requested bevel threshold."""
    commands = [
        PathCommand("M", [(1.0, 4.0)]),
        PathCommand("L", [(2.5, 1.0), (2.8, 4.0)]),
    ]

    high = _render(PathDrawing(_style(miterlimit=20.0), commands))
    low = _render(PathDrawing(_style(miterlimit=1.0), commands))

    assert high != low


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_unsafe_path_miter_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-PATH-STROKE-P17: Generated miter coordinates are preflighted."""
    commands = [
        PathCommand("M", [(53_687_090.0, 1.0)]),
        PathCommand("L", [(53_687_091.1, 1.0), (53_687_091.1, 2.0)]),
    ]
    path = PathDrawing(_style(miterlimit=20.0), commands)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(ValueError, match="safe coordinate range"):
        render_drawing_group(
            DrawingComponentGroup("unsafe-miter", [path]),
            Canvas(2.0, 2.0, "in"),
            dpi=20,
        )


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_path_dashes_remain_outside_p17_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-PATH-STROKE-P17: P17 does not silently add dash continuity."""
    style = _style(linecap="round", linejoin="round")
    style.stroke_dasharray = [0.2, 0.1]
    path = PathDrawing(style, [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(1.0, 1.0)])])
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))

    with pytest.raises(ValueError, match="dashed strokes are supported only"):
        render_drawing_group(
            DrawingComponentGroup("dashed-path", [path]),
            Canvas(2.0, 2.0, "in"),
            dpi=20,
        )


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
@given(
    points=st.lists(
        st.tuples(
            st.integers(min_value=-100, max_value=100).map(float),
            st.integers(min_value=-100, max_value=100).map(float),
        ),
        min_size=2,
        max_size=12,
        unique=True,
    ),
    closed=st.booleans(),
)
def test_linear_path_join_count_is_defined_by_source_segments(
    points: list[tuple[float, float]],
    closed: bool,
) -> None:
    """RASTER-PATH-STROKE-P17: Join cardinality follows source topology."""
    commands = [PathCommand("M", [points[0]]), PathCommand("L", points[1:])]
    if closed:
        commands.append(PathCommand("Z"))
    subpath = raster_renderer._sampled_path_geometry(PathDrawing(_style(), commands))[0]

    expected = len(points) if closed else max(0, len(points) - 2)
    assert len(raster_renderer._semantic_path_join_triples(subpath)) == expected
