# API Reference

This section provides a high-level index of the primary modules and classes exposed by InkGen. For detailed signatures consult the source files under `src/InkGen/` or generated API docs when available.

## Boundary (`InkGen.boundary`)

- `Boundary`: Base class representing convex hull boundaries.
- `Canvas`: Specialised boundary used as the drawing surface.

## Components (`InkGen.component`)

- `Component`: Base class with identifiers and serialization.
- `DrawingComponent` and subclasses (`StandardDrawingComponent`, `SingleDimensionDrawingComponent`, `PolygonalDrawingComponent`, etc.).
- Geometry-specific classes such as `Arc`, `QuadraticBezier`, `CubicBezier`, `Path`.
- `ComponentGroup`: Collection of components with shared metadata.

## Document (`InkGen.document`)

- `Layer`: Container for component groups.
- `Layers`: Layer stack with convenience helpers.
- `Document`: Multi-page document abstraction.

## SVG Generator (`InkGen.svg_generator`)

- `RectangleSVG`, `LineSVG`, `PolygonalSVG`, `RegularPolygonSVG`, `CircleSVG`, `PathSVG`, `TextSVG`.
- `ComponentGroupSVG`, `TableSVG`, `DocumentSVG`.
- `IncludeLayer`: Enum controlling which layers are exported.

## Tables (`InkGen.table`)

- `Table`, `Row`, `Column`, `Cell`.
- `AutoFitRule`: Column and row sizing strategies.

## Styling (`InkGen.style`)

- `Style`: Base style class.
- `DrawingStyle`, `TextStyle`, `Font`.

## Text Fitting (`InkGen.text_fitter`, `InkGen.text_outline`)

- `TextBlock`, `TextFitter`, `FittingResult`.
- Helper functions for outlining text (`outline_for_text`, `sample_path_points`).

## CAD Component Groups (`InkGen.cad_component_groups`)

- `Zoning`: Grid layout utility for engineering drawings.

## Utilities (`InkGen.svg_utils`)

- `FlattenedPath`: Dataclass representing flattened path results.
- `flatten_svg()`: Converts SVG files into flattened path data.

---

To contribute more detailed function-level documentation:

1. Add docstrings to the relevant modules.
2. Expand this reference with code examples and parameter tables.
3. (Optional) Configure MkDocs auto-documentation via `mkdocstrings`.
