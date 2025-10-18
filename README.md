# InkGen

InkGen is a Python toolkit for procedurally generating richly annotated SVG
drawings. It provides reusable geometric primitives, styling utilities, layout
helpers, and end-to-end document builders that make it easy to produce
synthetic engineering schematics for experimentation and analysis.

## Features
- SVG components for common drawing primitives (rectangles, polygons, tables, etc.)
- Document and layer abstractions for multi-page drawings
- Text fitting, zoning, and annotation helpers tailored for technical diagrams
- Configurable styling pipeline for synthetic data generation workflows
- Example scripts that generate ready-to-use SVG artifacts

## Installation
```bash
git clone https://github.com/<your-org>/InkGen.git
cd InkGen
python -m venv .venv
. .venv/Scripts/activate   # On macOS/Linux use: source .venv/bin/activate
pip install -e .[dev]
```

## Quick Start
Install the development extras and run the example scripts to generate sample drawings:
```bash
pip install -e .[dev]
python examples/run_inkgen.py
python examples/run_inkgen_primitives.py
python examples/test_svg_drawing.py
```
Generated artifacts are stored in `examples/output/`. Execute the test suite with:
```bash
pytest
```

## Development Workflow
1. Create and activate a virtual environment: `python -m venv .venv`
2. Install dependencies: `pip install -e .[dev]`
3. Run formatting and lint checks:
   ```bash
   ruff check .
   ruff format .
   ```
4. Run the tests (optionally with coverage): `pytest --cov`
5. Update example outputs if needed via the scripts in `examples/`
6. Ensure CI passes and submit a pull request

## Testing
- Unit tests live under `tests/` alongside fixtures
- Example-driven smoke tests live in `examples/`
- Continuous Integration runs linting (`ruff`) and tests on every push

## Contributing
We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details on
our development workflow, coding standards, and how to propose changes. For
questions or feature requests, open an issue or start a discussion.

## Code of Conduct
This project adheres to the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating, you are expected to uphold this code. Report unacceptable
behavior to the maintainers listed in that document.

## License
InkGen is released under the terms of the [MIT License](LICENSE).
