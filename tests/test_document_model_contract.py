"""Tests for document model proof obligations."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.boundary import Canvas
from InkGen.component import ComponentGroup, WidthHeightDrawingComponent
from InkGen.document import Document, Layer, Layers
from InkGen.errors import IncompatibleCanvas, InvalidComponentGroupID
from InkGen.pdf_generator import ComponentGroupPDF, DocumentPDF, RectanglePDF
from InkGen.style import DrawingStyle, Style


def _canvas() -> Canvas:
    """Return the standard document contract canvas."""
    return Canvas(210.0, 297.0, "mm")


def _page(name: str = "base") -> Layers:
    """Return a page with a named base layer."""
    return Layers(_canvas(), name)


def _group() -> ComponentGroup:
    """Return a component group that fits on the standard canvas."""
    style = DrawingStyle(name=f"document_contract_{uuid4().hex}", stroke="#000000", fill="none")
    group = ComponentGroup(f"group_{uuid4().hex}")
    group.add_component(WidthHeightDrawingComponent((20.0, 20.0), 30.0, 20.0, style))
    return group


def _document_with_styled_group() -> tuple[Layer, Layers, Document]:
    """Return document-model objects containing a styled component group."""
    layer = Layer("base", _canvas())
    layer.add_component_group(_group())
    layers = Layers(_canvas(), layer=layer)
    document = Document(_canvas())
    document.add_page(page=layers)
    return layer, layers, document


def _pdf_group() -> ComponentGroupPDF:
    """Return a PDF-native group that fits on the standard canvas."""
    style = DrawingStyle(name=f"document_contract_pdf_{uuid4().hex}", stroke="#000000", fill="none")
    group = ComponentGroupPDF(f"pdf_group_{uuid4().hex}")
    group.add_component(RectanglePDF((20.0, 20.0), 30.0, 20.0, 0.0, style))
    return group


@pytest.mark.condition("DOCUMENT-MODEL-P1")
def test_document_page_insert_rejects_invalid_positions_and_booleans() -> None:
    """DOCUMENT-MODEL-P1: Page insertion accepts only -1 or existing one-based positions."""
    document = Document(_canvas())

    for position in (0, -2, 1):
        with pytest.raises(ValueError):
            document.add_page(position=position)
    for position in (True, 1.5, "1"):
        with pytest.raises(TypeError):
            document.add_page(position=position)  # type: ignore[arg-type]

    document.add_page()
    document.add_page()
    document.add_page(position=1, page=_page("inserted"))

    assert document.pages == 3
    assert document.page(1).layers == ["inserted"]

    document.add_page(position=2, page=_page("middle"))
    assert document.pages == 4
    assert document.page(1).layers == ["inserted"]
    assert document.page(2).layers == ["middle"]
    assert document.page(3).layers == ["base"]
    assert document.page(4).layers == ["base"]

    document.add_page(position=document.pages, page=_page("before_last"))
    assert document.pages == 5
    assert document.page(4).layers == ["before_last"]
    assert document.page(5).layers == ["base"]


@pytest.mark.condition("DOCUMENT-MODEL-P1")
def test_document_page_remove_and_lookup_reject_invalid_positions() -> None:
    """DOCUMENT-MODEL-P1: Page lookup and removal require existing one-based pages."""
    document = Document(_canvas())
    document.add_page(page=_page("first"))
    document.add_page(page=_page("second"))

    for operation in (document.page, document.remove_page):
        for position in (0, -1, 3):
            with pytest.raises(ValueError):
                operation(position)
        for position in (False, 1.25, "1"):
            with pytest.raises(TypeError):
                operation(position)  # type: ignore[arg-type]

    document.remove_page(1)
    assert document.pages == 1
    assert document.page(1).layers == ["second"]


@pytest.mark.condition("DOCUMENT-MODEL-IDENTIFIER-P2")
def test_layer_rejects_boolean_component_group_identifiers_before_integer_aliasing() -> None:
    """DOCUMENT-MODEL-IDENTIFIER-P2: Component group identifiers reject boolean aliases."""
    layer = Layer("base", _canvas())
    group = _group()
    layer.add_component_group(group)

    with pytest.raises(TypeError, match="group_id must be an integer id"):
        layer.group(True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="group_id must be an integer id or string label"):
        layer.remove_component_group(True)

    assert layer.group(group.group_id) is group
    assert layer.component_groups[group.group_label] == group.group_id


@pytest.mark.condition("DOCUMENT-MODEL-IDENTIFIER-P2")
def test_layer_rejects_malformed_component_group_lookup_identifiers() -> None:
    """DOCUMENT-MODEL-IDENTIFIER-P2: Component group lookup accepts only integer ids."""
    layer = Layer("base", _canvas())

    for group_id in ("missing", 1.25, object()):
        with pytest.raises(TypeError, match="group_id must be an integer id"):
            layer.group(group_id)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Invalid component group id"):
        layer.group(123_456)

    with pytest.raises(InvalidComponentGroupID, match="group_id must a valid group_id"):
        layer.remove_component_group(123_456)


@pytest.mark.condition("DOCUMENT-MODEL-IDENTIFIER-P2")
def test_layers_rejects_boolean_layer_identifiers_before_integer_aliasing() -> None:
    """DOCUMENT-MODEL-IDENTIFIER-P2: Layer identifiers reject boolean aliases."""
    layers = Layers(_canvas(), "base")

    with pytest.raises(TypeError, match="Invalid identifier"):
        layers.layer(True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Invalid identifier"):
        layers.remove_layer(True)  # type: ignore[arg-type]

    assert layers.layer("base").layer_name == "base"
    assert layers.layers == ["base"]


@pytest.mark.condition("DOCUMENT-MODEL-P1")
def test_document_rejects_pages_with_incompatible_canvas() -> None:
    """DOCUMENT-MODEL-P1: Inserted pages must use the document canvas contract."""
    document = Document(_canvas())
    incompatible_pages = [
        Layers(Canvas(200.0, 297.0, "mm"), "narrow"),
        Layers(Canvas(220.0, 297.0, "mm"), "wide"),
        Layers(Canvas(210.0, 290.0, "mm"), "short"),
        Layers(Canvas(210.0, 310.0, "mm"), "tall"),
        Layers(Canvas(210.0, 297.0, "in"), "wrong_units"),
    ]

    for incompatible in incompatible_pages:
        with pytest.raises(IncompatibleCanvas):
            document.add_page(page=incompatible)

    document.add_page(page=_page("compatible"))
    assert document.page(1).layers == ["compatible"]


@pytest.mark.condition("DOCUMENT-MODEL-P1")
def test_document_serialization_preserves_one_based_page_order() -> None:
    """DOCUMENT-MODEL-P1: Serialization round trip preserves one-based page order."""
    document = Document(_canvas())
    document.add_page(page=_page("first"))
    document.add_page(page=_page("second"))
    document.add_page(position=1, page=_page("inserted"))

    clone = Document.create_from_dict(document.parameters)

    assert clone.pages == 3
    assert clone.page(1).layers == ["inserted"]
    assert clone.page(2).layers == ["first"]
    assert clone.page(3).layers == ["second"]
    assert clone.parameters == document.parameters


@pytest.mark.condition("DOCUMENT-MODEL-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload", "error_type", "message"),
    [
        (Document.create_from_dict, object(), TypeError, "Document data must be a mapping"),
        (Document.create_from_dict, {}, ValueError, "Document data must include Document"),
        (Document.create_from_dict, {"Document": object()}, TypeError, "Document payload must be a mapping"),
        (
            Document.create_from_dict,
            {"Document": {"canvas": _canvas().parameters, "pages": "bad"}},
            TypeError,
            "Document pages must be a sequence",
        ),
        (Layers.create_from_dict, object(), TypeError, "Layers data must be a mapping"),
        (Layers.create_from_dict, {}, ValueError, "Layers data must include Layers"),
        (Layers.create_from_dict, {"Layers": object()}, TypeError, "Layers payload must be a mapping"),
        (
            Layers.create_from_dict,
            {"Layers": {"canvas": _canvas().parameters, "layers": "bad"}},
            TypeError,
            "Layers layers must be a mapping",
        ),
        (Layer.create_from_dict, object(), TypeError, "Layer data must be a mapping"),
        (Layer.create_from_dict, {}, ValueError, "Layer data must include Layer"),
        (Layer.create_from_dict, {"Layer": object()}, TypeError, "Layer payload must be a mapping"),
        (
            Layer.create_from_dict,
            {
                "Layer": {
                    "canvas": _canvas().parameters,
                    "layer_name": "base",
                    "model": True,
                    "component_groups": "bad",
                    "group_collision_settings": {},
                }
            },
            TypeError,
            "Layer component_groups must be a sequence",
        ),
    ],
)
def test_document_model_hydration_rejects_malformed_payload_envelopes(
    factory: object,
    payload: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """DOCUMENT-MODEL-PAYLOAD-P2: Serialized document envelopes fail before incidental lookup errors."""
    with pytest.raises(error_type, match=message):
        factory(payload)  # type: ignore[operator]


@pytest.mark.condition("DOCUMENT-MODEL-PAYLOAD-P2")
def test_layer_hydration_requires_collision_settings_for_each_group() -> None:
    """DOCUMENT-MODEL-PAYLOAD-P2: Layer hydration validates group collision settings."""
    layer = Layer("base", _canvas())
    group = _group()
    layer.add_component_group(group, allow_collision=False, strict=True)
    style = next(group.components()).style
    payload = layer.parameters
    payload["Layer"]["group_collision_settings"] = {}

    with pytest.raises(ValueError, match="group_collision_settings must include every component group label"):
        Layer.create_from_dict(payload, {style.name: style})


@pytest.mark.condition("DOCUMENT-MODEL-STYLES-MAPPING-P2")
@pytest.mark.parametrize("styles", [object(), ["style-name"], "style-name", b"style-name", {"style-name"}])
def test_document_model_hydration_rejects_malformed_style_caches(styles: object) -> None:
    """DOCUMENT-MODEL-STYLES-MAPPING-P2: Style caches must be mutable mappings before hydration."""
    layer, layers, document = _document_with_styled_group()

    for factory, payload in (
        (Layer.create_from_dict, layer.parameters),
        (Layers.create_from_dict, layers.parameters),
        (Document.create_from_dict, document.parameters),
    ):
        with pytest.raises(TypeError, match="styles must be a mutable mapping or None"):
            factory(payload, styles)  # type: ignore[operator]


@pytest.mark.condition("DOCUMENT-MODEL-STYLES-MAPPING-P2")
def test_document_load_rejects_malformed_style_cache(tmp_path) -> None:
    """DOCUMENT-MODEL-STYLES-MAPPING-P2: Document.load validates caller-provided style caches."""
    _, _, document = _document_with_styled_group()
    recipe_path = tmp_path / "document.yaml"
    document.save(str(recipe_path))

    with pytest.raises(TypeError, match="styles must be a mutable mapping or None"):
        Document.load(str(recipe_path), styles=["style-name"])  # type: ignore[arg-type]


@pytest.mark.condition("DOCUMENT-LOAD-STYLE-PREPASS-P2")
def test_document_load_populates_styles_through_validated_hydration(tmp_path) -> None:
    """DOCUMENT-LOAD-STYLE-PREPASS-P2: Document.load style cache comes from nested hydration."""
    _, _, document = _document_with_styled_group()
    style_name = document.parameters["Document"]["pages"][0]["Layers"]["layers"]["base"]["Layer"]["component_groups"][0]["ComponentGroup"][
        "components"
    ][0]["WidthHeightDrawingComponent"]["style"]["DrawingStyle"]["name"]
    recipe_path = tmp_path / "document.yaml"
    document.save(str(recipe_path))
    if style_name in Style.style_names:
        Style.style_names.remove(style_name)

    loaded_document, styles = Document.load(str(recipe_path))

    assert loaded_document.parameters == document.parameters
    assert styles


@pytest.mark.condition("DOCUMENT-LOAD-STYLE-PREPASS-P2")
@pytest.mark.parametrize(
    ("yaml_text", "error_type", "message"),
    [
        ("- bad\n", TypeError, "Document data must be a mapping"),
        ("style: broken\n", ValueError, "Document data must include Document"),
    ],
)
def test_document_load_delegates_malformed_yaml_to_document_factory(
    tmp_path,
    yaml_text: str,
    error_type: type[Exception],
    message: str,
) -> None:
    """DOCUMENT-LOAD-STYLE-PREPASS-P2: Malformed YAML fails at the document boundary."""
    recipe_path = tmp_path / "document.yaml"
    recipe_path.write_text(yaml_text, encoding="utf-8")

    with pytest.raises(error_type, match=message):
        Document.load(str(recipe_path))


@pytest.mark.condition("DOCUMENT-MODEL-P1")
def test_document_page_contract_remains_live_through_pdf_render_path() -> None:
    """DOCUMENT-MODEL-P1: PDF rendering consumes the one-based page contract."""
    document = DocumentPDF(_canvas())
    document.add_page()
    document.page(1).layer("base").add_component_group(_pdf_group())

    payload = document.to_pdf_bytes()

    assert payload.startswith(b"%PDF-1.4\n")
    assert b"/Type /Page" in payload
