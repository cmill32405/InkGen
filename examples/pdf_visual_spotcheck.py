"""Generate matched SVG/PDF artifacts for PDF backend visual spot checks."""

from __future__ import annotations

from pathlib import Path

from InkGen.boundary import Canvas
from InkGen.pdf_generator import CirclePDF, ComponentGroupPDF, DocumentPDF, LinePDF, RectanglePDF, TextPDF
from InkGen.style import DrawingStyle, Font, Style, TextStyle
from InkGen.svg_generator import CircleSVG, ComponentGroupSVG, DocumentSVG, LineSVG, RectangleSVG, TextSVG


def create_spotcheck_artifacts(output_dir: str | Path | None = None) -> dict[str, Path]:
    """Create matched SVG and PDF outputs for manual visual comparison."""
    target_dir = Path(output_dir) if output_dir is not None else Path(__file__).resolve().parent / "output"
    target_dir.mkdir(parents=True, exist_ok=True)

    svg_document = _build_svg_document()
    pdf_document = _build_pdf_document()

    svg_path = target_dir / "pdf_visual_spotcheck.svg"
    pdf_path = target_dir / "pdf_visual_spotcheck.pdf"
    svg_document.create_svg(str(svg_path))
    pdf_document.create_pdf(str(pdf_path))
    return {"svg": svg_path, "pdf": pdf_path}


def main() -> None:
    """Generate the SVG/PDF visual spot-check pair in examples/output."""
    paths = create_spotcheck_artifacts()
    print(f"SVG: {paths['svg']}")
    print(f"PDF: {paths['pdf']}")


def _build_svg_document() -> DocumentSVG:
    canvas = Canvas(120.0, 80.0)
    document = DocumentSVG(canvas)
    document.add_page()
    group = ComponentGroupSVG("spotcheck")
    drawing_style, accent_style, text_style = _styles("svg")
    group.add_component(RectangleSVG((12.0, 14.0), 48.0, 28.0, 0.0, drawing_style))
    group.add_component(LineSVG((12.0, 52.0), (96.0, 52.0), accent_style))
    group.add_component(CircleSVG((88.0, 28.0), 10.0, accent_style))
    group.add_component(TextSVG("PDF parity", (18.0, 31.0), text_style))
    document.page(1).layer("base").add_component_group(group)
    return document


def _build_pdf_document() -> DocumentPDF:
    canvas = Canvas(120.0, 80.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroupPDF("spotcheck")
    drawing_style, accent_style, text_style = _styles("pdf")
    group.add_component(RectanglePDF((12.0, 14.0), 48.0, 28.0, 0.0, drawing_style))
    group.add_component(LinePDF((12.0, 52.0), (96.0, 52.0), accent_style))
    group.add_component(CirclePDF((88.0, 28.0), 10.0, accent_style))
    group.add_component(TextPDF("PDF parity", (18.0, 31.0), text_style))
    document.page(1).layer("base").add_component_group(group)
    return document


def _styles(prefix: str) -> tuple[DrawingStyle, DrawingStyle, TextStyle]:
    drawing_style = DrawingStyle(
        name=_style_name(f"{prefix}_pdf_spotcheck_border"),
        stroke="#111111",
        stroke_width=0.4,
        fill="none",
    )
    accent_style = DrawingStyle(
        name=_style_name(f"{prefix}_pdf_spotcheck_accent"),
        stroke="#006699",
        stroke_width=0.6,
        fill="none",
    )
    text_style = TextStyle(name=_style_name(f"{prefix}_pdf_spotcheck_text"), font=Font(size=9.0))
    text_style.color = "#111111"
    return drawing_style, accent_style, text_style


def _style_name(base: str) -> str:
    if base not in Style.style_names:
        return base
    suffix = 1
    while f"{base}_{suffix}" in Style.style_names:
        suffix += 1
    return f"{base}_{suffix}"


if __name__ == "__main__":
    main()
