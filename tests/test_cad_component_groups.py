import random

import pytest

from InkGen.boundary import Canvas
from InkGen.cad_component_groups import Zoning
from InkGen.component import *
from InkGen.style import Font, TextStyle


@pytest.fixture
def canvas():
    return Canvas(210, 297, "mm")

@pytest.fixture
def line_style():
    return DrawingStyle(f'default_style_{random.randint(1000, 9999)}')

@pytest.fixture
def text_style():
    return TextStyle(f"text_style_{random.randint(1000, 9999)}", Font())

def test_create_zoning_group(canvas, line_style, text_style):
    zoning = Zoning(canvas=canvas, line_style=line_style, text_style=text_style)
    params = zoning._parameters
    assert params["margins"] is None
    assert params["h_margins"] is None
    assert params["v_margins"] is None
    assert params["left_margin"] == 5
    assert params["right_margin"] == 5
    assert params["top_margin"] == 5
    assert params["bottom_margin"] == 5
    assert params["zone_width"] is None
    assert params["h_zone_width"] is None
    assert params["v_zone_width"] is None
    text_probe = TextComponent("W", (0, 0), text_style)
    char_width = text_probe.bbox[1][0] - text_probe.bbox[0][0]
    expected_width = pytest.approx(char_width + 4, rel=1e-9)
    assert params["left_zone_width"] == expected_width
    assert params["right_zone_width"] == expected_width
    assert params["top_zone_width"] == expected_width
    assert params["bottom_zone_width"] == expected_width
    assert params["inner_radius"] == pytest.approx(0.0)
    assert params["outer_radius"] == pytest.approx(0.0)
    assert params["horizontal_zones"] == 8
    assert params["vertical_zones"] == 10
    assert params["first_horizontal_char"] == 49
    assert params["first_vertical_char"] == 65

def test_create_zoning_group_with_parameters(canvas, line_style, text_style):
    line_style._name = "default_style_1189"
    text_style._name = "text_style_1278"
    zoning = Zoning(canvas=canvas,
                    line_style=line_style,
                    text_style=text_style,
                    margins=5,
                    h_margins=6,
                    right_margin=7,
                    zone_width=10,
                    h_zone_width=12,
                    right_zone_width=14,
                    inner_radius=1.0,
                    outer_radius=1.0,
                    horizontal_zones=10,
                    vertical_zones=12,
                    first_horizontal_char=65,
                    first_vertical_char=49)
    assert zoning._parameters == {"margins": 5, "h_margins": 6, "v_margins": None,
                                "left_margin": 5, "right_margin": 7,
                                "top_margin": 6, "bottom_margin": 6,
                                "zone_width": 10, "h_zone_width": 12, "v_zone_width": None,
                                "left_zone_width": 10, "right_zone_width": 14,
                                "top_zone_width": 12, "bottom_zone_width": 12,
                                "inner_radius": 1.0, "outer_radius": 1.0,
                                "horizontal_zones": 10, "vertical_zones": 12,
                                "first_horizontal_char": 65, "first_vertical_char": 49}

def test_create_zoning_group_with_instance_errors(canvas, line_style, text_style):
    with pytest.raises(TypeError):
        Zoning(canvas=line_style, line_style=line_style, text_style=text_style)

    with pytest.raises(TypeError):
        Zoning(canvas=canvas, line_style=text_style, text_style=text_style)

    with pytest.raises(TypeError):
        Zoning(canvas=canvas, line_style=line_style, text_style=line_style)

def test_create_zoning_group_with_parameter_erros(canvas, line_style, text_style):
    with pytest.raises(ValueError):
        Zoning(canvas=canvas,
               line_style=line_style,
               text_style=text_style,
               margins="5",
               h_margins=6,
               right_margin=7,
               zone_width=10,
               h_zone_width=12,
               right_zone_width=14,
               inner_radius=1.0,
               outer_radius=1.0,
               horizontal_zones=10,
               vertical_zones=12,
               first_horizontal_char=65,
               first_vertical_char=49)

    with pytest.raises(ValueError):
        Zoning(canvas=canvas,
               line_style=line_style,
               text_style=text_style,
               margins=5,
               h_margins=6,
               right_margin=7,
               zone_width=10,
               h_zone_width=12,
               right_zone_width=14,
               inner_radius=1.0,
               outer_radius=1.0,
               horizontal_zones=10,
               vertical_zones=12,
               first_horizontal_char=60,
               first_vertical_char=49)

    with pytest.raises(ValueError):
        Zoning(canvas=canvas,
               line_style=line_style,
               text_style=text_style,
               margins=5,
               h_margins=6,
               right_margin=7,
               zone_width=10,
               h_zone_width=12,
               right_zone_width=14,
               inner_radius=1.0,
               outer_radius=1.0,
               horizontal_zones=11,
               vertical_zones=12,
               first_horizontal_char=65,
               first_vertical_char=49)

    with pytest.raises(KeyError):
        Zoning(canvas=canvas,
               line_style=line_style,
               text_style=text_style,
               margins=5,
               h_margins=6,
               right_margin=7,
               zone_width=10,
               h_zone_width=12,
               right_zone_width=14,
               inner_radius=1.0,
               outer_radius=1.0,
               horizontal_zones=10,
               vertical_zones=12,
               first_horizontal_char=65,
               first_vertical_char=49,
               nonsense="nonsens")

def test_save_and_recreate_zoning_group(canvas, line_style, text_style):
    styles = {text_style.name: text_style, line_style.name: line_style}
    zoning = Zoning(canvas=canvas,
                    line_style=line_style,
                    text_style=text_style,
                    margins=5,
                    h_margins=6,
                    right_margin=7,
                    zone_width=10,
                    h_zone_width=12,
                    right_zone_width=14,
                    inner_radius=1.0,
                    outer_radius=1.0,
                    horizontal_zones=10,
                    vertical_zones=12,
                    first_horizontal_char=65,
                    first_vertical_char=49)
    cg = zoning.component_group
    assert cg.group_label == "Zoning"
    params = zoning.parameters

    zoning_2 = Zoning.create_from_dict(params, styles)
    assert zoning_2._parameters == {"margins": 5, "h_margins": 6, "v_margins": None,
                                "left_margin": 5, "right_margin": 7,
                                "top_margin": 6, "bottom_margin": 6,
                                "zone_width": 10, "h_zone_width": 12, "v_zone_width": None,
                                "left_zone_width": 10, "right_zone_width": 14,
                                "top_zone_width": 12, "bottom_zone_width": 12,
                                "inner_radius": 1.0, "outer_radius": 1.0,
                                "horizontal_zones": 10, "vertical_zones": 12,
                                "first_horizontal_char": 65, "first_vertical_char": 49}

    params['Zoning']['line_style']['DrawingStyle']['name'] = "new_drawing_style_2939"
    params['Zoning']['text_style']['TextStyle']['name'] = "new_text_style_2939"
    Zoning.create_from_dict(params)
    assert zoning_2._parameters == {"margins": 5, "h_margins": 6, "v_margins": None,
                                "left_margin": 5, "right_margin": 7,
                                "top_margin": 6, "bottom_margin": 6,
                                "zone_width": 10, "h_zone_width": 12, "v_zone_width": None,
                                "left_zone_width": 10, "right_zone_width": 14,
                                "top_zone_width": 12, "bottom_zone_width": 12,
                                "inner_radius": 1.0, "outer_radius": 1.0,
                                "horizontal_zones": 10, "vertical_zones": 12,
                                "first_horizontal_char": 65, "first_vertical_char": 49}

