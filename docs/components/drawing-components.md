# Drawing Components

Drawing components are the foundational primitives of InkGen. Each component encapsulates geometric data, styling information, and SVG generation logic. Components derive from the core classes defined in `src/InkGen/component.py`.

## Core Hierarchy

| Class | Description |
|-------|-------------|
| `Component` | Base class providing unique identifiers and serialization helpers. |
| `DrawingComponent` | Extends `Component` with drawing-specific style information. |
| `StandardDrawingComponent` | Adds rectangular, two-point geometry (e.g., rectangles, arcs). |
| `SingleDimensionDrawingComponent` | Models a position and size instead of two points. |
| `PolygonalDrawingComponent` | Handles arbitrary polygon coordinate sets. |

### Rectangles and Lines

```python
from InkGen.style import DrawingStyle
from InkGen.svg_generator import RectangleSVG, LineSVG

style = DrawingStyle(name="Outline", stroke="#000", stroke_width=0.4, fill="none")
rect = RectangleSVG(position=(10, 10), width=100, height=50, corner_radii=2, style=style)
line = LineSVG(point_1=(10, 60), point_2=(110, 60), style=style)

svg_snippets = [rect.generate_svg(), line.generate_svg()]
```

### Polygons

```python
from InkGen.svg_generator import PolygonalSVG, RegularPolygonSVG

poly_style = DrawingStyle(name="Poly", stroke="#0057B8", fill="#CCE5FF")
irregular = PolygonalSVG([(0, 0), (60, 10), (40, 40), (0, 25)], poly_style)
regular = RegularPolygonSVG(position=(80, 30), sides=6, radius=20, style=poly_style)
```

### Paths and Beziers

For custom shapes use `PathSVG` with `PathCommand` instances or Bezier-specific classes.

```python
from InkGen.component import PathCommand
from InkGen.svg_generator import PathSVG

commands = [
    PathCommand("M", [(0.0, 0.0)]),
    PathCommand("L", [(40.0, 10.0), (60.0, 40.0)]),
    PathCommand("Z", []),
]
path = PathSVG(style=style, commands=commands)
```

### Text and Tables

Text components require a `TextStyle` and are covered in detail in [Text & Layout](../text-and-layout.md).

Table composition is provided by classes in `src/InkGen/table.py`. Tables are converted to SVG with `TableSVG`.

### Raster Images

Raster images use a renderer-neutral asset and drawing primitive. The asset
accepts any Pillow-decodable raster bytes, applies EXIF orientation when it
exposes decoded pixels, and leaves concrete renderers to decide how to serialize
the image.

```python
from InkGen.drawing_components import ImageDrawing, OutputFormat
from InkGen.image_assets import RasterImageAsset

asset = RasterImageAsset.from_file("examples/input/logo.png")
image = ImageDrawing(asset, position=(10, 10), width=40, height=20)

svg_component = image.to_component(OutputFormat.SVG)
pdf_component = image.to_component(OutputFormat.PDF)
```

SVG images are embedded as PNG data URIs. PDF images are emitted as image
XObjects, preserve transparency with a soft mask, and pass through RGB JPEG
bytes only when the source orientation is already identity. Flow-document DOCX
output consumes `ImageDrawing` as a native PNG media part with DrawingML
relationships. DXF raster image export is not supported until referenced-image
semantics are designed.

## Circles and Arcs

```python
from InkGen.svg_generator import CircleSVG, ArcSVG

circle_style = DrawingStyle(name="Circle", stroke="#FF0000", stroke_width=1.0, fill="#FFCCCC")
circle = CircleSVG(center=(50, 50), radius=25, style=circle_style)

arc = ArcSVG(
    point_1=(0, 0),
    point_2=(100, 50),
    radius=60,
    large_arc=False,
    sweep=True,
    style=circle_style
)
```

## Bezier Curves

InkGen supports both quadratic and cubic Bezier curves:

```python
from InkGen.svg_generator import QuadraticBezierSVG, CubicBezierSVG

# Quadratic Bezier (one control point)
quad_bezier = QuadraticBezierSVG(
    point_1=(0, 0),
    point_2=(100, 0),
    control=(50, 50),
    style=style
)

# Cubic Bezier (two control points)
cubic_bezier = CubicBezierSVG(
    point_1=(0, 0),
    point_2=(100, 0),
    control_1=(25, 50),
    control_2=(75, 50),
    style=style
)
```

## Serialization

Every component exposes a `parameters` property and `create_from_dict` constructor. This allows you to persist and reload components:

```python
params = rect.parameters
restored = RectangleSVG.create_from_dict(params)
assert restored.parameters == params
```

Components can be serialized to dictionaries and saved as YAML for later reconstruction:

```python
import yaml

# Save component
with open("component.yaml", "w") as f:
    yaml.dump(rect.parameters, f)

# Load component
with open("component.yaml", "r") as f:
    data = yaml.safe_load(f)
    restored = RectangleSVG.create_from_dict(data)
```

## Component Groups

Components are usually assembled into `ComponentGroupSVG` objects, which carry metadata for labels, masks, and annotations. Groups support serialization and enforce canvas boundaries when added to layers.

```python
from InkGen.svg_generator import ComponentGroupSVG

group = ComponentGroupSVG("BaseAssembly")
group.add_component(rect)
group.add_component(line)
```

Continue with [Document Structure](document-structure.md) to see how components are organised into layers and documents.
