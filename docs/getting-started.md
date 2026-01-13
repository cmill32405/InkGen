# Getting Started

This guide walks you through installing InkGen, setting up a development environment, and generating your first SVG output. It assumes you have Python 3.10 or later available on your system.

## 1. Install the Toolkit

Install the project in editable mode with development dependencies:

```bash
python -m venv .venv
. .venv/Scripts/activate  # Linux/macOS: source .venv/bin/activate
pip install -e .[dev]
```

The `dev` extras bundle testing, linting, and documentation tools including `pytest`, `ruff`, and `mkdocs`.

## 2. Verify the Environment

Run the automated test suite to ensure everything is wired correctly:

```bash
pytest
```

You should see all tests pass. The test suite covers core functionality including component creation, document structure, text fitting, and SVG generation.

### Code Quality Tools

Linting and formatting are handled by Ruff:

```bash
# Check for linting issues
ruff check .

# Auto-fix issues where possible
ruff check --fix .

# Format code
ruff format .
```

These commands help maintain code quality and consistency. The project is configured with a 140-character line length limit.

## 3. Generate Example Drawings

InkGen ships with a set of runnable examples under the `examples/` directory. Each script produces SVG output in `examples/output/`.

### Basic Example

```bash
python examples/run_inkgen.py
```

This creates a comprehensive drawing with:
- Basic shapes (rectangles, circles, polygons)
- Text fitting examples
- Embedded SVG artwork
- Zoning overlays
- Tables

Output: `examples/output/test1.svg` and `examples/output/test_document.yaml`

### Primitives Showcase

```bash
python examples/run_inkgen_primitives.py
```

This demonstrates all available drawing primitives with labels:
- Rectangles, circles, lines
- Polygons (regular and irregular)
- Arcs and Bezier curves
- Paths

Outputs:
- `examples/output/inkgen_primitives_showcase_base.svg` (base drawing)
- `examples/output/inkgen_primitives_showcase_mask.svg` (segmentation mask)

### Structured Drawing

```bash
python examples/test_svg_drawing.py
```

This creates a structured engineering drawing with:
- Revision tables
- Bill of materials
- Callouts and annotations
- Free text blocks

Output: `examples/output/test_svg_draw.svg`

After running the scripts, open the SVG files in a browser or vector editor (like Inkscape) to inspect the results.

## 4. Build the Documentation

Documentation is managed with MkDocs. To preview docs locally:

```bash
mkdocs serve
```

Visit `http://127.0.0.1:8000` to browse the site. To produce a static build:

```bash
mkdocs build
```

## 5. Next Steps

Once you have a working environment, continue with:

- [Drawing Components](components/drawing-components.md) for a tour of the available shapes.
- [Document Structure](components/document-structure.md) to see how components become layered documents.
- [Text & Layout](text-and-layout.md) for details on text fitting, zoning, and table composition.
- [Examples](examples.md) for cookbook-style guides that expand on the repository scripts.

For detailed information about the architecture and API, continue exploring the documentation sections above.
