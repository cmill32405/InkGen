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
from InkGen.svg_generator import DocumentSVG, IncludeLayer

doc_svg = DocumentSVG(canvas)
doc_svg.add_page()
doc_svg.page(0).add_layer("base", base_layer)
doc_svg.page(0).layer("base").add_component_group(group)

# Generate SVG with all layers
doc_svg.create_svg("output.svg")

# Generate SVG with only model layers (for segmentation)
doc_svg.create_svg("output_mask.svg", include_layers=IncludeLayer.MODEL_ONLY)

# Generate SVG with labels
doc_svg.create_svg("output_labeled.svg", include_layers=IncludeLayer.ALL, include_labels=True)
```

The `DocumentSVG` class supports:

- Adding layers and component groups to pages.
- Generating SVG output with optional masks and labels.
- Serializing to and from dictionaries (e.g., for YAML-based recipes).
- Filtering which layers are included in the output via `IncludeLayer` enum.

### Layer Filtering

The `IncludeLayer` enum controls which layers are exported:

- `IncludeLayer.ALL`: Export all layers
- `IncludeLayer.MODEL_ONLY`: Export only layers where `model=True`
- `IncludeLayer.NO_MODEL`: Export only layers where `model=False`

This is useful for generating separate base drawings and segmentation masks.

## Boundary Enforcement

Component groups use `ComponentGroupOffCanvas` exceptions to prevent out-of-bounds drawings. When adding groups to layers, you can handle boundary violations:

```python
from InkGen.errors import ComponentGroupOffCanvas, ComponentGroupCollision

try:
    layer.add_component_group(group, allow_collision=False, strict=True)
except ComponentGroupOffCanvas:
    print("Group extends beyond canvas boundaries")
except ComponentGroupCollision:
    print("Group collides with existing groups")
```

The `add_component_group` method accepts:
- `allow_collision`: If `True`, skip collision checking
- `strict`: If `True`, disallow even touching convex hulls (more restrictive)

## YAML Recipes

The combination of `parameters` properties and `create_from_dict` constructors allows document recipes to be stored as YAML. This enables version control, reproducibility, and programmatic document generation.

### Saving Documents

```python
# Save complete document structure
doc_svg.save("document.yaml")
```

The saved YAML includes all pages, layers, component groups, components, and styles in a structured format.

### Loading Documents

```python
from InkGen.document import Document

# Load document from YAML
document, styles = Document.load("document.yaml")

# Reconstruct DocumentSVG from loaded document
doc_svg = DocumentSVG(canvas)
# ... populate from document ...
```

YAML recipes are particularly useful for:
- Template-based document generation
- Reproducing specific drawing configurations
- Storing complex multi-page documents
- Version controlling document structures

---

Layers and documents provide the scaffold for layout logic. For a deeper look at zoning, tables, and fitted text, continue to [Text & Layout](../text-and-layout.md).
