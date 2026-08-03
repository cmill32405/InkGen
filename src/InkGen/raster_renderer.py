"""RASTER-RENDERER-P1 dependency-free rendering of neutral drawing groups."""

from __future__ import annotations

import io
import logging
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from InkGen.baird import BairdDegradationResult, BairdParams, baird_degrade_asset
from InkGen.boundary import Canvas
from InkGen.component import (
    Arc as SampledArc,
)
from InkGen.component import (
    CubicBezier as SampledCubicBezier,
)
from InkGen.component import (
    PathCommand,
    normalize_rectangle_corner_radii,
    regular_polygon_corner_geometry,
    sample_rounded_polygon_path,
)
from InkGen.component import (
    QuadraticBezier as SampledQuadraticBezier,
)
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
from InkGen.gradients import LinearGradientFill, coerce_linear_gradient
from InkGen.image_assets import RasterImageAsset
from InkGen.style import DrawingStyle, TextStyle

log = logging.getLogger(__name__)

_INCH_MILLIMETERS = 25.4
_MAX_SUPERSAMPLED_PIXELS = 64_000_000
_MAX_SUPERSAMPLE = 8
_GRADIENT_TILE_PIXELS = 1_000_000
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
    P1 supports basic rectangles, solid lines, circles, polygons, and raster
    images. Later closed slices add curves, text, rounded corners, and
    rectangle gradients.
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

    high_scale = pixels_per_unit * normalized_supersample
    _validate_render_domain(components, high_scale)
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


def _validate_render_domain(components: Sequence[RasterPrimitive], scale: float) -> None:
    for component in components:
        if isinstance(component, RectangleDrawing):
            normalize_rectangle_corner_radii(component.corner_radii, component.width, component.height)
            _validated_raster_gradient(component, scale)
        if isinstance(component, RegularPolygonDrawing):
            validated = RegularPolygonDrawing(
                component.position,
                component.sides,
                component.radius,
                component.style,
                component.angle,
                component.corner_radius,
            )
            if validated.corner_radius > 0.0:
                regular_polygon_corner_geometry(_regular_polygon_points(validated), validated.corner_radius)
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
            _sampled_path_subpaths(component)
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
        rx, ry = normalize_rectangle_corner_radii(component.corner_radii, component.width, component.height)
        pixel_width = box[2] - box[0]
        pixel_height = box[3] - box[1]
        radius_x = min(pixel_width // 2, max(1, round(rx * scale))) if rx > 0.0 else 0
        radius_y = min(pixel_height // 2, max(1, round(ry * scale))) if ry > 0.0 else 0
        gradient_and_axis = _validated_raster_gradient(component, scale)
        if gradient_and_axis is not None:
            gradient, axis = gradient_and_axis
            _render_linear_gradient_rectangle(
                surface,
                box,
                radius_x,
                radius_y,
                gradient,
                axis,
                component.style.fill_opacity,
            )
            if radius_x == 0 or radius_y == 0:
                draw.rectangle(box, fill=None, outline=stroke, width=stroke_width)
            else:
                _draw_rounded_rectangle(
                    draw,
                    box,
                    radius_x,
                    radius_y,
                    fill=None,
                    stroke=stroke,
                    stroke_width=stroke_width,
                )
        elif radius_x == 0 or radius_y == 0:
            draw.rectangle(box, fill=fill, outline=stroke, width=stroke_width)
        else:
            _draw_rounded_rectangle(
                draw,
                box,
                radius_x,
                radius_y,
                fill=fill,
                stroke=stroke,
                stroke_width=stroke_width,
            )
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
            for subpath in _sampled_path_subpaths(component):
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
        points = _regular_polygon_points(component)
        if component.corner_radius > 0.0:
            points = sample_rounded_polygon_path(regular_polygon_corner_geometry(points, component.corner_radius))
        _draw_polygon(draw, points, scale, fill, stroke, stroke_width)


def _regular_polygon_points(component: RegularPolygonDrawing) -> list[tuple[float, float]]:
    """Return the established neutral regular-polygon vertex formula."""
    return [
        (
            component.position[0] + component.radius * math.cos(math.radians(component.angle + 90.0 + index * 360.0 / component.sides)),
            component.position[1] + component.radius * math.sin(math.radians(component.angle + 90.0 + index * 360.0 / component.sides)),
        )
        for index in range(component.sides)
    ]


def _reflect_path_control(
    control: tuple[float, float],
    current: tuple[float, float],
) -> tuple[float, float]:
    """Reflect a smooth path control around the current point."""
    return 2.0 * current[0] - control[0], 2.0 * current[1] - control[1]


def _coerce_path_arc_number(value: object, name: str) -> float:
    """Return a finite SVG endpoint-arc number."""
    if isinstance(value, bool):
        raise TypeError(f"path arc {name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"path arc {name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"path arc {name} must be finite")
    return number


def _coerce_path_arc_flag(value: object, name: str) -> int:
    """Return an SVG arc flag normalized to zero or one."""
    if isinstance(value, bool):
        return int(value)
    if not isinstance(value, int):
        raise TypeError(f"path arc {name} must be an integer flag")
    if value not in (0, 1):
        raise ValueError(f"path arc {name} must be 0 or 1")
    return value


def _path_arc_parameters(command: PathCommand) -> tuple[float, float, float, int, int]:
    """Validate live SVG endpoint-arc flags and return canonical parameters."""
    flags = getattr(command, "flags", {})
    if not isinstance(flags, Mapping):
        raise TypeError("path arc flags must be a mapping")
    radii = flags.get("radii", (0.0, 0.0))
    if isinstance(radii, (str, bytes)) or not isinstance(radii, Sequence):
        raise TypeError("path arc radii must be a two-value sequence")
    if len(radii) != 2:
        raise ValueError("path arc radii must contain exactly two values")
    radius_x = abs(_coerce_path_arc_number(radii[0], "radius"))
    radius_y = abs(_coerce_path_arc_number(radii[1], "radius"))
    rotation = _coerce_path_arc_number(flags.get("rotation", 0.0), "rotation")
    large_arc = _coerce_path_arc_flag(flags.get("large_arc", 0), "large_arc")
    sweep = _coerce_path_arc_flag(flags.get("sweep", 0), "sweep")
    return radius_x, radius_y, rotation, large_arc, sweep


def _sampled_svg_endpoint_arc(
    start: tuple[float, float],
    end: tuple[float, float],
    command: PathCommand,
    style: DrawingStyle,
) -> list[tuple[float, float]]:
    """Convert one SVG endpoint arc to the canonical sampled center form."""
    radius_x, radius_y, rotation, large_arc, sweep = _path_arc_parameters(command)
    if start == end:
        return [start]
    if radius_x == 0.0 or radius_y == 0.0:
        return [start, end]

    normalized_rotation = rotation % 360.0
    phi = math.radians(normalized_rotation)
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)
    half_dx = start[0] / 2.0 - end[0] / 2.0
    half_dy = start[1] / 2.0 - end[1] / 2.0
    transformed_x = cos_phi * half_dx + sin_phi * half_dy
    transformed_y = -sin_phi * half_dx + cos_phi * half_dy
    radius_scale = math.hypot(transformed_x / radius_x, transformed_y / radius_y)
    if not math.isfinite(radius_scale):
        raise ValueError("path arc geometry must remain finite during radius correction")
    if radius_scale > 1.0:
        radius_x *= radius_scale
        radius_y *= radius_scale

    normalized_x = transformed_x / radius_x
    normalized_y = transformed_y / radius_y
    normalized_square = normalized_x * normalized_x + normalized_y * normalized_y
    if normalized_square <= 0.0 or not math.isfinite(normalized_square):
        raise ValueError("path arc geometry must remain finite during center conversion")
    normalized_square = min(1.0, normalized_square)
    sign = -1.0 if large_arc == sweep else 1.0
    center_scale = sign * math.sqrt(max(0.0, (1.0 - normalized_square) / normalized_square))
    center_x_prime = center_scale * radius_x * normalized_y
    center_y_prime = -center_scale * radius_y * normalized_x
    center = (
        cos_phi * center_x_prime - sin_phi * center_y_prime + start[0] / 2.0 + end[0] / 2.0,
        sin_phi * center_x_prime + cos_phi * center_y_prime + start[1] / 2.0 + end[1] / 2.0,
    )
    if not all(math.isfinite(value) for value in center):
        raise ValueError("path arc geometry must remain finite during center conversion")

    start_vector = (
        (transformed_x - center_x_prime) / radius_x,
        (transformed_y - center_y_prime) / radius_y,
    )
    start_angle = math.atan2(start_vector[1], start_vector[0])
    small_span = 2.0 * math.asin(math.sqrt(normalized_square))
    span_magnitude = math.tau - small_span if large_arc else small_span
    delta_angle = span_magnitude if sweep else -span_magnitude

    sampled = SampledArc(
        center,
        radius_x,
        radius_y,
        math.degrees(start_angle),
        math.degrees(start_angle + delta_angle),
        style,
        normalized_rotation,
    ).points
    if len(sampled) == 1:
        return [start, end]
    sampled[0] = start
    sampled[-1] = end
    return sampled


def _sampled_path_subpaths(component: PathDrawing) -> list[list[tuple[float, float]]]:
    """Validate and sample the closed P5/P6/P7 stroke-path command domain."""
    commands = component.commands
    if commands is None:
        return []
    if isinstance(commands, (str, bytes)) or not isinstance(commands, Sequence):
        raise TypeError("PathDrawing commands must be a sequence of PathCommand objects")

    subpaths: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] | None = None
    previous_cubic_control: tuple[float, float] | None = None
    previous_quadratic_control: tuple[float, float] | None = None
    for command in commands:
        if not isinstance(command, PathCommand):
            raise TypeError("PathDrawing commands must contain only PathCommand objects")
        command_type = command.type
        points = command.points
        if command_type not in {"M", "L", "H", "V", "Z", "C", "S", "Q", "T", "A"}:
            raise ValueError(f"path command {command_type} is not supported by raster renderer P7")
        if command_type == "M":
            if len(points) != 1:
                raise ValueError("path command M requires exactly one point")
            if current is not None:
                subpaths.append(current)
            current = [points[0]]
            previous_cubic_control = None
            previous_quadratic_control = None
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
            previous_cubic_control = None
            previous_quadratic_control = None
            continue
        if command_type == "C" and len(points) % 3:
            raise ValueError("path command C requires points in groups of three")
        if command_type == "S" and len(points) % 2:
            raise ValueError("path command S requires points in groups of two")
        if command_type == "Q" and len(points) % 2:
            raise ValueError("path command Q requires points in groups of two")
        if command_type == "T" and not points:
            raise ValueError("path command T requires an endpoint")
        if command_type == "A" and not points:
            raise ValueError("path command A requires an endpoint")
        if command_type in {"L", "H", "V"} and not points:
            raise ValueError(f"path command {command_type} requires at least one point")
        if command_type == "L":
            current.extend(points)
            previous_cubic_control = None
            previous_quadratic_control = None
        elif command_type == "H":
            current.extend((point[0], current[-1][1]) for point in points)
            previous_cubic_control = None
            previous_quadratic_control = None
        elif command_type == "V":
            current.extend((current[-1][0], point[1]) for point in points)
            previous_cubic_control = None
            previous_quadratic_control = None
        elif command_type == "C":
            for index in range(0, len(points), 3):
                control_1, control_2, end = points[index : index + 3]
                sampled = SampledCubicBezier(current[-1], control_1, control_2, end, component.style).points
                current.extend(sampled[1:])
                previous_cubic_control = control_2
                previous_quadratic_control = None
        elif command_type == "S":
            for index in range(0, len(points), 2):
                control_2, end = points[index : index + 2]
                control_1 = (
                    _reflect_path_control(previous_cubic_control, current[-1]) if previous_cubic_control is not None else current[-1]
                )
                sampled = SampledCubicBezier(current[-1], control_1, control_2, end, component.style).points
                current.extend(sampled[1:])
                previous_cubic_control = control_2
                previous_quadratic_control = None
        elif command_type == "Q":
            for index in range(0, len(points), 2):
                control, end = points[index : index + 2]
                sampled = SampledQuadraticBezier(current[-1], control, end, component.style).points
                current.extend(sampled[1:])
                previous_cubic_control = None
                previous_quadratic_control = control
        elif command_type == "A":
            sampled = _sampled_svg_endpoint_arc(current[-1], points[-1], command, component.style)
            current.extend(sampled[1:])
            previous_cubic_control = None
            previous_quadratic_control = None
        else:
            for end in points:
                control = (
                    _reflect_path_control(previous_quadratic_control, current[-1])
                    if previous_quadratic_control is not None
                    else current[-1]
                )
                sampled = SampledQuadraticBezier(current[-1], control, end, component.style).points
                current.extend(sampled[1:])
                previous_cubic_control = None
                previous_quadratic_control = control

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


def _validated_raster_gradient(
    component: RectangleDrawing,
    scale: float,
) -> tuple[LinearGradientFill, tuple[float, float, float, float]] | None:
    """Return a live-validated gradient and its finite supersampled axis."""
    gradient = coerce_linear_gradient(component.fill_gradient)
    if gradient is None:
        return None
    raw_axis = gradient.axis_for_box(component.position, component.width, component.height)
    axis = (raw_axis[0] * scale, raw_axis[1] * scale, raw_axis[2] * scale, raw_axis[3] * scale)
    if not all(math.isfinite(value) for value in axis):
        raise ValueError("raster gradient axis must be finite")
    delta_x = axis[2] - axis[0]
    delta_y = axis[3] - axis[1]
    squared_length = delta_x * delta_x + delta_y * delta_y
    if not math.isfinite(squared_length):
        raise ValueError("raster gradient axis length must be finite")
    if squared_length <= 0.0:
        raise ValueError("raster gradient axis must have positive length")
    return gradient, axis


def _render_linear_gradient_rectangle(
    surface: Image.Image,
    box: tuple[int, int, int, int],
    radius_x: int,
    radius_y: int,
    gradient: LinearGradientFill,
    axis: tuple[float, float, float, float],
    opacity: float,
) -> None:
    """Paint a clipped N-stop linear gradient in bounded two-dimensional tiles."""
    alpha = round(opacity * 255.0)
    if alpha == 0:
        return
    left, top, right, bottom = box
    clip_left = max(0, left)
    clip_top = max(0, top)
    clip_right = min(surface.width - 1, right)
    clip_bottom = min(surface.height - 1, bottom)
    if clip_left > clip_right or clip_top > clip_bottom:
        return

    x1, y1, x2, y2 = axis
    delta_x = x2 - x1
    delta_y = y2 - y1
    squared_length = delta_x * delta_x + delta_y * delta_y
    stops = gradient.extended_stops()
    offsets = np.asarray([stop.offset for stop in stops], dtype=np.float64)
    colors = np.asarray(
        [[int(stop.color[index : index + 2], 16) for index in (1, 3, 5)] for stop in stops],
        dtype=np.float64,
    )

    tile_width_limit = max(1, _GRADIENT_TILE_PIXELS)
    for tile_left in range(clip_left, clip_right + 1, tile_width_limit):
        tile_right = min(clip_right + 1, tile_left + tile_width_limit)
        tile_width = tile_right - tile_left
        tile_height = max(1, _GRADIENT_TILE_PIXELS // tile_width)
        x_projection = ((np.arange(tile_left, tile_right, dtype=np.float64) + 0.5 - x1) * delta_x) / squared_length
        for tile_top in range(clip_top, clip_bottom + 1, tile_height):
            tile_bottom = min(clip_bottom + 1, tile_top + tile_height)
            y_projection = ((np.arange(tile_top, tile_bottom, dtype=np.float64) + 0.5 - y1) * delta_y) / squared_length
            positions = np.clip(y_projection[:, np.newaxis] + x_projection[np.newaxis, :], 0.0, 1.0)
            rgb = np.empty((tile_bottom - tile_top, tile_width, 3), dtype=np.uint8)
            for channel in range(3):
                rgb[:, :, channel] = np.rint(np.interp(positions, offsets, colors[:, channel])).astype(np.uint8)
            tile = Image.fromarray(rgb)
            mask = Image.new("L", tile.size, 0)
            mask_draw = ImageDraw.Draw(mask)
            local_box = (left - tile_left, top - tile_top, right - tile_left, bottom - tile_top)
            if radius_x == 0 or radius_y == 0:
                mask_draw.rectangle(local_box, fill=alpha)
            else:
                _draw_rounded_rectangle(
                    mask_draw,
                    local_box,
                    radius_x,
                    radius_y,
                    fill=alpha,
                    stroke=None,
                    stroke_width=0,
                )
            tile.putalpha(mask)
            surface.alpha_composite(tile, dest=(tile_left, tile_top))


def _draw_rounded_rectangle(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius_x: int,
    radius_y: int,
    *,
    fill: int | tuple[int, int, int, int] | None,
    stroke: int | tuple[int, int, int, int] | None,
    stroke_width: int,
) -> None:
    """Paint an axis-aligned rectangle with elliptical rounded corners."""
    left, top, right, bottom = box
    left_center = left + radius_x
    right_center = right - radius_x
    top_center = top + radius_y
    bottom_center = bottom - radius_y
    top_left = (left, top, left + 2 * radius_x, top + 2 * radius_y)
    top_right = (right - 2 * radius_x, top, right, top + 2 * radius_y)
    bottom_right = (right - 2 * radius_x, bottom - 2 * radius_y, right, bottom)
    bottom_left = (left, bottom - 2 * radius_y, left + 2 * radius_x, bottom)

    if fill is not None:
        draw.rectangle((left_center, top, right_center, bottom), fill=fill)
        draw.rectangle((left, top_center, right, bottom_center), fill=fill)
        draw.pieslice(top_left, 180, 270, fill=fill)
        draw.pieslice(top_right, 270, 360, fill=fill)
        draw.pieslice(bottom_right, 0, 90, fill=fill)
        draw.pieslice(bottom_left, 90, 180, fill=fill)

    if stroke is not None:
        draw.line([(left_center, top), (right_center, top)], fill=stroke, width=stroke_width)
        draw.line([(right, top_center), (right, bottom_center)], fill=stroke, width=stroke_width)
        draw.line([(right_center, bottom), (left_center, bottom)], fill=stroke, width=stroke_width)
        draw.line([(left, bottom_center), (left, top_center)], fill=stroke, width=stroke_width)
        draw.arc(top_left, 180, 270, fill=stroke, width=stroke_width)
        draw.arc(top_right, 270, 360, fill=stroke, width=stroke_width)
        draw.arc(bottom_right, 0, 90, fill=stroke, width=stroke_width)
        draw.arc(bottom_left, 90, 180, fill=stroke, width=stroke_width)


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
