"""SVG document renderer contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.style import DrawingStyle, Font, Style, TextStyle
from InkGen.svg_generator import ComponentGroupSVG, DocumentSVG, IncludeLayer, PolygonalSVG, RectangleSVG, TextSVG


def _drawing_style() -> DrawingStyle:
    return DrawingStyle(f"svg_doc_line_{uuid4().hex}", stroke="#202020", stroke_width=0.5, fill="none")


def _fill_style() -> DrawingStyle:
    return DrawingStyle(f"svg_doc_fill_{uuid4().hex}", stroke="none", fill="#abcdef")


def _text_style() -> TextStyle:
    style = TextStyle(f"svg_doc_text_{uuid4().hex}", Font(size=10.0))
    style.color = "#112233"
    return style


def _document_with_panel(*, pages: int = 1) -> DocumentSVG:
    document = DocumentSVG(Canvas(120.0, 80.0, "mm"))
    for _ in range(pages):
        document.add_page()
        group = ComponentGroupSVG(f"Panel-{document.pages}")
        group.add_component(RectangleSVG((20.0, 20.0), 30.0, 8.0, 0.0, _drawing_style()))
        group.add_component(TextSVG("Panel", (35.0, 24.0), _text_style()))
        document.page(document.pages).layer("base").add_component_group(group)
    return document


def _document_with_rectangle_group(label: str = "Box") -> DocumentSVG:
    document = DocumentSVG(Canvas(120.0, 80.0, "mm"))
    document.add_page()
    group = ComponentGroupSVG(label)
    group.add_component(RectangleSVG((20.0, 20.0), 30.0, 8.0, 0.0, _drawing_style()))
    document.page(1).layer("base").add_component_group(group)
    return document


@pytest.mark.condition("SVG-DOC-P1")
def test_document_svg_writes_single_and_multi_page_files(tmp_path) -> None:
    """SVG-DOC-P1: DocumentSVG writes deterministic single-page and multi-page filenames."""
    single = _document_with_panel()
    single_path = tmp_path / "single.svg"
    multi = _document_with_panel(pages=2)
    multi_path = tmp_path / "multi.svg"

    single.create_svg(str(single_path))
    multi.create_svg(str(multi_path))

    assert single_path.exists()
    assert (tmp_path / "multi_page_1.svg").exists()
    assert (tmp_path / "multi_page_2.svg").exists()
    assert '<svg\n\twidth="120.0mm"' in single_path.read_text(encoding="utf-8")
    assert "Panel" in (tmp_path / "multi_page_2.svg").read_text(encoding="utf-8")


@pytest.mark.condition("SVG-DOC-P1")
def test_document_svg_rejects_missing_output_directory(tmp_path) -> None:
    """SVG-DOC-P1: DocumentSVG fails loudly for missing output directories."""
    document = _document_with_panel()

    with pytest.raises(ValueError, match="file path does not exist"):
        document.create_svg(str(tmp_path / "missing" / "drawing.svg"))


@pytest.mark.condition("SVG-DOC-P1")
def test_document_svg_include_layer_flags_can_be_combined(tmp_path) -> None:
    """SVG-DOC-P1: IncludeLayer flag combinations add requested modeling layers."""
    document = _document_with_panel()
    target = tmp_path / "combined.svg"

    document.create_svg(str(target), include=IncludeLayer.LABEL | IncludeLayer.MASK)

    assert "label" in document.page(1).layers
    assert "mask" in document.page(1).layers
    payload = target.read_text(encoding="utf-8")
    assert payload.count('inkscape:groupmode="layer"') == 3
    mask_layer = document.page(1).layer("mask")
    assert any(
        isinstance(component, PolygonalSVG)
        for _, group_id in mask_layer.component_groups.items()
        for component in mask_layer.group(group_id).components()
    )


@pytest.mark.condition("SVG-DOC-P1")
def test_document_svg_label_layer_uses_group_bbox_rectangles(tmp_path) -> None:
    """SVG-DOC-P1: Label modeling layers render bbox rectangles, not mask polygons."""
    document = _document_with_rectangle_group()

    document.create_svg(str(tmp_path / "labels.svg"), include=IncludeLayer.LABEL)

    label_layer = document.page(1).layer("label")
    label_group = label_layer.group(next(iter(label_layer.component_groups.values())))
    components = list(label_group.components())
    assert len(components) == 2
    assert all(isinstance(component, RectangleSVG) for component in components)
    assert components[0].position == (20.0, 20.0)
    assert components[0].width == 30.0
    assert components[0].height == 8.0


@pytest.mark.condition("SVG-DOC-P1")
def test_document_svg_duplicate_group_labels_are_disambiguated(tmp_path) -> None:
    """SVG-DOC-P1: Repeated source labels remain addressable in modeling layers."""
    document = _document_with_rectangle_group("Repeat")
    group = ComponentGroupSVG("Repeat")
    group.add_component(RectangleSVG((70.0, 20.0), 10.0, 10.0, 0.0, _drawing_style()))
    document.page(1).layer("base").add_component_group(group)

    document.create_svg(str(tmp_path / "duplicates.svg"), include=IncludeLayer.LABEL)

    label_names = set(document.page(1).layer("label").component_groups)
    assert "Repeat" in label_names
    assert len(label_names) == 2
    assert any(name.startswith("Repeat_") for name in label_names)


@pytest.mark.condition("SVG-DOC-P1")
def test_document_svg_rebuilds_modeling_layers_without_stale_geometry(tmp_path) -> None:
    """SVG-DOC-P1: Label and mask layers are rebuilt instead of accumulating stale groups."""
    document = _document_with_panel()
    first = tmp_path / "first.svg"
    second = tmp_path / "second.svg"

    document.create_svg(str(first), include=IncludeLayer.LABEL)
    label_group_count = len(document.page(1).layer("label").component_groups)
    group = ComponentGroupSVG("Added")
    group.add_component(RectangleSVG((70.0, 20.0), 10.0, 10.0, 0.0, _drawing_style()))
    document.page(1).layer("base").add_component_group(group)
    document.create_svg(str(second), include=IncludeLayer.LABEL)

    assert label_group_count == 1
    assert len(document.page(1).layer("label").component_groups) == 2


@pytest.mark.condition("SVG-DOC-P1")
def test_document_svg_round_trips_parameters_and_keeps_component_markup() -> None:
    """SVG-DOC-P1: DocumentSVG parameter round trip preserves rendered component markup."""
    document = DocumentSVG(Canvas(40.0, 20.0, "mm"))
    document.add_page()
    group = ComponentGroupSVG("RoundTrip")
    fill_style = _fill_style()
    group.add_component(RectangleSVG((1.0, 2.0), 3.0, 4.0, 0.0, fill_style))
    document.page(1).layer("base").add_component_group(group)

    if fill_style.name in Style.style_names:
        Style.style_names.remove(fill_style.name)
    style_cache = {}
    clone = DocumentSVG.create_from_dict(document.parameters, style_cache)
    svg = clone._assemble_page_svg(clone.page(1), [])

    assert clone.parameters == document.parameters
    assert fill_style.name in style_cache
    assert "fill:#abcdef" in svg
    assert "stroke:none" in svg
    assert 'width="3.0"' in svg
    assert 'width="40.0mm"' in svg
