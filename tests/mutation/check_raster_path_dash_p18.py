"""Fast deterministic witnesses for measured raster path dashes P18."""

from __future__ import annotations

import hashlib
import sys
from importlib.util import module_from_spec, spec_from_file_location
from itertools import count
from pathlib import Path
from types import ModuleType

from check_raster_path_stroke_p17 import main as path_stroke_main

import InkGen.raster_renderer as rr
from InkGen.boundary import Canvas
from InkGen.component import PathCommand
from InkGen.drawing_components import DrawingComponentGroup, PathDrawing, RectangleDrawing
from InkGen.style import DrawingStyle

_STYLE_IDS = count()
STROKE = (16, 32, 48, 255)


class _RecordingDraw:
    """Record exact Pillow drawing calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def line(self, points: object, *, fill: object, width: int) -> None:
        self.calls.append(("line", list(points), fill, width))  # type: ignore[arg-type]

    def ellipse(self, box: object, *, fill: object) -> None:
        self.calls.append(("ellipse", box, fill))

    def polygon(self, points: object, *, fill: object) -> None:
        self.calls.append(("polygon", list(points), fill))  # type: ignore[arg-type]


def _style(
    *,
    dash: tuple[float, ...] = (1.5, 0.5),
    offset: float = 0.0,
    cap: str = "butt",
    join: str = "miter",
    limit: float = 10.0,
    fill: str = "none",
    stroke_opacity: float = 1.0,
) -> DrawingStyle:
    return DrawingStyle(
        f"mutation-path-dash-{next(_STYLE_IDS)}",
        fill=fill,
        stroke="#102030",
        stroke_width=0.4,
        stroke_opacity=stroke_opacity,
        stroke_dasharray=dash,
        stroke_dash_offset=offset,
        stroke_linecap=cap,
        stroke_linejoin=join,
        stroke_miterlimit=limit,
    )


def _path(style: DrawingStyle, *, closed: bool = False, two_subpaths: bool = False) -> PathDrawing:
    commands = [
        PathCommand("M", [(0.0, 0.0)]),
        PathCommand("L", [(1.0, 0.0), (1.0, 2.0)]),
    ]
    if closed:
        commands.append(PathCommand("Z"))
    if two_subpaths:
        commands.extend((PathCommand("M", [(0.0, 3.0)]), PathCommand("L", [(1.0, 3.0), (1.0, 5.0)])))
    return PathDrawing(style, commands)


def _geometry(path: PathDrawing) -> tuple[rr._DashedPathSubpath, ...]:
    dash = rr._validated_line_dash(path.style)
    assert dash is not None
    return rr._dashed_path_geometry(rr._sampled_path_geometry(path), *dash)


def _raises(error: type[Exception], call: object, text: str) -> None:
    try:
        call()  # type: ignore[operator]
    except error as exc:
        assert text in str(exc)
        return
    raise AssertionError(f"expected {error.__name__}")


def _assert_metric_partition() -> None:
    subpath = rr._SampledPathSubpath(((0.0, 0.0), (1.0, 0.0), (1.0, 2.0)), (0, 1, 2), 2, False)
    cumulative = rr._sampled_path_cumulative_distances(subpath)
    assert cumulative == (0.0, 1.0, 3.0)
    intervals = rr._path_dash_intervals(3.0, (1.5, 0.5), 0.0, 4, closed=False)
    assert intervals == rr._DashIntervals(((0.0, 1.5), (2.0, 3.0)), 3, False)
    assert rr._path_dash_intervals(0.0, (1.0, 1.0), 0.0, 0, closed=True) == rr._DashIntervals((), 0, False)
    _raises(ValueError, lambda: rr._path_dash_intervals(4.0, (1.0, 1.0), 0.0, 3, closed=False), "operation limit")
    _raises(
        ValueError,
        lambda: rr._path_dash_intervals(1e16, (1e12, 0.000001), 0.0, 100_000, closed=False),
        "cannot advance",
    )

    nonfinite = rr._SampledPathSubpath(((1e308, 0.0), (-1e308, 0.0)), (0, 1), 1, False)
    _raises(ValueError, lambda: rr._sampled_path_cumulative_distances(nonfinite), "length must remain finite")


def _assert_zero_dashes() -> None:
    assert rr._zero_length_dash_distances(2.0, (0.0, 1.0), 0.0, 10, closed=False) == (0.0, 1.0, 2.0)
    assert rr._zero_length_dash_distances(2.0, (0.0, 1.0), 0.0, 10, closed=True) == (0.0, 1.0)
    assert rr._zero_length_dash_distances(1.0, (0.0, 1.0), 0.5, 10, closed=False) == (0.5,)
    assert rr._zero_length_dash_distances(1.0, (0.0, 0.0, 0.0, 1.0), 0.0, 10, closed=False) == (0.0, 1.0)
    assert rr._zero_length_dash_distances(0.0, (1.0, 1.0), 0.0, 1, closed=False) == (0.0,)
    assert rr._zero_length_dash_distances(0.0, (1.0, 1.0), 1.0, 0, closed=False) == ()
    _raises(ValueError, lambda: rr._zero_length_dash_distances(1.0, (0.0, 1.0), 0.0, 0, closed=False), "operation limit")


def _assert_metric_geometry() -> None:
    subpath = rr._SampledPathSubpath(((0.0, 0.0), (0.0, 0.0), (2.0, 0.0), (2.0, 2.0)), (0, 2, 3), 2, False)
    cumulative = rr._sampled_path_cumulative_distances(subpath)
    assert cumulative == (0.0, 0.0, 2.0, 4.0)
    assert rr._path_edge_index(cumulative, 0.0, outgoing=True) == 2
    assert rr._path_edge_index(cumulative, 2.0, outgoing=False) == 2
    assert rr._path_edge_index((0.0,), 0.0, outgoing=True) is None
    assert rr._path_edge_index((0.0, 0.0), 0.0, outgoing=False) is None
    assert rr._path_point_at_distance(subpath, cumulative, 1.0, outgoing=True) == (1.0, 0.0)
    assert rr._path_point_at_distance(subpath, cumulative, -1.0, outgoing=True) == (0.0, 0.0)
    assert rr._path_point_at_distance(subpath, cumulative, 5.0, outgoing=False) == (2.0, 2.0)
    assert rr._path_tangent_at_distance(subpath, cumulative, 0.0, outgoing=True) == (1.0, 0.0)
    assert rr._path_tangent_at_distance(subpath, cumulative, 4.0, outgoing=False) == (0.0, 1.0)
    assert rr._path_points_between(subpath, cumulative, 1.0, 3.0) == ((1.0, 0.0), (2.0, 0.0), (2.0, 1.0))

    empty = rr._SampledPathSubpath(((2.0, 2.0),), (0,), 0, False)
    assert rr._path_point_at_distance(empty, (0.0,), 0.0, outgoing=True) == (2.0, 2.0)
    assert rr._path_tangent_at_distance(empty, (0.0,), 0.0, outgoing=True) == (1.0, 0.0)


def _assert_runs_and_joins() -> None:
    dashed = _geometry(_path(_style()))[0]
    assert dashed.cumulative_distances == (0.0, 1.0, 3.0)
    assert [(run.start_distance, run.end_distance) for run in dashed.runs] == [(0.0, 1.5), (2.0, 3.0)]
    assert dashed.runs[0].sections == (((0.0, 0.0), (1.0, 0.0)), ((1.0, 0.0), (1.0, 0.5)))
    records = rr._path_join_records_with_distances(dashed.source, dashed.cumulative_distances)
    assert records[0][0] == 1.0 and len(records) == 1
    assert [distance for distance, _ in rr._painted_path_join_records(dashed)] == [1.0]

    boundary = _geometry(_path(_style(dash=(1.0, 1.0), cap="round", join="round")))[0]
    assert rr._painted_path_join_records(boundary) == ()
    assert rr._flatten_dash_sections(dashed.runs[0].sections) == ((0.0, 0.0), (1.0, 0.0), (1.0, 0.5))

    two = _geometry(_path(_style(dash=(1.0, 1.0), offset=0.25), two_subpaths=True))
    assert len(two) == 2
    assert [run.start_distance for run in two[0].runs] == [0.0, 1.75]
    assert [run.start_distance for run in two[1].runs] == [0.0, 1.75]


def _assert_closed_seams() -> None:
    commands = [
        PathCommand("M", [(1.0, 1.0)]),
        PathCommand("L", [(2.0, 1.0), (2.0, 2.0), (1.0, 2.0)]),
        PathCommand("Z"),
    ]
    crossing = _geometry(PathDrawing(_style(dash=(2.0, 1.0), join="round"), commands))[0]
    assert crossing.joins_closed_seam is True
    assert crossing.runs[0].wraps_seam is True and crossing.runs[0].closed_cycle is False
    assert [distance for distance, _ in rr._painted_path_join_records(crossing)] == [0.0, 1.0]

    boundary = _geometry(PathDrawing(_style(dash=(1.5, 1.0), join="round"), commands))[0]
    assert boundary.joins_closed_seam is False
    assert all(not run.wraps_seam for run in boundary.runs)

    cycle = _geometry(PathDrawing(_style(dash=(10.0, 1.0), cap="round", join="round"), commands))[0]
    assert len(cycle.runs) == 1
    assert cycle.runs[0].wraps_seam is True and cycle.runs[0].closed_cycle is True
    assert len(rr._painted_path_join_records(cycle)) == 4
    assert rr._join_closed_dash_seam(()) == ()


def _assert_draw_dispatch() -> None:
    style = _style(dash=(1.0, 1.0), cap="round", join="round")
    geometry = _geometry(_path(style))[0]
    draw = _RecordingDraw()
    rr._draw_dashed_path_subpath(draw, geometry, style, 10.0, STROKE, 4)  # type: ignore[arg-type]
    kinds = [call[0] for call in draw.calls]
    assert kinds.count("line") == 2
    assert kinds.count("ellipse") == 4
    assert kinds.count("polygon") == 0

    dotted_style = _style(dash=(0.0, 1.0), cap="square")
    dotted = _RecordingDraw()
    rr._draw_path_strokes(dotted, rr._sampled_path_geometry(_path(dotted_style)), dotted_style, 10.0, STROKE, 4)  # type: ignore[arg-type]
    assert [call[0] for call in dotted.calls] == ["polygon", "polygon", "polygon", "polygon"]

    solid_style = _style(dash=())
    solid = _RecordingDraw()
    rr._draw_path_strokes(solid, rr._sampled_path_geometry(_path(solid_style)), solid_style, 10.0, STROKE, 4)  # type: ignore[arg-type]
    assert [call[0] for call in solid.calls] == ["line"]


def _assert_validation() -> None:
    path = _path(_style(limit=2.0))
    rr._validate_raster_stroke_style(path, path.style, 20.0)
    gap_style = _style(dash=(0.5, 1.0), limit=2.0)
    gap_path = _path(gap_style)
    rr._validate_raster_stroke_style(gap_path, gap_style, 20.0)

    rectangle = RectangleDrawing((0.0, 0.0), 1.0, 1.0, 0.0, _style())
    _raises(ValueError, lambda: rr._validate_raster_stroke_style(rectangle, rectangle.style), "LineDrawing P13 or PathDrawing P18")

    old_limit = rr._MAX_DASH_STEPS
    rr._MAX_DASH_STEPS = 3
    try:
        _raises(
            ValueError,
            lambda: rr._dashed_path_geometry(rr._sampled_path_geometry(_path(_style(dash=(1.0, 1.0)), two_subpaths=True)), (1.0, 1.0), 0.0),
            "3-operation limit",
        )
    finally:
        rr._MAX_DASH_STEPS = old_limit


def _digest(path: PathDrawing) -> str:
    result = rr.render_drawing_group(
        DrawingComponentGroup("mutation-path-dash", [path]),
        Canvas(6.0, 6.0, "in"),
        dpi=20,
        supersample=1,
    )
    return hashlib.sha256(result.asset.data).hexdigest()


def _assert_public_outputs() -> None:
    outputs = {
        "plain": _digest(_path(_style())),
        "offset": _digest(_path(_style(offset=0.25))),
        "round": _digest(_path(_style(cap="round", join="round"))),
        "square": _digest(_path(_style(cap="square", join="bevel"))),
        "closed": _digest(_path(_style(cap="round", join="round"), closed=True)),
        "filled": _digest(_path(_style(fill="#80A0C0", stroke_opacity=0.5), closed=True)),
    }
    assert len(set(outputs.values())) == len(outputs)

    filled = PathDrawing(
        _style(dash=(2.0, 1.0), fill="#80A0C0", stroke_opacity=0.5, join="bevel"),
        [PathCommand("M", [(1.0, 1.0)]), PathCommand("L", [(4.0, 1.0), (2.5, 4.0)]), PathCommand("Z")],
    )
    result = rr.render_drawing_group(
        DrawingComponentGroup("mutation-filled-dash", [filled]),
        Canvas(5.0, 5.0, "in"),
        dpi=20,
        supersample=1,
    )
    with result.asset.image() as image:
        assert image.getpixel((20, 20)) == (72, 96, 120, 255)
        assert image.getpixel((50, 40))[:3] == (128, 160, 192)


class _UnusedStrategy:
    """Satisfy property-decorator construction without running Hypothesis."""

    def __getattr__(self, name: str) -> object:
        del name
        return lambda *args, **kwargs: self

    def filter(self, predicate: object) -> _UnusedStrategy:
        del predicate
        return self


def _load_condition_module() -> object:
    """Import deterministic P18 conditions without a mutation-env dependency."""
    hypothesis = ModuleType("hypothesis")
    decorator = lambda *args, **kwargs: lambda function: function  # noqa: E731
    hypothesis.given = decorator  # type: ignore[attr-defined]
    hypothesis.settings = decorator  # type: ignore[attr-defined]
    hypothesis.strategies = _UnusedStrategy()  # type: ignore[attr-defined]
    previous = sys.modules.get("hypothesis")
    sys.modules["hypothesis"] = hypothesis
    try:
        path = Path(__file__).resolve().parents[1] / "test_raster_path_dash_contract.py"
        spec = spec_from_file_location("_p18_condition_tests", path)
        assert spec is not None and spec.loader is not None
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            del sys.modules["hypothesis"]
        else:
            sys.modules["hypothesis"] = previous


def _assert_condition_suite() -> None:
    """Run every deterministic P18 condition against the mutated module."""
    import pytest

    conditions = _load_condition_module()
    direct_names = (
        "test_dash_distance_continues_across_source_segments_and_joins",
        "test_dash_phase_resets_at_every_move_subpath",
        "test_curve_samples_advance_distance_without_becoming_joins",
        "test_dash_endpoint_at_source_vertex_uses_caps_not_a_join",
        "test_closed_path_joins_only_a_dash_that_crosses_the_seam",
        "test_logical_dash_lengths_scale_with_output_dpi",
        "test_move_only_subpath_does_not_invent_a_zero_dash",
        "test_zero_length_drawing_segment_obeys_current_dash_and_cap",
        "test_dashed_stroke_source_over_composites_after_fill",
        "test_metric_and_zero_dash_defensive_boundaries",
        "test_metric_edge_search_and_join_scan_skip_degenerate_or_exhausted_ranges",
    )
    for name in direct_names:
        getattr(conditions, name)()
    for linecap in ("round", "square"):
        conditions.test_zero_length_on_dashes_use_the_local_path_tangent(linecap)
        with pytest.MonkeyPatch.context() as monkeypatch:
            conditions.test_each_open_dash_receives_two_caps(monkeypatch, linecap)
    monkeypatch_names = (
        "test_closed_dash_covering_whole_subpath_has_joins_and_no_caps",
        "test_closed_seam_crossing_has_one_join_and_only_gap_caps",
        "test_global_dash_operation_limit_fails_before_surface_allocation",
        "test_dash_operation_limit_accepts_exact_boundary_and_rejects_next",
        "test_unrepresentable_dash_progress_fails_before_surface_allocation",
        "test_miter_preflight_ignores_source_join_inside_a_gap",
        "test_non_path_non_line_dashes_remain_outside_closed_domain",
        "test_solid_path_keeps_the_p17_dispatch",
    )
    for name in monkeypatch_names:
        with pytest.MonkeyPatch.context() as monkeypatch:
            getattr(conditions, name)(monkeypatch)


def _assert_survivor_boundaries() -> None:
    """Distinguish arithmetic and dispatch alternatives from closed semantics."""
    assert rr._path_dash_intervals(-1.0, (1.0, 1.0), 0.0, 0, closed=False) == rr._DashIntervals((), 0, False)
    assert rr._path_dash_intervals(1.5, (1.0, 1.0), 1.0, 10, closed=True) == rr._DashIntervals(
        ((1.0, 1.5),),
        2,
        False,
    )
    assert rr._path_dash_intervals(0.5, (1.0, 1.0, 2.0, 1.0), 2.0, 10, closed=True) == rr._DashIntervals(
        ((0.0, 0.5),),
        1,
        True,
    )
    _raises(
        ValueError,
        lambda: rr._path_dash_intervals(2_001.0, (1.0, 1.0), 0.0, 1_000, closed=False),
        "operation limit",
    )
    assert rr._zero_length_dash_distances(6.0, (1.0, 1.0, 0.0, 2.0), 0.0, 10, closed=False) == (2.0, 6.0)
    assert rr._zero_length_dash_distances(6.0, (1.0, 1.0, 0.0, 2.0), 0.5, 10, closed=False) == (1.5, 5.5)
    assert rr._zero_length_dash_distances(3.0, (1.0, 0.0, 1.0, 1.0), 0.0, 10, closed=False) == ()
    assert rr._zero_length_dash_distances(2.0, (0.0, 3.0), 2.0, 10, closed=False) == (1.0,)
    assert rr._zero_length_dash_distances(0.0, (1.0, 1.0, 2.0, 1.0), 2.0, 10, closed=False) == (0.0,)
    assert rr._zero_length_dash_distances(2.0, (0.0, 2.0), 0.0, 10, closed=True) == (0.0,)
    _raises(
        ValueError,
        lambda: rr._zero_length_dash_distances(2.0, (0.0, 1.0), 0.0, 1, closed=False),
        "operation limit",
    )
    _raises(
        ValueError,
        lambda: rr._zero_length_dash_distances(1_000.0, (0.0, 1.0), 0.0, 1_000, closed=False),
        "operation limit",
    )

    source = rr._SampledPathSubpath(((0.0, 0.0), (2.0, 0.0)), (0, 1), 1, False)
    dotted, operations = rr._dashed_path_subpath(source, (0.0, 1.0), 0.0, 10)
    assert operations == 5
    assert dotted.zero_dash_distances == (0.0, 1.0, 2.0)
    move = rr._SampledPathSubpath(((1.0, 1.0),), (0,), 0, False)
    move_dash, move_operations = rr._dashed_path_subpath(move, (1.0, 1.0), 0.0, 10)
    assert move_operations == 0
    assert move_dash == rr._DashedPathSubpath(move, (0.0,), (), (), (), False)
    _raises(
        ValueError,
        lambda: rr._dashed_path_subpath(source, (1.0, 1.0, 0.0, 2.0), 0.0, 2),
        "operation limit",
    )

    cumulative = (0.0, 0.0, 2.0, 2.0, 5.0)
    assert rr._path_edge_index(cumulative, -1.0, outgoing=True) == 2
    assert rr._path_edge_index(cumulative, 0.0, outgoing=False) == 2
    assert rr._path_edge_index(cumulative, 2.0, outgoing=True) == 4
    assert rr._path_edge_index(cumulative, 5.0, outgoing=False) == 4

    descending = rr._SampledPathSubpath(((2.0, 0.0), (1.0, 0.0), (0.0, 0.0)), (0, 1, 2), 2, False)
    assert rr._path_points_between(descending, (0.0, 1.0, 2.0), 0.0, 2.0) == (
        (2.0, 0.0),
        (1.0, 0.0),
        (0.0, 0.0),
    )
    duplicate = rr._SampledPathSubpath(((0.0, 0.0), (0.0, 0.0)), (0, 1), 1, False)
    assert rr._path_points_between(duplicate, (0.0, 0.0), 0.0, 0.0) == ((0.0, 0.0),)
    first_duplicate = (1.0, 0.0)
    second_duplicate = tuple([1.0, 0.0])
    assert first_duplicate == second_duplicate and first_duplicate is not second_duplicate
    distinct_duplicates = rr._SampledPathSubpath(
        ((0.0, 0.0), first_duplicate, second_duplicate, (2.0, 0.0)),
        (0, 1, 2, 3),
        3,
        False,
    )
    assert rr._path_points_between(distinct_duplicates, (0.0, 1.0, 1.0, 2.0), 0.0, 2.0) == (
        (0.0, 0.0),
        (1.0, 0.0),
        (2.0, 0.0),
    )
    closed = rr._SampledPathSubpath(
        ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 0.0)),
        (0, 1, 2),
        3,
        True,
    )
    assert rr._path_points_between(closed, (0.0, 1.0, 2.0, 2.0 + 2.0**0.5), 0.0, 2.0 + 2.0**0.5)[-1] == (
        0.0,
        0.0,
    )

    corner = rr._SampledPathSubpath(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0)), (0, 1, 2), 2, False)
    start_corner = rr._path_dash_run(corner, (0.0, 1.0, 2.0), (1.0,), 1.0, 2.0)
    end_corner = rr._path_dash_run(corner, (0.0, 1.0, 2.0), (1.0,), 0.0, 1.0)
    assert start_corner.start_tangent == (0.0, 1.0)
    assert len(start_corner.sections) == 1
    assert end_corner.end_tangent == (1.0, 0.0)
    assert len(rr._path_dash_run(corner, (0.0, 1.0, 2.0), (2.0, 3.0), 0.0, 2.0).sections) == 1

    interval_source = rr._SampledPathSubpath(
        ((0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)),
        (0, 1, 2, 3),
        3,
        False,
    )
    interval_dash = rr._DashedPathSubpath(
        interval_source,
        (0.0, 1.0, 2.0, 3.0),
        ((0.0, 0.5), (1.5, 2.5)),
        (),
        (),
        False,
    )
    assert [distance for distance, _ in rr._painted_path_join_records(interval_dash)] == [2.0]

    large_source = rr._SampledPathSubpath(((0.0, 0.0), (1_000.0, 0.0), (0.0, 0.0)), (0, 1), 2, True)
    many_intervals = tuple((float(index * 2), float(index * 2 + 1)) for index in range(300))
    large_dash = rr._DashedPathSubpath(large_source, (0.0, 1_000.0, 2_000.0), many_intervals, (), (), False)
    assert rr._painted_path_join_records(large_dash) == ()

    assert rr._flatten_dash_sections((((2.0, 0.0), (1.0, 0.0)), ((1.0, 0.0), (0.0, 0.0)))) == (
        (2.0, 0.0),
        (1.0, 0.0),
        (0.0, 0.0),
    )


def _assert_exact_drawing_operations() -> None:
    """Record section dispatch, join scaling, cap endpoints, and miter preflight."""
    default_style = _style(dash=(1.5, 0.5))
    default_geometry = _geometry(_path(default_style))[0]
    default_draw = _RecordingDraw()
    rr._draw_dashed_path_subpath(default_draw, default_geometry, default_style, 10.0, STROKE, 4)  # type: ignore[arg-type]
    assert [call[0] for call in default_draw.calls].count("line") == 2

    for join, limit in (("round", 10.0), ("bevel", 10.0), ("miter", 9.0), ("miter", 11.0)):
        style = _style(dash=(1.5, 0.5), join=join, limit=limit)
        draw = _RecordingDraw()
        rr._draw_dashed_path_subpath(draw, _geometry(_path(style))[0], style, 10.0, STROKE, 4)  # type: ignore[arg-type]
        assert [call[0] for call in draw.calls].count("line") == 3

    dynamic_miter = "".join(("mi", "ter"))
    style = _style(dash=(1.5, 0.5))
    style._stroke_linejoin = dynamic_miter
    draw = _RecordingDraw()
    rr._draw_dashed_path_subpath(draw, _geometry(_path(style))[0], style, 10.0, STROKE, 4)  # type: ignore[arg-type]
    assert [call[0] for call in draw.calls].count("line") == 2

    dynamic_butt = "".join(("bu", "tt"))
    capped_style = _style(dash=(1.5, 0.5), cap="round")
    captured_caps: list[tuple[object, ...]] = []
    original_cap = rr._draw_path_endpoint_cap
    rr._draw_path_endpoint_cap = lambda *args, **kwargs: captured_caps.append((*args, kwargs))  # type: ignore[assignment]
    try:
        rr._draw_dashed_path_subpath(
            _RecordingDraw(),
            _geometry(_path(capped_style))[0],
            capped_style,
            10.0,
            STROKE,
            4,
        )  # type: ignore[arg-type]
        butt_style = _style(dash=(1.5, 0.5))
        butt_style._stroke_linecap = dynamic_butt
        before = len(captured_caps)
        rr._draw_dashed_path_subpath(
            _RecordingDraw(),
            _geometry(_path(butt_style))[0],
            butt_style,
            10.0,
            STROKE,
            4,
        )  # type: ignore[arg-type]
        assert len(captured_caps) == before
    finally:
        rr._draw_path_endpoint_cap = original_cap
    assert captured_caps[0][1] == (0.0, 0.0)
    assert captured_caps[1][1] == (10.0, 5.0)

    zero_corner_style = _style(dash=(0.0, 1.0), cap="square")
    zero_corner = _geometry(_path(zero_corner_style))[0]
    zero_marks: list[tuple[object, ...]] = []
    original_segment = rr._draw_capped_segment
    rr._draw_capped_segment = lambda *args: zero_marks.append(args)  # type: ignore[assignment]
    try:
        rr._draw_dashed_path_subpath(
            _RecordingDraw(),
            zero_corner,
            zero_corner_style,
            10.0,
            STROKE,
            4,
        )  # type: ignore[arg-type]
    finally:
        rr._draw_capped_segment = original_segment
    assert zero_marks[1][-1] == (0.0, 1.0)

    curve_style = _style(dash=(100.0, 1.0), cap="round")
    curve = PathDrawing(
        curve_style,
        [PathCommand("M", [(1.0, 4.0)]), PathCommand("Q", [(1.0, 1.0), (4.0, 1.0)])],
    )
    caps: list[tuple[object, ...]] = []
    original_cap = rr._draw_path_endpoint_cap
    rr._draw_path_endpoint_cap = lambda *args, **kwargs: caps.append((*args, kwargs))  # type: ignore[assignment]
    try:
        rr._draw_dashed_path_subpath(_RecordingDraw(), _geometry(curve)[0], curve_style, 10.0, STROKE, 4)  # type: ignore[arg-type]
    finally:
        rr._draw_path_endpoint_cap = original_cap
    assert caps[0][1] == (10.0, 40.0)
    assert caps[1][1] == (40.0, 10.0)

    miter_style = _style(dash=(100.0, 1.0), limit=2.0)
    dashed = _geometry(_path(miter_style))[0]
    miters: list[tuple[object, ...]] = []
    original_miter = rr._miter_join_polygon
    rr._miter_join_polygon = lambda *args: miters.append(args) or []  # type: ignore[assignment]
    try:
        rr._validate_dashed_path_miter_geometry((dashed,), 3.0, 4, 2.0)
    finally:
        rr._miter_join_polygon = original_miter
    assert miters == [((0.0, 0.0), (3.0, 0.0), (3.0, 6.0), 4, 2.0)]


def _assert_exact_seam_merge() -> None:
    """Prove closed-seam run ordering and metadata without pixel ambiguity."""
    first = rr._DashedPathRun((((0.0, 0.0), (1.0, 0.0)),), 0.0, 1.0, (1.0, 0.0), (1.0, 0.0))
    middle = rr._DashedPathRun((((2.0, 0.0), (3.0, 0.0)),), 2.0, 3.0, (1.0, 0.0), (1.0, 0.0))
    last = rr._DashedPathRun((((4.0, 0.0), (5.0, 0.0)),), 4.0, 5.0, (1.0, 0.0), (1.0, 0.0))
    merged = rr._join_closed_dash_seam((first, middle, last))
    assert merged == (
        rr._DashedPathRun(
            (*last.sections, *first.sections),
            4.0,
            1.0,
            last.start_tangent,
            first.end_tangent,
            wraps_seam=True,
        ),
        middle,
    )
    cycle = rr._join_closed_dash_seam((middle,))
    assert cycle == (
        rr._DashedPathRun(
            middle.sections,
            middle.start_distance,
            middle.end_distance,
            middle.start_tangent,
            middle.end_tangent,
            wraps_seam=True,
            closed_cycle=True,
        ),
    )


def main() -> None:
    path_stroke_main()
    _assert_metric_partition()
    _assert_zero_dashes()
    _assert_metric_geometry()
    _assert_runs_and_joins()
    _assert_closed_seams()
    _assert_draw_dispatch()
    _assert_validation()
    _assert_public_outputs()
    _assert_condition_suite()
    _assert_survivor_boundaries()
    _assert_exact_drawing_operations()
    _assert_exact_seam_merge()


if __name__ == "__main__":
    main()
