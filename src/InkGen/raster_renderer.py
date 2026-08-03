"""RASTER-RENDERER-P1 dependency-free rendering of neutral drawing groups."""

from __future__ import annotations

import io
import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from InkGen.baird import BairdDegradationResult, BairdParams, baird_degrade_asset
from InkGen.boundary import Canvas
from InkGen.component import Arc as SampledArc
from InkGen.component import CubicBezier as SampledCubicBezier
from InkGen.component import PathCommand
from InkGen.component import QuadraticBezier as SampledQuadraticBezier
from InkGen.drawing_components import (
    ArcDrawing,
    CircleDrawing,
    CubicBezierDrawing,
    DrawingComponentGroup,
    ImageDrawing,
    LineDrawing,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
)
from InkGen.image_assets import RasterImageAsset
from InkGen.style import DrawingStyle, TextStyle

log = logging.getLogger(__name__)

_INCH_MILLIMETERS = 25.4
_MAX_SUPERSAMPLED_PIXELS = 64_000_000
_MAX_SUPERSAMPLE = 8
_RENDERER_NAME = "inkgen-raster-v1"

RasterPrimitive = (
    RectangleDrawing
    | LineDrawing
    | CircleDrawing
    | ArcDrawing
    | PathDrawing
    | PolygonalDrawing
    | RegularPolygonDrawing
    | ImageDrawing
    | QuadraticBezierDrawing
    | CubicBezierDrawing
    | TextDrawing
)


@dataclass(frozen=True, slots=True)
class RasterRenderResult:
    """A rendered PNG asset and deterministic rasterization provenance."""

    asset: RasterImageAsset
    canvas_width: float
    canvas_height: float
    canvas_units: str
    dpi: float
    supersample: int
    background_rgba: tuple[int, int, int, int] | None
    component_count: int

    @property
    def manifest(self) -> dict[str, object]:
        """Return a stable serialization-friendly rendering manifest."""
        return {
            "renderer": _RENDERER_NAME,
            "canvas": {
                "width": self.canvas_width,
                "height": self.canvas_height,
                "units": self.canvas_units,
            },
            "dpi": self.dpi,
            "supersample": self.supersample,
            "background_rgba": list(self.background_rgba) if self.background_rgba is not None else None,
            "output_pixels": [self.asset.width, self.asset.height],
            "component_count": self.component_count,
        }


@dataclass(frozen=True, slots=True)
class RasterBairdResult:
    """A clean raster render paired with its Baird-degraded scan."""

    clean: RasterRenderResult
    degraded: BairdDegradationResult

    def __post_init__(self) -> None:
        """Reject invalid result envelopes at the public boundary."""
        if not isinstance(self.clean, RasterRenderResult):
            raise TypeError("clean must be a RasterRenderResult")
        if not isinstance(self.degraded, BairdDegradationResult):
            raise TypeError("degraded must be a BairdDegradationResult")

    @property
    def manifest(self) -> dict[str, object]:
        """Return the complete render and degradation provenance."""
        return {
            "render": self.clean.manifest,
            "degradation": self.degraded.manifest,
        }


def render_drawing_group(
    group: DrawingComponentGroup,
    canvas: Canvas,
    *,
    dpi: float = 300.0,
    supersample: int = 2,
    background_rgba: tuple[int, int, int, int] | None = None,
    source: str | None = None,
) -> RasterRenderResult:
    """Render a supported neutral drawing group to a deterministic RGBA PNG.

    Geometry uses the canvas's top-left, y-down coordinate system. Transparent
    output remains transparent unless the caller supplies ``background_rgba``.
    P1 supports rectangles without rounded corners or gradients, solid lines,
    circles, polygons without rounded corners, and raster images. Later closed
    slices add supported curve and text domains.
    """
    components = _validated_components(group)
    if not isinstance(canvas, Canvas):
        raise TypeError("canvas must be a Canvas")
    normalized_dpi = _positive_finite_number(dpi, "dpi")
    normalized_supersample = _validated_supersample(supersample)
    background = _validated_background(background_rgba)
    pixels_per_unit = normalized_dpi if canvas.units == "in" else normalized_dpi / _INCH_MILLIMETERS
    output_width = max(1, round(canvas.width * pixels_per_unit))
    output_height = max(1, round(canvas.height * pixels_per_unit))
    high_width = output_width * normalized_supersample
    high_height = output_height * normalized_supersample
    if high_width * high_height > _MAX_SUPERSAMPLED_PIXELS:
        raise ValueError(f"canvas, dpi, and supersample exceed the {_MAX_SUPERSAMPLED_PIXELS:,}-pixel supersampled limit")

    _validate_render_domain(components)
    high_scale = pixels_per_unit * normalized_supersample
    points_scale = normalized_dpi * normalized_supersample / 72.0
    initial = background if background is not None else (0, 0, 0, 0)
    surface = Image.new("RGBA", (high_width, high_height), initial)
    log.debug(
        "Rendering %d neutral components to %dx%d RGBA pixels at %.3f dpi",
        len(components),
        output_width,
        output_height,
        normalized_dpi,
    )
    for component in components:
        layer = Image.new("RGBA", surface.size, (0, 0, 0, 0))
        _render_component(layer, component, high_scale, points_scale=points_scale)
        surface = Image.alpha_composite(surface, layer)

    if normalized_supersample != 1:
        surface = surface.resize((output_width, output_height), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    surface.save(output, format="PNG", optimize=False)
    asset = RasterImageAsset.from_bytes(output.getvalue(), source=source)
    return RasterRenderResult(
        asset=asset,
        canvas_width=float(canvas.width),
        canvas_height=float(canvas.height),
        canvas_units=canvas.units,
        dpi=normalized_dpi,
        supersample=normalized_supersample,
        background_rgba=background,
        component_count=len(components),
    )


def render_and_degrade_drawing_group(
    group: DrawingComponentGroup,
    canvas: Canvas,
    params: BairdParams,
    *,
    seed: int,
    background_rgb: tuple[int, int, int],
    dpi: float = 300.0,
    render_supersample: int = 2,
    source: str | None = None,
) -> RasterBairdResult:
    """Render neutral drawings and apply Baird degradation without PDF or SVG.

    The clean result remains transparent RGBA. ``background_rgb`` names the
    physical substrate used only when converting that clean asset into Baird's
    opaque scan domain.
    """
    clean = render_drawing_group(
        group,
        canvas,
        dpi=dpi,
        supersample=render_supersample,
        background_rgba=None,
        source=source,
    )
    degraded = baird_degrade_asset(
        clean.asset,
        params,
        seed=seed,
        background_rgb=background_rgb,
        source=source,
    )
    return RasterBairdResult(clean, degraded)


def _validated_components(group: object) -> list[RasterPrimitive]:
    if not isinstance(group, DrawingComponentGroup):
        raise TypeError("group must be a DrawingComponentGroup")
    if isinstance(group.components, (str, bytes)) or not isinstance(group.components, Sequence):
        raise TypeError("components must be a sequence of drawing primitives")
    components = list(group.components)
    for component in components:
        if not callable(getattr(component, "to_component", None)):
            raise TypeError("component must implement to_component(output_format)")
        if not isinstance(
            component,
            (
                RectangleDrawing,
                LineDrawing,
                CircleDrawing,
                ArcDrawing,
                PathDrawing,
                PolygonalDrawing,
                RegularPolygonDrawing,
                ImageDrawing,
                QuadraticBezierDrawing,
                CubicBezierDrawing,
                TextDrawing,
            ),
        ):
            raise ValueError(f"unsupported raster primitive: {component.__class__.__name__}")
    return components


def _positive_finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if number <= 0.0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def _validated_supersample(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("supersample must be an integer")
    if not 1 <= value <= _MAX_SUPERSAMPLE:
        raise ValueError(f"supersample must be between 1 and {_MAX_SUPERSAMPLE}")
    return value


def _validated_background(value: object) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("background_rgba must contain four integer channels")
    if len(value) != 4:
        raise ValueError("background_rgba must contain four integer channels")
    channels: list[int] = []
    for channel in value:
        if isinstance(channel, bool) or not isinstance(channel, int):
            raise TypeError("background_rgba channels must be integers")
        if not 0 <= channel <= 255:
            raise ValueError("background_rgba channels must be between zero and 255")
        channels.append(channel)
    return channels[0], channels[1], channels[2], channels[3]


def _validate_render_domain(components: Sequence[RasterPrimitive]) -> None:
    for component in components:
        if isinstance(component, RectangleDrawing):
            radii = component.corner_radii
            if (isinstance(radii, tuple) and radii != (0.0, 0.0)) or (not isinstance(radii, tuple) and radii != 0.0):
                raise ValueError("rounded rectangles are not supported by raster renderer P1")
            if component.fill_gradient is not None:
                raise ValueError("rectangle gradients are not supported by raster renderer P1")
        if isinstance(component, RegularPolygonDrawing) and component.corner_radius != 0.0:
            raise ValueError("rounded regular polygons are not supported by raster renderer P1")
        if isinstance(component, TextDrawing):
            if "\n" in component.text or "\r" in component.text:
                raise ValueError("multiline text is not supported by raster renderer P3")
            if component.style.character_spacing != 0.0:
                raise ValueError("text character spacing is not supported by raster renderer P3")
            if component.style.superscript:
                raise ValueError("text superscript is not supported by raster renderer P3")
            if component.style.subscript:
                raise ValueError("text subscript is not supported by raster renderer P3")
        if isinstance(component, PathDrawing):
            if component.style.fill != "none" and component.style.fill_opacity != 0.0:
                raise ValueError("path fills are not supported by raster renderer P5")
            _linear_path_subpaths(component)
        style = getattr(component, "style", None)
        if isinstance(style, DrawingStyle):
            if isinstance(component, ArcDrawing) and style.fill != "none" and style.fill_opacity != 0.0:
                raise ValueError("arc fills are not supported by raster renderer P4")
            if isinstance(component, (QuadraticBezierDrawing, CubicBezierDrawing)) and style.fill != "none" and style.fill_opacity != 0.0:
                raise ValueError("curve fills are not supported by raster renderer P2")
            if style.stroke_dasharray:
                raise ValueError("dashed strokes are not supported by raster renderer P1")
            if style.stroke_dash_offset != 0.0:
                raise ValueError("stroke dash offsets are not supported by raster renderer P1")
            if style.stroke_linecap != "butt":
                raise ValueError("only butt stroke caps are supported by raster renderer P1")
            if style.stroke_linejoin != "miter":
                raise ValueError("only miter stroke joins are supported by raster renderer P1")
            if style.stroke_miterlimit != 10.0:
                raise ValueError("nondefault stroke miter limits are not supported by raster renderer P1")


def _render_component(
    surface: Image.Image,
    component: RasterPrimitive,
    scale: float,
    *,
    points_scale: float | None = None,
) -> None:
    if isinstance(component, ImageDrawing):
        _render_image(surface, component, scale)
        return
    if isinstance(component, TextDrawing):
        if points_scale is None:
            raise ValueError("points_scale is required to render text")
        _render_text(surface, component, scale, points_scale)
        return
    draw = ImageDraw.Draw(surface)
    style = component.style
    fill = _style_color(style.fill, style.fill_opacity)
    stroke = _style_color(style.stroke, style.stroke_opacity) if style.stroke_width > 0.0 else None
    stroke_width = max(1, round(style.stroke_width * scale)) if stroke is not None else 0
    if isinstance(component, RectangleDrawing):
        x, y = component.position
        box = _scaled_box(x, y, x + component.width, y + component.height, scale)
        draw.rectangle(box, fill=fill, outline=stroke, width=stroke_width)
    elif isinstance(component, LineDrawing):
        if stroke is not None:
            draw.line([_scaled_point(component.point_1, scale), _scaled_point(component.point_2, scale)], fill=stroke, width=stroke_width)
    elif isinstance(component, CircleDrawing):
        x, y = component.position
        radius = component.radius
        draw.ellipse(_scaled_box(x - radius, y - radius, x + radius, y + radius, scale), fill=fill, outline=stroke, width=stroke_width)
    elif isinstance(component, ArcDrawing):
        if stroke is not None:
            points = SampledArc(
                component.center,
                component.radius_x,
                component.radius_y,
                component.start_angle,
                component.end_angle,
                style,
                component.rotation,
            ).points
            _draw_curve(draw, points, scale, stroke, stroke_width)
    elif isinstance(component, PathDrawing):
        if stroke is not None:
            for subpath in _linear_path_subpaths(component):
                _draw_curve(draw, subpath, scale, stroke, stroke_width)
    elif isinstance(component, PolygonalDrawing):
        _draw_polygon(draw, component.points, scale, fill, stroke, stroke_width)
    elif isinstance(component, QuadraticBezierDrawing):
        if stroke is not None:
            points = SampledQuadraticBezier(
                component.start_point,
                component.control_point,
                component.end_point,
                style,
            ).points
            _draw_curve(draw, points, scale, stroke, stroke_width)
    elif isinstance(component, CubicBezierDrawing):
        if stroke is not None:
            points = SampledCubicBezier(
                component.start_point,
                component.control_point1,
                component.control_point2,
                component.end_point,
                style,
            ).points
            _draw_curve(draw, points, scale, stroke, stroke_width)
    else:
        # The validated RasterPrimitive union leaves only RegularPolygonDrawing.
        points = [
            (
                component.position[0] + component.radius * math.cos(math.radians(component.angle + 90.0 + index * 360.0 / component.sides)),
                component.position[1] + component.radius * math.sin(math.radians(component.angle + 90.0 + index * 360.0 / component.sides)),
            )
            for index in range(component.sides)
        ]
        _draw_polygon(draw, points, scale, fill, stroke, stroke_width)


def _linear_path_subpaths(component: PathDrawing) -> list[list[tuple[float, float]]]:
    """Validate and expand the closed P5 M/L/H/V/Z command domain."""
    commands = component.commands
    if commands is None:
        return []
    if isinstance(commands, (str, bytes)) or not isinstance(commands, Sequence):
        raise TypeError("PathDrawing commands must be a sequence of PathCommand objects")

    subpaths: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] | None = None
    for command in commands:
        if not isinstance(command, PathCommand):
            raise TypeError("PathDrawing commands must contain only PathCommand objects")
        command_type = command.type
        points = command.points
        if command_type not in {"M", "L", "H", "V", "Z"}:
            raise ValueError(f"path command {command_type} is not supported by raster renderer P5")
        if command_type == "M":
            if len(points) != 1:
                raise ValueError("path command M requires exactly one point")
            if current is not None:
                subpaths.append(current)
            current = [points[0]]
            continue
        if current is None:
            message = "new subpath must begin with M" if subpaths else "path must begin with M"
            raise ValueError(message)
        if command_type == "Z":
            if points:
                raise ValueError("path command Z does not accept points")
            if len(current) > 1:
                current.append(current[0])
            subpaths.append(current)
            current = None
            continue
        if not points:
            raise ValueError(f"path command {command_type} requires at least one point")
        if command_type == "L":
            current.extend(points)
        elif command_type == "H":
            current.extend((point[0], current[-1][1]) for point in points)
        else:
            current.extend((current[-1][0], point[1]) for point in points)

    if current is not None:
        subpaths.append(current)
    return subpaths


def _draw_curve(
    draw: ImageDraw.ImageDraw,
    points: Sequence[tuple[float, float]],
    scale: float,
    stroke: tuple[int, int, int, int],
    stroke_width: int,
) -> None:
    """Draw the established sampled curve as a supersampled polyline."""
    if len(points) < 2:
        return
    draw.line([_scaled_point(point, scale) for point in points], fill=stroke, width=stroke_width)


def _draw_polygon(
    draw: ImageDraw.ImageDraw,
    points: Sequence[tuple[float, float]],
    scale: float,
    fill: tuple[int, int, int, int] | None,
    stroke: tuple[int, int, int, int] | None,
    stroke_width: int,
) -> None:
    scaled = [_scaled_point(point, scale) for point in points]
    if fill is not None:
        draw.polygon(scaled, fill=fill)
    if stroke is not None:
        draw.line([*scaled, scaled[0]], fill=stroke, width=stroke_width)


def _render_image(surface: Image.Image, component: ImageDrawing, scale: float) -> None:
    width = max(1, round(component.width * scale))
    height = max(1, round(component.height * scale))
    with component.image.image() as decoded:
        resized = decoded.convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
    position = _scaled_point(component.position, scale)
    surface.alpha_composite(resized, dest=position)


def _render_text(surface: Image.Image, component: TextDrawing, scale: float, points_scale: float) -> None:
    style: TextStyle = component.style
    color = _style_color(style.color, 1.0)
    if not component.text or not style.visible or color is None:
        return
    font_size = max(1, round(style.font.size * points_scale))
    try:
        font = ImageFont.truetype(style.font.font_file, font_size)
    except (OSError, ValueError) as exc:
        raise ValueError("raster text font could not be loaded") from exc
    anchor = {"start": "ls", "center": "ms", "end": "rs"}[style.text_align]
    ImageDraw.Draw(surface).text(
        _scaled_point(component.position, scale),
        component.text,
        font=font,
        fill=color,
        anchor=anchor,
    )


def _style_color(color: str, opacity: float) -> tuple[int, int, int, int] | None:
    if color == "none" or opacity == 0.0:
        return None
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16), round(opacity * 255.0)


def _scaled_point(point: tuple[float, float], scale: float) -> tuple[int, int]:
    return round(point[0] * scale), round(point[1] * scale)


def _scaled_box(left: float, top: float, right: float, bottom: float, scale: float) -> tuple[int, int, int, int]:
    return round(left * scale), round(top * scale), round(right * scale), round(bottom * scale)
