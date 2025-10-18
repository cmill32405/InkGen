# Getting Started

This guide walks you through installing InkGen, setting up a development environment, and generating your first SVG output. It assumes you have Python 3.10 or later available on your system.

## 1. Install the Toolkit

Clone the repository and install the project in editable mode with development dependencies:

```bash
git clone https://github.com/<your-org>/InkGen.git
cd InkGen
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

Linting and formatting are handled by Ruff:

```bash
ruff check .
ruff format .
```

All lint/formatting checks must pass before code is merged.

## 3. Generate Example Drawings

InkGen ships with a set of runnable examples under the `examples/` directory. Each script produces SVG output in `examples/output/`.

```bash
python examples/run_inkgen.py
python examples/run_inkgen_primitives.py
python examples/test_svg_drawing.py
```

After running the scripts you will find SVG files such as `test1.svg` and `inkgen_primitives_showcase_base.svg` ready to inspect in a browser or vector editor.

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

If you plan to contribute, please read the [Contributing Guide](contributing.md) and follow the coding standards described there.
