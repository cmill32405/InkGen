"""
An intelligent text-in-shape fitting utility for the InkGen Framework.
"""
import logging
import os
import random
from dataclasses import dataclass
from math import isfinite

import matplotlib
import matplotlib.pyplot as plt
from PIL import ImageFont
from shapely.affinity import scale as shapely_scale
from shapely.affinity import translate as shapely_translate
from shapely.errors import TopologicalError
from shapely.geometry import (
    GeometryCollection,
    MultiPolygon,
    Point,
)
from shapely.geometry import (
    Polygon as ShapelyPolygon,
)
from shapely.geometry import (
    box as shapely_box,
)
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from InkGen.boundary import Boundary
from InkGen.component import Component
from InkGen.text_outline import outline_for_text

matplotlib.use('Agg')

PX_TO_MM = 25.4 / 96.0
JITTER_SAFETY_MARGIN_DEFAULT = 0.5
MAX_JITTER_ATTEMPTS = 8

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass
class FitterShape:
    polygon: ShapelyPolygon
    line_thickness_range: tuple[float, float] = (1.0, 3.0)
    padding: float = 1.0

    def __post_init__(self) -> None:
        """Validate the public shape boundary before fitting math consumes it."""
        self.polygon = _normalize_fitter_polygon(self.polygon)
        self.line_thickness_range = _normalize_finite_range(
            self.line_thickness_range,
            name="line_thickness_range",
            minimum=0.0,
        )
        self.padding = _normalize_non_negative_float(self.padding, name="padding")


@dataclass
class TextBlock:
    text: str
    font_path: str
    font_size_range: tuple[int, int] = (4, 24)
    min_font_size_px: int = 6
    max_line_width: float | None = 80.0


@dataclass
class FittingResult:
    original_shape: FitterShape
    fitted_text_lines: list[str]
    line_positions: list[tuple[float, float]]
    line_widths: list[float]
    font_size: float
    final_line_thickness: float
    text_geometry: BaseGeometry
    text_convex_hull: ShapelyPolygon

    @property
    def text_bounding_box(self) -> ShapelyPolygon:
        """Convex hull for backward compatibility with legacy bounding box usage."""
        return self.text_convex_hull


def _normalize_jitter_margin(value: object) -> float:
    """Normalize the public jitter margin without string or truthiness coercion."""
    if isinstance(value, bool | str | bytes):
        raise TypeError("jitter_margin must be a finite number")
    try:
        margin = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("jitter_margin must be a finite number") from exc
    if not isfinite(margin):
        raise ValueError("jitter_margin must be a finite number")
    return max(0.0, margin)


def _normalize_fitter_polygon(value: object) -> ShapelyPolygon:
    """Normalize the public fitter polygon before Shapely operations run."""
    if not isinstance(value, ShapelyPolygon):
        raise TypeError("polygon must be a Shapely Polygon")
    if value.is_empty or not value.is_valid:
        raise ValueError("polygon must be a non-empty valid Shapely Polygon")
    return value


def _normalize_finite_range(
    value: object,
    *,
    name: str,
    minimum: float | None = None,
) -> tuple[float, float]:
    """Normalize a public two-value numeric range."""
    if isinstance(value, bool | str | bytes):
        raise TypeError(f"{name} must be a two-value numeric range")
    try:
        lower, upper = value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain exactly two values") from exc
    lower_value = _normalize_finite_float(lower, name=name)
    upper_value = _normalize_finite_float(upper, name=name)
    if minimum is not None and (lower_value < minimum or upper_value < minimum):
        raise ValueError(f"{name} values must be at least {minimum}")
    if lower_value > upper_value:
        raise ValueError(f"{name} lower bound must not exceed upper bound")
    return lower_value, upper_value


def _normalize_non_negative_float(value: object, *, name: str) -> float:
    """Normalize a public non-negative finite scalar."""
    number = _normalize_finite_float(value, name=name)
    if number < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return number


def _normalize_finite_float(value: object, *, name: str) -> float:
    """Normalize a public finite scalar without string or bool coercion."""
    if isinstance(value, bool | str | bytes):
        raise TypeError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite number") from exc
    if not isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def plot_polygon(ax, poly, color, label):
    """Helper to plot a shapely Polygon or MultiPolygon robustly."""
    if poly.is_empty:
        return
    if poly.geom_type == 'MultiPolygon':
        for p in poly.geoms:
            x, y = p.exterior.xy
            ax.fill(x, y, alpha=0.5, fc=color, ec='none')
    elif poly.geom_type == 'Polygon':
        x, y = poly.exterior.xy
        ax.fill(x, y, alpha=0.5, fc=color, ec='none', label=label)


def save_debug_image(boundary: ShapelyPolygon, text_poly: ShapelyPolygon, font_size: int, text: str):
    """Saves a plot of the geometry for visual debugging."""
    path = "debug_images"
    os.makedirs(path, exist_ok=True)
    filename = os.path.join(path, f"debug_fit_fail_{text[:10].replace(' ','_')}_fs{font_size}.png")
    fig, ax = plt.subplots()

    plot_polygon(ax, boundary, 'blue', 'Inner Boundary')
    plot_polygon(ax, text_poly, 'red', 'Text Footprint')

    bounds_with_padding = boundary.buffer(10).bounds
    ax.set_xlim(bounds_with_padding[0], bounds_with_padding[2])
    ax.set_ylim(bounds_with_padding[1], bounds_with_padding[3])
    ax.set_aspect('equal', adjustable='box')
    plt.title(f"Containment Fail | Font Size: {font_size}")
    plt.savefig(filename)
    plt.close(fig)
    logger.debug(f"Saved debug image to {filename}")


class TextFitter:
    """Manage text fitting into shapes and optional jitter offsets."""
    def __init__(self, rng: random.Random | None = None):
        """Initialise the fitter with an optional random source."""
        self.rng = rng if rng is not None else random.Random(4242)
        self._pil_font_cache = {}

    def _get_pil_font(self, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        """Return a PIL font, caching instances per size."""
        try:
            if (font_path, size) not in self._pil_font_cache:
                self._pil_font_cache[(font_path, size)] = ImageFont.truetype(font_path, size)
            return self._pil_font_cache[(font_path, size)]
        except OSError:
            return ImageFont.load_default()

    @staticmethod
    def _polygon_from_coords(coords: list[tuple[float, float]]) -> ShapelyPolygon | None:
        """Create a shapely polygon from coordinates when possible."""
        if not coords:
            return None
        try:
            polygon = ShapelyPolygon(coords)
        except (ValueError, TopologicalError):
            return None
        if polygon.is_empty:
            return None
        if not polygon.is_valid:
            try:
                polygon = polygon.buffer(0)
            except TopologicalError:
                return None
        return polygon if not polygon.is_empty else None

    def _create_line_outline(
        self,
        line_text: str,
        font_path: str,
        font_size: int,
        origin_x: float,
        origin_y: float,
    ) -> ShapelyPolygon | None:
        """Generate an outline polygon for a single line of text."""
        if not line_text.strip():
            return None
        try:
            origin_x_px = origin_x / PX_TO_MM
            origin_y_px = origin_y / PX_TO_MM
            outline = outline_for_text(
                text=line_text,
                font_path=font_path,
                size_px=font_size,
                x=origin_x_px,
                y=origin_y_px,
                units="px",
                y_down=True,
            )
        except Exception:
            return None

        hull_poly = self._polygon_from_coords(outline.get("convex_hull", []))
        if hull_poly:
            return shapely_scale(hull_poly, xfact=PX_TO_MM, yfact=PX_TO_MM, origin=(0, 0))

        bbox_poly = self._polygon_from_coords(outline.get("bbox", []))
        if bbox_poly:
            return shapely_scale(bbox_poly, xfact=PX_TO_MM, yfact=PX_TO_MM, origin=(0, 0))
        return None

    @staticmethod
    def _merge_polygons(polygons: list[BaseGeometry]) -> BaseGeometry | None:
        """Merge multiple geometries into a single shape."""
        valid_geoms = [poly for poly in polygons if poly and not poly.is_empty]
        if not valid_geoms:
            return None
        merged = unary_union(valid_geoms)
        if isinstance(merged, GeometryCollection) and not merged:
            return None
        if merged.is_empty:
            return None
        if not merged.is_valid:
            try:
                merged = merged.buffer(0)
            except TopologicalError:
                return None
        return merged

    def _calculate_inner_boundary(self, shape: FitterShape) -> tuple[ShapelyPolygon | None, float]:
        """Calculate the inner boundary polygon after padding and stroke adjustments."""
        min_thick, max_thick = shape.line_thickness_range
        random_thickness = self.rng.uniform(min_thick, max_thick)
        total_inset = shape.padding + (random_thickness / 2.0)
        inner_boundary = shape.polygon.buffer(-total_inset, join_style="mitre")
        if inner_boundary.is_empty or not isinstance(inner_boundary, (ShapelyPolygon, MultiPolygon)):
            return None, random_thickness
        return inner_boundary, random_thickness

    def _adaptive_word_wrap(
        self,
        text: str,
        inner_boundary: ShapelyPolygon,
        font: ImageFont.FreeTypeFont,
        font_size: int,
        font_path: str,
        max_line_width: float | None,
    ) -> tuple[list[tuple[str, float, float, float]], BaseGeometry] | None:
        """Wrap text to fit within the inner boundary using adaptive line widths."""
        words = text.split()
        if not words:
            return None

        temp_wrapped_lines: list[str] = []
        temp_words = list(words)
        max_possible_width = inner_boundary.bounds[2] - inner_boundary.bounds[0]
        if max_line_width is not None:
            max_possible_width = min(max_possible_width, max_line_width)
        px_to_doc = PX_TO_MM
        while temp_words:
            line, words_in_line = "", 0
            for i in range(1, len(temp_words) + 1):
                candidate = " ".join(temp_words[:i])
                candidate_width = font.getlength(candidate) * px_to_doc
                if candidate_width > max_possible_width:
                    break
                line, words_in_line = candidate, i
            if not line:
                return None
            temp_wrapped_lines.append(line)
            temp_words = temp_words[words_in_line:]

        ascent, descent = font.getmetrics()
        ascent_mm = ascent * px_to_doc
        descent_mm = descent * px_to_doc
        line_height = (ascent_mm + descent_mm)
        total_text_height = len(temp_wrapped_lines) * line_height
        center_y = inner_boundary.centroid.y
        start_y = center_y - total_text_height / 2.0

        wrapped_lines_data: list[tuple[str, float, float, float]] = []
        all_line_rects = []
        outline_polygons = []
        current_y = start_y

        for line_text in temp_wrapped_lines:
            slicer = shapely_box(inner_boundary.bounds[0], current_y, inner_boundary.bounds[2], current_y + line_height)
            intersection = inner_boundary.intersection(slicer)
            if intersection.is_empty:
                return None

            available_width = intersection.bounds[2] - intersection.bounds[0]
            line_w = font.getlength(line_text) * px_to_doc
            if line_w > available_width:
                return None

            line_start_x = intersection.bounds[0] + (available_width - line_w) / 2
            baseline_y = current_y + ascent_mm
            wrapped_lines_data.append((line_text, line_start_x, baseline_y, line_w))

            all_line_rects.append(shapely_box(line_start_x, current_y, line_start_x + line_w, current_y + line_height))

            outline_poly = self._create_line_outline(line_text, font_path, font_size, line_start_x, baseline_y)
            if outline_poly:
                outline_polygons.append(outline_poly)
                bounds = outline_poly.bounds
                logger.debug(
                    "outline_bounds: text=%r start_x=%.3f width=%.3f bounds=%s",
                    line_text,
                    line_start_x,
                    line_w,
                    tuple(round(v, 3) for v in bounds) if bounds else None,
                )
            else:
                logger.debug(
                    "outline_missing: text=%r start_x=%.3f width=%.3f",
                    line_text,
                    line_start_x,
                    line_w,
                )

            current_y += line_height

        if not wrapped_lines_data:
            return None

        text_geometry = self._merge_polygons(outline_polygons)
        if text_geometry is None:
            text_geometry = self._merge_polygons(all_line_rects)

        if text_geometry is None:
            return None

        return wrapped_lines_data, text_geometry

    def _check_fit(self, text_block: TextBlock, inner_boundary: ShapelyPolygon, font_size: int) -> tuple | None:
        """Evaluate whether the given font size fits within the inner boundary."""
        font = self._get_pil_font(text_block.font_path, font_size)
        fit_details = self._adaptive_word_wrap(
            text_block.text,
            inner_boundary,
            font,
            font_size,
            text_block.font_path,
            text_block.max_line_width,
        )

        if not fit_details:
            return None

        wrapped_data, text_geometry = fit_details

        if inner_boundary.contains(text_geometry):
            return wrapped_data, text_geometry

        debug_geometry = (
            text_geometry.convex_hull if hasattr(text_geometry, "convex_hull") else text_geometry
        )
        save_debug_image(inner_boundary, debug_geometry, font_size, text_block.text)
        return None

    def _max_axis_shift(
        self,
        inner_boundary: BaseGeometry,
        geometry: BaseGeometry,
        axis: str,
        direction: int,
        max_bound: float,
        tolerance: float = 1e-3,
    ) -> float:
        """Binary search the maximum shift along a single axis."""
        if max_bound <= 0.0:
            return 0.0
        low = 0.0
        high = max_bound
        iterations = 0
        max_iterations = 32
        while high - low > tolerance and iterations < max_iterations:
            iterations += 1
            mid = (low + high) / 2.0
            dx = mid * direction if axis == 'x' else 0.0
            dy = mid * direction if axis == 'y' else 0.0
            shifted = shapely_translate(geometry, xoff=dx, yoff=dy)
            if inner_boundary.covers(shifted):
                low = mid
            else:
                high = mid
        return low

    def _axis_shift_limits(
        self,
        inner_boundary: BaseGeometry,
        geometry: BaseGeometry,
        axis: str,
        safety_margin: float,
    ) -> tuple[float, float]:
        """Return min/max shifts allowed along an axis after applying the safety margin."""
        inner_minx, inner_miny, inner_maxx, inner_maxy = inner_boundary.bounds
        geom_minx, geom_miny, geom_maxx, geom_maxy = geometry.bounds
        if axis == 'x':
            positive_bound = max(0.0, inner_maxx - geom_maxx)
            negative_bound = max(0.0, geom_minx - inner_minx)
        elif axis == 'y':
            positive_bound = max(0.0, inner_maxy - geom_maxy)
            negative_bound = max(0.0, geom_miny - inner_miny)
        else:
            raise ValueError("axis must be 'x' or 'y'")
        max_positive = self._max_axis_shift(inner_boundary, geometry, axis, 1, positive_bound)
        max_negative = self._max_axis_shift(inner_boundary, geometry, axis, -1, negative_bound)
        if safety_margin > 0.0:
            max_positive = max(0.0, max_positive - safety_margin)
            max_negative = max(0.0, max_negative - safety_margin)
        return (-max_negative, max_positive)

    def _sample_axis_offset(self, min_offset: float, max_offset: float) -> float:
        """Sample a jitter offset biased toward the extreme values."""
        if max_offset <= 1e-6 and min_offset >= -1e-6:
            return 0.0
        neg_span = abs(min_offset) if min_offset < 0.0 else 0.0
        pos_span = max_offset if max_offset > 0.0 else 0.0
        if pos_span == 0.0 and neg_span == 0.0:
            return 0.0
        total_span = pos_span + neg_span
        edge_bias = 0.2
        choose_positive = False
        if pos_span > 0.0 and (neg_span == 0.0 or self.rng.random() < pos_span / total_span):
            choose_positive = True
        if choose_positive:
            if self.rng.random() < 0.25:
                return pos_span
            base_random = self.rng.random()
            if self.rng.random() < 0.6:
                scale = base_random ** edge_bias
            else:
                scale = base_random
            return pos_span * scale
        else:
            if self.rng.random() < 0.25:
                return -neg_span
            base_random = self.rng.random()
            if self.rng.random() < 0.6:
                scale = base_random ** edge_bias
            else:
                scale = base_random
            return -neg_span * scale

    def _compute_jitter_offsets(
        self,
        inner_boundary: BaseGeometry,
        outer_boundary: BaseGeometry,
        geometry: BaseGeometry,
        jitter_x: bool,
        jitter_y: bool,
        safety_margin: float,
    ) -> tuple[float, float, BaseGeometry]:
        """Calculate jitter offsets while ensuring containment inside both boundaries."""
        if not (jitter_x or jitter_y):
            logger.debug('jitter skipped', extra={'inkgen': {'reason': 'no jitter axes enabled'}})
            return 0.0, 0.0, geometry

        boundary_geom = inner_boundary
        if isinstance(inner_boundary, MultiPolygon):
            boundary_geom = unary_union(inner_boundary)
            if boundary_geom.geom_type != 'Polygon':
                boundary_geom = boundary_geom.convex_hull
        boundary = Boundary(list(boundary_geom.exterior.coords), outer_boundary=False)

        for _ in range(MAX_JITTER_ATTEMPTS):
            dx = 0.0
            dy = 0.0
            working_geometry = geometry

            if jitter_x:
                min_x, max_x = self._axis_shift_limits(
                    inner_boundary,
                    working_geometry,
                    'x',
                    safety_margin,
                )
                if max_x - min_x > 1e-6:
                    dx = self._sample_axis_offset(min_x, max_x)
                    if abs(dx) > 1e-9:
                        working_geometry = shapely_translate(working_geometry, xoff=dx)

            if jitter_y:
                min_y, max_y = self._axis_shift_limits(
                    inner_boundary,
                    working_geometry,
                    'y',
                    safety_margin,
                )
                if max_y - min_y > 1e-6:
                    dy = self._sample_axis_offset(min_y, max_y)
                    if abs(dy) > 1e-9:
                        working_geometry = shapely_translate(working_geometry, yoff=dy)

            hull_points: list[tuple[float, float]] = []
            if hasattr(working_geometry, 'convex_hull'):
                hull_points = list(working_geometry.convex_hull.exterior.coords)

            boundary_result = (
                boundary.boundary_check(hull_points, strict=False) if hull_points else None
            )
            covers_result = inner_boundary.covers(working_geometry)
            outer_covers = (
                outer_boundary.covers(working_geometry)
                if outer_boundary is not None
                else True
            )
            candidate_inside = (bool(boundary_result) or covers_result) and outer_covers

            if not candidate_inside and (abs(dx) > 1e-9 or abs(dy) > 1e-9):
                low, high = 0.0, 1.0
                best_geom = None
                for _ in range(24):
                    mid = (low + high) / 2.0
                    candidate = shapely_translate(geometry, xoff=dx * mid, yoff=dy * mid)
                    if inner_boundary.covers(candidate) and (outer_boundary is None or outer_boundary.covers(candidate)):
                        low = mid
                        best_geom = candidate
                    else:
                        high = mid
                if best_geom is not None and low > 1e-3:
                    dx *= low
                    dy *= low
                    working_geometry = best_geom
                    hull_points = (
                        list(working_geometry.convex_hull.exterior.coords)
                        if hasattr(working_geometry, 'convex_hull')
                        else []
                    )
                    boundary_result = (
                        boundary.boundary_check(hull_points, strict=False)
                        if hull_points
                        else None
                    )
                    covers_result = True
                    outer_covers = (
                        outer_boundary.covers(working_geometry)
                        if outer_boundary is not None
                        else True
                    )
                    candidate_inside = True

            sample_points = hull_points[:4] if hull_points else None
            if inner_boundary.intersects(working_geometry):
                diff_inner = working_geometry.difference(inner_boundary).area
            else:
                diff_inner = working_geometry.area

            if outer_boundary is None:
                diff_outer = 0.0
            elif outer_boundary.intersects(working_geometry):
                diff_outer = working_geometry.difference(outer_boundary).area
            elif outer_boundary.contains(working_geometry):
                diff_outer = 0.0
            else:
                diff_outer = working_geometry.area

            log_details = (
                f"boundary={boundary_result} covers_inner={covers_result} "
                f"covers_outer={outer_covers} diff_inner={diff_inner:.6f} "
                f"diff_outer={diff_outer:.6f} dx={dx:.4f} dy={dy:.4f} "
                f"sample={sample_points}"
            )

            if candidate_inside:
                logger.debug('jitter candidate accepted: %s', log_details)
                return dx, dy, working_geometry

            logger.debug('jitter candidate rejected: %s', log_details)

        logger.debug('jitter fallback: no jitter candidate accepted')
        return 0.0, 0.0, geometry

    def fit(
    self,
    text_block: TextBlock,
    shape: FitterShape,
    *,
    jitter_x: bool = False,
    jitter_y: bool = False,
    jitter_margin: float = JITTER_SAFETY_MARGIN_DEFAULT,
) -> FittingResult | None:
        """Fit text into the provided shape and return placement details."""
        inner_boundary, random_thickness = self._calculate_inner_boundary(shape)
        if not inner_boundary:
            return None

        low, high = text_block.font_size_range
        best_fit_details = None
        best_size = None

        while low <= high:
            font_size = (low + high) // 2
            if font_size < text_block.font_size_range[0]:
                break

            fit_details = self._check_fit(text_block, inner_boundary, font_size)

            if fit_details:
                best_fit_details, best_size = fit_details, font_size
                low = font_size + 1
            else:
                high = font_size - 1

        if not best_fit_details or best_size < max(text_block.min_font_size_px, text_block.font_size_range[0]):
            logger.debug("No suitable font size found")
            return None

        wrapped_lines_data, final_text_geometry = best_fit_details
        wrapped_lines_data = list(wrapped_lines_data)
        text_convex_hull = final_text_geometry.convex_hull if hasattr(final_text_geometry, "convex_hull") else final_text_geometry

        original_lines = list(wrapped_lines_data)
        original_geometry = final_text_geometry
        original_hull = text_convex_hull

        if jitter_x or jitter_y:
            safety_margin = _normalize_jitter_margin(jitter_margin)
            jitter_dx, jitter_dy, jittered_geometry = self._compute_jitter_offsets(
                inner_boundary,
                shape.polygon,
                final_text_geometry,
                jitter_x,
                jitter_y,
                safety_margin,
            )
            if abs(jitter_dx) > 1e-9 or abs(jitter_dy) > 1e-9:
                candidate_lines = [
                    (line_text, x + jitter_dx, y + jitter_dy, width)
                    for line_text, x, y, width in wrapped_lines_data
                ]
                candidate_geometry = jittered_geometry
                candidate_hull = candidate_geometry.convex_hull if hasattr(candidate_geometry, "convex_hull") else candidate_geometry
                if inner_boundary.covers(candidate_geometry):
                    wrapped_lines_data = candidate_lines
                    final_text_geometry = candidate_geometry
                    text_convex_hull = candidate_hull
                else:
                    wrapped_lines_data = original_lines
                    final_text_geometry = original_geometry
                    text_convex_hull = original_hull

        corrected_lines = []
        corrected_outlines = []
        for line_text, x_pos, y_pos, width in wrapped_lines_data:
            outline_poly = self._create_line_outline(line_text, text_block.font_path, best_size, x_pos, y_pos)
            if outline_poly:
                bounds = outline_poly.bounds
                actual_left, _, actual_right, _ = bounds
                actual_width = actual_right - actual_left
                corrected_lines.append((line_text, actual_left, y_pos, actual_width))
                corrected_outlines.append(outline_poly)
                logger.debug(
                    "final_outline: text=%r stored_left=%.3f stored_width=%.3f actual_left=%.3f actual_right=%.3f",
                    line_text,
                    x_pos,
                    width,
                    actual_left,
                    actual_right,
                )
            else:
                corrected_lines.append((line_text, x_pos, y_pos, width))

        if corrected_outlines:
            merged = self._merge_polygons(corrected_outlines)
            if merged is not None:
                final_text_geometry = merged
                text_convex_hull = merged.convex_hull if hasattr(merged, "convex_hull") else merged

        wrapped_lines_data = corrected_lines

        final_positions = [(x, y) for _, x, y, _ in wrapped_lines_data]
        final_widths = [width for _, _, _, width in wrapped_lines_data]
        return FittingResult(
            original_shape=shape,
            fitted_text_lines=[line for line, _, _, _ in wrapped_lines_data],
            line_positions=final_positions,
            line_widths=final_widths,
            font_size=best_size,
            final_line_thickness=random_thickness,
            text_geometry=final_text_geometry,
            text_convex_hull=text_convex_hull
        )


def component_to_fitter_shape(
    component: Component,
    thickness_range: tuple[float, float] = (1.0, 3.0),
    padding: float = 1.0,
) -> FitterShape | None:
    """Convert a component into a FitterShape wrapper."""
    polygon = None
    if hasattr(component, 'convex_hull'):
        hull_points = component.convex_hull
        if hull_points:
            polygon = ShapelyPolygon(hull_points)
    elif hasattr(component, 'radius'):
        polygon = Point(component.position).buffer(component.radius, quad_segs=64)
    if polygon:
        return FitterShape(polygon=polygon, line_thickness_range=thickness_range, padding=padding)
    return None




