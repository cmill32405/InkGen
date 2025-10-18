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

## Serialization

Every component exposes a `parameters` property and `create_from_dict` constructor. This allows you to persist and reload components:

```python
params = rect.parameters
restored = RectangleSVG.create_from_dict(params)
assert restored.parameters == params
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
