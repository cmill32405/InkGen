"""Dependency-free DXF export for renderer-neutral drawing recipes."""

from __future__ import annotations

import os
from dataclasses import dataclass

from InkGen.drawing_components import (
    ArcDrawing,
    CircleDrawing,
    CubicBezierDrawing,
    DrawingComponentGroup,
    LineDrawing,
    OutputFormat,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
)


@dataclass(frozen=True)
class DXFRenderContext:
    """Settings for materializing InkGen coordinates into DXF entities."""

    canvas_height: float | None = None
    layer: str = "0"

    def point(self, x: float, y: float) -> tuple[float, float]:
        """Convert an InkGen point to DXF coordinates."""
        if self.canvas_height is None:
            return float(x), float(y)
        return float(x), float(self.canvas_height - y)


class DXFDocument:
    """ASCII DXF document assembled from neutral drawing groups."""

    def __init__(self, *, canvas_height: float | None = None) -> None:
        """Create an empty DXF document."""
        self._canvas_height = canvas_height
        self._entities: list[str] = []

    def add_group(self, group: DrawingComponentGroup, *, layer: str | None = None) -> None:
        """Append all supported entities from a neutral drawing group."""
        if not isinstance(group, DrawingComponentGroup):
            raise TypeError("group must be a DrawingComponentGroup")
        context = DXFRenderContext(canvas_height=self._canvas_height, layer=layer or group.group_label or "0")
        for component in group.components:
            self._entities.extend(_component_to_entities(component, context))

    def to_dxf_string(self) -> str:
        """Serialize this document as ASCII DXF."""
        lines = [
            "0",
            "SECTION",
            "2",
            "HEADER",
            "9",
            "$ACADVER",
            "1",
            "AC1015",
            "0",
            "ENDSEC",
            "0",
            "SECTION",
            "2",
            "ENTITIES",
        ]
        for entity in self._entities:
            lines.extend(entity.splitlines())
        lines.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(lines) + "\n"

    def create_dxf(self, filepath: str) -> None:
        """Write this document to a DXF file."""
        path = os.path.abspath(filepath)
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            raise ValueError("The file path does not exist.")
        with open(path, "w", encoding="ascii") as handle:
            handle.write(self.to_dxf_string())


def _component_to_entities(component: object, context: DXFRenderContext) -> list[str]:
    if isinstance(component, LineDrawing):
        return [_line_entity(component.point_1, component.point_2, context)]
    if isinstance(component, RectangleDrawing):
        x, y = component.position
        x2 = x + component.width
        y2 = y + component.height
        points = [(x, y), (x2, y), (x2, y2), (x, y2)]
        return [_lwpolyline_entity(points, context, closed=True)]
    if isinstance(component, CircleDrawing):
        return [_circle_entity(component, context)]
    if isinstance(component, PolygonalDrawing):
        return [_lwpolyline_entity(component.points, context, closed=True)]
    if isinstance(component, RegularPolygonDrawing):
        concrete = component.to_component(OutputFormat.PDF)
        return [_lwpolyline_entity(concrete.points, context, closed=True)]
    if isinstance(component, (ArcDrawing, QuadraticBezierDrawing, CubicBezierDrawing)):
        concrete = component.to_component(OutputFormat.PDF)
        return [_lwpolyline_entity(concrete.points, context, closed=False)]
    if isinstance(component, PathDrawing):
        concrete = component.to_component(OutputFormat.PDF)
        closed = bool(component.commands and component.commands[-1].type.upper() == "Z")
        return [_lwpolyline_entity(concrete.points, context, closed=closed)]
    if isinstance(component, TextDrawing):
        return [_text_entity(component, context)]
    raise TypeError(f"Unsupported DXF component: {component.__class__.__name__}")


def _line_entity(point_1: tuple[float, float], point_2: tuple[float, float], context: DXFRenderContext) -> str:
    x1, y1 = context.point(point_1[0], point_1[1])
    x2, y2 = context.point(point_2[0], point_2[1])
    return _pairs(
        [
            (0, "LINE"),
            (8, context.layer),
            (10, x1),
            (20, y1),
            (30, 0.0),
            (11, x2),
            (21, y2),
            (31, 0.0),
        ]
    )


def _lwpolyline_entity(points: list[tuple[float, float]], context: DXFRenderContext, *, closed: bool) -> str:
    pairs: list[tuple[int, object]] = [
        (0, "LWPOLYLINE"),
        (8, context.layer),
        (90, len(points)),
        (70, 1 if closed else 0),
    ]
    for x, y in points:
        dxf_x, dxf_y = context.point(x, y)
        pairs.append((10, dxf_x))
        pairs.append((20, dxf_y))
    return _pairs(pairs)


def _text_entity(component: TextDrawing, context: DXFRenderContext) -> str:
    x, y = context.point(component.position[0], component.position[1])
    height = float(component.style.font.size) * 25.4 / 72.0
    return _pairs(
        [
            (0, "TEXT"),
            (8, context.layer),
            (10, x),
            (20, y),
            (30, 0.0),
            (40, height),
            (1, component.text.replace("\n", " ")),
        ]
    )


def _circle_entity(component: CircleDrawing, context: DXFRenderContext) -> str:
    x, y = context.point(component.position[0], component.position[1])
    return _pairs(
        [
            (0, "CIRCLE"),
            (8, context.layer),
            (10, x),
            (20, y),
            (30, 0.0),
            (40, component.radius),
        ]
    )


def _pairs(pairs: list[tuple[int, object]]) -> str:
    lines: list[str] = []
    for code, value in pairs:
        lines.append(str(code))
        lines.append(_format_value(value))
    return "\n".join(lines)


def _format_value(value: object) -> str:
    if isinstance(value, float):
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)
