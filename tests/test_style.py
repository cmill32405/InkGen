
import pytest

from InkGen.style import DrawingStyle, Font, Style, TextStyle


@pytest.fixture
def next_id():
    return Style.id_iter.__reduce__()[1][0]

def test_create_style(next_id):
    style = Style("Joe")
    assert style.id == next_id
    assert style.name == "Joe"

def test_invalid_name(next_id):
    with pytest.raises(TypeError):
        Style(DrawingStyle(name="WTF"))
    with pytest.raises(TypeError):
        Style({"dog": 1})
    with pytest.raises(TypeError):
        Style(1)

def test_cant_set_id_or_name(next_id):
    name = "Volcano"
    style = Style(name)
    assert style.id == next_id
    assert style.name == name

    with pytest.raises(AttributeError):
        style.id = 2
    with pytest.raises(AttributeError):
        style.name = "Frank"

    assert style.id == next_id
    assert style.name == name

def test_cant_reuse_style_name(next_id):
    name = "Original"
    Style(name)

    with pytest.raises(ValueError):
        Style(name)

def test_create_drawingstyle(next_id):
    name = "Bob"
    stroke = "#ff2201"
    fill = "#ffffff"
    style = DrawingStyle(name=name, stroke=stroke, stroke_width=0.3,
                         fill=fill, stroke_opacity=0.9, fill_opacity=0.8)
    assert style.id == next_id
    assert style.name == name
    assert style.stroke == stroke
    assert style.stroke_width == 0.3
    assert style.fill == fill
    assert style.stroke_opacity == 0.9
    assert style.fill_opacity == 0.8


def test_update_drawingstyle(next_id):
    name = "Bill"
    stroke = "#ff2201"
    fill = "#ffffff"
    style = DrawingStyle(name=name, stroke=stroke, stroke_width=0.3,
                         fill=fill, stroke_opacity=0.9, fill_opacity=0.8)
    assert style.id == next_id
    assert style.name == name
    assert style.stroke == stroke
    assert style.stroke_width == 0.3
    assert style.fill == fill
    assert style.stroke_opacity == 0.9
    assert style.fill_opacity == 0.8

    new_stroke = "#aa3311"
    new_fill = "#112233"
    new_width = 0.5
    new_stroke_opacity = 0.2
    new_fill_opacity = 0.1

    style.stroke = new_stroke
    assert style.stroke == new_stroke

    style.fill = new_fill
    assert style.fill == new_fill

    style.stroke_width = new_width
    assert style.stroke_width == new_width

    style.stroke_opacity = new_stroke_opacity
    assert style.stroke_opacity == new_stroke_opacity

    style.fill_opacity = new_fill_opacity
    assert style.fill_opacity == new_fill_opacity

def test_create_and_update_style_with_named_colors(next_id):
    name = "Colors"
    stroke = "black"
    fill = "Blue"
    style = DrawingStyle(name=name, stroke=stroke, fill=fill)
    assert style.id == next_id
    assert style.name == name
    assert style.stroke == '#000000'
    assert style.fill == "#0000ff"

def test_invalid_colors(next_id):
    name = "BadColors"
    stroke = "orangutan"
    fill = "Blue"
    with pytest.raises(ValueError):
        DrawingStyle(name=name, stroke=stroke, fill=fill)

    stroke = "black"
    fill = "putrid"
    with pytest.raises(ValueError):
        DrawingStyle(name=name, stroke=stroke, fill=fill)

    stroke = "#0123ag"
    fill = "Blue"
    with pytest.raises(ValueError):
        DrawingStyle(name=name, stroke=stroke, fill=fill)

    stroke = "black"
    fill = "#11223g"
    with pytest.raises(ValueError):
        style = DrawingStyle(name=name, stroke=stroke, fill=fill)

    stroke = "#ffffaab"
    fill = "Blue"
    with pytest.raises(ValueError):
        style = DrawingStyle(name=name, stroke=stroke, fill=fill)

    stroke = "black"
    fill = "#ffffaab"
    with pytest.raises(ValueError):
        style = DrawingStyle(name=name, stroke=stroke, fill=fill)

    stroke = "001122"
    fill = "Blue"
    with pytest.raises(ValueError):
        style = DrawingStyle(name=name, stroke=stroke, fill=fill)

    stroke = "black"
    fill = "001122"
    with pytest.raises(ValueError):
        style = DrawingStyle(name=name, stroke=stroke, fill=fill)

    name = "GoodColors"
    stroke = "Black"
    fill = "Blue"

    style = DrawingStyle(name=name, stroke=stroke, fill=fill)
    assert style.name == name
    assert style.stroke == "#000000"
    assert style.fill == "#0000ff"

    with pytest.raises(ValueError):
        style.stroke = "Orangee"

    with pytest.raises(ValueError):
        style.fill = "Pinkish"

    with pytest.raises(ValueError):
        style.stroke = "#00aabg"

    with pytest.raises(ValueError):
        style.fill = "#00aabg"

    with pytest.raises(ValueError):
        style.stroke = "00aabb"

    with pytest.raises(ValueError):
        style.fill = "00aabb"

    with pytest.raises(ValueError):
        style.stroke = "#00aabba"

    with pytest.raises(ValueError):
        style.fill = "#00aabba"

    with pytest.raises(ValueError):
        style.stroke = "00aabba"

    with pytest.raises(ValueError):
        style.fill = "00aabba"

def test_invalid_opacity(next_id):
    name = "Opacities"
    stroke = "black"
    fill = "Blue"
    with pytest.raises(ValueError):
        style = DrawingStyle(name=name, stroke=stroke, fill=fill, stroke_opacity=1.00000001)

    with pytest.raises(ValueError):
        style = DrawingStyle(name=name, stroke=stroke, fill=fill, fill_opacity=1.00000001)

    style = DrawingStyle(name=name, stroke=stroke, fill=fill, stroke_opacity=0.0, fill_opacity=1.0)

    with pytest.raises(ValueError):
        style.stroke_opacity = 1.0001

    with pytest.raises(ValueError):
        style.fill_opacity = 1.0001

    with pytest.raises(ValueError):
        style.stroke_opacity = -0.0000001

    with pytest.raises(ValueError):
        style.fill_opacity = -0.0000001

# Test Font Class
def test_create_font():

    ff = Font("Times New Roman", "italic", "small-caps", "expanded", "bold", 16.0)
    assert ff.family == "Times New Roman"
    assert ff.style == "italic"
    assert ff.variant == "small-caps"
    assert ff.stretch == "expanded"
    assert ff.weight == "bold"
    assert ff.size == 16.0

def test_create_font_custom_location():
    ff = Font(family="Times New Roman", custom_font_paths="C:\\Windows\\Fonts")
    assert ff.family == "Times New Roman"

def test_update_font():

    ff = Font("Times New Roman", "italic", "small-caps", "expanded", "bold", 16.0)
    assert ff.family == "Times New Roman"
    assert ff.style == "italic"
    assert ff.variant == "small-caps"
    assert ff.stretch == "expanded"
    assert ff.weight == "bold"
    assert ff.size == 16.0
    assert ff.font_file.replace("\\", "/") == "C:/Windows/Fonts/timesbi.ttf"

    ff.style = "normal"
    ff.variant = "normal"
    ff.stretch = "normal"
    ff.weight = "normal"
    ff.size = 20.0
    assert ff.style == "normal"
    assert ff.variant == "normal"
    assert ff.stretch == "normal"
    assert ff.weight == "normal"
    assert ff.size == 20.0

    ff.family = "arial"
    ff.stretch = 500
    ff.weight = 500
    ff.size = "x-large"
    assert ff.family == "Arial"
    assert ff.stretch == 500
    assert ff.weight == 500
    assert ff.size == 14.399999999999999
    assert ff.configuration == "arial:style=normal:variant=normal:weight=500:stretch=500:size=14.399999999999999"

# @pytest.fixture
# def platform(mocker):
#     mock = Mock()
#     #mocker.patch('platform.system', return_value=mock)
#     mock.system.return_value = "Linux"
#     return mock

# def test_system_files(platform):
#     assert platform.system() == "Linux"
#     ff = Font(family="Times New Roman")
#     assert ff._font_paths == ['/usr/bin/fc-list',
#                     '/usr/sbin/fc-list',
#                     '/usr/local/sbin/fc-list',
#                     '/usr/local/bin/fc-list']



def test_font_errors():

    with pytest.raises(ValueError):
        ff = Font(family="Times New Roman", custom_font_paths="C:\\Windows\\Font")

    ff = Font(family="Times New Roman")

    with pytest.raises(ValueError):
        ff.style = "error"

    with pytest.raises(ValueError):
        ff.variant = "error"

    with pytest.raises(ValueError):
        ff.weight = "error"

    with pytest.raises(ValueError):
        ff.stretch = "error"

    with pytest.raises(ValueError):
        ff.size = "error"

# Test TextStyle

@pytest.fixture
def font():
    ff = Font("Times New Roman")
    return ff

def test_create_text_style(font):
    ts = TextStyle("Test", font)
    assert ts.name == "Test"
    assert ts.color == "#000000"
    assert ts.superscript is False
    assert ts.subscript is False
    assert ts.text_align == "start"
    assert ts.text_anchor == "start"
    assert ts.line_spacing == 1.0
    assert ts.font.family == "Times New Roman"

def test_update_text_style(font):
    ts = TextStyle("Test1", font)
    new_font = Font("arial")
    assert ts.font.family == "Times New Roman"
    ts.font = new_font
    assert ts.font.family == "Arial"
    ts.color = "#FFFFFF"
    assert ts.color == "#ffffff"
    ts.text_align = "end"
    assert ts.text_align == "end"
    assert ts.text_anchor == "end"
    ts.text_align = "center"
    assert ts.text_align == "center"
    assert ts.text_anchor == "middle"
    ts.line_spacing = 1.5
    assert ts.line_spacing == 1.5

def test_style_errors(font):
    ts = TextStyle("Test2", font)
    style = Style("Oops")
    with pytest.raises(TypeError):
        ts.font = style

    with pytest.raises(ValueError):
        ts.color = "NotColor"

    with pytest.raises(TypeError):
        ts.subscript = "False"

    with pytest.raises(TypeError):
        ts.superscript = "False"

    with pytest.raises(TypeError):
        ts.line_spacing = "f"

def test_save_and_create_style():
    style = Style("test_another_style")
    assert style.parameters == {"Style": {"name": "test_another_style"}}

    style_2 = Style.create_from_dict({"Style": {"name": "another_style_obj"}})
    assert style_2.name == "another_style_obj"

def test_save_and_create_drawing_style():
    style = DrawingStyle("Test_this_drawing_style",
                         "red", 0.4, "red", 0.5, 0.5)
    assert style.parameters == {"DrawingStyle": {"name": "Test_this_drawing_style",
                                                 "stroke": '#ff0000',
                                                 "stroke_width": 0.4,
                                                 "fill": '#ff0000',
                                                 "stroke_opacity": 0.5,
                                                 "fill_opacity": 0.5}}

    style_2 = DrawingStyle.create_from_dict({"DrawingStyle":
                                             {"name": "Make_another_of_these",
                                              "stroke": "red",
                                              "stroke_width": 0.4,
                                              "fill": "red",
                                              "stroke_opacity": 0.5,
                                              "fill_opacity": 0.5}})

    assert style_2.name == "Make_another_of_these"
    assert style_2.stroke == '#ff0000'
    assert style_2.stroke_width == 0.4
    assert style_2.fill == '#ff0000'
    assert style_2.stroke_opacity == 0.5
    assert style_2.fill_opacity == 0.5

def test_save_and_create_text_style():
    font_ = Font("Times New Roman", "italic", "normal", "normal", "bold", 12.0, 'C:/Windows/Fonts/')
    font_parameters = font_.parameters
    assert font_parameters["Font"]["family"] == "Times New Roman"
    assert font_parameters["Font"]["style"] == "italic"
    assert font_parameters["Font"]["variant"] == "normal"
    assert font_parameters["Font"]["stretch"] == "normal"
    assert font_parameters["Font"]["weight"] == "bold"
    assert font_parameters["Font"]["size"] == 12.0
    assert 'C:/Windows/Fonts/' in font_parameters["Font"]["custom_font_paths"]

    style = TextStyle("Let's make a Text Style!", font=font_)
    style.color = "red"
    style.line_spacing = 2
    style.text_align = "end"
    style.superscript = True
    style_parameters = style.parameters
    style_parameters['TextStyle']['name'] = "The style formally known as Pharos."

    style_2 = TextStyle.create_from_dict(style_parameters)
    assert style_2.color == '#ff0000'
    assert style_2.font.family == "Times New Roman"
    assert style_2.line_spacing == 2.0
    assert style_2.text_align == "end"
    assert style_2.superscript is True
