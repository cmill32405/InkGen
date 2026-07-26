"""Linear-gradient value, renderer, truth, and failure contracts."""

from __future__ import annotations

import json
import math
from dataclasses import FrozenInstanceError
from xml.etree import ElementTree

import pytest

from InkGen import GradientStop, LinearGradientFill
from InkGen.boundary import Canvas
from InkGen.document_outputs import FlowDocument
from InkGen.drawing_components import DrawingComponentGroup, OutputFormat, RectangleDrawing
from InkGen.dxf_generator import DXFDocument
from InkGen.extraction_truth import (
    ExtractionTruthRecord,
    annotate_extraction_truth,
    sort_extraction_truth_records,
)
from InkGen.gradients import _zero_near_origin, coerce_linear_gradient
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import (
    ComponentGroupSVG,
    DocumentSVG,
    RectangleSVG,
    _style_properties,
)


def _style(*, fill_opacity: float = 1.0) -> DrawingStyle:
    """Return a unique style for one gradient contract test."""
    return DrawingStyle(
        f"gradient_contract_{len(DrawingStyle.style_names)}",
        stroke="#112233",
        stroke_width=0.4,
        fill="#abcdef",
        fill_opacity=fill_opacity,
    )


def _gradient(*, angle_deg: float = 0.0) -> LinearGradientFill:
    """Return the two-stop gradient used by DocInt's panel contract."""
    return LinearGradientFill([(0.0, "#008040"), (1.0, "#ffffff")], angle_deg)


def _pdf_document(rectangle: RectanglePDF) -> DocumentPDF:
    """Put one rectangle through the live PDF document path."""
    document = DocumentPDF(Canvas(100.0, 80.0, "mm"))
    document.add_page()
    group = ComponentGroupPDF("gradient-panel")
    group.add_component(rectangle)
    document.page(1).layer("base").add_component_group(group)
    return document


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_linear_gradient_normalizes_angle_stops_and_payload() -> None:
    """LINEAR-GRADIENT-P1: Public gradient values normalize into deterministic parameters."""
    gradient = LinearGradientFill(
        [GradientStop(0, "#008040"), (0.4, "#80c0a0"), [1, "#FFFFFF"]],
        -90,
    )

    assert gradient.angle_deg == 270.0
    assert gradient.stops == (
        GradientStop(0.0, "#008040"),
        GradientStop(0.4, "#80c0a0"),
        GradientStop(1.0, "#ffffff"),
    )
    assert gradient.parameters == {
        "kind": "linear",
        "stops": [[0.0, "#008040"], [0.4, "#80c0a0"], [1.0, "#ffffff"]],
        "angle_deg": 270.0,
    }
    assert LinearGradientFill.from_dict(gradient.parameters) == gradient
    assert coerce_linear_gradient(gradient) is gradient


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_gradient_values_are_immutable_and_default_to_zero_degrees() -> None:
    """LINEAR-GRADIENT-P1: Value objects are frozen and omitted angles mean zero."""
    stop = GradientStop(0.0, "#000000")
    gradient = LinearGradientFill([stop, (1.0, "#ffffff")])

    assert gradient.angle_deg == 0.0
    assert LinearGradientFill.from_dict({"kind": "linear", "stops": [[0.0, "#000000"], [1.0, "#ffffff"]]}).angle_deg == 0.0
    with pytest.raises(FrozenInstanceError):
        stop.offset = 0.5  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        gradient.angle_deg = 90.0  # type: ignore[misc]


@pytest.mark.condition("LINEAR-GRADIENT-P1")
@pytest.mark.parametrize(
    ("offset", "color", "error"),
    [
        (True, "#000000", TypeError),
        (object(), "#000000", TypeError),
        (float("nan"), "#000000", ValueError),
        (1.1, "#000000", ValueError),
        (0.0, 123, TypeError),
        (0.0, "#00000", ValueError),
        (0.0, "#0000000", ValueError),
        (0.0, "x000000", ValueError),
        (0.0, "#g00000", ValueError),
        (0.0, "#00000g", ValueError),
    ],
)
def test_gradient_stop_rejects_each_invalid_boundary(
    offset: object,
    color: object,
    error: type[Exception],
) -> None:
    """LINEAR-GRADIENT-P1: Each independent stop invariant rejects bad data."""
    with pytest.raises(error):
        GradientStop(offset, color)  # type: ignore[arg-type]


@pytest.mark.condition("LINEAR-GRADIENT-P1")
@pytest.mark.parametrize("value", ["00", b"00", object(), [0.0], [0.0, "#000000", "extra"]])
def test_gradient_stop_pair_coercion_rejects_non_pairs(value: object) -> None:
    """LINEAR-GRADIENT-P1: Stop coercion accepts only non-string two-item sequences."""
    with pytest.raises(TypeError, match="offset/color pairs"):
        GradientStop.from_value(value)


@pytest.mark.condition("LINEAR-GRADIENT-P1")
@pytest.mark.parametrize("angle", [True, "90", float("nan")])
def test_linear_gradient_rejects_non_numeric_or_non_finite_angles(angle: object) -> None:
    """LINEAR-GRADIENT-P1: Angle validation excludes bools, strings, and NaN."""
    error = ValueError if isinstance(angle, float) else TypeError
    with pytest.raises(error):
        LinearGradientFill([(0.0, "#000000"), (1.0, "#ffffff")], angle)  # type: ignore[arg-type]


@pytest.mark.condition("LINEAR-GRADIENT-P1")
@pytest.mark.parametrize(
    ("value", "error", "message"),
    [
        ({"kind": "radial", "stops": [[0.0, "#000000"], [1.0, "#ffffff"]]}, ValueError, "kind must be 'linear'"),
        ({"kind": "aardvark", "stops": [[0.0, "#000000"], [1.0, "#ffffff"]]}, ValueError, "kind must be 'linear'"),
        ({"stops": [[0.0, "#000000"], [1.0, "#ffffff"]]}, ValueError, "kind must be 'linear'"),
        ({"kind": "linear"}, ValueError, "must include stops"),
        ({"kind": "linear", "stops": "bad"}, TypeError, "must be a sequence"),
        ({"kind": "linear", "stops": [[0.0, "#000000"]]}, ValueError, "at least two stops"),
        (
            {"kind": "linear", "stops": [[0.0, "#000000"], [0.0, "#ffffff"]]},
            ValueError,
            "strictly increasing",
        ),
        (
            {"kind": "linear", "stops": [[0.7, "#000000"], [0.2, "#ffffff"]]},
            ValueError,
            "strictly increasing",
        ),
        (
            {"kind": "linear", "stops": [[-0.1, "#000000"], [1.0, "#ffffff"]]},
            ValueError,
            "between 0.0 and 1.0",
        ),
        (
            {"kind": "linear", "stops": [[0.0, "green"], [1.0, "#ffffff"]]},
            ValueError,
            "#rrggbb",
        ),
        (
            {"kind": "linear", "stops": [[0.0, "#000000"], [1.0, "#ffffff"]], "angle_deg": float("inf")},
            ValueError,
            "angle_deg must be finite",
        ),
    ],
)
def test_linear_gradient_rejects_malformed_public_payloads(
    value: object,
    error: type[Exception],
    message: str,
) -> None:
    """LINEAR-GRADIENT-P1: Malformed gradients fail before renderer materialization."""
    with pytest.raises(error, match=message):
        LinearGradientFill.from_dict(value)


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_linear_gradient_axis_cardinal_directions_use_visual_ccw_semantics() -> None:
    """LINEAR-GRADIENT-P1: Canvas axes use CCW angles despite top-left y coordinates."""
    box = ((10.0, 20.0), 40.0, 20.0)

    assert _gradient(angle_deg=0).axis_for_box(*box) == pytest.approx((10.0, 30.0, 50.0, 30.0))
    assert _gradient(angle_deg=90).axis_for_box(*box) == pytest.approx((30.0, 40.0, 30.0, 20.0))
    assert _gradient(angle_deg=180).axis_for_box(*box) == pytest.approx((50.0, 30.0, 10.0, 30.0))
    assert _gradient(angle_deg=270).axis_for_box(*box) == pytest.approx((30.0, 20.0, 30.0, 40.0))


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_linear_gradient_extends_only_missing_endpoint_stops() -> None:
    """LINEAR-GRADIENT-P1: PDF endpoint extension preserves colors and existing stops."""
    complete = LinearGradientFill([(0.0, "#111111"), (1.0, "#eeeeee")])
    interior = LinearGradientFill([(0.2, "#112233"), (0.8, "#ddeeff")])

    assert complete.extended_stops() == complete.stops
    assert interior.extended_stops() == (
        GradientStop(0.0, "#112233"),
        GradientStop(0.2, "#112233"),
        GradientStop(0.8, "#ddeeff"),
        GradientStop(1.0, "#ddeeff"),
    )


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_gradient_axis_rejects_negative_and_non_finite_geometry() -> None:
    """LINEAR-GRADIENT-P1: Axis construction rejects every invalid geometry class."""
    gradient = _gradient()

    for width, height in ((-1.0, 1.0), (1.0, -1.0), (0.0, 1.0), (1.0, 0.0)):
        with pytest.raises(ValueError, match="positive width and height"):
            gradient.axis_for_box((0.0, 0.0), width, height)
    for position, width, height in (
        ((float("nan"), 0.0), 1.0, 1.0),
        ((0.0, float("inf")), 1.0, 1.0),
        ((0.0, 0.0), float("inf"), 1.0),
        ((0.0, 0.0), 1.0, float("nan")),
    ):
        with pytest.raises(ValueError, match="geometry must be finite"):
            gradient.axis_for_box(position, width, height)


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_gradient_axis_zero_normalization_has_an_exact_tolerance_boundary() -> None:
    """LINEAR-GRADIENT-P1: Trig residue is zeroed strictly below the documented tolerance."""
    assert _zero_near_origin(0.0) == 0.0
    assert _zero_near_origin(5e-13) == 0.0
    assert _zero_near_origin(-5e-13) == 0.0
    assert _zero_near_origin(1e-12) == 1e-12
    assert _zero_near_origin(-1e-12) == -1e-12


@pytest.mark.condition("LINEAR-GRADIENT-P1")
@pytest.mark.parametrize("angle_deg", [0.0, 17.0, 45.0, 89.0, 90.0, 137.0, 225.0, 359.0])
@pytest.mark.parametrize(("width", "height"), [(1.0, 1.0), (80.0, 5.0), (5.0, 80.0), (37.5, 19.25)])
def test_linear_gradient_axis_spans_every_rectangle_corner(
    angle_deg: float,
    width: float,
    height: float,
) -> None:
    """LINEAR-GRADIENT-P1: Axis endpoints equal the extrema of all corner projections."""
    x, y = 7.25, 11.5
    x1, y1, x2, y2 = _gradient(angle_deg=angle_deg).axis_for_box((x, y), width, height)
    axis_x = x2 - x1
    axis_y = y2 - y1
    axis_length = math.hypot(axis_x, axis_y)
    direction = (axis_x / axis_length, axis_y / axis_length)
    projections = [
        corner_x * direction[0] + corner_y * direction[1]
        for corner_x, corner_y in (
            (x, y),
            (x + width, y),
            (x, y + height),
            (x + width, y + height),
        )
    ]

    assert x1 * direction[0] + y1 * direction[1] == pytest.approx(min(projections))
    assert x2 * direction[0] + y2 * direction[1] == pytest.approx(max(projections))
    visual_angle = math.degrees(math.atan2(-axis_y, axis_x)) % 360.0
    assert visual_angle == pytest.approx(angle_deg)


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_gradient_rectangles_reject_degenerate_geometry() -> None:
    """LINEAR-GRADIENT-P1: Zero-area gradient panels fail rather than emit invalid axes."""
    gradient = _gradient()
    style = _style()

    with pytest.raises(ValueError, match="positive width and height"):
        RectangleDrawing((0.0, 0.0), 0.0, 10.0, 0.0, style, gradient)
    with pytest.raises(ValueError, match="positive width and height"):
        RectangleSVG((0.0, 0.0), 10.0, 0.0, 0.0, style, gradient)
    with pytest.raises(ValueError, match="positive width and height"):
        RectanglePDF((0.0, 0.0), 0.0, 0.0, 0.0, style, gradient)


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_neutral_gradient_rectangle_materializes_and_round_trips() -> None:
    """LINEAR-GRADIENT-P1: Neutral rectangle payloads reach both supported renderers."""
    gradient = _gradient(angle_deg=30.0)
    style = _style()
    drawing = RectangleDrawing((10.0, 20.0), 40.0, 15.0, 2.0, style, gradient)

    svg = drawing.to_component(OutputFormat.SVG)
    pdf = drawing.to_component(OutputFormat.PDF)
    svg_clone = RectangleSVG.create_from_dict(svg.parameters, style)
    pdf_clone = RectanglePDF.create_from_dict(pdf.parameters, style)

    assert drawing.fill_gradient == gradient.parameters
    assert isinstance(svg, RectangleSVG)
    assert isinstance(pdf, RectanglePDF)
    assert svg.fill_gradient == gradient
    assert pdf.fill_gradient == gradient
    assert svg_clone.parameters == svg.parameters
    assert pdf_clone.parameters == pdf.parameters


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_flow_document_serializes_gradient_rectangle_as_plain_data() -> None:
    """LINEAR-GRADIENT-P1: Neutral gradient payloads remain JSON-safe flow-document data."""
    style = _style()
    group = DrawingComponentGroup(
        "gradient-panel",
        [RectangleDrawing((10.0, 20.0), 40.0, 15.0, 0.0, style, _gradient(angle_deg=25.0))],
    )
    document = FlowDocument(title="Gradient Panel")
    document.add_drawing_group(group)

    payload = document.parameters
    recreated = FlowDocument.create_from_dict(json.loads(json.dumps(payload)), {style.name: style})

    assert recreated.parameters == payload
    component_payload = payload["FlowDocument"]["blocks"][0]["payload"]["components"][0]["payload"]
    assert component_payload["fill_gradient"] == _gradient(angle_deg=25.0).parameters


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_solid_rectangles_keep_legacy_parameter_and_markup_shapes() -> None:
    """LINEAR-GRADIENT-P1: Opt-in gradients do not alter existing solid rectangles."""
    style = _style()
    svg = RectangleSVG((1.0, 2.0), 3.0, 4.0, 0.0, style)
    pdf = RectanglePDF((1.0, 2.0), 3.0, 4.0, 0.0, style)

    assert "fill_gradient" not in svg.parameters["RectangleSVG"]
    assert "fill_gradient" not in pdf.parameters["RectanglePDF"]
    assert "<linearGradient" not in svg.generate_svg()
    assert "fill:#abcdef" in svg.generate_svg()
    assert "1 2 3 4 re" in pdf.generate_pdf()
    assert " sh" not in pdf.generate_pdf()


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_svg_gradient_emits_user_space_axis_stops_and_reference() -> None:
    """LINEAR-GRADIENT-P1: SVG output uses a physical user-space gradient axis."""
    rectangle = RectangleSVG((10.0, 20.0), 40.0, 20.0, 0.0, _style(), _gradient(angle_deg=90.0))
    payload = rectangle.generate_svg()

    assert "<defs>" in payload
    assert "<linearGradient" in payload
    assert 'gradientUnits="userSpaceOnUse"' in payload
    assert 'x1="30"' in payload
    assert 'y1="40"' in payload
    assert 'x2="30"' in payload
    assert 'y2="20"' in payload
    assert '<stop offset="0.0" stop-color="#008040" />' in payload
    assert '<stop offset="1.0" stop-color="#ffffff" />' in payload
    assert f"fill:url(#linearGradient{rectangle.id})" in payload
    ElementTree.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{payload}</svg>')


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_svg_gradient_fill_override_preserves_opacity_and_none_semantics() -> None:
    """LINEAR-GRADIENT-P1: Paint-server fills get opacity while dynamic none does not."""
    gradient_style = _style(fill_opacity=0.35)
    payload = RectangleSVG(
        (1.0, 2.0),
        10.0,
        5.0,
        0.0,
        gradient_style,
        _gradient(),
    ).generate_svg()
    none_style = DrawingStyle(
        f"gradient_none_{len(DrawingStyle.style_names)}",
        stroke="#112233",
        fill="".join(("n", "one")),
        fill_opacity=0.35,
    )

    assert "fill:url(#linearGradient" in payload
    assert "fill-opacity:0.35" in payload
    assert "fill-opacity:0.35" in _style_properties(gradient_style)
    assert "fill:none" in _style_properties(none_style)
    assert "fill-opacity" not in _style_properties(none_style)


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_svg_truth_parameter_provider_distinguishes_solid_and_gradient_rectangles() -> None:
    """LINEAR-GRADIENT-P1: SVG truth metadata is absent for solid fills and exact for gradients."""
    style = _style()
    solid = RectangleSVG((0.0, 0.0), 10.0, 5.0, 0.0, style)
    gradient = RectangleSVG((0.0, 0.0), 10.0, 5.0, 0.0, style, _gradient(angle_deg=15.0))

    assert solid.extraction_truth_parameters() is None
    assert gradient.extraction_truth_parameters() == {"fill_gradient": _gradient(angle_deg=15.0).parameters}


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_svg_document_live_path_writes_parseable_gradient(tmp_path) -> None:
    """LINEAR-GRADIENT-P1: DocumentSVG writes the gradient through its normal page path."""
    document = DocumentSVG(Canvas(100.0, 80.0, "mm"))
    document.add_page()
    group = ComponentGroupSVG("gradient-panel")
    group.add_component(RectangleSVG((10.0, 20.0), 40.0, 20.0, 0.0, _style(), _gradient(angle_deg=15.0)))
    document.page(1).layer("base").add_component_group(group)
    target = tmp_path / "gradient.svg"

    document.create_svg(target)
    payload = target.read_text(encoding="utf-8")

    assert "<linearGradient" in payload
    assert "fill:url(#linearGradient" in payload
    ElementTree.fromstring(payload)


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_pdf_gradient_emits_axial_shading_clip_stroke_and_opacity() -> None:
    """LINEAR-GRADIENT-P1: PDF output registers and invokes a clipped axial shading."""
    rectangle = RectanglePDF(
        (10.0, 20.0),
        40.0,
        20.0,
        3.0,
        _style(fill_opacity=0.5),
        _gradient(angle_deg=90.0),
    )
    payload = _pdf_document(rectangle).to_pdf_bytes().decode("latin-1")

    assert "/Shading << /Sh1 " in payload
    assert "/ShadingType 2" in payload
    assert "/Coords [30 40 30 20]" in payload
    assert "/FunctionType 2" in payload
    assert "/C0 [0 0.501961 0.25098]" in payload
    assert "/C1 [1 1 1]" in payload
    assert "/Extend [true true]" in payload
    assert "/Sh1 sh" in payload
    assert "\nW\nn\n/Sh1 sh\n" in payload
    assert "/ExtGState" in payload
    assert "/ca 0.5" in payload
    assert "/GS1 gs" in payload
    assert "0.066667 0.133333 0.2 RG" in payload
    assert payload.count(" c\n") >= 4


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_pdf_two_stop_gradient_uses_one_interpolation_function() -> None:
    """LINEAR-GRADIENT-P1: Two stops avoid an unnecessary stitching function."""
    payload = _pdf_document(RectanglePDF((10.0, 20.0), 40.0, 20.0, 0.0, _style(), _gradient())).to_pdf_bytes().decode("latin-1")

    assert payload.count("/FunctionType 2") == 1
    assert "/FunctionType 3" not in payload
    assert "/Bounds [" not in payload
    assert "/Encode [" not in payload


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_pdf_gradient_emits_stitching_function_for_n_stops() -> None:
    """LINEAR-GRADIENT-P1: N-stop PDF gradients use one axial shading with stitched functions."""
    gradient = LinearGradientFill(
        [(0.2, "#000000"), (0.5, "#ff0000"), (0.8, "#ffffff")],
        0.0,
    )
    payload = _pdf_document(RectanglePDF((10.0, 20.0), 40.0, 20.0, 0.0, _style(), gradient)).to_pdf_bytes().decode("latin-1")

    assert "/ShadingType 2" in payload
    assert "/FunctionType 3" in payload
    assert payload.count("/FunctionType 2") == 4
    assert "/Bounds [0.2 0.5 0.8]" in payload
    assert "/Encode [0 1 0 1 0 1 0 1]" in payload


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_pdf_even_stop_gradient_emits_one_encode_pair_per_segment() -> None:
    """LINEAR-GRADIENT-P1: Stitching encode cardinality is N minus one for even N."""
    gradient = LinearGradientFill(
        [
            (0.0, "#000000"),
            (0.25, "#404040"),
            (0.75, "#bfbfbf"),
            (1.0, "#ffffff"),
        ]
    )
    payload = _pdf_document(RectanglePDF((10.0, 20.0), 40.0, 20.0, 0.0, _style(), gradient)).to_pdf_bytes().decode("latin-1")

    assert payload.count("/FunctionType 2") == 3
    assert "/Bounds [0.25 0.75]" in payload
    assert "/Encode [0 1 0 1 0 1]" in payload


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_pdf_registers_distinct_gradients_and_reuses_identical_resources() -> None:
    """LINEAR-GRADIENT-P1: Shading resource names are unique and deterministic."""
    style = _style()
    document = DocumentPDF(Canvas(100.0, 80.0, "mm"))
    document.add_page()
    group = ComponentGroupPDF("gradient-resources")
    first = RectanglePDF((5.0, 5.0), 20.0, 10.0, 0.0, style, _gradient())
    second = RectanglePDF((30.0, 5.0), 20.0, 10.0, 0.0, style, _gradient(angle_deg=90.0))
    first_clone = RectanglePDF((5.0, 5.0), 20.0, 10.0, 0.0, style, _gradient())
    group.add_component(first)
    group.add_component(second)
    group.add_component(first_clone)
    document.page(1).layer("base").add_component_group(group)
    payload = document.to_pdf_bytes().decode("latin-1")

    assert "/Shading << /Sh1 " in payload
    assert "/Sh2 " in payload
    assert "/Sh0 " not in payload
    assert payload.count("/ShadingType 2") == 2
    assert payload.count("/Sh1 sh") == 2
    assert payload.count("/Sh2 sh") == 1


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_pdf_gradient_live_render_changes_color_along_requested_axis() -> None:
    """LINEAR-GRADIENT-P1: A PDF consumer renders a smooth directional color transition."""
    fitz = pytest.importorskip("fitz")
    rectangle = RectanglePDF((10.0, 20.0), 40.0, 20.0, 0.0, _style(), _gradient(angle_deg=0.0))
    pdf = fitz.open(stream=_pdf_document(rectangle).to_pdf_bytes(), filetype="pdf")
    pixmap = pdf[0].get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
    points_per_mm = 72.0 / 25.4

    def sample(x_mm: float, y_mm: float) -> tuple[int, int, int]:
        x = round(x_mm * points_per_mm * 2.0)
        y = round(y_mm * points_per_mm * 2.0)
        return pixmap.pixel(x, y)

    left = sample(15.0, 30.0)
    middle = sample(30.0, 30.0)
    right = sample(45.0, 30.0)

    assert all(left[channel] < middle[channel] < right[channel] for channel in range(3))


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_extraction_truth_includes_gradient_parameters_and_pdf_bbox() -> None:
    """LINEAR-GRADIENT-P1: Truth records preserve both panel bounds and gradient intent."""
    gradient = _gradient(angle_deg=35.0)
    style = _style()
    rectangle = RectanglePDF((10.0, 20.0), 40.0, 20.0, 0.0, style, gradient)
    annotate_extraction_truth(rectangle, "gradient_panel", "bill_header")
    document = _pdf_document(rectangle)

    truth = document.extraction_truth()
    recreated = DocumentPDF.create_from_dict(document.parameters, {style.name: style})

    assert len(truth) == 1
    assert truth[0]["bbox"] == pytest.approx(
        [
            10.0 * 72.0 / 25.4,
            40.0 * 72.0 / 25.4,
            50.0 * 72.0 / 25.4,
            60.0 * 72.0 / 25.4,
        ]
    )
    assert truth[0]["parameters"] == {"fill_gradient": gradient.parameters}
    assert recreated.extraction_truth() == truth
    assert recreated.to_pdf_bytes() == document.to_pdf_bytes()


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_truth_record_parameter_sorting_is_key_order_independent_and_none_first() -> None:
    """LINEAR-GRADIENT-P1: Parameter mappings contribute canonical JSON to record ordering."""

    def record(parameters: dict[str, object] | None) -> ExtractionTruthRecord:
        return ExtractionTruthRecord(
            field="panel",
            value="value",
            role="value",
            page=1,
            bbox=None,
            source_channel="body",
            is_truth=True,
            instance_id=None,
            parameters=parameters,
        )

    none_record = record(None)
    canonical_first = record({"b": 9, "a": 0})
    canonical_second = record({"a": 1, "b": 0})

    assert sort_extraction_truth_records([canonical_second, canonical_first, none_record]) == [
        none_record,
        canonical_first,
        canonical_second,
    ]


@pytest.mark.condition("LINEAR-GRADIENT-P1")
def test_dxf_rejects_gradient_instead_of_flattening_to_solid_fill() -> None:
    """LINEAR-GRADIENT-P1: DXF fails explicitly because this slice has no gradient contract."""
    drawing = RectangleDrawing((10.0, 20.0), 40.0, 20.0, 0.0, _style(), _gradient())
    document = DXFDocument()

    with pytest.raises(ValueError, match="DXF does not support linear-gradient rectangle fills"):
        document.add_group(DrawingComponentGroup("gradient-panel", [drawing]))
