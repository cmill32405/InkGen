import pytest
from shapely.geometry import box as shapely_box

from InkGen.boundary import Boundary


def _summarize(inner, candidate):
    boundary = Boundary(list(inner.exterior.coords), outer_boundary=False)
    hull_points = list(candidate.exterior.coords)
    return {
        "boundary_check": boundary.boundary_check(hull_points, strict=False),
        "boundary_check_strict": boundary.boundary_check(hull_points, strict=True),
        "covers": inner.covers(candidate),
        "contains": inner.contains(candidate),
        "within": candidate.within(inner),
        "touches": inner.touches(candidate),
        "intersects": inner.intersects(candidate),
    }


@pytest.fixture
def rectangle_boundary():
    return shapely_box(0.0, 0.0, 10.0, 10.0)


def test_boundary_checks_inside(rectangle_boundary):
    candidate = shapely_box(2.0, 2.0, 8.0, 8.0)
    summary = _summarize(rectangle_boundary, candidate)
    assert summary == {
        "boundary_check": True,
        "boundary_check_strict": True,
        "covers": True,
        "contains": True,
        "within": True,
        "touches": False,
        "intersects": True,
    }


def test_boundary_checks_crossing(rectangle_boundary):
    candidate = shapely_box(-1.0, 2.0, 5.0, 8.0)
    summary = _summarize(rectangle_boundary, candidate)
    assert summary == {
        "boundary_check": False,
        "boundary_check_strict": False,
        "covers": False,
        "contains": False,
        "within": False,
        "touches": False,
        "intersects": True,
    }


def test_boundary_checks_touching(rectangle_boundary):
    candidate = shapely_box(0.0, 2.0, 6.0, 8.0)
    summary = _summarize(rectangle_boundary, candidate)
    assert summary == {
        "boundary_check": True,
        "boundary_check_strict": False,
        "covers": True,
        "contains": True,
        "within": True,
        "touches": False,
        "intersects": True,
    }
