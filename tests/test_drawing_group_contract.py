"""Behavioral tests for renderer-neutral drawing group contracts."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.drawing_components import DrawingComponentGroup, OutputFormat, RectangleDrawing, normalize_output_format
from InkGen.grammar_truth import annotate_grammar_truth, get_grammar_truth_annotations
from InkGen.pdf_generator import ComponentGroupPDF
from InkGen.style import DrawingStyle
from InkGen.svg_generator import ComponentGroupSVG


class _AttributeOnlyPrimitive:
    to_component = None


class _InvalidMaterializationPrimitive:
    def to_component(self, output_format: OutputFormat | str) -> object:
        """Return a deliberately invalid concrete materialization."""
        return object()


class _StringifiesToSvg:
    def __str__(self) -> str:
        """Return a supported format name despite not being a string."""
        return "svg"


class _RecordingPrimitive:
    def __init__(self) -> None:
        """Create a primitive that records materialization attempts."""
        self.calls: list[object] = []

    def to_component(self, output_format: OutputFormat | str) -> object:
        """Record materialization and return an invalid object."""
        self.calls.append(output_format)
        return object()


@pytest.fixture
def drawing_style() -> DrawingStyle:
    """Return a visible drawing style with a unique name."""
    return DrawingStyle(f"group_contract_style_{uuid4().hex}", stroke="#111111", fill="none", stroke_width=0.2)


@pytest.mark.condition("DRAWING-GROUP-P1")
@pytest.mark.parametrize("label", [123, None, object()])
def test_drawing_group_rejects_non_string_labels(label: object) -> None:
    """DRAWING-GROUP-P1: Neutral group labels must be strings."""
    with pytest.raises(TypeError, match="group_label must be a string"):
        DrawingComponentGroup(label)  # type: ignore[arg-type]


@pytest.mark.condition("DRAWING-GROUP-P1")
def test_drawing_group_materializes_svg_and_pdf_groups(drawing_style: DrawingStyle) -> None:
    """DRAWING-GROUP-P1: Neutral groups materialize supported concrete group types."""
    group = DrawingComponentGroup("portable")
    rectangle = RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, drawing_style)
    annotate_grammar_truth(group, "GROUP", "construct", value="portable")
    annotate_grammar_truth(rectangle, "RECT", "cue", value="box")

    group.add_component(rectangle)
    svg_group = group.to_group(OutputFormat.SVG)
    pdf_group = group.to_group("pdf")

    assert isinstance(svg_group, ComponentGroupSVG)
    assert isinstance(pdf_group, ComponentGroupPDF)
    assert svg_group.group_label == "portable"
    assert pdf_group.group_label == "portable"
    assert [component.__class__.__name__ for component in svg_group.components()] == ["RectangleSVG"]
    assert [component.__class__.__name__ for component in pdf_group.components()] == ["RectanglePDF"]
    assert get_grammar_truth_annotations(svg_group)[0].condition_id == "GROUP"
    assert get_grammar_truth_annotations(pdf_group)[0].condition_id == "GROUP"
    assert get_grammar_truth_annotations(next(svg_group.components()))[0].condition_id == "RECT"
    assert get_grammar_truth_annotations(next(pdf_group.components()))[0].condition_id == "RECT"


@pytest.mark.condition("DRAWING-GROUP-COMPONENTS-P2")
def test_drawing_group_constructor_accepts_valid_component_sequences(drawing_style: DrawingStyle) -> None:
    """DRAWING-GROUP-COMPONENTS-P2: Constructor normalizes valid primitive sequences."""
    rectangle = RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, drawing_style)
    group = DrawingComponentGroup("direct", (rectangle,))

    svg_group = group.to_group(OutputFormat.SVG)

    assert group.components == [rectangle]
    assert [component.__class__.__name__ for component in svg_group.components()] == ["RectangleSVG"]


@pytest.mark.condition("DRAWING-GROUP-COMPONENTS-P2")
@pytest.mark.parametrize(
    "components",
    [
        "bad",
        b"bad",
        object(),
        [object()],
        [_AttributeOnlyPrimitive()],
    ],
)
def test_drawing_group_constructor_rejects_malformed_components(components: object) -> None:
    """DRAWING-GROUP-COMPONENTS-P2: Constructor rejects malformed component collections."""
    with pytest.raises(TypeError, match="component|components"):
        DrawingComponentGroup("invalid", components)  # type: ignore[arg-type]


@pytest.mark.condition("DRAWING-GROUP-P1")
def test_drawing_group_rejects_invalid_recipe_boundaries(drawing_style: DrawingStyle) -> None:
    """DRAWING-GROUP-P1: Invalid neutral recipes fail before silent renderer omission."""
    group = DrawingComponentGroup("invalid")

    with pytest.raises(TypeError, match="to_component"):
        group.add_component(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="to_component"):
        group.add_component(_AttributeOnlyPrimitive())  # type: ignore[arg-type]

    group.components.append(_InvalidMaterializationPrimitive())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must return an InkGen Component"):
        group.to_group(OutputFormat.SVG)


@pytest.mark.condition("DRAWING-GROUP-P1")
def test_drawing_group_rejects_unsupported_formats_before_materializing(drawing_style: DrawingStyle) -> None:
    """DRAWING-GROUP-P1: Unsupported formats fail before component materialization."""
    group = DrawingComponentGroup("bad_format")
    group.add_component(RectangleDrawing((1.0, 2.0), 3.0, 4.0, 0.0, drawing_style))

    with pytest.raises(ValueError, match="Unsupported output format"):
        group.to_group("dxf")


@pytest.mark.condition("DRAWING-FORMAT-P2")
def test_normalize_output_format_rejects_stringifiable_objects() -> None:
    """DRAWING-FORMAT-P2: Backend selectors must be strings or OutputFormat values."""
    with pytest.raises(TypeError, match="OutputFormat or string"):
        normalize_output_format(_StringifiesToSvg())  # type: ignore[arg-type]


@pytest.mark.condition("DRAWING-FORMAT-P2")
def test_drawing_group_rejects_non_string_format_before_materializing() -> None:
    """DRAWING-FORMAT-P2: Invalid backend selector types fail before materialization."""
    group = DrawingComponentGroup("bad_format_type")
    primitive = _RecordingPrimitive()
    group.add_component(primitive)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="OutputFormat or string"):
        group.to_group(_StringifiesToSvg())  # type: ignore[arg-type]

    assert primitive.calls == []
