"""
Generate an SVG showcase of InkGen drawing primitives.

Creates a base SVG illustrating each drawing component with a brief label
describing its parameters, plus a companion convex-hull mask SVG.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Tuple

from InkGen.boundary import Canvas
from InkGen.svg_generator import (
    ArcSVG,
    CircleSVG,
    ComponentGroupSVG,
    CubicBezierSVG,
    DocumentSVG,
    IncludeLayer,
    LineSVG,
    PathSVG,
    PolygonalSVG,
    QuadraticBezierSVG,
    RectangleSVG,
    RegularPolygonSVG,
    TextSVG,
)
from InkGen.component import PathCommand
from InkGen.errors import ComponentGroupOffCanvas
from InkGen.document import Layer
from InkGen.style import DrawingStyle, Font, TextStyle

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"

LabelPos = Tuple[float, float]


def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _bbox_from_points(points: Iterable[Tuple[float, float]]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    xs: List[float] = []
    ys: List[float] = []
    for x, y in points:
        xs.append(float(x))
        ys.append(float(y))
    if not xs or not ys:
        return (0.0, 0.0), (0.0, 0.0)
    return (min(xs), min(ys)), (max(xs), max(ys))


def _label_position(
    component,
    canvas_width: float,
    canvas_height: float,
    label_text: str,
    label_style: TextStyle,
) -> LabelPos:
    (xmin, ymin), (xmax, ymax) = _bbox_from_points(component.points)
    y_pos = ymax + 6.0
    margin = 4.0
    font_size = float(getattr(label_style.font, "size", 6.0))
    est_width = max(0.0, len(label_text) * font_size * 0.6)

    alignment = label_style.text_align.lower()
    if alignment == "end":
        x_pos = xmax
        x_pos = max(margin + est_width, min(canvas_width - margin, x_pos))
    elif alignment in {"middle", "center"}:
        x_pos = (xmin + xmax) / 2.0
        half = est_width / 2.0
        x_pos = max(margin + half, min(canvas_width - margin - half, x_pos))
    else:  # start / left
        x_pos = xmin
        x_pos = max(margin, min(canvas_width - margin - est_width, x_pos))

    y_pos = max(margin, min(canvas_height - margin, y_pos))
    return x_pos, y_pos


def _format_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, (tuple, list)):
        if value and isinstance(value[0], dict):
            return f"{len(value)} items"
        if value and isinstance(value[0], (tuple, list)):
            joined = ";".join(f"({','.join(f'{float(coord):.1f}' for coord in pair)})" for pair in value[:3])
            if len(value) > 3:
                joined += ",..."
            return joined
        return "(" + ", ".join(_format_value(v) for v in value) + ")"
    if isinstance(value, dict):
        return f"{len(value)} keys"
    return str(value)


def _format_parameters(component) -> str:
    params = component.parameters
    component_name = next(iter(params.keys()))
    values = params[component_name]
    parts: List[str] = []
    for key, value in values.items():
        if key == "style":
            continue
        parts.append(f"{key}={_format_value(value)}")
        if len(parts) >= 2:
            break
    remaining = sum(1 for key in values.keys() if key != "style") - len(parts)
    summary = "; ".join(parts)
    if remaining > 0:
        summary = f"{summary}; ..."
    if len(summary) > 60:
        summary = summary[:57] + "..."
    return f"{component_name}: {summary}"


def _create_styles() -> Tuple[DrawingStyle, DrawingStyle, DrawingStyle, TextStyle]:
    outline_style = DrawingStyle(
        name="ShowcaseOutline",
        stroke="#1F77B4",
        stroke_width=0.6,
        fill="none",
        stroke_opacity=1.0,
    )
    fill_style = DrawingStyle(
        name="ShowcaseFill",
        stroke="#2E4057",
        stroke_width=0.4,
        fill="#DDEEFF",
        stroke_opacity=0.9,
        fill_opacity=0.8,
    )
    accent_style = DrawingStyle(
        name="ShowcaseAccent",
        stroke="#D62728",
        stroke_width=0.5,
        fill="none",
        stroke_opacity=1.0,
    )
    label_font = Font(family="Arial", size=6.0)
    label_style = TextStyle("ShowcaseLabel", label_font)
    label_style.color = "#333333"
    label_style.text_align = "start"
    return outline_style, fill_style, accent_style, label_style


def _add_component_with_label(
    group: ComponentGroupSVG,
    component,
    label_style: TextStyle,
    canvas_width: float,
    canvas_height: float,
    label_text: str | None = None,
) -> TextSVG:
    group.add_component(component)
    if label_text is None:
        label_text = _format_parameters(component)
    label_x, label_y = _label_position(component, canvas_width, canvas_height, label_text, label_style)
    label = TextSVG(label_text, (label_x, label_y), label_style)
    return label


def _build_showcase(document: DocumentSVG, output_dir: str, filename: str) -> None:
    outline_style, fill_style, accent_style, label_style = _create_styles()
    page = document.page(1)
    base_layer = page.layer("base")

    shapes_group = ComponentGroupSVG("PrimitiveShowcase")
    labels_group = ComponentGroupSVG("PrimitiveLabels")

    canvas_width = page._canvas.width
    canvas_height = page._canvas.height

    rectangle = RectangleSVG((10.0, 10.0), 40.0, 24.0, corner_radii=4.0, style=fill_style)
    rect_label = "RectangleSVG w40 h24 r4"
    rect_label_component = _add_component_with_label(shapes_group, rectangle, label_style, canvas_width, canvas_height, rect_label)
    labels_group.add_component(rect_label_component)

    circle = CircleSVG((80.0, 22.0), 12.0, outline_style)
    circle_label = "CircleSVG r12"
    circle_label_component = _add_component_with_label(shapes_group, circle, label_style, canvas_width, canvas_height, circle_label)
    labels_group.add_component(circle_label_component)

    line = LineSVG((120.0, 12.0), (160.0, 28.0), accent_style)
    line_label = "LineSVG span40"
    line_label_component = _add_component_with_label(shapes_group, line, label_style, canvas_width, canvas_height, line_label)
    labels_group.add_component(line_label_component)

    polygon = RegularPolygonSVG(position=(26.0, 70.0), sides=6, radius=14.0, style=outline_style, angle=15.0, corner_radius=1.5)
    regular_label = "RegularPolygonSVG hex"
    polygon_label_component = _add_component_with_label(shapes_group, polygon, label_style, canvas_width, canvas_height, regular_label)
    labels_group.add_component(polygon_label_component)

    poly_points = [(62.0, 58.0), (84.0, 60.0), (90.0, 80.0), (70.0, 86.0), (58.0, 72.0)]
    irregular = PolygonalSVG(poly_points, fill_style)
    polygonal_label = "PolygonalSVG 5pts"
    polygonal_label_component = _add_component_with_label(shapes_group, irregular, label_style, canvas_width, canvas_height, polygonal_label)
    labels_group.add_component(polygonal_label_component)

    arc = ArcSVG(center=(126.0, 70.0), radius_x=18.0, radius_y=12.0, start_angle=0.0, end_angle=210.0, rotation=25.0, style=accent_style)
    arc_label = "ArcSVG rx18 ry12"
    arc_label_component = _add_component_with_label(shapes_group, arc, label_style, canvas_width, canvas_height, arc_label)
    labels_group.add_component(arc_label_component)

    quad = QuadraticBezierSVG(start_point=(18.0, 108.0), control_point=(36.0, 92.0), end_point=(60.0, 114.0), style=outline_style)
    quad_label = "QuadraticBezierSVG"
    quad_label_component = _add_component_with_label(shapes_group, quad, label_style, canvas_width, canvas_height, quad_label)
    labels_group.add_component(quad_label_component)

    cubic = CubicBezierSVG(
        start_point=(76.0, 104.0),
        control_point1=(90.0, 88.0),
        control_point2=(112.0, 120.0),
        end_point=(138.0, 102.0),
        style=accent_style,
    )
    cubic_label = "CubicBezierSVG"
    cubic_label_component = _add_component_with_label(shapes_group, cubic, label_style, canvas_width, canvas_height, cubic_label)
    labels_group.add_component(cubic_label_component)

    path_commands = [
        PathCommand("M", [(18.0, 126.0)]),
        PathCommand("L", [(42.0, 118.0), (58.0, 132.0)]),
        PathCommand("C", [(70.0, 140.0), (84.0, 120.0), (102.0, 132.0)]),
        PathCommand("Q", [(118.0, 140.0), (132.0, 128.0)]),
        PathCommand("Z", []),
    ]
    path = PathSVG(outline_style, commands=path_commands)
    path_label = "PathSVG 5cmds"
    path_label_component = _add_component_with_label(shapes_group, path, label_style, canvas_width, canvas_height, path_label)
    labels_group.add_component(path_label_component)

    try:
        shapes_group._mask_override = list(shapes_group.convex_hull)
    except Exception:
        shapes_group._mask_override = []

    try:
        base_layer.add_component_group(shapes_group)
    except ComponentGroupOffCanvas as exc:
        print(f"[WARN] Component group '{shapes_group.group_label}' exceeded canvas bounds: {exc}")
        raise

    if "labels" not in page.layers:
        page.add_layer(layer=Layer("labels", page._canvas, model=False))
    label_layer = page.layer("labels")
    try:
        label_layer.add_component_group(labels_group)
    except ComponentGroupOffCanvas as exc:
        print(f"[WARN] Label group exceeded canvas bounds: {exc}")
        raise

    output_dir_path = Path(output_dir)
    _ensure_output_dir(output_dir_path)
    base_path = output_dir_path / f"{filename}_base.svg"
    mask_path = output_dir_path / f"{filename}_mask.svg"
    document.create_svg(str(base_path), include=IncludeLayer.BASE)
    document.create_svg(str(mask_path), include=IncludeLayer.MASK)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a showcase of InkGen drawing primitives.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write the SVG outputs.",
    )
    parser.add_argument("--filename", default="inkgen_primitives_showcase", help="Base filename for generated SVGs.")
    parser.add_argument(
        "--width",
        type=float,
        default=190.0,
        help="Canvas width in millimeters.",
    )
    parser.add_argument(
        "--height",
        type=float,
        default=160.0,
        help="Canvas height in millimeters.",
    )
    args = parser.parse_args()

    canvas = Canvas(args.width, args.height, "mm")
    document = DocumentSVG(canvas)
    document.add_page()

    _build_showcase(document, args.output_dir, args.filename)
    print(f"Generated SVG primitives showcase at {args.output_dir}")


if __name__ == "__main__":
    main()
