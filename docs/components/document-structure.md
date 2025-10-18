# Document Structure

InkGen models drawings as layered documents built on top of the `Canvas`, `Layer`, and `Document` abstractions found in `src/InkGen/boundary.py`, `src/InkGen/document.py`, and `src/InkGen/svg_generator.py`.

## Canvas

The `Canvas` defines the drawing coordinate system and units.

```python
from InkGen.boundary import Canvas

canvas = Canvas(width=210, height=297, units="mm")  # A4 in millimetres
```

Internally, a canvas is a specialized `Boundary` that can validate whether components stay within limits.

## Layers

Layers group related component groups and enforce ordering. Drawing layers are managed by the `Layers` container:

```python
from InkGen.document import Layer, Layers

base_layer = Layer("base", canvas)
layers = Layers(canvas)
layers.add_layer(layer=base_layer)
```

`Layers` automatically creates a `base` layer and tracks subsequent layers by ID.

## Document

`Document` is a collection of pages (each a `Layers` instance) and stores high-level metadata.

```python
from InkGen.document import Document

document = Document(canvas)
document.add_page(page=layers)
```

## DocumentSVG

While `Document` manages data, `DocumentSVG` is responsible for rendering, serialization, and exporting:

```python
from InkGen.svg_generator import DocumentSVG

doc_svg = DocumentSVG(canvas)
doc_svg.add_page()
doc_svg.page(1).add_layer("base", base_layer)
doc_svg.page(1).layer("base").add_component_group(group)

doc_svg.create_svg("output.svg")
```

The `DocumentSVG` class supports:

- Adding layers and component groups to pages.
- Generating SVG output with optional masks and labels.
- Serializing to and from dictionaries (e.g., for YAML-based recipes).

## Boundary Enforcement

Component groups use `ComponentGroupOffCanvas` exceptions to prevent out-of-bounds drawings. Use the helper `_safe_add` pattern (as seen in `examples/run_inkgen.py`) to add groups and skip those that fall outside the canvas.

## YAML Recipes

The combination of `parameters` properties and `create_from_dict` constructors allows document recipes to be stored as YAML. The `DocumentSVG.save()` method writes a complete recipe, while `DocumentSVG.create_from_dict()` reconstructs documents from persisted dictionaries.

---

Layers and documents provide the scaffold for layout logic. For a deeper look at zoning, tables, and fitted text, continue to [Text & Layout](../text-and-layout.md).
