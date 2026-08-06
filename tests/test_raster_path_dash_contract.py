"""RASTER-PATH-DASH-P18 conditions for measured raster path dashes."""

from __future__ import annotations

from itertools import count

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import InkGen.raster_renderer as raster_renderer
from InkGen.boundary import Canvas
from InkGen.component import PathCommand
from InkGen.drawing_components import DrawingComponentGroup, PathDrawing, RectangleDrawing
from InkGen.raster_renderer import render_drawing_group
from InkGen.style import DrawingStyle

_STYLE_IDS = count()


def _style(
    *,
    dasharray: tuple[float, ...] = (1.5, 0.5),
    offset: float = 0.0,
    linecap: str = "butt",
    linejoin: str = "miter",
    miterlimit: float = 10.0,
    fill: str = "none",
    fill_opacity: float = 1.0,
    stroke_opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"raster_path_dash_{next(_STYLE_IDS)}",
        stroke="#102030",
        fill=fill,
        stroke_width=0.4,
        stroke_opacity=stroke_opacity,
        fill_opacity=fill_opacity,
        stroke_dasharray=dasharray,
        stroke_dash_offset=offset,
        stroke_linecap=linecap,
        stroke_linejoin=linejoin,
        stroke_miterlimit=miterlimit,
    )


def _path(style: DrawingStyle, commands: list[PathCommand]) -> PathDrawing:
    return PathDrawing(style, commands)


def _geometry(path: PathDrawing) -> tuple[raster_renderer._DashedPathSubpath, ...]:
    dash = raster_renderer._validated_line_dash(path.style)
    assert dash is not None
    return raster_renderer._dashed_path_geometry(raster_renderer._sampled_path_geometry(path), *dash)


def _render(path: PathDrawing, *, dpi: float = 20.0) -> bytes:
    return render_drawing_group(
        DrawingComponentGroup("path-dash", [path]),
        Canvas(6.0, 6.0, "in"),
        dpi=dpi,
        supersample=1,
    ).asset.data


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_dash_distance_continues_across_source_segments_and_joins() -> None:
    """P18: A source command boundary does not restart the dash cursor."""
    path = _path(
        _style(),
        [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(1.0, 0.0), (1.0, 2.0)])],
    )

    dashed = _geometry(path)[0]

    assert dashed.cumulative_distances == (0.0, 1.0, 3.0)
    assert [(run.start_distance, run.end_distance) for run in dashed.runs] == [(0.0, 1.5), (2.0, 3.0)]
    assert dashed.runs[0].sections == (((0.0, 0.0), (1.0, 0.0)), ((1.0, 0.0), (1.0, 0.5)))
    assert [distance for distance, _ in raster_renderer._painted_path_join_records(dashed)] == [1.0]


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_dash_phase_resets_at_every_move_subpath() -> None:
    """P18: SVG/PDF subpaths independently reapply the configured phase."""
    path = _path(
        _style(dasharray=(1.0, 1.0), offset=0.25),
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("L", [(3.0, 0.0)]),
            PathCommand("M", [(0.0, 2.0)]),
            PathCommand("L", [(3.0, 2.0)]),
        ],
    )

    dashed = _geometry(path)

    assert len(dashed) == 2
    assert [[(run.start_distance, run.end_distance) for run in subpath.runs] for subpath in dashed] == [
        [(0.0, 0.75), (1.75, 2.75)],
        [(0.0, 0.75), (1.75, 2.75)],
    ]


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_curve_samples_advance_distance_without_becoming_joins() -> None:
    """P18: Curve tessellation controls length but not source join topology."""
    path = _path(
        _style(dasharray=(100.0, 1.0), linejoin="round"),
        [
            PathCommand("M", [(0.5, 3.0)]),
            PathCommand("Q", [(2.0, 0.5), (3.5, 3.0)]),
            PathCommand("L", [(4.5, 3.0)]),
        ],
    )

    dashed = _geometry(path)[0]

    assert len(dashed.source.points) > 3
    assert len(dashed.runs) == 1
    assert len(dashed.runs[0].sections) == 2
    assert len(raster_renderer._painted_path_join_records(dashed)) == 1


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_dash_endpoint_at_source_vertex_uses_caps_not_a_join() -> None:
    """P18: A vertex exactly at a dash boundary is not inside that dash."""
    path = _path(
        _style(dasharray=(1.0, 1.0), linecap="round", linejoin="round"),
        [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(1.0, 0.0), (1.0, 2.0)])],
    )

    dashed = _geometry(path)[0]

    assert raster_renderer._painted_path_join_records(dashed) == ()
    assert dashed.runs[0].end_distance == 1.0


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_closed_path_joins_only_a_dash_that_crosses_the_seam() -> None:
    """P18: A closed seam is joined only for on-dash continuity across Z."""
    commands = [
        PathCommand("M", [(1.0, 1.0)]),
        PathCommand("L", [(2.0, 1.0), (2.0, 2.0), (1.0, 2.0)]),
        PathCommand("Z"),
    ]

    crossing = _geometry(_path(_style(dasharray=(2.0, 1.0), linejoin="round"), commands))[0]
    boundary = _geometry(_path(_style(dasharray=(1.5, 1.0), linejoin="round"), commands))[0]

    assert crossing.runs[0].wraps_seam is True
    assert crossing.runs[0].closed_cycle is False
    assert [distance for distance, _ in raster_renderer._painted_path_join_records(crossing)] == [0.0, 1.0]
    assert all(not run.wraps_seam for run in boundary.runs)
    assert 0.0 not in [distance for distance, _ in raster_renderer._painted_path_join_records(boundary)]


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_closed_dash_covering_whole_subpath_has_joins_and_no_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    """P18: A single closed on-dash is a joined cycle rather than an open run."""
    path = _path(
        _style(dasharray=(10.0, 1.0), linecap="round", linejoin="round"),
        [PathCommand("M", [(1.0, 1.0)]), PathCommand("L", [(3.0, 1.0), (2.0, 3.0)]), PathCommand("Z")],
    )
    caps: list[object] = []
    monkeypatch.setattr(raster_renderer, "_draw_path_endpoint_cap", lambda *args, **kwargs: caps.append((args, kwargs)))

    dashed = _geometry(path)[0]
    _render(path)

    assert len(dashed.runs) == 1
    assert dashed.runs[0].closed_cycle is True
    assert len(raster_renderer._painted_path_join_records(dashed)) == 3
    assert caps == []


@pytest.mark.condition("RASTER-PATH-DASH-P18")
@pytest.mark.parametrize("linecap", ["round", "square"])
def test_each_open_dash_receives_two_caps(monkeypatch: pytest.MonkeyPatch, linecap: str) -> None:
    """P18: Every positive open dash receives its configured start and end cap."""
    path = _path(
        _style(dasharray=(1.0, 1.0), linecap=linecap),
        [PathCommand("M", [(1.0, 2.0)]), PathCommand("L", [(5.0, 2.0)])],
    )
    caps: list[bool] = []
    original = raster_renderer._draw_path_endpoint_cap

    def capture(*args: object, **kwargs: object) -> None:
        caps.append(bool(kwargs["at_start"]))
        original(*args, **kwargs)

    monkeypatch.setattr(raster_renderer, "_draw_path_endpoint_cap", capture)

    _render(path)

    assert caps == [True, False, True, False]


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_closed_seam_crossing_has_one_join_and_only_gap_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    """P18: A wrapped closed dash joins at Z and caps only its two gap ends."""
    path = _path(
        _style(dasharray=(2.0, 1.0), linecap="round", linejoin="round"),
        [
            PathCommand("M", [(1.0, 1.0)]),
            PathCommand("L", [(2.0, 1.0), (2.0, 2.0), (1.0, 2.0)]),
            PathCommand("Z"),
        ],
    )
    caps: list[bool] = []
    joins: list[tuple[float, float]] = []
    original_cap = raster_renderer._draw_path_endpoint_cap
    original_join = raster_renderer._draw_stroke_join

    def capture_cap(*args: object, **kwargs: object) -> None:
        caps.append(bool(kwargs["at_start"]))
        original_cap(*args, **kwargs)

    def capture_join(*args: object, **kwargs: object) -> None:
        joins.append(args[2])  # type: ignore[arg-type]
        original_join(*args, **kwargs)

    monkeypatch.setattr(raster_renderer, "_draw_path_endpoint_cap", capture_cap)
    monkeypatch.setattr(raster_renderer, "_draw_stroke_join", capture_join)

    _render(path)

    assert caps == [True, False]
    assert joins == [(20.0, 20.0), (40.0, 20.0)]


@pytest.mark.condition("RASTER-PATH-DASH-P18")
@pytest.mark.parametrize("linecap", ["round", "square"])
def test_zero_length_on_dashes_use_the_local_path_tangent(linecap: str) -> None:
    """P18: Zero on-slots produce bounded marks with defined curve orientation."""
    path = _path(
        _style(dasharray=(0.0, 1.0), linecap=linecap),
        [PathCommand("M", [(1.0, 4.0)]), PathCommand("Q", [(1.0, 1.0), (4.0, 1.0)])],
    )

    dashed = _geometry(path)[0]
    output = _render(path)

    assert dashed.zero_dash_distances[0] == 0.0
    assert len(dashed.zero_dash_distances) >= 2
    assert output


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_logical_dash_lengths_scale_with_output_dpi() -> None:
    """P18: Dash lengths remain physical logical units before pixel scaling."""
    path = _path(
        _style(dasharray=(1.0, 1.0)),
        [PathCommand("M", [(0.0, 1.0)]), PathCommand("L", [(4.0, 1.0)])],
    )
    low = render_drawing_group(DrawingComponentGroup("low", [path]), Canvas(5.0, 2.0, "in"), dpi=10, supersample=1)
    high = render_drawing_group(DrawingComponentGroup("high", [path]), Canvas(5.0, 2.0, "in"), dpi=20, supersample=1)

    with low.asset.image() as low_image, high.asset.image() as high_image:
        assert low_image.getpixel((5, 10))[3] > 0
        assert low_image.getpixel((15, 10))[3] == 0
        assert low_image.getpixel((25, 10))[3] > 0
        assert high_image.getpixel((10, 20))[3] > 0
        assert high_image.getpixel((30, 20))[3] == 0
        assert high_image.getpixel((50, 20))[3] > 0


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_move_only_subpath_does_not_invent_a_zero_dash() -> None:
    """P18: M without a drawing command remains transparent under dotted styles."""
    path = _path(_style(dasharray=(0.0, 1.0), linecap="round"), [PathCommand("M", [(2.0, 2.0)])])
    result = render_drawing_group(DrawingComponentGroup("move-only", [path]), Canvas(4.0, 4.0, "in"), dpi=20)

    with result.asset.image() as image:
        assert image.getbbox() is None


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_zero_length_drawing_segment_obeys_current_dash_and_cap() -> None:
    """P18: A degenerate L paints once only when the initial dash is on."""
    on_path = _path(
        _style(dasharray=(1.0, 1.0), linecap="round"),
        [PathCommand("M", [(2.0, 2.0)]), PathCommand("L", [(2.0, 2.0)])],
    )
    gap_path = _path(
        _style(dasharray=(1.0, 1.0), offset=1.0, linecap="round"),
        [PathCommand("M", [(2.0, 2.0)]), PathCommand("L", [(2.0, 2.0)])],
    )

    on = render_drawing_group(DrawingComponentGroup("on", [on_path]), Canvas(4.0, 4.0, "in"), dpi=20)
    gap = render_drawing_group(DrawingComponentGroup("gap", [gap_path]), Canvas(4.0, 4.0, "in"), dpi=20)

    with on.asset.image() as on_image, gap.asset.image() as gap_image:
        assert on_image.getpixel((40, 40))[3] > 0
        assert gap_image.getbbox() is None


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_dashed_stroke_source_over_composites_after_fill() -> None:
    """P18: P12 fill remains below one translucent dashed stroke layer."""
    path = _path(
        _style(
            dasharray=(2.0, 1.0),
            fill="#80A0C0",
            stroke_opacity=0.5,
            linejoin="bevel",
        ),
        [PathCommand("M", [(1.0, 1.0)]), PathCommand("L", [(4.0, 1.0), (2.5, 4.0)]), PathCommand("Z")],
    )
    result = render_drawing_group(
        DrawingComponentGroup("filled-dash", [path]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )

    with result.asset.image() as image:
        assert image.getpixel((20, 20)) == (72, 96, 120, 255)
        assert image.getpixel((50, 40))[:3] == (128, 160, 192)


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_global_dash_operation_limit_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """P18: Multiple subpaths share one pre-allocation dash-work budget."""
    monkeypatch.setattr(raster_renderer, "_MAX_DASH_STEPS", 3)
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    path = _path(
        _style(dasharray=(1.0, 1.0)),
        [
            PathCommand("M", [(0.0, 0.0)]),
            PathCommand("L", [(2.0, 0.0)]),
            PathCommand("M", [(0.0, 1.0)]),
            PathCommand("L", [(2.0, 1.0)]),
        ],
    )

    with pytest.raises(ValueError, match="3-operation limit"):
        render_drawing_group(DrawingComponentGroup("bounded", [path]), Canvas(3.0, 3.0, "in"), dpi=20)


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_dash_operation_limit_accepts_exact_boundary_and_rejects_next(monkeypatch: pytest.MonkeyPatch) -> None:
    """P18: The preflight operation ceiling has an exact inclusive boundary."""
    monkeypatch.setattr(raster_renderer, "_MAX_DASH_STEPS", 3)
    accepted = raster_renderer._path_dash_intervals(3.0, (1.0, 1.0), 0.0, 3, closed=False)

    assert accepted.operation_count == 3
    assert accepted.intervals == ((0.0, 1.0), (2.0, 3.0))
    with pytest.raises(ValueError, match="3-operation limit"):
        raster_renderer._path_dash_intervals(4.0, (1.0, 1.0), 0.0, 3, closed=False)


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_unrepresentable_dash_progress_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """P18: Floating-point stagnation cannot turn the dash walker into a loop."""
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    path = _path(
        _style(dasharray=(1_000_000_000_000.0, 0.000001)),
        [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(10_000_000_000_000_000.0, 0.0)])],
    )

    with pytest.raises(ValueError, match="cannot advance"):
        render_drawing_group(DrawingComponentGroup("stagnant", [path]), Canvas(2.0, 2.0, "in"), dpi=20)


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_miter_preflight_ignores_source_join_inside_a_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    """P18: Derived miter work is limited to source joins crossed by on-dashes."""
    path = _path(
        _style(dasharray=(0.5, 1.0), linejoin="miter", miterlimit=2.0),
        [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(1.0, 0.0), (1.0, 2.0)])],
    )
    monkeypatch.setattr(raster_renderer, "_miter_join_polygon", lambda *args: pytest.fail("gap join constructed"))

    assert _render(path)


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_metric_and_zero_dash_defensive_boundaries() -> None:
    """P18: Nonfinite metrics, duplicate dots, closed seams, and empty edges are explicit."""
    nonfinite = raster_renderer._SampledPathSubpath(
        points=((1e308, 0.0), (-1e308, 0.0)),
        endpoint_indices=(0, 1),
        segment_count=1,
        closed=False,
    )
    with pytest.raises(ValueError, match="length must remain finite"):
        raster_renderer._sampled_path_cumulative_distances(nonfinite)

    assert raster_renderer._zero_length_dash_distances(2.0, (0.0, 1.0), 0.0, 10, closed=True) == (0.0, 1.0)
    assert raster_renderer._zero_length_dash_distances(1.0, (0.0, 1.0), 0.5, 10, closed=False) == (0.5,)
    assert raster_renderer._zero_length_dash_distances(1.0, (0.0, 0.0, 0.0, 1.0), 0.0, 10, closed=False) == (
        0.0,
        1.0,
    )
    with pytest.raises(ValueError, match="operation limit"):
        raster_renderer._zero_length_dash_distances(1.0, (0.0, 1.0), 0.0, 0, closed=False)
    with pytest.raises(ValueError, match="operation limit"):
        raster_renderer._zero_length_dash_distances(0.0, (1.0, 1.0), 0.0, 0, closed=False)

    empty_edge = raster_renderer._SampledPathSubpath(
        points=((2.0, 2.0),),
        endpoint_indices=(0,),
        segment_count=0,
        closed=False,
    )
    assert raster_renderer._path_edge_index((0.0,), 0.0, outgoing=True) is None
    assert raster_renderer._path_point_at_distance(empty_edge, (0.0,), 0.0, outgoing=True) == (2.0, 2.0)
    assert raster_renderer._path_tangent_at_distance(empty_edge, (0.0,), 0.0, outgoing=True) == (1.0, 0.0)
    assert raster_renderer._join_closed_dash_seam(()) == ()


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_metric_edge_search_and_join_scan_skip_degenerate_or_exhausted_ranges() -> None:
    """P18: Duplicate samples and joins beyond the final dash cannot create geometry."""
    assert raster_renderer._path_edge_index((0.0, 1.0, 1.0), 1.0, outgoing=True) == 1
    assert raster_renderer._path_edge_index((0.0, 0.0, 0.0), 0.0, outgoing=False) is None
    assert raster_renderer._flatten_dash_sections((((0.0, 0.0), (1.0, 0.0)), ((1.0, 0.0), (2.0, 0.0)))) == (
        (0.0, 0.0),
        (1.0, 0.0),
        (2.0, 0.0),
    )

    path = _path(
        _style(dasharray=(0.5, 10.0), linejoin="round"),
        [PathCommand("M", [(0.0, 0.0)]), PathCommand("L", [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0)])],
    )
    assert raster_renderer._painted_path_join_records(_geometry(path)[0]) == ()


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_non_path_non_line_dashes_remain_outside_closed_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    """P18: The slice does not silently broaden rectangle dash support."""
    monkeypatch.setattr(raster_renderer.Image, "new", lambda *args, **kwargs: pytest.fail("surface allocated"))
    rectangle = RectangleDrawing((0.0, 0.0), 1.0, 1.0, 0.0, _style())

    with pytest.raises(ValueError, match="LineDrawing P13 or PathDrawing P18"):
        render_drawing_group(DrawingComponentGroup("rectangle", [rectangle]), Canvas(2.0, 2.0, "in"), dpi=20)


@pytest.mark.condition("RASTER-PATH-DASH-P18")
def test_solid_path_keeps_the_p17_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """P18: An empty dash array never reaches the new dash geometry path."""
    path = _path(
        _style(dasharray=()),
        [PathCommand("M", [(1.0, 1.0)]), PathCommand("L", [(4.0, 1.0), (4.0, 4.0)])],
    )
    monkeypatch.setattr(raster_renderer, "_dashed_path_geometry", lambda *args: pytest.fail("dash route used"))

    assert _render(path)


@pytest.mark.condition("RASTER-PATH-DASH-P18")
@settings(max_examples=100, deadline=None)
@given(
    length=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
    pattern=st.lists(
        st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=6,
    ).filter(lambda values: len(values) % 2 == 0),
    offset=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
)
def test_dash_intervals_are_ordered_bounded_and_nonoverlapping(
    length: float,
    pattern: list[float],
    offset: float,
) -> None:
    """P18: Every generated dash is an ordered subset of its finite subpath."""
    result = raster_renderer._path_dash_intervals(length, tuple(pattern), offset, 100_000, closed=False)

    previous_end = 0.0
    for start, end in result.intervals:
        assert 0.0 <= start < end <= length
        assert start >= previous_end
        previous_end = end
    assert result.operation_count <= 100_000
    assert result.joins_closed_seam is False
