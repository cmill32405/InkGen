from InkGen.svg_generator import *
from InkGen.style import DrawingStyle, Font, Style, TextStyle
from InkGen.boundary import Canvas
from InkGen.svg_utils import flatten_svg
import uuid
import pytest
import InkGen.svg_generator as svg_module
import InkGen.component as component_module

@pytest.fixture
def style_obj():
    style = DrawingStyle(
        name=f"default_{uuid.uuid4().hex}",
        stroke="#000000",
        stroke_width=0.2,
        fill="none",
        stroke_opacity=1.0,
    )
    return style


def _write_simple_svg(path):
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10">
  <g transform="translate(5,5)">
    <path d="M0,0 L10,0 L10,5 Z" style="fill:#ff0000;stroke:#000000;stroke-width:1" />
  </g>
</svg>
"""
    path.write_text(svg_content, encoding="utf-8")

def test_create_rectangle_svg(style_obj):
    rect = RectangleSVG((50, 50), 100, 100, 1.0, style_obj)
    assert rect.corner_radii == 1.0
    rect.corner_radii = 0.5
    assert rect.corner_radii == 0.5
    rect.corner_radii = (0.25, 0.75)
    assert rect.corner_radii == (0.25, 0.75)
    rect.corner_radii = (50, 50)
    assert rect.corner_radii == (50, 50)

def test_rectangle_svg_errors(style_obj):
    with pytest.raises(TypeError):
        rect = RectangleSVG((50, 50), 100, 100, {"width": 0.5, "height": 0.5}, style_obj)

    with pytest.raises(ValueError):
        rect = RectangleSVG((20, 20), 5, 5, [2.6, 2.6], style_obj)

    with pytest.raises(ValueError):
        rect = RectangleSVG((20, 20), 5, 5, [2.5, 2.6], style_obj)
    
    with pytest.raises(ValueError):
        rect = RectangleSVG((20, 20), 5, 6, 2.6, style_obj)

    with pytest.raises(ValueError):
        rect = RectangleSVG((20, 20), 5, 6, 3.1, style_obj)

def test_save_and_recreate_rectangle_svg(style_obj):
    rect = RectangleSVG((50, 50), 100, 100, 1.0, style_obj)
    params = rect.parameters

    rect2 = RectangleSVG.create_from_dict(params, style_obj)
    assert rect.parameters == rect2.parameters

    params['RectangleSVG']['style']['DrawingStyle']['name'] = "NewNameForStyle"
    rect3 = RectangleSVG.create_from_dict(params)
    assert rect3.parameters == params

def test_output_svg_data_from_rectangle_svg(style_obj):
    rect = RectangleSVG((50, 50), 100, 100, 1.0, style_obj)
    
    assert rect.generate_svg() == f"""<rect
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0"
            id="rect{rect.id}"
            width="100.0"
            height="100.0"
            x="50.0"
            y="50.0" />"""

def test_save_and_recreate_line_svg(style_obj):
    line = LineSVG((50.0, 50.0), (100.0, 100.0), style_obj)
    params = line.parameters

    line_2 = LineSVG.create_from_dict(params, style_obj)
    assert line.parameters == line_2.parameters

    params['LineSVG']['style']['DrawingStyle']['name'] = "NewNameForLineStyle"
    line_3 = LineSVG.create_from_dict(params)
    assert params == line_3.parameters

def test_output_svg_data_from_line_svg(style_obj):
    line = LineSVG((50.0, 50.0), (100.0, 100.0), style_obj)
    assert line.generate_svg() == f"""<path
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0"
            d="M 50.0,50.0 L 100.0,100.0"
            id="path{line.id}" />"""


def test_arc_svg_generate(style_obj):
    arc = ArcSVG((0.0, 0.0), 10.0, 5.0, 0.0, 90.0, style_obj)
    expected = f"""<path
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0"
            d="M 10.0,0.0 A 10.0,5.0 0.0 0 1 0.0,5.0"
            id="path{arc.id}" />"""
    assert arc.generate_svg() == expected
    recreated = ArcSVG.create_from_dict(arc.parameters, style_obj)
    assert recreated.parameters == arc.parameters


def test_quadratic_bezier_svg_generate(style_obj):
    curve = QuadraticBezierSVG((0.0, 0.0), (1.0, 1.0), (2.0, 0.0), style_obj)
    expected = f"""<path
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0"
            d="M 0.0,0.0 Q 1.0,1.0 2.0,0.0"
            id="path{curve.id}" />"""
    assert curve.generate_svg() == expected
    recreated = QuadraticBezierSVG.create_from_dict(curve.parameters, style_obj)
    assert recreated.parameters == curve.parameters


def test_cubic_bezier_svg_generate(style_obj):
    curve = CubicBezierSVG((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), style_obj)
    expected = f"""<path
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0"
            d="M 0.0,0.0 C 0.0,1.0 1.0,1.0 1.0,0.0"
            id="path{curve.id}" />"""
    assert curve.generate_svg() == expected
    recreated = CubicBezierSVG.create_from_dict(curve.parameters, style_obj)
    assert recreated.parameters == curve.parameters


def test_path_svg_generate(style_obj):
    commands = [
        component_module.PathCommand("M", [(0.0, 0.0)]),
        component_module.PathCommand("L", [(1.0, 1.0), (2.0, 2.0)]),
        component_module.PathCommand("A", [(3.0, 3.0)]),
        component_module.PathCommand("Z", []),
    ]
    arc_command = commands[2]
    arc_command.flags = {"radii": (2.0, 1.0), "rotation": 30.0, "large_arc": 0, "sweep": 1}
    path = PathSVG(style_obj, commands=commands)
    expected = f"""<path
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0"
            d="M 0.0,0.0 L 1.0,1.0 2.0,2.0 A 2.0,1.0 30.0 0 1 3.0,3.0 Z"
            id="path{path.id}" />"""
    assert path.generate_svg() == expected
    recreated = PathSVG.create_from_dict(path.parameters, style_obj)
    original_serialized = []
    for cmd in commands:
        entry = dict(cmd.parameters)
        flags = getattr(cmd, "flags", None)
        if flags is not None:
            entry["flags"] = flags
        original_serialized.append(entry)
    recreated_serialized = []
    for cmd in recreated.commands:
        entry = dict(cmd.parameters)
        flags = getattr(cmd, "flags", None)
        if flags is not None:
            entry["flags"] = flags
        recreated_serialized.append(entry)
    assert recreated_serialized == original_serialized


def test_flatten_svg_normalizes_paths(tmp_path):
    svg_file = tmp_path / "sample.svg"
    _write_simple_svg(svg_file)
    flattened = flatten_svg(str(svg_file))
    assert len(flattened.paths) == 1
    (min_x, min_y), (max_x, max_y) = flattened.bbox
    assert min_x == pytest.approx(0.0)
    assert min_y == pytest.approx(0.0)
    assert max_x == pytest.approx(10.0)
    assert max_y == pytest.approx(5.0)
    assert "M 0" in flattened.paths[0].d


def test_svg_component_embeds_external_svg(tmp_path):
    svg_file = tmp_path / "sample.svg"
    _write_simple_svg(svg_file)
    component = SVGComponent(filepath=str(svg_file), position=(5.0, 4.0), scale=2.0)
    pts = component.points
    assert pts[0] == (pytest.approx(5.0), pytest.approx(4.0))
    assert pts[2] == (pytest.approx(25.0), pytest.approx(14.0))
    svg_markup = component.generate_svg()
    assert '<g transform="translate(5.0,4.0) scale(2.0)">' in svg_markup
    assert 'path d="M 0.0,0.0 L 10.0,0.0 L 10.0,5.0' in svg_markup
    params = component.parameters
    restored = SVGComponent.create_from_dict(params)
    assert restored.parameters == params

def test_create_circle_svg(style_obj):
    circle = CircleSVG((50.0, 50.0), 10.0, style_obj)
    assert circle.radius == 10.0

    circle.radius = 12.0
    assert circle.radius == 12.0

def test_circle_svg_errors(style_obj):
    with pytest.raises(ValueError):
        circle = CircleSVG((50.0, 50.0), -10.0, style_obj)

    with pytest.raises(ValueError):
        circle = CircleSVG((50.0, 50.0), (10,10), style_obj)

    circle = CircleSVG((50.0, 50.0), 10.0, style_obj)
    with pytest.raises(ValueError):
        circle.radius = -10.0

    with pytest.raises(ValueError):
        circle.radius = (10, 10)

def test_save_and_recreate_circle_svg(style_obj):
    circle = CircleSVG((50.0, 50.0), 10.0, style_obj)
    params = circle.parameters

    circle_2 = CircleSVG.create_from_dict(params, style_obj)
    assert circle.parameters == circle_2.parameters

    params['CircleSVG']['style']['DrawingStyle']['name'] = "NewNameForCircleLineStyle"
    circle_3 = CircleSVG.create_from_dict(params)
    assert params == circle_3.parameters

def test_output_svg_data_from_circle_svg(style_obj):
    circle = CircleSVG((50.0, 50.0), 10.0, style_obj)
    assert circle.generate_svg() == f"""<circle
            cx="50.0"
            cy="50.0"
            r="10.0"
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0"
            id="circle{circle.id}" />"""
    
def test_circe_svg_read_only_properties(style_obj):
    circle = CircleSVG((50.0, 50.0), 10.0, style_obj)
    assert circle.bbox == [(40.0, 40.0), (60.0, 60.0)]
    assert len(circle.points) == 314
    assert circle.points[0][0] == 60.0
    assert circle.points == circle.convex_hull

def test_output_svg_from_polygon_svg(style_obj):
    poly = PolygonalSVG([(5.0, 10.0), (24.0, 10.0), (24.0, 20.0), (5.0, 20.0)], style_obj)
    assert poly.generate_svg() == f"""<path
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0;stroke-linecap:butt;stroke-linejoin:miter"
            d="M 5.0,10.0 24.0,10.0 24.0,20.0 5.0,20.0 Z"
            id="path{poly.id}" />"""
    
def test_save_and_recreate_polygon_svg(style_obj):
    poly = PolygonalSVG([(5.0, 10.0), (24.0, 10.0), (24.0, 20.0), (5.0, 20.0)], style_obj)
    params = poly.parameters

    poly_2 = PolygonalSVG.create_from_dict(params, style_obj)
    assert poly.parameters == poly_2.parameters

    params['PolygonalSVG']['style']['DrawingStyle']['name'] = "NewNameForPolyLineStyle"
    poly_3 = PolygonalSVG.create_from_dict(params)
    assert params == poly_3.parameters

def test_output_svg_from_regular_polygon_svg(style_obj):
    poly = RegularPolygonSVG((0, 0), 5, 10, style_obj, 15.0, 1.0)
    assert poly.generate_svg() == f"""<path
            style="fill:none;stroke:#000000;stroke-width:0.2;stroke-opacity:1.0;stroke-linecap:butt;stroke-linejoin:miter"
            d="M -2.587944546462854, 9.659014857863776 -9.985987866920038, 0.5235182152760215 -3.5837353665377925, -9.33546280709351 7.771117603714625, -6.293151530770307 8.38655017620606, 5.446081264724031  Z"
            id="path{poly.id}" />"""
    
def test_save_and_recreate_regular_polygon_svg(style_obj):
    poly = RegularPolygonSVG((0,0), 5, 10, style_obj, 15.0, 1.0)
    params = poly.parameters

    poly_2 = RegularPolygonSVG.create_from_dict(params, style_obj)
    assert poly.parameters == poly_2.parameters

    params['RegularPolygonSVG']['style']['DrawingStyle']['name'] = "NewNameForRegPolyLineStyle"
    poly_3 = RegularPolygonSVG.create_from_dict(params)
    assert params == poly_3.parameters

def test_interface_subclass_hooks():
    assert issubclass(RectangleSVG, DrawingGeneratorInterface)
    assert issubclass(ComponentGroupSVG, LabelGenerator)
    assert issubclass(ComponentGroupSVG, SegmentGenerator)

@pytest.fixture()
def draw_gen_obj():
    class Test(DrawingGeneratorInterface):
        pass
    Test.__abstractmethods__ = frozenset()
    return Test() 

def test_not_implemented_errors_for_draw_gen_interfaces(draw_gen_obj):
    with pytest.raises(NotImplementedError):
        data = draw_gen_obj.generate_svg()

@pytest.fixture()
def label_gen_obj():
    class Test(LabelGenerator):
        pass
    Test.__abstractmethods__ = frozenset()
    return Test() 

def test_not_implemented_errors_for_label_gen_interfaces(label_gen_obj):
    with pytest.raises(NotImplementedError):
        data = label_gen_obj.generate_label()

@pytest.fixture()
def segment_gen_obj():
    class Test(SegmentGenerator):
        pass
    Test.__abstractmethods__ = frozenset()
    return Test() 

def test_not_implemented_errors_for_segment_gen_interfaces(segment_gen_obj):
    with pytest.raises(NotImplementedError):
        data = segment_gen_obj.generate_segmentation_mask()
import uuid

from InkGen.table import Table
from InkGen.svg_generator import ComponentGroupSVG, RectangleSVG, TableSVG, TextSVG
from InkGen.style import DrawingStyle, Font, TextStyle


def test_table_svg_builds_component_group():
    table = Table(position=(0.0, 0.0))
    table.add_column(width=12.0)
    table.add_row(height=6.0)
    style_id = f"text-style-{uuid.uuid4()}"
    table.cell(0, 0).add_paragraph("A1", style_id=style_id)

    border_style = DrawingStyle(
        name=f"border-{uuid.uuid4()}",
        stroke="#000000",
        stroke_width=0.5,
        fill="none",
    )
    text_style = TextStyle(name=style_id, font=Font())

    group = TableSVG.from_table(
        table,
        group_label="tbl",
        border_style=border_style,
        text_styles={style_id: text_style},
    )

    assert isinstance(group, ComponentGroupSVG)
    components = list(group.components())
    assert len(components) == 2
    assert isinstance(components[0], RectangleSVG)
    assert isinstance(components[1], TextSVG)
    assert components[1].text == "A1"


def test_style_properties_respects_flags():
    style = DrawingStyle(
        name=f"style-{uuid.uuid4().hex}",
        stroke="#123456",
        stroke_width=0.4,
        stroke_opacity=0.6,
        fill="#abcdef",
    )
    style.fill_opacity = 0.25

    tokens = dict(part.split(":") for part in svg_module._style_properties(style).split(";"))
    assert tokens["fill"] == "#abcdef"
    assert tokens["stroke"] == "#123456"
    assert pytest.approx(float(tokens["stroke-width"])) == 0.4
    assert pytest.approx(float(tokens["stroke-opacity"])) == 0.6
    assert pytest.approx(float(tokens["fill-opacity"])) == 0.25

    no_fill = svg_module._style_properties(style, include_fill=False)
    assert "fill:none" in no_fill.split(";")

    no_stroke = svg_module._style_properties(style, include_stroke=False)
    assert "stroke:none" in no_stroke.split(";")


def test_text_svg_roundtrip_and_escape():
    text_style = TextStyle(name=f"text-{uuid.uuid4().hex}", font=Font())
    text_style.color = "#112233"
    text = "Voltage & Current"
    component = TextSVG(text=text, position=(12.5, 7.5), style=text_style)

    params = component.parameters
    if text_style.name in Style.style_names:
        Style.style_names.remove(text_style.name)
    restored = TextSVG.create_from_dict(params)
    assert restored.parameters == params

    reused = TextSVG.create_from_dict(params, text_style)
    assert reused.style is text_style

    rendered = component.generate_svg()
    assert "&amp;" in rendered
    assert f"text{component.id}" in rendered


def test_text_svg_fallback_outline(monkeypatch):
    text_style = TextStyle(name=f"text-{uuid.uuid4().hex}", font=Font())
    text_style.text_align = "end"
    component = TextSVG(text="Fallback", position=(10.0, 5.0), style=text_style)

    def _raise_outline(*args, **kwargs):
        raise RuntimeError("outline unavailable")

    monkeypatch.setattr(component_module, "outline_for_text", _raise_outline)
    hull = component.convex_hull
    assert len(hull) == 4
    bbox = component.bbox
    assert bbox[0][0] < bbox[1][0]


def test_text_svg_alignment_adjustment(monkeypatch):
    text_style = TextStyle(name=f"text-{uuid.uuid4().hex}", font=Font())
    text_style.text_align = "center"
    component = TextSVG(text="Aligned", position=(20.0, 5.0), style=text_style)

    outline = {
        "points": [(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (0.0, 1.0)],
        "convex_hull": [(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (0.0, 1.0)],
        "bbox": [(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (0.0, 1.0)],
    }
    monkeypatch.setattr(component_module, "outline_for_text", lambda *args, **kwargs: outline)

    xs = [pt[0] for pt in component.points]
    assert min(xs) == pytest.approx(18.0)
    assert max(xs) == pytest.approx(22.0)


def _write_sample_svg(path):
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:svg="http://www.w3.org/2000/svg">
  <g>
    <g>
      <g transform="matrix(1,0,0,1,0,0)">
        <path d="M 0,0 L 20,0 L 20,10 z" />
      </g>
      <g transform="translate(5,5)">
        <path d="M 0,0 L 0,15" />
      </g>
      <g transform="scale(1)">
        <path d="M 0,0 L 10,10" />
      </g>
    </g>
  </g>
</svg>
""",
        encoding="utf-8",
    )


def test_svg_component_parses_paths(tmp_path):
    svg_path = tmp_path / "sample.svg"
    _write_sample_svg(svg_path)

    component = SVGComponent(filepath=str(svg_path))
    assert component.points
    assert component.convex_hull
    assert component.bbox[0] != component.bbox[1]
    assert "<path" in component.generate_svg()

    params = component.parameters
    clone = SVGComponent.create_from_dict(params)
    assert clone.parameters == params


def test_svg_component_validation_errors(tmp_path):
    missing = tmp_path / "missing.svg"
    with pytest.raises(FileNotFoundError):
        SVGComponent(str(missing))

    not_svg = tmp_path / "not_svg.txt"
    not_svg.write_text("<svg/>", encoding="utf-8")
    with pytest.raises(ValueError):
        SVGComponent(str(not_svg))

    svg_path = tmp_path / "still.svg"
    _write_sample_svg(svg_path)
    with pytest.raises(ValueError):
        SVGComponent()


def test_component_group_svg_roundtrip_with_style_cache():
    border_style = DrawingStyle(
        name=f"border-{uuid.uuid4().hex}",
        stroke="#000000",
        stroke_width=0.3,
        fill="none",
    )
    text_style = TextStyle(name=f"text-{uuid.uuid4().hex}", font=Font())
    group = ComponentGroupSVG("CacheGroup")
    group.add_component(RectangleSVG((1.0, 1.0), 3.0, 2.0, 0.0, border_style))
    group.add_component(TextSVG("Item", (2.0, 2.0), text_style))

    params = group.parameters
    for name in (border_style.name, text_style.name):
        if name in Style.style_names:
            Style.style_names.remove(name)
    style_cache: dict[str, object] = {}
    restored_one = ComponentGroupSVG.create_from_dict(params, style_cache)
    restored_two = ComponentGroupSVG.create_from_dict(params, style_cache)

    assert restored_one.generate_label() == {"CacheGroup": restored_one.bbox}
    assert restored_one.generate_segmentation_mask() == {"CacheGroup": restored_one.convex_hull}

    restored_text_1 = next(comp for comp in restored_one.components() if isinstance(comp, TextSVG)).style
    restored_text_2 = next(comp for comp in restored_two.components() if isinstance(comp, TextSVG)).style
    assert restored_text_1 is style_cache[restored_text_1.name]
    assert restored_text_2 is style_cache[restored_text_1.name]


def test_document_svg_creates_model_layers(tmp_path):
    canvas = Canvas(120.0, 80.0, "mm")
    document = DocumentSVG(canvas)
    document.add_page()
    base_layer = document.page(1).layer("base")

    border_style = DrawingStyle(
        name=f"border-{uuid.uuid4().hex}",
        stroke="#202020",
        stroke_width=0.5,
        fill="none",
    )
    text_style = TextStyle(name=f"text-{uuid.uuid4().hex}", font=Font())
    text_style.text_align = "center"

    group = component_module.ComponentGroup("Panel")
    group.add_component(RectangleSVG((20.0, 20.0), 30.0, 8.0, 0.0, border_style))
    group.add_component(TextSVG("Panel 01", (35.0, 24.0), text_style))
    base_layer.add_component_group(group)

    label_path = tmp_path / "label.svg"
    document.create_svg(str(label_path), include=IncludeLayer.LABEL)
    assert label_path.exists()
    assert "label" in document.page(1).layers

    mask_path = tmp_path / "mask.svg"
    document.create_svg(str(mask_path), include=IncludeLayer.MASK)
    assert mask_path.exists()
    assert "mask" in document.page(1).layers

    mask_layer = document.page(1).layer("mask")
    has_polygon = any(
        isinstance(component, PolygonalSVG)
        for _, group_id in mask_layer.component_groups.items()
        for component in mask_layer.group(group_id).components()
    )
    assert has_polygon


def test_document_svg_serialization_roundtrip():
    canvas = Canvas(60.0, 40.0, "mm")
    document = DocumentSVG(canvas)
    document.add_page()
    base_layer = document.page(1).layer("base")

    border_style = DrawingStyle(
        name=f"serialize-{uuid.uuid4().hex}",
        stroke="#101010",
        stroke_width=0.4,
        fill="none",
    )
    group = component_module.ComponentGroup("Serialize")
    group.add_component(
        component_module.WidthHeightDrawingComponent((5.0, 5.0), 10.0, 6.0, border_style)
    )
    base_layer.add_component_group(group)

    params = document.parameters
    if border_style.name in Style.style_names:
        Style.style_names.remove(border_style.name)
    clone = DocumentSVG.create_from_dict(params)
    assert clone.parameters == params
