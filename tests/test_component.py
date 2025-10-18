import random

import numpy as np
import pytest

from InkGen.component import (
    Arc,
    Component,
    ComponentGroup,
    CubicBezier,
    DrawingComponent,
    Path,
    PathCommand,
    PolarCoordinateDrawingComponent,
    PolygonalDrawingComponent,
    QuadraticBezier,
    RegularPolygonDrawingComponent,
    SingleDimensionDrawingComponent,
    StandardDrawingComponent,
    TextComponent,
    WidthHeightDrawingComponent,
)
from InkGen.errors import InvalidComponentID, InvalidPolygonError
from InkGen.style import DrawingStyle, Font, TextStyle


@pytest.fixture
def next_comp_id():
    return Component.id_iter.__reduce__()[1][0]

def test_create_component(next_comp_id):
    comp1 = Component()
    comp2 = Component()
    assert comp1.id == next_comp_id
    assert comp2.id == next_comp_id + 1
    assert comp1.component_type == "Component"
    assert comp2.component_type == "Component"


def test_cant_set_id_or_type(next_comp_id):
    comp3 = Component()
    assert comp3.id == next_comp_id
    assert comp3.component_type == "Component"
    with pytest.raises(AttributeError):
        comp3.id = 1
    assert comp3.id == next_comp_id
    with pytest.raises(AttributeError):
        comp3.component_type = "DrawingComponent"
    assert comp3.component_type == "Component"

# Test Drawing Component and Standard Drawing Component
@pytest.fixture
def style_obj():
    style = DrawingStyle(
        name=f"default{random.randint(0, 99999)}",
        stroke="#000000",
        stroke_width=0.2,
        fill="none",
        stroke_opacity=1.0,
    )
    return style

def test_drawing_component_creation(style_obj, next_comp_id):
    dr_comp = DrawingComponent(style_obj)
    assert dr_comp.style.stroke == "#000000"
    assert dr_comp.id == next_comp_id
    assert dr_comp.component_type == "DrawingComponent"

def test_update_style_in_drawing_component(style_obj):
    dr_comp = DrawingComponent(style_obj)
    new_style = DrawingStyle(
        name="Alternative",
        stroke="#000001",
        stroke_width=0.5,
        fill="#ffffff",
        stroke_opacity=0.9,
    )
    dr_comp.style = new_style
    assert dr_comp.style.stroke == "#000001"
    dr_comp.style.stroke = "black"
    assert dr_comp.style.stroke == "#000000"

def test_invalid_style(style_obj):
    dr_comp = DrawingComponent(style_obj)
    assert dr_comp.style.stroke == "#000000"
    with pytest.raises(TypeError):
        DrawingComponent(Component())

def test_standard_drawing_component_creation(style_obj, next_comp_id):
    dr_unit = StandardDrawingComponent((1.0, 2.0), (3.0, 4.0), style_obj)
    assert dr_unit.bbox == [(1.0, 2.0), (3.0, 4.0)]
    assert dr_unit.convex_hull == [(1.0, 2.0), (3.0, 4.0)]
    assert dr_unit.id == next_comp_id
    assert dr_unit.component_type == "StandardDrawingComponent"

def test_standard_drawing_unit_with_neg_pos(style_obj):
    with pytest.raises(ValueError):
        StandardDrawingComponent((-1, 2.0), (3.0, 4.0), style_obj)

# Removed this functionality when it became clear that it makes no sense with
# subclasses needing to be in multiple directions.
# def test_standard_drawing_unit_with_x1_gt_x2(style_obj):
#     with pytest.raises(ValueError):
#         dr_unit = StandardDrawingComponent((5, 2.0), (3.0, 4.0), style_obj)

# Removed this functionality when it became clear that it makes no sense with
# subclasses needing to be in multiple directions.
# def test_standard_drawing_unit_with_y1_gt_y2(style_obj):
#     with pytest.raises(ValueError):
#         dr_unit = StandardDrawingComponent((5, 9.0), (8.0, 4.0), style_obj)

def test_get_points_after_declaration(style_obj):
    dr_unit = StandardDrawingComponent((1.0, 2.0), (3.0, 4.0), style_obj)
    assert dr_unit.point_1 == (1.0, 2.0)
    dr_unit.point_1 = (1.5, 2.5)
    assert dr_unit.point_1 == (1.5, 2.5)

    assert dr_unit.point_2 == (3.0, 4.0)
    dr_unit.point_2 = (3.5, 4.5)
    assert dr_unit.point_2 == (3.5, 4.5)

# Removed this functionality when it became clear that it makes no sense with
# subclasses needing to be in multiple directions.
# def test_invalid_point_change(style_obj):
#     dr_unit = StandardDrawingComponent((1.0, 2.0), (3.0, 4.0), style_obj)
#     assert dr_unit.point_1 == (1.0, 2.0)
#     with pytest.raises(ValueError):
#         dr_unit.point_1 = (5.0, 4.0)


#  Test SingleDimensionDrawingComponent

def test_create_single_dimension_component(style_obj):
    dr_unit = SingleDimensionDrawingComponent((5, 2.0), 200, style_obj)
    assert dr_unit.point_1 == (5.0, 2.0)
    assert dr_unit.point_2 == (205.0, 202.0)
    assert dr_unit.position == (5.0, 2.0)
    assert dr_unit.size == 200.0
    assert dr_unit.component_type == "SingleDimensionDrawingComponent"
    assert dr_unit.points == [(5.0, 2.0), (205.0, 202.0)]
    assert dr_unit.bbox == [(5.0, 2.0), (205.0, 202.0)]
    assert dr_unit.convex_hull == [(5.0, 2.0), (205.0, 202.0)]

def test_updated_single_dimension_component(style_obj):
    dr_unit = SingleDimensionDrawingComponent((5, 2.0), 200, style_obj)
    dr_unit.size = 210
    dr_unit.position = (10, 10)

    assert dr_unit.point_1 == (10.0, 10.0)
    assert dr_unit.point_2 == (220.0, 220.0)
    assert dr_unit.position == (10.0, 10.0)
    assert dr_unit.size == 210.0


#  Test WidthHeightDrawingComponent

def test_create_width_height_comonent(style_obj):
    dr_unit = WidthHeightDrawingComponent((5, 2.0), 200, 150, style_obj)
    assert dr_unit.point_1 == (5.0, 2.0)
    assert dr_unit.position == (5.0, 2.0)
    assert dr_unit.point_2 == (205.0, 152.0)
    assert dr_unit.width == 200.0
    assert dr_unit.height == 150.0
    assert dr_unit.component_type == "WidthHeightDrawingComponent"
    assert dr_unit.bbox == [(5.0, 2.0), (205.0, 152.0)]
    assert dr_unit.convex_hull == [(5.0, 2.0), (205.0, 2.0), (205.0, 152.0), (5.0, 152.0)]

def test_updated_width_height_component(style_obj):
    dr_unit = WidthHeightDrawingComponent((5, 2.0), 200, 150, style_obj)
    dr_unit.width = 100
    dr_unit.height = 100
    dr_unit.position = (10.0, 10.0)

    assert dr_unit.point_1 == (10.0, 10.0)
    assert dr_unit.point_2 == (110.0, 110.0)
    assert dr_unit.position == (10.0, 10.0)
    assert dr_unit.width == 100
    assert dr_unit.height == 100

# Test PolarCoordinateDrawingComponent
def test_create_polar_coordinate_component(style_obj):
    polr = PolarCoordinateDrawingComponent((2.0, 5.0), 10.0, 35.0, style_obj)
    assert polr.position == (2.0, 5.0)
    assert polr.point_1 == (2.0, 5.0)
    assert np.isclose(polr.point_2[0], 10.192, 0.001)
    assert np.isclose(polr.point_2[1], 10.736, 0.001)
    assert np.isclose(polr.length, 10.0, 0.001)
    assert polr.angle - 35.0 <= 0.0001

def test_update_position_polar_coordinate_component(style_obj):
    polr = PolarCoordinateDrawingComponent((2.0, 5.0), 10.0, 35.0, style_obj)
    assert polr.position == (2.0, 5.0)
    assert polr.point_1 == (2.0, 5.0)
    assert np.isclose(polr.point_2[0], 10.192, 0.001)
    assert np.isclose(polr.point_2[1], 10.736, 0.001)
    assert np.isclose(polr.length, 10.0, 0.001)
    assert np.isclose(polr.angle, 35.0, 0.001)
    assert polr.component_type == "PolarCoordinateDrawingComponent"
    assert polr.points == [polr.point_1, polr.point_2]
    assert polr.bbox == [polr.point_1, polr.point_2]
    assert polr.convex_hull == [polr.point_1, polr.point_2]

    polr.position = (10, 10)
    assert polr.position == (10.0, 10.0)
    assert polr.point_1 == (10.0, 10.0)
    assert np.isclose(polr.point_2[0], 18.192, 0.001)
    assert np.isclose(polr.point_2[1], 15.736, 0.001)
    assert np.isclose(polr.length , 10.0, 0.001)
    assert np.isclose(polr.angle , 35.0, 0.001)

# def test_reverse_polar_coordinates(style_obj):
#     polr = PolarCoordinateDrawingComponent((2.0, 5.0), 10.0, 135.0, style_obj)
#     assert polr.points == [(2.0, 5.0), (225, 221)]

def test_update_length_polar_coordinate_component(style_obj):
    polr = PolarCoordinateDrawingComponent((2.0, 5.0), 10.0, 35.0, style_obj)
    assert polr.position == (2.0, 5.0)
    assert polr.point_1 == (2.0, 5.0)
    assert np.isclose(polr.point_2[0], 10.192, 0.001)
    assert np.isclose(polr.point_2[1], 10.736, 0.001)
    assert np.isclose(polr.length, 10.0, 0.001)
    assert np.isclose(polr.angle, 35.0, 0.001)

    polr.length = 20.0
    assert polr.position == (2.0, 5.0)
    assert polr.point_1 == (2.0, 5.0)
    assert np.isclose(polr.point_2[0], 18.383, 0.001)
    assert np.isclose(polr.point_2[1], 16.472, 0.001)
    assert np.isclose(polr.length, 20.0, 0.001)
    assert np.isclose(polr.angle, 35.0, 0.001)

def test_update_angle_polar_coordinate_component(style_obj):
    polr = PolarCoordinateDrawingComponent((2.0, 5.0), 10.0, 35.0, style_obj)
    assert polr.position == (2.0, 5.0)
    assert polr.point_1 == (2.0, 5.0)
    assert np.isclose(polr.point_2[0], 10.192, 0.001)
    assert np.isclose(polr.point_2[1], 10.736, 0.001)
    assert np.isclose(polr.length, 10.0, 0.001)
    assert np.isclose(polr.angle, 35.0, 0.001)

    polr.angle = 15.0
    assert polr.position == (2.0, 5.0)
    assert polr.point_1 == (2.0, 5.0)
    assert np.isclose(polr.point_2[0], 11.66, 0.001)
    assert np.isclose(polr.point_2[1], 7.58819, 0.001)
    assert np.isclose(polr.length, 10.0, 0.001)
    assert np.isclose(polr.angle, 15.0, 0.001)

def test_create_polygonal_drawing_component(style_obj):
    poly = PolygonalDrawingComponent([(10.0, 10.0), (12.0, 7.5), (9.0, 5.0), (7.0, 5.0), (5.0, 7.0)], style_obj)
    assert poly.bbox == ((5.0, 5.0), (12.0, 10.0))
    assert poly.convex_hull == [(7.0, 5.0), (5.0, 7.0), (10.0, 10.0), (12.0, 7.5), (9.0, 5.0)]
    assert poly.points == [(10.0, 10.0), (12.0, 7.5), (9.0, 5.0), (7.0, 5.0), (5.0, 7.0)]
    assert poly.polygon.area == 19.25

def test_update_polygonal_drawing_component(style_obj):
     poly = PolygonalDrawingComponent([(10.0, 10.0), (12.0, 7.5), (9.0, 5.0), (7.0, 5.0), (5.0, 7.0)], style_obj)
     assert poly.points == [(10.0, 10.0), (12.0, 7.5), (9.0, 5.0), (7.0, 5.0), (5.0, 7.0)]

     poly.points = [(10.0, 10.0), (12.0, 7.5), (9.0, 5.0), (7.0, 5.0), (5.0, 7.5)]
     assert poly.points == [(10.0, 10.0), (12.0, 7.5), (9.0, 5.0), (7.0, 5.0), (5.0, 7.5)]

def test_create_invalid_polygonal_drawing_component(style_obj):
    with pytest.raises(InvalidPolygonError):
        PolygonalDrawingComponent([(10.0, 10.0), (12.0, 7.5)], style_obj)

    with pytest.raises(InvalidPolygonError):
        PolygonalDrawingComponent([(10.0, 10.0), (12.0, 7.5), (12.0, 4.5, 2.3)], style_obj)

    poly = PolygonalDrawingComponent([(10.0, 10.0), (12.0, 7.5), (12.0, 4.5)], style_obj)
    with pytest.raises(InvalidPolygonError):
        poly.points = [(10.0, 10.0), (12.0, 7.5), (12.0, 4.5, 2.3)]

@pytest.fixture
def next_comp_grp_id():
    return ComponentGroup.grp_id_iter.__reduce__()[1][0]

# Test ComponentGroup
def test_create_component_group(style_obj, next_comp_grp_id):
    comp_group = ComponentGroup("zoning")
    assert comp_group.group_id == next_comp_grp_id
    assert comp_group.group_label == "zoning"

def test_invalid_group_label_type(style_obj):
    with pytest.raises(TypeError):
        ComponentGroup(1)

def test_add_components_to_component_group(style_obj):
    comp_group = ComponentGroup("zoning")
    comp_group.add_component(Component())
    comp_group.add_component(DrawingComponent(style_obj))
    comp_group.add_component(StandardDrawingComponent((1.0, 2.0), (3.0, 4.0), style_obj))
    component_names = ['Component', 'DrawingComponent', 'StandardDrawingComponent']

    for i, comp in enumerate(comp_group.components()):
        assert component_names[i]  == comp.component_type

def test_get_component_from_component_group_and_error(style_obj):
    comp_group1 = ComponentGroup("zoning")
    comp_group1.add_component(Component())
    comp_group1.add_component(DrawingComponent(style_obj))
    comp_group1.add_component(StandardDrawingComponent((1.0, 2.0), (3.0, 4.0), style_obj))

    ids = []
    for k in comp_group1.components():
        ids.append(k.id)

    assert comp_group1.get_component(ids[0]).component_type == 'Component'
    assert comp_group1.get_component(ids[1]).component_type == 'DrawingComponent'
    assert comp_group1.get_component(ids[2]).component_type == 'StandardDrawingComponent'

    with pytest.raises(InvalidComponentID):
        comp_group1.get_component(max(ids) + 1)

def test_component_group_points(style_obj):
    comp_group = ComponentGroup("zoning")
    comp_group.add_component(Component())
    comp_group.add_component(DrawingComponent(style_obj))
    comp_group.add_component(StandardDrawingComponent((1.0, 2.0), (3.0, 4.0), style_obj))

    assert comp_group.points == [(1.0, 2.0), (3.0, 4.0)]
    assert comp_group.bbox == ((1.0, 2.0), (3.0, 4.0))

def test_component_group_convex_hull(style_obj):
    comp_group = ComponentGroup("Thing")
    comp_group.add_component(StandardDrawingComponent((7.0, 5.0), (12.0, 7.5), style_obj))
    comp_group.add_component(StandardDrawingComponent((9.0, 5.0), (10.0, 10.0), style_obj))
    comp_group.add_component(StandardDrawingComponent((5.0, 7.0), (10.0, 10.0), style_obj))

    assert comp_group.convex_hull == [(7.0, 5.0), (5.0, 7.0), (10.0, 10.0), (12.0, 7.5), (9.0, 5.0)]


def test_remove_component_from_component_group(style_obj):
    comp_group = ComponentGroup("zoning")
    comp_group.add_component(Component())
    comp_group.add_component(DrawingComponent(style_obj))
    comp_group.add_component(StandardDrawingComponent((1.0, 2.0), (3.0, 4.0), style_obj))

    ids = []
    for k in comp_group.components():
        ids.append(k.id)

    assert comp_group.get_component(ids[0]).component_type == 'Component'

    comp_group.remove_component(ids[0])

    for component in comp_group.components():
        assert component.component_type != "Component"

    with pytest.raises(InvalidComponentID):
        comp_group.remove_component(89)

# Test RegularPolygonDrawingComponent
def test_create_regular_polygon(style_obj):
    reg_poly = RegularPolygonDrawingComponent((0.0, 0.0), 6, 20, style_obj, 0, 0)
    assert reg_poly.position == (0.0, 0.0)
    assert reg_poly.sides == 6
    assert reg_poly.radius == 20.0
    assert round(reg_poly.angle, 1) == 0.0
    assert reg_poly.corner_radius == 0.0
    assert np.isclose(reg_poly.bbox, ((-17.32050808, -20), (17.32050808, 20)), atol=1e-3, rtol=1e-3).all()
    assert np.isclose(reg_poly.points, [(1.22514845490862E-15, 20), (-17.3205080756888, 10), (-17.3205080756888, -10),
                                        (-3.67544536472586E-15, -20), (17.3205080756888, -10), (17.3205080756888, 10)]).all()
    assert np.isclose(reg_poly.convex_hull, [(-3.67544536472586E-15, -20), (-17.3205080756888, -10), (-17.3205080756888, 10),
                                            (1.22514845490862E-15, 20), (17.3205080756888, 10),  (17.3205080756888, -10)]).all()
    reg_poly.radius = 30
    assert reg_poly.radius == 30.0

def test_invalid_inputs(style_obj):
    with pytest.raises(ValueError):
        reg_poly = RegularPolygonDrawingComponent((0.0, 0.0), 2, 20, style_obj, 0, 0)

    with pytest.raises(ValueError):
        reg_poly = RegularPolygonDrawingComponent((0.0, 0.0), 6, 20, style_obj, 12, 12)

    with pytest.raises(ValueError):
        reg_poly = RegularPolygonDrawingComponent(position=(0.0, 0.0), sides=6, radius=-1.0, style=style_obj, angle=0, corner_radius=0)

    reg_poly = RegularPolygonDrawingComponent(position=(0.0, 0.0), sides=6, radius=20.0, style=style_obj, angle=0, corner_radius=0)
    with pytest.raises(ValueError):
        reg_poly.radius = -1

@pytest.fixture
def text_style():
    text_style = TextStyle("TimesNormal", Font("Times New Roman", size=12))
    return text_style

def test_text_component(text_style):
    #text_style.text_align = "end"
    text_comp = TextComponent("Test Text", (120, 120), text_style)
    assert text_comp.text == "Test Text"
    assert text_comp.position == (120.0, 120.0)
    assert text_comp.style.color == "#000000"
    text_comp.text = 2.0
    assert text_comp.text == "2.0"
    assert text_comp.style.font.size == 12.0
    text_comp.text = "Test Text"
    expected_points = [(120.609375, 109.40625),
                       (120.484375, 111.890625),
                       (122.6484375, 120.0),
                       (132.375, 120.21875),
                       (162.515625, 120.21875),
                       (176.5625, 120.1171875),
                       (177.0859375, 120.0205078125),
                       (177.59375, 119.73046875),
                       (178.037109375, 119.2490234375),
                       (178.3671875, 118.578125),
                       (178.1484375, 112.84375),
                       (176.4765625, 110.4921875),
                       (159.3984375, 109.40625)]
    assert len(text_comp.points) == len(expected_points)
    for actual, expected in zip(text_comp.points, expected_points, strict=False):
        assert actual == pytest.approx(expected, rel=1e-6)
    bbox = text_comp.bbox
    assert bbox[0] == pytest.approx((120.484375, 109.40625), rel=1e-6)
    assert bbox[1] == pytest.approx((178.3671875, 120.21875), rel=1e-6)
    assert text_comp.convex_hull == text_comp.points
    cached_points = list(text_comp.points)
    text_comp.style.text_align = "center"
    assert text_comp.points == cached_points

def test_text_component_errors():
    new_style = TextStyle("TimesBold", Font("Times New Roman", weight="bold", size=12))
    text_comp = TextComponent("Test Text", (120, 120), new_style)

    style = DrawingStyle("DrawStyle")

    with pytest.raises(TypeError):
        text_comp.text = style

    with pytest.raises(TypeError):
        text_comp.style = style

def test_save_and_recreate_drawing_component_object():
    test_style = DrawingStyle("Some Name for a Style", 'red', 0.5, 'red', 0.5, 0.5)
    component = DrawingComponent(test_style)
    parameters  = component.parameters
    parameters['DrawingComponent']['style']['DrawingStyle']['name'] = "That's a lot of keys!"
    comp_2 = DrawingComponent.create_from_dict(parameters)

    assert comp_2.style.stroke == "#ff0000"
    assert comp_2.style.fill == "#ff0000"
    assert comp_2.style.name == "That's a lot of keys!"

    comp_3 = DrawingComponent.create_from_dict(parameters, test_style)
    assert comp_3.style.name == "Some Name for a Style"


def test_save_and_recreate_standard_drawing_component_object(style_obj):
    component = StandardDrawingComponent((0,0), (1,1), style_obj)
    parameters = component.parameters

    comp_2 = StandardDrawingComponent.create_from_dict(parameters, style_obj)

    assert comp_2.style.name == style_obj.name
    assert comp_2.point_1 == (0.0, 0.0)
    assert comp_2.point_2 == (1.0, 1.0)

    parameters['StandardDrawingComponent']['style']['DrawingStyle']['name'] = "StyleName45"
    comp_3 = StandardDrawingComponent.create_from_dict(parameters)

    assert comp_3.style.name == "StyleName45"

def test_save_and_recreate_single_dimension_drawing_component_object(style_obj):
    component = SingleDimensionDrawingComponent((0,0), 15.0, style_obj)
    parameters = component.parameters

    comp_2 = SingleDimensionDrawingComponent.create_from_dict(parameters, style_obj)

    assert comp_2.style.name == style_obj.name
    assert comp_2.position == (0.0, 0.0)
    assert comp_2.size == 15.0

    parameters['SingleDimensionDrawingComponent']['style']['DrawingStyle']['name'] = "StyleName46"
    comp_3 = SingleDimensionDrawingComponent.create_from_dict(parameters)

    assert comp_3.style.name == "StyleName46"

def test_save_and_recreate_height_width_drawing_component_object(style_obj):
    component = WidthHeightDrawingComponent((0,0), 15.0, 20.0, style_obj)
    parameters = component.parameters

    comp_2 = WidthHeightDrawingComponent.create_from_dict(parameters, style_obj)

    assert comp_2.style.name == style_obj.name
    assert comp_2.position == (0.0, 0.0)
    assert comp_2.width == 15.0
    assert comp_2.height == 20.0

    parameters['WidthHeightDrawingComponent']['style']['DrawingStyle']['name'] = "StyleName47"
    comp_3 = WidthHeightDrawingComponent.create_from_dict(parameters)

    assert comp_3.style.name == "StyleName47"

def test_save_and_recreate_polar_coordinate_drawing_component_object(style_obj):
    component = PolarCoordinateDrawingComponent((0,0), 15.0, 20.0, style_obj)
    parameters = component.parameters

    comp_2 = PolarCoordinateDrawingComponent.create_from_dict(parameters, style_obj)

    assert comp_2.style.name == style_obj.name
    assert comp_2.position == (0.0, 0.0)
    assert np.isclose(comp_2.length, 15.0, 0.001)
    assert np.isclose(comp_2.angle, 20.0, 0.001)

    parameters['PolarCoordinateDrawingComponent']['style']['DrawingStyle']['name'] = "StyleName48"
    comp_3 = PolarCoordinateDrawingComponent.create_from_dict(parameters)

    assert comp_3.style.name == "StyleName48"

def test_save_and_recreate_regular_polygon_drawing_component_object(style_obj):
    component = RegularPolygonDrawingComponent((0,0), 5, 20.0, style_obj, 15.0, 2.0)
    parameters = component.parameters

    comp_2 = RegularPolygonDrawingComponent.create_from_dict(parameters, style_obj)

    assert comp_2.style.name == style_obj.name
    assert comp_2.position == (0.0, 0.0)
    assert comp_2.sides == 5
    assert np.isclose(comp_2.radius, 20.0, 0.001)
    assert np.isclose(comp_2.angle, 15.0, 0.001)
    assert comp_2.corner_radius == 2.0

    parameters['RegularPolygonDrawingComponent']['style']['DrawingStyle']['name'] = "StyleName49"
    comp_3 = RegularPolygonDrawingComponent.create_from_dict(parameters)

    assert comp_3.style.name == "StyleName49"

def test_path_command_basic():
    cmd = PathCommand("m", [(0, 0), (1.1114, 2.5555)])
    assert cmd.type == "M"
    points = cmd.points
    assert points[0] == (0.0, 0.0)
    assert points[1][0] == pytest.approx(1.111, abs=0.001)
    assert points[1][1] == pytest.approx(2.556, abs=0.002)
    cmd.add_point((2, 3))
    assert cmd.points[-1] == (2.0, 3.0)
    params = cmd.parameters
    assert params["type"] == "M"
    assert params["points"] == cmd.points
    with pytest.raises(ValueError):
        PathCommand("R", [(0, 0)])

def test_arc_points_and_parameters(style_obj):
    arc = Arc(center=(0, 0), radius_x=10, radius_y=5, start_angle=0, end_angle=90, style=style_obj)
    pts = arc.points
    assert pts[0] == (10.0, 0.0)
    assert pts[-1] == (0.0, 5.0)
    assert len(pts) >= 3
    params = arc.parameters
    assert params["Arc"]["center"] == (0.0, 0.0)
    recreated = Arc.create_from_dict(params, style_obj)
    assert recreated.parameters == params

def test_arc_invalid_radius(style_obj):
    with pytest.raises(ValueError):
        Arc(center=(0, 0), radius_x=0, radius_y=5, start_angle=0, end_angle=90, style=style_obj)

def test_quadratic_bezier_points(style_obj):
    bezier = QuadraticBezier((0, 0), (1, 1), (2, 0), style_obj)
    pts = bezier.points
    assert pts[0] == (0.0, 0.0)
    assert pts[-1] == (2.0, 0.0)
    mid = pts[len(pts) // 2]
    assert mid[0] == pytest.approx(1.0, abs=0.01)
    assert mid[1] == pytest.approx(0.5, abs=0.01)
    recreated = QuadraticBezier.create_from_dict(bezier.parameters, style_obj)
    assert recreated.parameters == bezier.parameters

def test_cubic_bezier_points(style_obj):
    bezier = CubicBezier((0, 0), (0, 1), (1, 1), (1, 0), style_obj)
    pts = bezier.points
    assert pts[0] == (0.0, 0.0)
    assert pts[-1] == (1.0, 0.0)
    mid = pts[len(pts) // 2]
    assert mid[0] == pytest.approx(0.5, abs=0.02)
    assert mid[1] == pytest.approx(0.75, abs=0.02)
    recreated = CubicBezier.create_from_dict(bezier.parameters, style_obj)
    assert recreated.parameters == bezier.parameters

def test_path_component_points(style_obj):
    move = PathCommand("M", [(0, 0)])
    path = Path(style_obj, commands=[move])
    path.add_command({"type": "L", "points": [(1, 1), (2, 2)]})
    points = path.points
    assert points == [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
    params = path.parameters
    recreated = Path.create_from_dict(params, style_obj)
    assert [cmd.parameters for cmd in recreated.commands] == [cmd.parameters for cmd in path.commands]
    assert recreated.points == points

def test_save_and_recreate_polygonal_drawing_component_object(style_obj):
    component = PolygonalDrawingComponent([(0,0), (2, 2), (2.5, 3)], style_obj)
    parameters = component.parameters

    comp_2 = PolygonalDrawingComponent.create_from_dict(parameters, style_obj)

    assert comp_2.style.name == style_obj.name
    assert comp_2.points == [(0.0, 0.0), (2.0, 2.0), (2.5, 3)]

    parameters['PolygonalDrawingComponent']['style']['DrawingStyle']['name'] = "StyleName50"
    comp_3 = PolygonalDrawingComponent.create_from_dict(parameters)

    assert comp_3.style.name == "StyleName50"

def test_save_and_recreate_text_component_object():
    text_style = TextStyle("TestArial", Font("Arial"))
    component = TextComponent(text="test", position=(0, 0), style=text_style)
    parameters = component.parameters

    comp_2 = TextComponent.create_from_dict(parameters, text_style)

    assert comp_2.style.name == text_style.name
    assert comp_2.position == (0.0, 0.0)

    parameters['TextComponent']['style']['TextStyle']['name'] = "StyleName51"
    comp_3 = TextComponent.create_from_dict(parameters)

    assert comp_3.style.name == "StyleName51"

def test_save_and_recreate_component_group_object():
    text_style = TextStyle("TestCGtext_style", Font("Arial"))
    draw_style = DrawingStyle("TestCGdraw_style")
    component1 = TextComponent(text="test", position=(0, 0), style=text_style)
    component2 = PolygonalDrawingComponent([(0,0), (2, 2), (2.5, 3)], draw_style)
    component3 = RegularPolygonDrawingComponent((0,0), 5, 20.0, draw_style, 15.0, 2.0)
    group = ComponentGroup("TestCG")

    group.add_component(component2)
    group.add_component(component3)
    group.add_component(component1)

    params = group.parameters
    group_2 = ComponentGroup.create_from_dict(params,
                                              {"TestCGtext_style": text_style,
                                               "TestCGdraw_style": draw_style})
    assert group_2.group_label == "TestCG"

    assert group.parameters == group_2.parameters

    component_entries = params['ComponentGroup']['components']
    component_entries[2]['TextComponent']['style']['TextStyle']['name'] = "new_text_style_8822"
    component_entries[0]['PolygonalDrawingComponent']['style']['DrawingStyle']['name'] = "new_draw_style_8922"
    component_entries[1]['RegularPolygonDrawingComponent']['style']['DrawingStyle']['name'] = "new_draw_style_8932"

    group_3 = ComponentGroup.create_from_dict(params)
    recreated_components = group_3.parameters['ComponentGroup']['components']
    assert (
        recreated_components[2]['TextComponent']['style']['TextStyle']['name']
        == "new_text_style_8822"
    )
    assert (
        recreated_components[0]['PolygonalDrawingComponent']['style']['DrawingStyle']['name']
        == "new_draw_style_8922"
    )
    assert (
        recreated_components[1]['RegularPolygonDrawingComponent']['style']['DrawingStyle']['name']
        == "new_draw_style_8932"
    )

def test_save_and_recreate_component():
    comp = Component()
    params = comp.parameters
    comp2 = Component.create_from_dict(params)
    assert comp2.__class__.__name__ == "Component"

