"""Dependency-free PDF rendering backend for InkGen documents.

This module mirrors the SVG renderer with PDF-specific mixins over the existing
geometry, document, and style model. It intentionally uses only the Python
standard library so InkGen does not gain another PDF dependency.
"""

from __future__ import annotations

import abc
import math
import os
import sys
from dataclasses import dataclass

from InkGen.boundary import Canvas
from InkGen.component import Arc as ArcComponent
from InkGen.component import (
    ComponentGroup,
    PathCommand,
    PolygonalDrawingComponent,
    RegularPolygonDrawingComponent,
    SingleDimensionDrawingComponent,
    StandardDrawingComponent,
    TextComponent,
    WidthHeightDrawingComponent,
)
from InkGen.component import CubicBezier as CubicBezierComponent
from InkGen.component import Path as PathComponent
from InkGen.component import QuadraticBezier as QuadraticBezierComponent
from InkGen.document import Document, Layers
from InkGen.style import DrawingStyle, TextStyle

PDF_FIXED_DATE = "D:20000101000000Z"


class PDFGeneratorInterface(metaclass=abc.ABCMeta):
    """Interface for components that can emit PDF content-stream operators."""

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool:
        return hasattr(subclass, "generate_pdf") and callable(subclass.generate_pdf) or NotImplemented

    @abc.abstractmethod
    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF content-stream operators for this drawing component."""
        raise NotImplementedError


@dataclass(frozen=True)
class PDFRenderContext:
    """Rendering settings shared by PDF components on a page."""

    canvas_height: float


class _PDFObjectWriter:
    """Small deterministic PDF object writer."""

    def __init__(self) -> None:
        self._objects: dict[int, bytes] = {}

    def set_object(self, object_id: int, payload: str | bytes) -> None:
        """Register a PDF object payload at a stable object id."""
        if isinstance(payload, str):
            payload = payload.encode("latin-1")
        self._objects[object_id] = payload

    def build(self, *, root_id: int, info_id: int) -> bytes:
        """Build a PDF file with a classic xref table."""
        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for object_id in sorted(self._objects):
            offsets.append(len(output))
            output.extend(f"{object_id} 0 obj\n".encode("ascii"))
            output.extend(self._objects[object_id])
            output.extend(b"\nendobj\n")

        xref_offset = len(output)
        output.extend(f"xref\n0 {len(self._objects) + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f\n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n\n".encode("ascii"))
        output.extend(
            (
                f"trailer\n<< /Size {len(self._objects) + 1} /Root {root_id} 0 R /Info {info_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )
        return bytes(output)


def _number(value: float | int) -> str:
    """Format a PDF number deterministically."""
    numeric = float(value)
    if math.isclose(numeric, round(numeric), abs_tol=1e-9):
        return str(int(round(numeric)))
    return f"{numeric:.6f}".rstrip("0").rstrip(".")


def _escape_pdf_string(value: str) -> str:
    """Escape text for a literal PDF string."""
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\r", "\\r").replace("\n", "\\n")


def _color_components(color: str) -> tuple[float, float, float] | None:
    """Convert an InkGen color into RGB values in PDF's 0-1 range."""
    if not color or color.lower() == "none":
        return None
    hex_color = color.lstrip("#")
    if len(hex_color) != 6:
        return None
    return (
        int(hex_color[0:2], 16) / 255.0,
        int(hex_color[2:4], 16) / 255.0,
        int(hex_color[4:6], 16) / 255.0,
    )


def _style_operators(style: DrawingStyle, *, fill: bool = True, stroke: bool = True) -> list[str]:
    """Emit PDF graphics-state operators for an InkGen drawing style."""
    operators: list[str] = []
    if stroke:
        stroke_color = _color_components(getattr(style, "stroke", "none"))
        if stroke_color is not None:
            operators.append(f"{_number(stroke_color[0])} {_number(stroke_color[1])} {_number(stroke_color[2])} RG")
        operators.append(f"{_number(getattr(style, 'stroke_width', 0.0))} w")
    if fill:
        fill_color = _color_components(getattr(style, "fill", "none"))
        if fill_color is not None:
            operators.append(f"{_number(fill_color[0])} {_number(fill_color[1])} {_number(fill_color[2])} rg")
    return operators


def _paint_operator(style: DrawingStyle, *, fill: bool = True, stroke: bool = True) -> str:
    """Choose the PDF path-painting operator for a drawing style."""
    has_fill = fill and _color_components(getattr(style, "fill", "none")) is not None
    has_stroke = stroke and _color_components(getattr(style, "stroke", "none")) is not None
    if has_fill and has_stroke:
        return "B"
    if has_fill:
        return "f"
    if has_stroke:
        return "S"
    return "n"


def _path_from_points(points: list[tuple[float, float]], *, close: bool) -> list[str]:
    """Build PDF path operators from a point list."""
    if not points:
        return []
    commands = [f"{_number(points[0][0])} {_number(points[0][1])} m"]
    for x, y in points[1:]:
        commands.append(f"{_number(x)} {_number(y)} l")
    if close:
        commands.append("h")
    return commands


def _quadratic_to_cubic(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Convert a quadratic Bezier control point into cubic controls."""
    c1 = (start[0] + (2.0 / 3.0) * (control[0] - start[0]), start[1] + (2.0 / 3.0) * (control[1] - start[1]))
    c2 = (end[0] + (2.0 / 3.0) * (control[0] - end[0]), end[1] + (2.0 / 3.0) * (control[1] - end[1]))
    return c1, c2


def _drawing_pdf(style: DrawingStyle, path_operators: list[str], *, fill: bool = True, stroke: bool = True) -> str:
    """Wrap a path with style and paint operators."""
    operators = ["q"]
    operators.extend(_style_operators(style, fill=fill, stroke=stroke))
    operators.extend(path_operators)
    operators.append(_paint_operator(style, fill=fill, stroke=stroke))
    operators.append("Q")
    return "\n".join(operators)


class RectanglePDF(WidthHeightDrawingComponent, PDFGeneratorInterface):
    """PDF representation of a rectangle component."""

    def __init__(
        self,
        position: tuple[float, float],
        width: float | int,
        height: float | int,
        corner_radii: float | tuple[float, float],
        style: DrawingStyle,
    ) -> None:
        super().__init__(position, width, height, style)
        self.corner_radii = corner_radii

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> RectanglePDF:
        """Recreate a RectanglePDF from serialized parameters."""
        payload = data["RectanglePDF"]
        if style is None:
            style = DrawingStyle.create_from_dict(payload["style"])
        return cls(payload["position"], payload["width"], payload["height"], payload["corner_radii"], style)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return {
            "RectanglePDF": {
                "position": self.position,
                "width": self.width,
                "height": self.height,
                "corner_radii": self.corner_radii,
                "style": self.style.parameters,
            }
        }

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this rectangle."""
        path = [f"{_number(self.position[0])} {_number(self.position[1])} {_number(self.width)} {_number(self.height)} re"]
        return _drawing_pdf(self.style, path)


class LinePDF(StandardDrawingComponent, PDFGeneratorInterface):
    """PDF representation of a line component."""

    def __init__(self, point_1: tuple[float, float], point_2: tuple[float, float], style: DrawingStyle) -> None:
        super().__init__(point_1=point_1, point_2=point_2, style=style)

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this line."""
        path = [
            f"{_number(self.point_1[0])} {_number(self.point_1[1])} m",
            f"{_number(self.point_2[0])} {_number(self.point_2[1])} l",
        ]
        return _drawing_pdf(self.style, path, fill=False)


class ArcPDF(ArcComponent, PDFGeneratorInterface):
    """PDF representation of an elliptical arc."""

    def __init__(
        self,
        center: tuple[float, float],
        radius_x: float,
        radius_y: float,
        start_angle: float,
        end_angle: float,
        style: DrawingStyle,
        rotation: float = 0.0,
    ) -> None:
        super().__init__(
            center=center,
            radius_x=radius_x,
            radius_y=radius_y,
            start_angle=start_angle,
            end_angle=end_angle,
            style=style,
            rotation=rotation,
        )

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this arc using InkGen's sampled points."""
        return _drawing_pdf(self.style, _path_from_points(list(self.points), close=False), fill=False)


class QuadraticBezierPDF(QuadraticBezierComponent, PDFGeneratorInterface):
    """PDF representation of a quadratic Bezier curve."""

    def __init__(
        self,
        start_point: tuple[float, float],
        control_point: tuple[float, float],
        end_point: tuple[float, float],
        style: DrawingStyle,
    ) -> None:
        super().__init__(start_point=start_point, control_point=control_point, end_point=end_point, style=style)

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this quadratic Bezier."""
        c1, c2 = _quadratic_to_cubic(self.start_point, self.control_point, self.end_point)
        path = [
            f"{_number(self.start_point[0])} {_number(self.start_point[1])} m",
            f"{_number(c1[0])} {_number(c1[1])} {_number(c2[0])} {_number(c2[1])} {_number(self.end_point[0])} {_number(self.end_point[1])} c",
        ]
        return _drawing_pdf(self.style, path, fill=False)


class CubicBezierPDF(CubicBezierComponent, PDFGeneratorInterface):
    """PDF representation of a cubic Bezier curve."""

    def __init__(
        self,
        start_point: tuple[float, float],
        control_point1: tuple[float, float],
        control_point2: tuple[float, float],
        end_point: tuple[float, float],
        style: DrawingStyle,
    ) -> None:
        super().__init__(
            start_point=start_point, control_point1=control_point1, control_point2=control_point2, end_point=end_point, style=style
        )

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this cubic Bezier."""
        path = [
            f"{_number(self.start_point[0])} {_number(self.start_point[1])} m",
            (
                f"{_number(self.control_point1[0])} {_number(self.control_point1[1])} "
                f"{_number(self.control_point2[0])} {_number(self.control_point2[1])} "
                f"{_number(self.end_point[0])} {_number(self.end_point[1])} c"
            ),
        ]
        return _drawing_pdf(self.style, path, fill=False)


class PathPDF(PathComponent, PDFGeneratorInterface):
    """PDF representation of a generic path built from commands."""

    def __init__(self, style: DrawingStyle, commands: list[PathCommand] | None = None) -> None:
        super().__init__(style=style, commands=commands)

    def _command_operators(self) -> list[str]:
        operators: list[str] = []
        current_point = (0.0, 0.0)
        for command in self.commands:
            command_type = command.type.upper()
            points = list(command.points)
            if command_type == "M" and points:
                current_point = points[-1]
                operators.append(f"{_number(current_point[0])} {_number(current_point[1])} m")
            elif command_type == "L":
                for point in points:
                    current_point = point
                    operators.append(f"{_number(point[0])} {_number(point[1])} l")
            elif command_type == "H":
                for point in points:
                    current_point = (point[0], current_point[1])
                    operators.append(f"{_number(current_point[0])} {_number(current_point[1])} l")
            elif command_type == "V":
                for point in points:
                    current_point = (current_point[0], point[1])
                    operators.append(f"{_number(current_point[0])} {_number(current_point[1])} l")
            elif command_type == "C" and len(points) >= 3:
                for index in range(0, len(points), 3):
                    segment = points[index : index + 3]
                    if len(segment) == 3:
                        c1, c2, end = segment
                        current_point = end
                        operators.append(
                            f"{_number(c1[0])} {_number(c1[1])} {_number(c2[0])} {_number(c2[1])} {_number(end[0])} {_number(end[1])} c"
                        )
            elif command_type == "Q" and len(points) >= 2:
                for index in range(0, len(points), 2):
                    segment = points[index : index + 2]
                    if len(segment) == 2:
                        control, end = segment
                        c1, c2 = _quadratic_to_cubic(current_point, control, end)
                        current_point = end
                        operators.append(
                            f"{_number(c1[0])} {_number(c1[1])} {_number(c2[0])} {_number(c2[1])} {_number(end[0])} {_number(end[1])} c"
                        )
            elif command_type == "A" and points:
                current_point = points[-1]
                operators.append(f"{_number(current_point[0])} {_number(current_point[1])} l")
            elif command_type == "Z":
                operators.append("h")
        return operators

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this path."""
        return _drawing_pdf(self.style, self._command_operators())


class RegularPolygonPDF(RegularPolygonDrawingComponent, PDFGeneratorInterface):
    """PDF representation of a regular polygon."""

    def __init__(
        self,
        position: tuple[float, float],
        sides: int,
        radius: float,
        style: DrawingStyle,
        angle: float = 0.0,
        corner_radius: float = 0.0,
    ) -> None:
        super().__init__(position=position, sides=sides, radius=radius, style=style, angle=angle, corner_radius=corner_radius)

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this regular polygon."""
        return _drawing_pdf(self.style, _path_from_points(self._get_points(), close=True))


class PolygonalPDF(PolygonalDrawingComponent, PDFGeneratorInterface):
    """PDF representation of an irregular polygon."""

    def __init__(self, points: list[tuple[float, float]], style: DrawingStyle) -> None:
        super().__init__(points=points, style=style)

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this polygon."""
        return _drawing_pdf(self.style, _path_from_points(list(self.points), close=True))


class CirclePDF(SingleDimensionDrawingComponent, PDFGeneratorInterface):
    """PDF representation of a circle component."""

    def __init__(self, position: tuple[float, float], radius: float, style: DrawingStyle) -> None:
        if isinstance(radius, (float, int)) and radius > 0:
            super().__init__(position, radius, style)
        else:
            raise ValueError("Radii must be greater than 0")

    @property
    def radius(self) -> float:
        """Return the circle radius."""
        return self.size

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this circle using cubic Bezier arcs."""
        x, y = self.position
        radius = self.radius
        control = radius * 0.5522847498307936
        path = [
            f"{_number(x + radius)} {_number(y)} m",
            f"{_number(x + radius)} {_number(y + control)} {_number(x + control)} {_number(y + radius)} {_number(x)} {_number(y + radius)} c",
            f"{_number(x - control)} {_number(y + radius)} {_number(x - radius)} {_number(y + control)} {_number(x - radius)} {_number(y)} c",
            f"{_number(x - radius)} {_number(y - control)} {_number(x - control)} {_number(y - radius)} {_number(x)} {_number(y - radius)} c",
            f"{_number(x + control)} {_number(y - radius)} {_number(x + radius)} {_number(y - control)} {_number(x + radius)} {_number(y)} c",
            "h",
        ]
        return _drawing_pdf(self.style, path)


class TextPDF(TextComponent, PDFGeneratorInterface):
    """PDF representation of a text component."""

    def __init__(self, text: str, position: tuple[float, float], style: TextStyle) -> None:
        super().__init__(text=text, position=position, style=style)

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this text."""
        color = _color_components(getattr(self.style, "color", "#000000")) or (0.0, 0.0, 0.0)
        size = float(getattr(self.style.font, "size", 10.0))
        x, y = self.position
        escaped = _escape_pdf_string(self.text)
        return "\n".join(
            [
                "q",
                f"{_number(color[0])} {_number(color[1])} {_number(color[2])} rg",
                "BT",
                f"/F1 {_number(size)} Tf",
                f"1 0 0 -1 {_number(x)} {_number(y)} Tm",
                f"({escaped}) Tj",
                "ET",
                "Q",
            ]
        )


class ComponentGroupPDF(ComponentGroup):
    """Component group that serializes child PDF components."""

    @classmethod
    def create_from_dict(cls, data: dict, styles: dict | None = None) -> ComponentGroupPDF:
        """Recreate a ComponentGroupPDF from serialized parameters."""
        group = cls(data["ComponentGroupPDF"]["group_label"])
        if styles is None:
            styles = {}
        for component_data in data["ComponentGroupPDF"]["components"]:
            style = None
            component_class_name = list(component_data.keys())[0]
            payload = component_data[component_class_name]
            if "style" in payload:
                style_name = list(payload["style"].keys())[0]
                stored_name = payload["style"][style_name]["name"]
                if stored_name not in styles:
                    style_class = getattr(sys.modules[__name__], style_name)
                    style = style_class.create_from_dict(payload["style"])
                    styles[stored_name] = style
                else:
                    style = styles[stored_name]
            component_class = getattr(sys.modules[__name__], component_class_name)
            group.add_component(component_class.create_from_dict(component_data, style))
        return group

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized group information."""
        return {
            "ComponentGroupPDF": {
                "group_label": self.group_label,
                "components": [component.parameters for component in self._components.values()],
            }
        }

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for all child components."""
        operators: list[str] = []
        for component in self.components():
            generate_pdf = getattr(component, "generate_pdf", None)
            if generate_pdf is None:
                raise TypeError(f"Component {component.__class__.__name__} does not implement generate_pdf().")
            operators.append(generate_pdf(context))
        return "\n".join(operators)


class DocumentPDF(Document):
    """Document renderer that writes one PDF page for each InkGen page."""

    def create_pdf(self, filepath: str) -> None:
        """Create a deterministic PDF file at the requested path."""
        path = os.path.abspath(filepath)
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            raise ValueError("The file path does not exist.")
        with open(path, "wb") as handle:
            handle.write(self.to_pdf_bytes())

    def to_pdf_bytes(self) -> bytes:
        """Render this document to deterministic PDF bytes."""
        writer = _PDFObjectWriter()
        catalog_id = 1
        pages_id = 2
        font_id = 3
        info_id = 4
        page_ids: list[int] = []
        object_id = 5

        writer.set_object(font_id, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        writer.set_object(
            info_id,
            (
                "<< /Creator (InkGen) /Producer (InkGen dependency-free PDF backend) "
                f"/CreationDate ({PDF_FIXED_DATE}) /ModDate ({PDF_FIXED_DATE}) >>"
            ),
        )

        for page_number in range(1, self.pages + 1):
            page = self.page(page_number)
            content = self._render_page_content(page)
            content_bytes = content.encode("latin-1")
            content_id = object_id
            page_id = object_id + 1
            object_id += 2
            page_ids.append(page_id)
            writer.set_object(
                content_id, b"<< /Length " + str(len(content_bytes)).encode("ascii") + b" >>\nstream\n" + content_bytes + b"\nendstream"
            )
            writer.set_object(
                page_id,
                (
                    f"<< /Type /Page /Parent {pages_id} 0 R "
                    f"/MediaBox [0 0 {_number(page._canvas.width)} {_number(page._canvas.height)}] "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                    f"/Contents {content_id} 0 R >>"
                ),
            )

        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        writer.set_object(pages_id, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
        writer.set_object(catalog_id, f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
        return writer.build(root_id=catalog_id, info_id=info_id)

    def _render_page_content(self, page: Layers) -> str:
        context = PDFRenderContext(canvas_height=page._canvas.height)
        operators = ["q", f"1 0 0 -1 0 {_number(page._canvas.height)} cm"]
        for layer_name in page.layers:
            layer = page.layer(layer_name)
            for _, group_id in layer.component_groups.items():
                group = layer.group(group_id)
                if hasattr(group, "generate_pdf"):
                    operators.append(group.generate_pdf(context))
                    continue
                for component in group.components():
                    generate_pdf = getattr(component, "generate_pdf", None)
                    if generate_pdf is None:
                        raise TypeError(f"Component {component.__class__.__name__} does not implement generate_pdf().")
                    operators.append(generate_pdf(context))
        operators.append("Q")
        return "\n".join(operators)

    @classmethod
    def create_from_dict(cls, data: dict, styles: dict | None = None) -> DocumentPDF:
        """Recreate a DocumentPDF from serialized parameters."""
        document = cls(Canvas.create_from_dict(data["DocumentPDF"]["canvas"]))
        for page_payload in data["DocumentPDF"]["pages"]:
            page = Layers.create_from_dict(page_payload, styles)
            document.add_page(position=-1, page=page)
        return document

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized document information."""
        return {
            "DocumentPDF": {
                "canvas": self._canvas.parameters,
                "pages": [self.page(page).parameters for page in list(self._pages.keys())],
            }
        }
