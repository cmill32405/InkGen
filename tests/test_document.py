import json
import os

import pytest

from InkGen.boundary import Boundary, Canvas
from InkGen.component import *
from InkGen.document import Document, Layer, Layers
from InkGen.errors import ComponentGroupCollision, ComponentGroupOffCanvas, IncompatibleCanvas, InvalidComponentGroupID
from InkGen.style import Style


@pytest.fixture
def canvas():
    return Canvas(210, 297, "mm")

@pytest.fixture
def next_comp_grp_id():
    return ComponentGroup.grp_id_iter.__reduce__()[1][0]

@pytest.fixture
def next_layer_id():
    return Layer.id_iter.__reduce__()[1][0]

def test_create_layer(canvas, next_layer_id):
    layer = Layer("name", canvas)
    assert layer.layer_id == next_layer_id
    assert layer.canvas.width == 210
    assert layer.canvas.height == 297
    assert layer.canvas.units == "mm"
    assert layer.layer_name == "name"

def test_add_component_group(canvas, next_comp_grp_id):
    layer = Layer("name", canvas)
    group = ComponentGroup("TestGroup")
    style = DrawingStyle('test_style')
    box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
    pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
    group.add_component(box)
    group.add_component(pentagon)
    layer.add_component_group(group)
    assert layer.component_groups == {"TestGroup": next_comp_grp_id}

def test_remove_component_group(canvas, next_comp_grp_id):
    layer = Layer("name", canvas)
    group1 = ComponentGroup("Group1")
    group2 = ComponentGroup("Group2")
    style = DrawingStyle('default_style')
    box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
    pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
    group1.add_component(box)
    group2.add_component(pentagon)
    layer.add_component_group(group1)
    layer.add_component_group(group2, allow_collision=False)
    assert layer.component_groups == {"Group1": next_comp_grp_id, "Group2": next_comp_grp_id+1}
    layer.remove_component_group("Group2")
    assert layer.component_groups == {"Group1": next_comp_grp_id}

def test_boundary_component_groups(canvas, next_comp_grp_id):
    layer = Layer("name", canvas)
    group1 = ComponentGroup("Group1")
    group2 = ComponentGroup("Group2")
    style = DrawingStyle('some_style')
    box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
    pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
    group1.add_component(box)
    group2.add_component(pentagon)
    layer.add_component_group(group1, allow_collision=False, strict=True)
    assert layer.component_groups == {"Group1": next_comp_grp_id}
    with pytest.raises(ComponentGroupCollision):
        layer.add_component_group(group2, allow_collision=False)

def test_layer_class_errors(canvas, next_comp_grp_id):

    with pytest.raises(TypeError):
        # Boundary is the ancestor class of Canvas
        boundary = Boundary([(0,0), (5,0), (5,5), (0,5)], False)
        layer = Layer("name", boundary)

    with pytest.raises(TypeError):
        layer = Layer(5, canvas)

    with pytest.raises(TypeError):
        layer = Layer("name", canvas)
        group = ComponentGroup("Tester")
        style = DrawingStyle('another_style')
        box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
        pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
        group.add_component(box)
        group.add_component(pentagon)
        layer.add_component_group(group, allow_collision=5)

    with pytest.raises(TypeError):
        layer = Layer("name", canvas)
        group = ComponentGroup("Groupalicious")
        box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
        pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
        group.add_component(box)
        group.add_component(pentagon)
        layer.add_component_group(box)

    with pytest.raises(InvalidComponentGroupID):
        layer = Layer("name", canvas)
        group1 = ComponentGroup("Group1")
        group2 = ComponentGroup("Group2")
        style = DrawingStyle('default_style5')
        box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
        pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
        group1.add_component(box)
        group2.add_component(pentagon)
        layer.add_component_group(group1)
        layer.add_component_group(group2, allow_collision=False)
        layer.remove_component_group(4.5)

    with pytest.raises(InvalidComponentGroupID):
        layer = Layer("name", canvas)
        group1 = ComponentGroup("Group1")
        group2 = ComponentGroup("Group2")
        style = DrawingStyle('default_style1')
        box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
        pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
        group1.add_component(box)
        group2.add_component(pentagon)
        layer.add_component_group(group1)
        layer.add_component_group(group2, allow_collision=False)
        layer.remove_component_group("Group3")

    with pytest.raises(ComponentGroupOffCanvas):
        layer = Layer("name", canvas)
        group1 = ComponentGroup("Group1")
        style = DrawingStyle('default_style2')
        pentagon = RegularPolygonDrawingComponent((10, 10), 5, 25, style)
        group1.add_component(pentagon)
        layer.add_component_group(group1)

def test_default_layers(canvas, next_layer_id):
    page = Layers(canvas)
    assert page.layer("base").layer_id == next_layer_id

def test_named_layers(canvas, next_layer_id):
    page = Layers(canvas, "NewLayer")
    assert page.layer("NewLayer").layer_id == next_layer_id

def test_layer_id_lookup(canvas, next_layer_id):
    page = Layers(canvas, "NumberedLayer")
    assert page.layer(next_layer_id).layer_name == "NumberedLayer"

def test_layers_errors(canvas):
    new_canvas = Canvas(200, 300, "mm")
    layer = Layer("WillFail", new_canvas)
    with pytest.raises(IncompatibleCanvas):
        Layers(canvas, None, layer)

    with pytest.raises(TypeError):
        Layers(layer)

    with pytest.raises(TypeError):
        page = Layers(canvas, "BadLayer")
        page.layer(canvas)

    with pytest.raises(ValueError):
        page = Layers(canvas, "CorrectName")
        page.layer("WrongName")

def test_add_layer(canvas, next_layer_id):
    page = Layers(canvas)
    new_layer = Layer("SegmentationMask", canvas)
    page.add_layer(layer=new_layer)
    assert page.layer(next_layer_id).layer_name == "base"
    assert page.layer(next_layer_id+1).layer_name == "SegmentationMask"
    page.add_layer()
    assert page.layer(next_layer_id+2).layer_name == f"unamed_{next_layer_id+2}"
    assert page.layers == ["base", "SegmentationMask", f"unamed_{next_layer_id+2}"]

def test_add_layer_errors(canvas):
    page = Layers(canvas)
    with pytest.raises(TypeError):
        page.add_layer(layer=canvas)

    with pytest.raises(TypeError):
        page.add_layer(name=5)

def test_remove_layer(canvas, next_layer_id):

    page = Layers(canvas)
    new_layer = Layer("SegmentationMask", canvas)
    page.add_layer(layer=new_layer)
    assert page.layer(next_layer_id).layer_name == "base"
    assert page.layer(next_layer_id+1).layer_name == "SegmentationMask"
    page.add_layer()
    assert page.layer(next_layer_id+2).layer_name == f"unamed_{next_layer_id+2}"
    id = next_layer_id+2
    page.remove_layer(id)
    assert id not in page._layers
    page.remove_layer("SegmentationMask")
    assert len(page._layers) == 1

# Test Document class

def test_create_document(canvas, next_layer_id):
    document = Document(canvas)
    document.add_page(page=Layers(canvas, "base1"))
    document.add_page(page=Layers(canvas, "base2"))
    document.add_page(page=Layers(canvas, "base3"))
    assert document.pages == 3
    assert document.page(3).layer(next_layer_id+2).layer_name == "base3"
    document.add_page(position=2, page=Layers(canvas,"middle1"))
    assert document.pages == 4
    assert document.page(2).layer(next_layer_id+3).layer_name == "middle1"
    assert document.page(1).layers == ["base1"]
    assert document.page(2).layers == ["middle1"]
    assert document.page(3).layers == ["base2"]
    assert document.page(4).layers == ["base3"]
    document.add_page(position=1)
    assert document.page(1).layers == ["base"]

def test_remove_document(canvas, next_layer_id):
    document = Document(canvas)
    document.add_page(page=Layers(canvas, "base1"))
    document.add_page(page=Layers(canvas, "base2"))
    document.add_page(page=Layers(canvas, "base3"))
    assert document.pages == 3
    assert document.page(1).layers == ["base1"]
    document.remove_page(1)
    assert document.pages == 2
    assert document.page(1).layers == ["base2"]
    assert document.page(2).layers == ["base3"]
    document.add_page(page=Layers(canvas, "base4"))
    assert document.pages == 3
    assert document.page(3).layers == ["base4"]
    document.remove_page(3)
    assert document.pages == 2
    assert document.page(1).layers == ["base2"]
    assert document.page(2).layers == ["base3"]
    document.remove_page(1)
    document.remove_page(1)
    assert document.pages == 0

def test_creat_document_errors(canvas, next_layer_id):

    with pytest.raises(TypeError):
        layer1 = Layers(canvas)
        document = Document(layer1)

    document = Document(canvas)

    with pytest.raises(TypeError):
        document.add_page(page=canvas)

    with pytest.raises(ValueError):
        document.add_page(position=3, page=Layers(canvas, "base"))

    with pytest.raises(ValueError):
        document = Document(canvas)
        document.add_page(page=Layers(canvas, "base"))
        document.remove_page(2)

def test_save_and_recreate_layer_object(canvas):
    layer = Layer("name", canvas)
    group1 = ComponentGroup("Group1")
    group2 = ComponentGroup("Group2")
    style = DrawingStyle('testGrStyle')
    box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
    pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
    group1.add_component(box)
    group2.add_component(pentagon)
    layer.add_component_group(group1)
    layer.add_component_group(group2, allow_collision=False)

    params = layer.parameters

    layer2 = Layer.create_from_dict(params, {"testGrStyle": style})
    assert params == layer2.parameters

def test_save_and_recreate_layers_object(canvas):
    layer = Layer("base", canvas)
    group1 = ComponentGroup("Group1")
    group2 = ComponentGroup("Group2")
    style = DrawingStyle('testLayersStyle')
    box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
    pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
    group1.add_component(box)
    group2.add_component(pentagon)
    layer.add_component_group(group1)
    layer.add_component_group(group2, allow_collision=False)
    page = Layers(canvas, 'base', layer)
    new_layer = Layer("SegmentationMask", canvas)
    page.add_layer(layer=new_layer)

    params = page.parameters
    print(params)

    page_2 = Layers.create_from_dict(params, {"testLayersStyle": style})

    print(page_2.parameters)
    assert params == page_2.parameters

def test_save_and_recreate_document_object(canvas):
    document = Document(canvas)
    layer = Layer("base", canvas)
    group1 = ComponentGroup("Group1")
    group2 = ComponentGroup("Group2")
    style = DrawingStyle('testDocumentStyle')
    box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
    pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
    group1.add_component(box)
    group2.add_component(pentagon)
    layer.add_component_group(group1)
    layer.add_component_group(group2, allow_collision=False)
    page = Layers(canvas, 'base', layer)
    new_layer = Layer("SegmentationMask", canvas)
    page.add_layer(layer=new_layer)
    document.add_page(page=page)

    params = document.parameters

    doc_2 = Document.create_from_dict(params, {"testDocumentStyle": style})

    assert params == doc_2.parameters

def test_save_document_parameters_to_file(canvas):
    document = Document(canvas)
    layer = Layer("base", canvas)
    group1 = ComponentGroup("Group1")
    group2 = ComponentGroup("Group2")
    style = DrawingStyle('test_file_save_style')
    box = WidthHeightDrawingComponent((50, 50), 100, 100, style)
    pentagon = RegularPolygonDrawingComponent((100, 100), 5, 25, style)
    polygon = PolygonalDrawingComponent([(0,0), (2, 2), (2.5, 3)], style)
    group1.add_component(box)
    group2.add_component(pentagon)
    group2.add_component(polygon)
    layer.add_component_group(group1)
    layer.add_component_group(group2, allow_collision=False)
    page = Layers(canvas, 'base', layer)
    new_layer = Layer("SegmentationMask", canvas)
    page.add_layer(layer=new_layer)
    document.add_page(page=page)
    script_dir = os.path.dirname(__file__)
    relative_path = "temp_files"
    filename = "document.yaml"
    full_path = os.path.join(script_dir, relative_path, filename)

    document.save(full_path)
    assert os.path.exists(full_path)

    new_document, new_styles = Document.load(full_path, {"test_file_save_style": style})

    assert new_document.parameters == document.parameters
    assert new_styles == {"test_file_save_style": style}

def test_document_save_and_load_round_trip(tmp_path, canvas):
    document = Document(canvas)
    document.add_page()
    base_layer = document.page(1).layer("base")

    style = DrawingStyle('round_trip_style')
    group = ComponentGroup("SerializedGroup")
    box = WidthHeightDrawingComponent((20.0, 20.0), 30.0, 15.0, style)
    group.add_component(box)
    base_layer.add_component_group(group, allow_collision=False)

    yaml_path = tmp_path / "document.yaml"
    document.save(str(yaml_path))

    if style.name in Style.style_names:
        Style.style_names.remove(style.name)
    loaded_doc, styles = Document.load(str(yaml_path))
    assert loaded_doc.parameters == document.parameters
    assert styles

def test_interdict():
    file = "C:\\Users\\cmill\\OneDrive\\Documents\\PythonScripts\\DrawingGen\\tests\\temp_files\\test_document.json"
    with open(file) as json_file:
        data = json.load(json_file)
    print(data)
