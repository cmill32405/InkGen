"""Dependency-free DXF export for renderer-neutral drawing recipes."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from hashlib import sha256

from InkGen.component import normalize_rectangle_corner_radii
from InkGen.drawing_components import (
    ArcDrawing,
    CircleDrawing,
    CubicBezierDrawing,
    DrawingComponentGroup,
    ImageDrawing,
    LineDrawing,
    OutputFormat,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
)
from InkGen.image_assets import RasterImageAsset

ROUNDED_RECTANGLE_CORNER_SEGMENTS = 4


@dataclass(frozen=True)
class DXFRenderContext:
    """Settings for materializing InkGen coordinates into DXF entities."""

    canvas_height: float | None = None
    layer: str = "0"

    def __post_init__(self) -> None:
        """Validate the optional canvas height used for y-axis conversion."""
        if self.canvas_height is not None:
            object.__setattr__(
                self,
                "canvas_height",
                _coerce_finite_float(self.canvas_height, name="canvas_height", minimum=0.0),
            )
        object.__setattr__(self, "layer", _coerce_dxf_layer(self.layer, name="layer"))

    def point(self, x: float, y: float) -> tuple[float, float]:
        """Convert an InkGen point to DXF coordinates."""
        dxf_x = _coerce_finite_float(x, name="x")
        source_y = _coerce_finite_float(y, name="y")
        if self.canvas_height is None:
            return dxf_x, source_y
        return dxf_x, float(self.canvas_height - source_y)


def _coerce_finite_float(value: object, *, name: str, minimum: float | None = None) -> float:
    """Return a finite float and reject booleans or malformed numeric values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} must be greater than or equal to {minimum}.")
    return number


def _coerce_dxf_layer(value: object, *, name: str) -> str:
    """Return a DXF layer name and reject values that would be stringified."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    return value


class DXFDocument:
    """ASCII DXF document assembled from neutral drawing groups."""

    def __init__(self, *, canvas_height: float | None = None) -> None:
        """Create an empty DXF document."""
        self._canvas_height = None if canvas_height is None else _coerce_finite_float(canvas_height, name="canvas_height", minimum=0.0)
        self._entities: list[str] = []
        self._image_registry = _DXFImageRegistry()

    def add_group(self, group: DrawingComponentGroup, *, layer: str | None = None) -> None:
        """Append all supported entities from a neutral drawing group."""
        if not isinstance(group, DrawingComponentGroup):
            raise TypeError("group must be a DrawingComponentGroup")
        if layer is not None:
            layer = _coerce_dxf_layer(layer, name="layer")
        context = DXFRenderContext(canvas_height=self._canvas_height, layer=layer or group.group_label or "0")
        for component in group.components:
            self._entities.extend(_component_to_entities(component, context, image_registry=self._image_registry))

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
        if self._image_registry.definitions():
            lines[-2:-2] = _dxf_objects_section(self._image_registry).splitlines()
        return "\n".join(lines) + "\n"

    def create_dxf(self, filepath: str | os.PathLike[str]) -> None:
        """Write this document to a DXF file."""
        path = _normalize_output_filepath(filepath)
        self._image_registry.write_sidecars(os.path.dirname(path) or os.curdir)
        with open(path, "w", encoding="ascii") as handle:
            handle.write(self.to_dxf_string())


def _normalize_output_filepath(filepath: object) -> str:
    """Return an absolute output path or fail at the DXF writer boundary."""
    try:
        path_value = os.fspath(filepath)
    except TypeError as exc:
        raise TypeError("file path must be a string or path-like object") from exc
    if not isinstance(path_value, str):
        raise TypeError("file path must be a string or path-like object")
    if not path_value:
        raise ValueError("file path must not be empty")
    path = os.path.abspath(path_value)
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        raise ValueError("The file path does not exist.")
    return path


@dataclass(frozen=True)
class _DXFImageDefinition:
    """External image definition referenced by DXF IMAGE entities."""

    handle: str
    filename: str
    data: bytes
    width: int
    height: int


class _DXFImageRegistry:
    """Deterministic registry for DXF external image references."""

    def __init__(self) -> None:
        self._definition_by_digest: dict[str, _DXFImageDefinition] = {}

    def register(self, image: RasterImageAsset) -> _DXFImageDefinition:
        """Register an EXIF-normalized PNG sidecar image for DXF reference."""
        data = image.png_bytes()
        digest = sha256(data).hexdigest()
        if digest not in self._definition_by_digest:
            index = len(self._definition_by_digest) + 1
            self._definition_by_digest[digest] = _DXFImageDefinition(
                handle=f"{0x100 + index:X}",
                filename=f"image{index}.png",
                data=data,
                width=image.width,
                height=image.height,
            )
        return self._definition_by_digest[digest]

    def definitions(self) -> tuple[_DXFImageDefinition, ...]:
        """Return registered image definitions in deterministic insertion order."""
        return tuple(self._definition_by_digest.values())

    def write_sidecars(self, directory: str) -> None:
        """Write registered sidecar images to a DXF output directory."""
        for definition in self.definitions():
            path = os.path.join(directory, definition.filename)
            with open(path, "wb") as handle:
                handle.write(definition.data)


def _component_to_entities(
    component: object,
    context: DXFRenderContext,
    image_registry: _DXFImageRegistry | None = None,
) -> list[str]:
    if isinstance(component, LineDrawing):
        return [_line_entity(component.point_1, component.point_2, context)]
    if isinstance(component, RectangleDrawing):
        points = _rectangle_points(component)
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
    if isinstance(component, ImageDrawing):
        if image_registry is None:
            image_registry = _DXFImageRegistry()
        definition = image_registry.register(component.image)
        return [_image_entity(component, definition, context)]
    raise TypeError(f"Unsupported DXF component: {component.__class__.__name__}")


def _rectangle_points(component: RectangleDrawing) -> list[tuple[float, float]]:
    """Return DXF polyline points for sharp or rounded rectangle drawings."""
    x, y = component.position
    width = component.width
    height = component.height
    right = x + width
    bottom = y + height
    rx, ry = normalize_rectangle_corner_radii(component.corner_radii, width, height)
    if rx == 0.0 or ry == 0.0:
        return [(x, y), (right, y), (right, bottom), (x, bottom)]

    points: list[tuple[float, float]] = []

    def append(point: tuple[float, float]) -> None:
        rounded = (round(float(point[0]), 6), round(float(point[1]), 6))
        if not points or points[-1] != rounded:
            points.append(rounded)

    append((x + rx, y))
    append((right - rx, y))
    _append_corner_arc(points, center=(right - rx, y + ry), rx=rx, ry=ry, start_degrees=-90.0, end_degrees=0.0)
    append((right, bottom - ry))
    _append_corner_arc(points, center=(right - rx, bottom - ry), rx=rx, ry=ry, start_degrees=0.0, end_degrees=90.0)
    append((x + rx, bottom))
    _append_corner_arc(points, center=(x + rx, bottom - ry), rx=rx, ry=ry, start_degrees=90.0, end_degrees=180.0)
    append((x, y + ry))
    _append_corner_arc(points, center=(x + rx, y + ry), rx=rx, ry=ry, start_degrees=180.0, end_degrees=270.0)
    if points[-1] == points[0]:
        points.pop()
    return points


def _append_corner_arc(
    points: list[tuple[float, float]], *, center: tuple[float, float], rx: float, ry: float, start_degrees: float, end_degrees: float
) -> None:
    """Append sampled elliptical arc points for a rounded rectangle corner."""
    step = (end_degrees - start_degrees) / ROUNDED_RECTANGLE_CORNER_SEGMENTS
    for index in range(1, ROUNDED_RECTANGLE_CORNER_SEGMENTS + 1):
        angle = math.radians(start_degrees + (step * index))
        point = (
            round(center[0] + (rx * math.cos(angle)), 6),
            round(center[1] + (ry * math.sin(angle)), 6),
        )
        if not points or points[-1] != point:
            points.append(point)


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


def _image_entity(component: ImageDrawing, definition: _DXFImageDefinition, context: DXFRenderContext) -> str:
    x, y = context.point(component.position[0], component.position[1])
    _, y_bottom = context.point(component.position[0], component.position[1] + component.height)
    v_height = y_bottom - y
    return _pairs(
        [
            (0, "IMAGE"),
            (8, context.layer),
            (100, "AcDbRasterImage"),
            (90, 0),
            (10, x),
            (20, y),
            (30, 0.0),
            (11, component.width),
            (21, 0.0),
            (31, 0.0),
            (12, 0.0),
            (22, v_height),
            (32, 0.0),
            (13, definition.width),
            (23, definition.height),
            (340, definition.handle),
            (70, 1),
            (280, 0),
            (281, 50),
        ]
    )


def _dxf_objects_section(image_registry: _DXFImageRegistry) -> str:
    pairs: list[tuple[int, object]] = [(0, "SECTION"), (2, "OBJECTS")]
    for definition in image_registry.definitions():
        pairs.extend(
            [
                (0, "IMAGEDEF"),
                (5, definition.handle),
                (100, "AcDbRasterImageDef"),
                (90, 0),
                (1, definition.filename),
                (10, definition.width),
                (20, definition.height),
                (11, 1.0),
                (21, 1.0),
                (280, 1),
                (281, 0),
            ]
        )
    pairs.extend([(0, "ENDSEC")])
    return _pairs(pairs)


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
