import pytest

from InkGen.boundary import Boundary, Canvas
from InkGen.errors import IllegalArgumentError, InvalidConvexHull

##### Test Boundary Class ########

def test_create_boundary_object():
    boundary = Boundary([(0.0, 0.0), (1, 0), (0, 1), (1,1)])
    assert boundary.boundary_points == [(0.0, 0.0), (1, 0), (0, 1), (1,1)]
    assert boundary.boundary_type == "inner"

def test_create_boundary_object_with_inner_boundary():
    boundary = Boundary([(0.0, 0.0), (1, 0), (0, 1), (1,1)], True)
    assert boundary.boundary_points == [(0.0, 0.0), (1, 0), (0, 1), (1,1)]
    assert boundary.boundary_type == "outer"

def test_create_boundary_raises_invalid_convex_hull():
    with pytest.raises(InvalidConvexHull):
        Boundary([(0.0, 0.0), (1, 0), (0.5, 0.5), (0, 1), (1, 1)])

def test_create_boundary_raises_invalid_argument():
    with pytest.raises(InvalidConvexHull):
        Boundary([("0.0", 0.0), (1, 0), (0.5, 0.5), (0, 1), (1, 1)], False)

def test_create_boundary_raises_invalid_type():
    with pytest.raises(TypeError):
        Boundary([(0.0, 0.0), (1, 0), (0.5, 0.5), (0, 1), (1, 1)], "False")

def test_boundary_check_clear():
    boundary = Boundary([(0.0, 0.0), (270, 0), (270,650),(0, 650)], True)
    check_list = [(-1, -1), (290, -1), (290, 800), (-1, 800)]
    assert boundary.boundary_check(check_list)

    boundary = Boundary([(0.0, 0.0), (270, 0), (270,650),(0, 650)], False)
    check_list = [(1, 1), (250, 1), (250, 600), (1, 600)]
    assert boundary.boundary_check(check_list)

def test_boundary_check_false():
    boundary = Boundary([(0.0, 0.0), (270, 0), (270,650),(0, 650)], True)
    check_list = [(-1, 1), (290, -1), (290, 800), (-1, 800)]
    assert not boundary.boundary_check(check_list)

    boundary = Boundary([(0.0, 0.0), (270, 0), (270,650),(0, 650)], False)
    check_list = [(1, -1), (250, 1), (250, 600), (1, 600)]
    assert not boundary.boundary_check(check_list)

def test_strict_boundary_check():
    boundary = Boundary([(0.0, 0.0), (270, 0), (270,650),(0, 650)], True)
    check_list = [(0, 0), (0, 0), (290, -1), (290, 800), (-1, 800)]
    assert not boundary.boundary_check(check_list, True)

    boundary = Boundary([(0.0, 0.0), (270, 0), (270,650),(0, 650)], False)
    check_list = [(1, 1), (50,0), (250, 1), (250, 600), (1, 600)]
    assert not boundary.boundary_check(check_list, True)


##### Test Canvas Class ########

def test_create_canvas_object_with_mm_units():
    canvas = Canvas(200, 300, "mm")
    assert canvas.width == 200
    assert canvas.height == 300
    assert canvas.units == "mm"

def test_create_canvas_object_with_metric_units():
    canvas = Canvas(200, 300, "Metric")
    assert canvas.width == 200
    assert canvas.height == 300
    assert canvas.units == "mm"

def test_create_canvas_object_with_in_units():
    canvas = Canvas(200, 300, "in")
    assert canvas.width == 200
    assert canvas.height == 300
    assert canvas.units == "in"

def test_create_canvas_object_with_inch_units():
    canvas = Canvas(200, 300, "Inch")
    assert canvas.width == 200
    assert canvas.height == 300
    assert canvas.units == "in"

def test_create_canvas_object_with_imperial_units():
    canvas = Canvas(200, 300, "imperiaL")
    assert canvas.width == 200
    assert canvas.height == 300
    assert canvas.units == "in"

def test_create_canvas_raises_type_error_width():
    with pytest.raises(TypeError):
        Canvas("200", 300, "mm")

def test_create_canvas_raises_type_error_height():
    with pytest.raises(TypeError):
        Canvas(200, "300", "mm")

def test_create_canvas_raises_value_error_unit():
    with pytest.raises(IllegalArgumentError):
        Canvas(200, 300, "milli")

def test_save_and_recreate_canvas_object():
    canvas = Canvas(200, 300, "mm")
    canvas_dict = canvas.parameters
    assert canvas.parameters == {"Canvas": {"width": 200, "height": 300, "units": "mm"}}

    canvas_2 = Canvas.create_from_dict(canvas_dict)
    assert canvas_2.width == 200
    assert canvas_2.height == 300
    assert canvas_2.units == "mm"

def test_save_and_recreate_boundary_object():
    boundary = Boundary([(0.0, 0.0), (1, 0), (0, 1), (1,1)], True)
    boundary_params = boundary.parameters

    boundary_2 = Boundary.create_from_dict(boundary_params)
    assert boundary_2.boundary_type == "outer"
    assert boundary_2.boundary_points == [(0.0, 0.0), (1, 0), (0, 1), (1,1)]
