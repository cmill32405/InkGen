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
    Component,
    ComponentGroup,
    PathCommand,
    PolygonalDrawingComponent,
    RegularPolygonDrawingComponent,
    SingleDimensionDrawingComponent,
    StandardDrawingComponent,
    TextComponent,
    WidthHeightDrawingComponent,
    normalize_rectangle_corner_radii,
)
from InkGen.component import CubicBezier as CubicBezierComponent
from InkGen.component import Path as PathComponent
from InkGen.component import QuadraticBezier as QuadraticBezierComponent
from InkGen.document import Document, Layer, Layers
from InkGen.extraction_truth import (
    extraction_truth_json,
    restore_extraction_truth_annotations,
    serialize_extraction_truth_annotations,
    sort_extraction_truth_records,
)
from InkGen.extraction_truth import (
    records_for_annotated_target as extraction_records_for_annotated_target,
)
from InkGen.grammar_truth import (
    grammar_truth_json,
    restore_grammar_truth_annotations,
    serialize_grammar_truth_annotations,
    sort_grammar_truth_records,
)
from InkGen.grammar_truth import (
    records_for_annotated_target as grammar_records_for_annotated_target,
)
from InkGen.pdf_render_contract import ensure_builtin_pdf_component, ensure_pdf_group
from InkGen.style import DrawingStyle, TextStyle
from InkGen.svg_generator import LabelGenerator, SegmentGenerator

PDF_FIXED_DATE = "D:20000101000000Z"


class PDFGeneratorInterface(metaclass=abc.ABCMeta):
    """Interface for components that can emit PDF content-stream operators."""

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool:
        """Return whether a subclass provides a callable PDF generator."""
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


def _rounded_rectangle_path(x: float, y: float, width: float, height: float, rx: float, ry: float) -> list[str]:
    """Build PDF path operators for a rounded rectangle."""
    if rx == 0.0 or ry == 0.0:
        return [f"{_number(x)} {_number(y)} {_number(width)} {_number(height)} re"]

    right = x + width
    bottom = y + height
    kappa = 0.5522847498307936
    cx = rx * kappa
    cy = ry * kappa
    return [
        f"{_number(x + rx)} {_number(y)} m",
        f"{_number(right - rx)} {_number(y)} l",
        f"{_number(right - rx + cx)} {_number(y)} {_number(right)} {_number(y + ry - cy)} {_number(right)} {_number(y + ry)} c",
        f"{_number(right)} {_number(bottom - ry)} l",
        f"{_number(right)} {_number(bottom - ry + cy)} {_number(right - rx + cx)} {_number(bottom)} {_number(right - rx)} {_number(bottom)} c",
        f"{_number(x + rx)} {_number(bottom)} l",
        f"{_number(x + rx - cx)} {_number(bottom)} {_number(x)} {_number(bottom - ry + cy)} {_number(x)} {_number(bottom - ry)} c",
        f"{_number(x)} {_number(y + ry)} l",
        f"{_number(x)} {_number(y + ry - cy)} {_number(x + rx - cx)} {_number(y)} {_number(x + rx)} {_number(y)} c",
        "h",
    ]


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


def _primitive_parameters(name: str, *, values: dict[str, object], style: DrawingStyle**TextStyle) -> dict[str, dict[str, object]]:
    """Return a serialization dictionary for a PDF primitive component."""
    payload = dict(values)
    payload["style"] = style.parameters
    return {name: payload}


def _path_command_from_dict(data: dict[str, object]) -> PathCommand:
    """Recreate a PathCommand from serialized command parameters."""
    command = PathCommand(str(data["type"]), data.get("points", []))
    flags = data.get("flags")
    if flags:
        command.flags = flags
    return command


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
        """Create a PDF rectangle with position, size, corner radii, and style."""
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

    @property
    def corner_radii(self) -> float | tuple[float, float]:
        """Return the requested rectangle corner radii."""
        return self._corner_radii

    @corner_radii.setter
    def corner_radii(self, value: float | tuple[float, float]) -> None:
        """Validate and update the requested rectangle corner radii."""
        normalize_rectangle_corner_radii(value, self.width, self.height)
        self._corner_radii = value

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this rectangle."""
        rx, ry = normalize_rectangle_corner_radii(self.corner_radii, self.width, self.height)
        path = _rounded_rectangle_path(self.position[0], self.position[1], self.width, self.height, rx, ry)
        return _drawing_pdf(self.style, path)


class LinePDF(StandardDrawingComponent, PDFGeneratorInterface):
    """PDF representation of a line component."""

    def __init__(self, point_1: tuple[float, float], point_2: tuple[float, float], style: DrawingStyle) -> None:
        """Create a PDF line between two points."""
        super().__init__(point_1=point_1, point_2=point_2, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> LinePDF:
        """Recreate a LinePDF from serialized parameters."""
        payload = data["LinePDF"]
        if style is None:
            style = DrawingStyle.create_from_dict(payload["style"])
        return cls(tuple(payload["point_1"]), tuple(payload["point_2"]), style)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters("LinePDF", values={"point_1": self.point_1, "point_2": self.point_2}, style=self.style)

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
        """Create a PDF elliptical arc."""
        super().__init__(
            center=center,
            radius_x=radius_x,
            radius_y=radius_y,
            start_angle=start_angle,
            end_angle=end_angle,
            style=style,
            rotation=rotation,
        )

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> ArcPDF:
        """Recreate an ArcPDF from serialized parameters."""
        payload = data["ArcPDF"]
        if style is None:
            style = DrawingStyle.create_from_dict(payload["style"])
        return cls(
            center=tuple(payload["center"]),
            radius_x=payload["radius_x"],
            radius_y=payload["radius_y"],
            start_angle=payload["start_angle"],
            end_angle=payload["end_angle"],
            style=style,
            rotation=payload.get("rotation", 0.0),
        )

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters(
            "ArcPDF",
            values={
                "center": self.center,
                "radius_x": self.radius_x,
                "radius_y": self.radius_y,
                "start_angle": self.start_angle,
                "end_angle": self.end_angle,
                "rotation": self.rotation,
            },
            style=self.style,
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
        """Create a PDF quadratic Bezier curve."""
        super().__init__(start_point=start_point, control_point=control_point, end_point=end_point, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> QuadraticBezierPDF:
        """Recreate a QuadraticBezierPDF from serialized parameters."""
        payload = data["QuadraticBezierPDF"]
        if style is None:
            style = DrawingStyle.create_from_dict(payload["style"])
        return cls(tuple(payload["start_point"]), tuple(payload["control_point"]), tuple(payload["end_point"]), style)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters(
            "QuadraticBezierPDF",
            values={"start_point": self.start_point, "control_point": self.control_point, "end_point": self.end_point},
            style=self.style,
        )

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
        """Create a PDF cubic Bezier curve."""
        super().__init__(
            start_point=start_point, control_point1=control_point1, control_point2=control_point2, end_point=end_point, style=style
        )

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> CubicBezierPDF:
        """Recreate a CubicBezierPDF from serialized parameters."""
        payload = data["CubicBezierPDF"]
        if style is None:
            style = DrawingStyle.create_from_dict(payload["style"])
        return cls(
            tuple(payload["start_point"]),
            tuple(payload["control_point1"]),
            tuple(payload["control_point2"]),
            tuple(payload["end_point"]),
            style,
        )

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters(
            "CubicBezierPDF",
            values={
                "start_point": self.start_point,
                "control_point1": self.control_point1,
                "control_point2": self.control_point2,
                "end_point": self.end_point,
            },
            style=self.style,
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
        """Create a PDF path from SVG-style path commands."""
        super().__init__(style=style, commands=commands)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> PathPDF:
        """Recreate a PathPDF from serialized parameters."""
        payload = data["PathPDF"]
        if style is None:
            style = DrawingStyle.create_from_dict(payload["style"])
        commands = [_path_command_from_dict(command) for command in payload.get("commands", [])]
        return cls(style=style, commands=commands)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        serialized = []
        for command in self.commands:
            entry = dict(command.parameters)
            flags = getattr(command, "flags", None)
            if flags is not None:
                entry["flags"] = flags
            serialized.append(entry)
        return _primitive_parameters("PathPDF", values={"commands": serialized}, style=self.style)

    def _command_operators(self) -> list[str]:
        operators: list[str] = []
        current_point = (0.0, 0.0)
        for command in self.commands:
            command_type = command.type.upper()
            points = list(command.points)
            if command_type in {"S", "T"}:
                raise ValueError(f"PathPDF does not support path command {command_type}.")
            if command_type == "C" and len(points) % 3:
                raise ValueError("PathPDF command C requires points in groups of three.")
            if command_type == "Q" and len(points) % 2:
                raise ValueError("PathPDF command Q requires points in groups of two.")
            if command_type == "A" and not points:
                raise ValueError("PathPDF command A requires an endpoint.")
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
            elif command_type == "C":
                for index in range(0, len(points), 3):
                    segment = points[index : index + 3]
                    c1, c2, end = segment
                    current_point = end
                    operators.append(
                        f"{_number(c1[0])} {_number(c1[1])} {_number(c2[0])} {_number(c2[1])} {_number(end[0])} {_number(end[1])} c"
                    )
            elif command_type == "Q":
                for index in range(0, len(points), 2):
                    segment = points[index : index + 2]
                    control, end = segment
                    c1, c2 = _quadratic_to_cubic(current_point, control, end)
                    current_point = end
                    operators.append(
                        f"{_number(c1[0])} {_number(c1[1])} {_number(c2[0])} {_number(c2[1])} {_number(end[0])} {_number(end[1])} c"
                    )
            elif command_type == "A":
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
        """Create a PDF regular polygon."""
        super().__init__(position=position, sides=sides, radius=radius, style=style, angle=angle, corner_radius=corner_radius)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> RegularPolygonPDF:
        """Recreate a RegularPolygonPDF from serialized parameters."""
        payload = data["RegularPolygonPDF"]
        if style is None:
            style = DrawingStyle.create_from_dict(payload["style"])
        return cls(
            tuple(payload["position"]),
            payload["sides"],
            payload["radius"],
            style,
            payload.get("angle", 0.0),
            payload.get("corner_radius", 0.0),
        )

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters(
            "RegularPolygonPDF",
            values={
                "position": self.position,
                "sides": self.sides,
                "radius": self.radius,
                "angle": self.angle,
                "corner_radius": self.corner_radius,
            },
            style=self.style,
        )

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this regular polygon."""
        return _drawing_pdf(self.style, _path_from_points(self._get_points(), close=True))


class PolygonalPDF(PolygonalDrawingComponent, PDFGeneratorInterface):
    """PDF representation of an irregular polygon."""

    def __init__(self, points: list[tuple[float, float]], style: DrawingStyle) -> None:
        """Create a PDF polygon from explicit points."""
        super().__init__(points=points, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> PolygonalPDF:
        """Recreate a PolygonalPDF from serialized parameters."""
        payload = data["PolygonalPDF"]
        if style is None:
            style = DrawingStyle.create_from_dict(payload["style"])
        return cls([tuple(point) for point in payload["points"]], style)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters("PolygonalPDF", values={"points": self.points}, style=self.style)

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this polygon."""
        return _drawing_pdf(self.style, _path_from_points(list(self.points), close=True))


class CirclePDF(SingleDimensionDrawingComponent, PDFGeneratorInterface):
    """PDF representation of a circle component."""

    def __init__(self, position: tuple[float, float], radius: float, style: DrawingStyle) -> None:
        """Create a PDF circle."""
        if isinstance(radius, (float, int)) and radius > 0:
            super().__init__(position, radius, style)
        else:
            raise ValueError("Radii must be greater than 0")

    @property
    def radius(self) -> float:
        """Return the circle radius."""
        return self.size

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> CirclePDF:
        """Recreate a CirclePDF from serialized parameters."""
        payload = data["CirclePDF"]
        if style is None:
            style = DrawingStyle.create_from_dict(payload["style"])
        return cls(tuple(payload["position"]), payload["radius"], style)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters("CirclePDF", values={"position": self.position, "radius": self.radius}, style=self.style)

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
        """Create a PDF text component."""
        super().__init__(text=text, position=position, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: TextStyle | None = None) -> TextPDF:
        """Recreate a TextPDF from serialized parameters."""
        payload = data["TextPDF"]
        if style is None:
            style = TextStyle.create_from_dict(payload["style"])
        return cls(payload["text"], tuple(payload["position"]), style)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized text/style information."""
        return _primitive_parameters("TextPDF", values={"text": self.text, "position": self.position}, style=self.style)

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


PDF_RENDER_COMPONENT_TYPES = (
    RectanglePDF,
    LinePDF,
    ArcPDF,
    QuadraticBezierPDF,
    CubicBezierPDF,
    PathPDF,
    RegularPolygonPDF,
    PolygonalPDF,
    CirclePDF,
    TextPDF,
)


class ComponentGroupPDF(ComponentGroup, LabelGenerator, SegmentGenerator):
    """Component group that serializes child PDF components."""

    def add_component(self, component: Component) -> None:
        """Add a built-in PDF component to the group."""
        ensure_builtin_pdf_component(
            component,
            PDF_RENDER_COMPONENT_TYPES,
            message="ComponentGroupPDF only accepts built-in PDF components.",
        )
        super().add_component(component)

    @classmethod
    def create_from_dict(cls, data: dict, styles: dict | None = None) -> ComponentGroupPDF:
        """Recreate a ComponentGroupPDF from serialized parameters."""
        payload = data["ComponentGroupPDF"]
        group = cls(payload["group_label"])
        restore_extraction_truth_annotations(group, payload.get("extraction_truth", []))
        restore_grammar_truth_annotations(group, payload.get("grammar_truth", []))
        if styles is None:
            styles = {}
        component_annotations = payload.get("component_extraction_truth", [])
        component_grammar_annotations = payload.get("component_grammar_truth", [])
        for index, component_data in enumerate(payload["components"]):
            style = None
            component_class_name = list(component_data.keys())[0]
            component_payload = component_data[component_class_name]
            if "style" in component_payload:
                style_name = list(component_payload["style"].keys())[0]
                stored_name = component_payload["style"][style_name]["name"]
                if stored_name not in styles:
                    style_class = getattr(sys.modules[__name__], style_name)
                    style = style_class.create_from_dict(component_payload["style"])
                    styles[stored_name] = style
                else:
                    style = styles[stored_name]
            component_class = getattr(sys.modules[__name__], component_class_name)
            component = component_class.create_from_dict(component_data, style)
            if index < len(component_annotations):
                restore_extraction_truth_annotations(component, component_annotations[index])
            if index < len(component_grammar_annotations):
                restore_grammar_truth_annotations(component, component_grammar_annotations[index])
            group.add_component(component)
        return group

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized group information."""
        components = list(self._components.values())
        group_payload: dict[str, object] = {
            "group_label": self.group_label,
            "components": [component.parameters for component in components],
        }
        annotations = serialize_extraction_truth_annotations(self)
        if annotations:
            group_payload["extraction_truth"] = annotations
        component_annotations = [serialize_extraction_truth_annotations(component) for component in components]
        if any(component_annotations):
            group_payload["component_extraction_truth"] = component_annotations
        grammar_annotations = serialize_grammar_truth_annotations(self)
        if grammar_annotations:
            group_payload["grammar_truth"] = grammar_annotations
        component_grammar_annotations = [serialize_grammar_truth_annotations(component) for component in components]
        if any(component_grammar_annotations):
            group_payload["component_grammar_truth"] = component_grammar_annotations
        return {"ComponentGroupPDF": group_payload}

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for all child components."""
        operators: list[str] = []
        for component in self.components():
            ensure_builtin_pdf_component(
                component,
                PDF_RENDER_COMPONENT_TYPES,
                message="ComponentGroupPDF only renders built-in PDF components.",
            )
            operators.append(component.generate_pdf(context))
        return "\n".join(operators)

    def generate_label(self) -> dict[str, list[tuple[float, float]]]:
        """Generate renderer-agnostic label bounding boxes for this group."""
        return {self.group_label: self.bbox}

    def generate_segmentation_mask(self) -> dict[str, list[tuple[float, float]]]:
        """Generate renderer-agnostic segmentation hulls for this group."""
        return {self.group_label: self.convex_hull}


class DocumentPDF(Document):
    """Document renderer that writes one PDF page for each InkGen page."""

    @staticmethod
    def _iter_layer_groups(layer: Layer, *, sort: bool = False) -> tuple[ComponentGroup, ...]:
        """Return every stored group in a layer, including repeated labels."""
        groups = tuple(layer._component_groups.values())
        if sort:
            return tuple(sorted(groups, key=lambda group: (group.group_label, group.group_id)))
        return groups

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
            for group in self._iter_layer_groups(layer):
                ensure_pdf_group(
                    group,
                    ComponentGroupPDF,
                    message="DocumentPDF pages must contain ComponentGroupPDF groups.",
                )
                operators.append(group.generate_pdf(context))
        operators.append("Q")
        return "\n".join(operators)

    def extraction_truth(self) -> list[dict[str, object]]:
        """Emit semantic extraction truth in rendered PDF point coordinates."""
        records = extraction_records_for_annotated_target(
            self,
            page=0,
            canvas_height=self._canvas.height,
        )
        for page_number in range(1, self.pages + 1):
            page = self.page(page_number)
            for layer_name in sorted(page.layers):
                layer = page.layer(layer_name)
                for group in self._iter_layer_groups(layer, sort=True):
                    records.extend(
                        extraction_records_for_annotated_target(
                            group,
                            page=page_number,
                            canvas_height=page._canvas.height,
                        )
                    )
                    for component in group.components():
                        records.extend(
                            extraction_records_for_annotated_target(
                                component,
                                page=page_number,
                                canvas_height=page._canvas.height,
                            )
                        )
        return [record.to_dict() for record in sort_extraction_truth_records(records)]

    def extraction_truth_json(self) -> str:
        """Serialize this document's extraction truth to deterministic JSON."""
        return extraction_truth_json(self.extraction_truth())

    def grammar_truth(self) -> list[dict[str, object]]:
        """Emit grammar cue and construct truth in rendered PDF point coordinates."""
        records = grammar_records_for_annotated_target(
            self,
            page=0,
            canvas_height=self._canvas.height,
        )
        for page_number in range(1, self.pages + 1):
            page = self.page(page_number)
            for layer_name in sorted(page.layers):
                layer = page.layer(layer_name)
                for group in self._iter_layer_groups(layer, sort=True):
                    records.extend(
                        grammar_records_for_annotated_target(
                            group,
                            page=page_number,
                            canvas_height=page._canvas.height,
                        )
                    )
                    for component in group.components():
                        records.extend(
                            grammar_records_for_annotated_target(
                                component,
                                page=page_number,
                                canvas_height=page._canvas.height,
                            )
                        )
        return [record.to_dict() for record in sort_grammar_truth_records(records)]

    def grammar_truth_json(self) -> str:
        """Serialize this document's grammar truth to deterministic JSON."""
        return grammar_truth_json(self.grammar_truth())

    @classmethod
    def create_from_dict(cls, data: dict, styles: dict | None = None) -> DocumentPDF:
        """Recreate a DocumentPDF from serialized parameters."""
        if styles is None:
            styles = {}
        payload = data["DocumentPDF"]
        document = cls(Canvas.create_from_dict(payload["canvas"]))
        restore_extraction_truth_annotations(document, payload.get("extraction_truth", []))
        restore_grammar_truth_annotations(document, payload.get("grammar_truth", []))
        for page_payload in payload["pages"]:
            page = _layers_pdf_from_dict(page_payload, styles)
            document.add_page(position=-1, page=page)
        return document

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized document information."""
        document_payload: dict[str, object] = {
            "canvas": self._canvas.parameters,
            "pages": [self.page(page).parameters for page in list(self._pages.keys())],
        }
        annotations = serialize_extraction_truth_annotations(self)
        if annotations:
            document_payload["extraction_truth"] = annotations
        grammar_annotations = serialize_grammar_truth_annotations(self)
        if grammar_annotations:
            document_payload["grammar_truth"] = grammar_annotations
        return {"DocumentPDF": document_payload}


def _layer_pdf_from_dict(data: dict, styles: dict[str, object]) -> Layer:
    """Recreate a Layer containing ComponentGroupPDF instances."""
    payload = data["Layer"]
    layer = Layer(payload["layer_name"], Canvas.create_from_dict(payload["canvas"]), payload["model"])
    for group_payload in payload["component_groups"]:
        group = ComponentGroupPDF.create_from_dict(group_payload, styles)
        settings = payload["group_collision_settings"].get(group.group_label, {})
        layer.add_component_group(group, settings.get("allow_collision", True), settings.get("strict", False))
    return layer


def _layers_pdf_from_dict(data: dict, styles: dict[str, object]) -> Layers:
    """Recreate a Layers page containing PDF component groups."""
    payload = data["Layers"]
    layers = Layers(Canvas.create_from_dict(payload["canvas"]))
    if "base" in layers.layers:
        layers.remove_layer("base")
    for _, layer_payload in payload["layers"].items():
        layer = _layer_pdf_from_dict(layer_payload, styles)
        layers.add_layer(layer=layer)
    return layers
