from __future__ import annotations

import itertools
import logging
import os
import random
from pathlib import Path

from shapely.affinity import translate as shapely_translate
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import box as shapely_box
from shapely.ops import nearest_points
from svgpathtools import parse_path

from InkGen.boundary import Canvas
from InkGen.cad_component_groups import Zoning
from InkGen.component import Component
from InkGen.document import Layer
from InkGen.errors import ComponentGroupOffCanvas
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.svg_generator import (
    CircleSVG,
    ComponentGroupSVG,
    DocumentSVG,
    IncludeLayer,
    LineSVG,
    PolygonalSVG,
    RectangleSVG,
    RegularPolygonSVG,
    SVGComponent,
    TextSVG,
    _style_properties,
)
from InkGen.text_fitter import (
    JITTER_SAFETY_MARGIN_DEFAULT,
    FitterShape,
    FittingResult,
    TextBlock,
    TextFitter,
    component_to_fitter_shape,
)
from InkGen.text_outline import outline_for_text

LEFT_MARGIN = 0
RIGHT_MARGIN = 0
TOP_MARGIN = 0
BOTTOM_MARGIN = 0
TRIANGLE_PADDING = 0
TRIANGLE_SCALE = 0.38
PX_TO_MM = 25.4 / 96.0
EMIT_TEXT_OUTLINES = False
CONVERT_TEXT_TO_PATH = False
FORCE_FITTED_TEXT_START_ANCHOR = True
TEXT_INSET_MARGIN = 0.2  # mm safety inset to keep text inside fitted shapes
MAX_TEXT_ADJUST_ATTEMPTS = 8
EMIT_TEXT_DEBUG_OVERLAY = False

logging.basicConfig(level=logging.INFO)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR = BASE_DIR / "drawing_templates"


class DebugPathSVG(Component):
    def __init__(self, path_data: str, style: DrawingStyle):
        super().__init__()
        self._path_data = path_data
        self._style = style
        self._bbox = None

    def generate_svg(self) -> str:
        style_str = _style_properties(self._style)
        return f"""<path
            style="{style_str}"
            d="{self._path_data}"
            id="path{self.id}" />"""

    @property
    def points(self):
        if self._bbox is None:
            path = parse_path(self._path_data)
            xmin, xmax, ymin, ymax = path.bbox()
            self._bbox = ((xmin, ymin), (xmax, ymax))
        (xmin, ymin), (xmax, ymax) = self._bbox
        return [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]

    @property
    def bbox(self):
        if self._bbox is None:
            path = parse_path(self._path_data)
            xmin, xmax, ymin, ymax = path.bbox()
            self._bbox = ((xmin, ymin), (xmax, ymax))
        return self._bbox


def _safe_add(layer, group):
    try:
        layer.add_component_group(group)
    except ComponentGroupOffCanvas as exc:
        logger.info("Skipping group %s: %s", getattr(group, "group_label", "<unnamed>"), exc)

path = str(TEMPLATE_DIR) + "\\"
canvas = Canvas(277, 250, "mm")
doc = DocumentSVG(canvas)
doc.add_page()
group = ComponentGroupSVG("RandomStuff")
style = DrawingStyle("Default", stroke_width=0.4)
rectangle_component = RectangleSVG(position=(80.0, 50.0), width=56, height=56, corner_radii=0, style=style)
group.add_component(rectangle_component)
baseline_component = LineSVG((25, 110), (175, 110), style)
group.add_component(baseline_component)
polygon_component = RegularPolygonSVG((50, 50), 5, 25, style)
group.add_component(polygon_component)
connector_component = PolygonalSVG([(120, 120), (170, 120), (160, 145), (110, 145)], style)
group.add_component(connector_component)
# Triangle used in text-fitting tests placed near the zoning border.
triangle_template = [(100, 0), (200, 200), (0, 200)]
triangle_min_x = min(x for x, _ in triangle_template)
triangle_max_x = max(x for x, _ in triangle_template)
triangle_min_y = min(y for _, y in triangle_template)
triangle_max_y = max(y for _, y in triangle_template)
triangle_width = (triangle_max_x - triangle_min_x) * TRIANGLE_SCALE
triangle_height = (triangle_max_y - triangle_min_y) * TRIANGLE_SCALE
triangle_offset_x = max(LEFT_MARGIN + TRIANGLE_PADDING + 10,
                         canvas.width - RIGHT_MARGIN - triangle_width - TRIANGLE_PADDING - 10)
triangle_offset_y = TOP_MARGIN + TRIANGLE_PADDING + 10
triangle_points = [((x - triangle_min_x) * TRIANGLE_SCALE + triangle_offset_x,
                    (y - triangle_min_y) * TRIANGLE_SCALE + triangle_offset_y)
                   for x, y in triangle_template]
triangle_group = ComponentGroupSVG('TextFitterTriangle')
triangle_component = PolygonalSVG(triangle_points, style)
triangle_group.add_component(triangle_component)

text_fitter = TextFitter(rng=random.Random())
fitted_text_groups: list[ComponentGroupSVG] = []
_fitted_group_id = itertools.count()

font_path = "C:/Windows/Fonts/arial.ttf"

def _next_group_label(prefix: str) -> str:
    """Create a unique component group label.

    Args:
        prefix: Human readable prefix for the group.

    Returns:
        str: Label that is unique within the document.
    """
    return f"{prefix}_{next(_fitted_group_id)}"

def _add_fitted_text(
    component,
    body_text: str,
    style_name: str,
    *,
    padding: float = 2.0,
    thickness_range: tuple[float, float] = (0.75, 1.5),
    font_range: tuple[int, int] = (8, 64),
    max_line_width: float | None = None,
    jitter_x: bool = True,
    jitter_y: bool = True,
    jitter_margin: float = JITTER_SAFETY_MARGIN_DEFAULT,
    group_mode: str = "per_line",
) -> None:
    """Fit text into the supplied component and emit labelled component groups.

    Args:
        component: Vector component receiving the fitted text.
        body_text: Raw text content.
        style_name: Base name used for generated styles/groups.
        padding: Padding applied when converting the component to a fitting shape.
        thickness_range: Range of stroke thickness used when deriving padding.
        font_range: Minimum/maximum font size to explore.
        max_line_width: Maximum width before forcing additional wrapping.
        jitter_x: Enable jitter along the X axis.
        jitter_y: Enable jitter along the Y axis.
        jitter_margin: Safety margin to keep from the shape boundary.
        group_mode: ``"per_line"`` to emit one group per line or ``"combined"`` for a single group.
    """
    block = TextBlock(
        text=body_text,
        font_path=font_path,
        font_size_range=font_range,
        max_line_width=max_line_width,
    )

    def _fit_with_shape(f_shape: FitterShape | None) -> FittingResult | None:
        if not f_shape:
            return None
        return text_fitter.fit(
            block,
            f_shape,
            jitter_x=jitter_x,
            jitter_y=jitter_y,
            jitter_margin=jitter_margin,
        )

    fitter_shape = component_to_fitter_shape(
        component,
        thickness_range=thickness_range,
        padding=padding,
    )
    result = _fit_with_shape(fitter_shape)

    if not result and hasattr(component, "bbox"):
        try:
            (minx, miny), (maxx, maxy) = component.bbox
        except Exception:
            (minx, miny), (maxx, maxy) = None, None
        if minx is not None and maxx is not None:
            inset = padding * 0.5
            fallback_poly = shapely_box(minx + inset, miny + inset, maxx - inset, maxy - inset)
            if not fallback_poly.is_empty and fallback_poly.is_valid:
                fallback_shape = FitterShape(
                    polygon=fallback_poly,
                    line_thickness_range=(0.0, 0.0),
                    padding=0.0,
                )
                result = _fit_with_shape(fallback_shape)

    mode = group_mode.lower()
    if mode not in {"per_line", "combined"}:
        raise ValueError("group_mode must be 'per_line' or 'combined'")

    if not result:
        print(f"Unable to fit '{body_text}' inside {style_name}.")
        if hasattr(component, "bbox"):
            try:
                (minx, miny), (maxx, maxy) = component.bbox
                center_x = float((minx + maxx) / 2.0)
                center_y = float((miny + maxy) / 2.0)
                fallback_style = TextStyle(f"{style_name}_fallback", Font("Arial", size=10))
                fallback_style.text_align = "center"
                fallback_component = TextSVG(body_text, (center_x, center_y), fallback_style)
                fallback_group = ComponentGroupSVG(_next_group_label(f"{style_name}_fallback"))
                fallback_group.add_component(fallback_component)
                fitted_text_groups.append(fallback_group)
            except Exception:
                pass
        return

    point_size = float(result.font_size) * PX_TO_MM * (72.0 / 96.0)
    combined_group = None
    component_polygon = None
    try:
        hull_points = getattr(component, "convex_hull", None)
        if hull_points:
            component_polygon = ShapelyPolygon(hull_points)
            if not component_polygon.is_valid:
                component_polygon = component_polygon.buffer(0)
    except Exception:
        component_polygon = None

    if mode == "combined":
        combined_group = ComponentGroupSVG(_next_group_label(f"{style_name}_group"))

    for idx, (line_text, (x_pos, y_pos), width) in enumerate(
        zip(result.fitted_text_lines, result.line_positions, result.line_widths, strict=False)
    ):
        left_x = float(x_pos)
        center_x = left_x + float(width) / 2.0
        baseline_y = float(y_pos)
        line_style = TextStyle(f"{style_name}_{idx}", Font("Arial", size=point_size))
        line_style.text_align = "center"
        outline = outline_for_text(
            text=line_text,
            font_path=line_style.font.font_file,
            size_px=float(line_style.font.size) * (96.0 / 72.0),
            x=left_x,
            y=baseline_y,
            units="mm",
            dpi=96,
            y_down=True,
            add_one_pixel_margin=False,
        )
        mask_points = list(outline.get("convex_hull") or [])
        if mask_points and mask_points[0] == mask_points[-1]:
            mask_points = mask_points[:-1]
        mask_points = [(float(px), float(py)) for px, py in mask_points]

        path_d = outline.get("svg_path")

        offset_x = 0.0
        offset_y = 0.0
        mask_poly = None
        safe_polygon = component_polygon
        adjust_attempts = 0
        if component_polygon is not None and len(mask_points) >= 3:
            try:
                mask_poly = ShapelyPolygon(mask_points)
                if mask_poly.is_valid and not mask_poly.is_empty:
                    if TEXT_INSET_MARGIN > 0.0:
                        buffered = component_polygon.buffer(-TEXT_INSET_MARGIN)
                        if not buffered.is_empty:
                            safe_polygon = buffered
                    for attempt in range(1, MAX_TEXT_ADJUST_ATTEMPTS + 1):
                        if safe_polygon.contains(mask_poly):
                            adjust_attempts = attempt - 1
                            break
                        mask_pt, shape_pt = nearest_points(mask_poly, safe_polygon)
                        dx = shape_pt.x - mask_pt.x
                        dy = shape_pt.y - mask_pt.y
                        norm = (dx * dx + dy * dy) ** 0.5
                        if norm < 1e-9:
                            centroid_dx = safe_polygon.centroid.x - mask_poly.centroid.x
                            centroid_dy = safe_polygon.centroid.y - mask_poly.centroid.y
                            centroid_norm = (centroid_dx * centroid_dx + centroid_dy * centroid_dy) ** 0.5
                            if centroid_norm > 1e-9:
                                step = max(TEXT_INSET_MARGIN, 0.05)
                                dx = (centroid_dx / centroid_norm) * step
                                dy = (centroid_dy / centroid_norm) * step
                                mask_poly = shapely_translate(mask_poly, xoff=dx, yoff=dy)
                                offset_x += dx
                                offset_y += dy
                                adjust_attempts = attempt
                                continue
                            adjust_attempts = attempt
                            break
                        adjust = max(TEXT_INSET_MARGIN, 0.0)
                        dx += (dx / norm) * adjust
                        dy += (dy / norm) * adjust
                        mask_poly = shapely_translate(mask_poly, xoff=dx, yoff=dy)
                        offset_x += dx
                        offset_y += dy
                        adjust_attempts = attempt
                    coords = list(mask_poly.convex_hull.exterior.coords)
                    if len(coords) > 1 and coords[0] == coords[-1]:
                        coords = coords[:-1]
                    mask_points = [(float(px), float(py)) for px, py in coords]
            except Exception:
                offset_x = offset_y = 0.0
                mask_poly = None
                safe_polygon = component_polygon

        if offset_x or offset_y:
            left_x += offset_x
            center_x += offset_x
            baseline_y += offset_y
            if path_d:
                try:
                    translated_path = parse_path(path_d).translated(complex(offset_x, offset_y))
                    path_d = translated_path.d()
                except Exception:
                    pass

        final_mask_poly = None
        if mask_points and len(mask_points) >= 3:
            try:
                final_mask_poly = ShapelyPolygon(mask_points)
            except Exception:
                final_mask_poly = None

        debug_label = f"{style_name}_line_{idx}"
        if safe_polygon is not None and final_mask_poly is not None and not safe_polygon.contains(final_mask_poly):
            distance = final_mask_poly.exterior.distance(safe_polygon)
            violation_area = final_mask_poly.difference(safe_polygon).area
            logger.warning(
                "Text mask overlap detected for %s: offset=(%.4f, %.4f) attempts=%d dist=%.4f area=%.4f",
                debug_label,
                offset_x,
                offset_y,
                adjust_attempts,
                distance,
                violation_area,
            )
            if EMIT_TEXT_DEBUG_OVERLAY:
                debug_group = ComponentGroupSVG(_next_group_label(f"{style_name}_debug"))
                safe_coords = list(component_polygon.exterior.coords)
                if len(safe_coords) > 1 and safe_coords[0] == safe_coords[-1]:
                    safe_coords = safe_coords[:-1]
                safe_coords = [(float(px), float(py)) for px, py in safe_coords]
                safe_style = DrawingStyle(f"{style_name}_debug_safe", stroke="#ff0000", fill="none")
                hull_style = DrawingStyle(f"{style_name}_debug_mask", stroke="#0000ff", fill="none")
                debug_group.add_component(PolygonalSVG(safe_coords, safe_style))
                if mask_points:
                    debug_group.add_component(PolygonalSVG([(float(px), float(py)) for px, py in mask_points], hull_style))
                fitted_text_groups.append(debug_group)

        render_anchor = "center"
        render_x = center_x
        if FORCE_FITTED_TEXT_START_ANCHOR:
            render_anchor = "start"
            render_x = left_x
        line_style.text_align = render_anchor if render_anchor != "center" else "center"
        render_x = float(render_x)
        baseline_y = float(baseline_y)

        probe_component = TextSVG(line_text, (render_x, baseline_y), line_style)
        line_component: Component
        if CONVERT_TEXT_TO_PATH:
            if path_d:
                fill_color = getattr(line_style, "color", "#000000")
                path_style = DrawingStyle(f"{style_name}_{idx}_path_style", stroke="none", fill=fill_color)
                line_component = DebugPathSVG(path_d, path_style)
            else:
                line_component = probe_component
        else:
            line_component = probe_component

        if mode == "combined":
            combined_group.add_component(line_component)
        else:
            line_group = ComponentGroupSVG(_next_group_label(f"{style_name}_line"))
            line_group.add_component(line_component)
            if mask_points:
                line_group._mask_override = [(float(px), float(py)) for px, py in mask_points]
            fitted_text_groups.append(line_group)
        if EMIT_TEXT_OUTLINES:
            try:
                outline = outline_for_text(
                    text=line_text,
                    font_path=line_style.font.font_file,
                    size_px=float(result.font_size),
                    x=center_x,
                    y=baseline_y,
                    units="mm",
                    dpi=96,
                    y_down=True,
                    add_one_pixel_margin=False,
                )
                path_d = outline.get("svg_path")
                if path_d:
                    outline_group = ComponentGroupSVG(_next_group_label(f"{style_name}_outline"))
                    outline_style = DrawingStyle(f"{style_name}_{idx}_outline_style", stroke="#2ca02c")
                    outline_style.fill = "none"
                    outline_style.stroke_width = 0.2
                    outline_group.add_component(DebugPathSVG(path_d, outline_style))
                    fitted_text_groups.append(outline_group)
            except Exception as exc:
                logger.info("outline generation failed for %s line %s: %s", style_name, idx, exc)

    if combined_group:
        fitted_text_groups.append(combined_group)

fitted_text_specs = [
    (triangle_component, "A Big Beautiful Brain", "TriangleQuote", 0.08, (0.2, 0.2), (28, 84), 40.0, 0.0),
    (rectangle_component, "Control Core", "RectangleTitle", 0.25, (0.25, 0.25), (28, 88), None, 0.0),
    (polygon_component, "Idea", "PentagonTitle", 0.03, (0.15, 0.15), (24, 72), None, 0.0),
    (connector_component, "Relay", "ConnectorTitle", 0.03, (0.2, 0.2), (20, 64), None, 0.0),
]

for spec in fitted_text_specs:
    if len(spec) == 8:
        component, body_text, style_name, padding, thickness_range, font_range, max_line_width, jitter_margin = spec
        group_mode = "per_line"
    else:
        component, body_text, style_name, padding, thickness_range, font_range, max_line_width, jitter_margin, group_mode = spec
    _add_fitted_text(
        component,
        body_text,
        style_name,
        padding=padding,
        thickness_range=thickness_range,
        font_range=font_range,
        max_line_width=max_line_width,
        jitter_margin=jitter_margin,
        group_mode=group_mode,
    )

text_style = TextStyle("TimesNormal", Font("Times New Roman", size=12))
text_style.font.style = "italic"
text_style.text_align = "start"
text_comp = TextSVG("Test Text", (150, 200), text_style)
#underline = LineSVG((150, 202), (191, 202), style)

center_text_style = TextStyle("TimesCenter", Font("Times New Roman", size=12))
center_text_style.font.style = "italic"
center_text_style.text_align = "center"
center_text_comp = TextSVG("Test Text", (150, 240), center_text_style)

circle_group = ComponentGroupSVG("Circle Group")
circle_group.add_component(CircleSVG(position=(190, 100), radius=6, style=style))
callout_text = TextStyle("Callout", Font("Arial", size=10))
callout = TextSVG("1", (0, 0), callout_text)
callout_bbox = callout.bbox
callout_x_offset = (callout_bbox[0][0] + callout_bbox[1][0]) / 2
callout_y_offset = (callout_bbox[0][1] + callout_bbox[1][1]) / 2
callout.position = (190 - callout_x_offset, 100 - callout_y_offset)
circle_group.add_component(callout)

harry_template = TEMPLATE_DIR / "Harry Potter_small.svg"
harry_group: ComponentGroupSVG | None = None
if harry_template.exists():
    harry_svg_component = SVGComponent(
        filepath=str(harry_template),
        position=(200.0, 120.0),
        scale=0.1,
    )
    harry_group = ComponentGroupSVG("HarryPotterGraphic")
    harry_group.add_component(harry_svg_component)
else:
    logger.info("Skipping Harry Potter template; %s not found", harry_template)


fixed_text_group = ComponentGroupSVG("TextGroup")
fixed_text_group.add_component(text_comp)

center_text_group = ComponentGroupSVG("TextGroupCenter")
center_text_group.add_component(center_text_comp)

text_style_2 = TextStyle("Aria", Font("Arial", size=12))
text_style_2.text_align = "start"
text_comp_2 = TextSVG("Test Text", (50, 220), text_style_2)
text_group_2 = ComponentGroupSVG("TextGroup2")
text_group_2.add_component(text_comp_2)

#text_group.add_component(underline)
_safe_add(doc.page(1).layer("base"), group)
_safe_add(doc.page(1).layer("base"), triangle_group)
for text_group in fitted_text_groups:
    _safe_add(doc.page(1).layer("base"), text_group)
_safe_add(doc.page(1).layer("base"), fixed_text_group)
_safe_add(doc.page(1).layer("base"), center_text_group)
_safe_add(doc.page(1).layer("base"), circle_group)
if harry_group is not None:
    _safe_add(doc.page(1).layer("base"), harry_group)
_safe_add(doc.page(1).layer("base"), text_group_2)

zoning_text = TextStyle("ArialBlack", Font("Arial", weight="bold", size=6))
zoning_text.text_align = "center"

zoning = Zoning(canvas, style, zoning_text,
                left_margin=LEFT_MARGIN, right_margin=RIGHT_MARGIN, top_margin=TOP_MARGIN, bottom_margin=BOTTOM_MARGIN,
                v_zone_width=10, h_zone_width=8, inner_radius=10.0, outer_radius=10.0,
                vertical_zones=10, horizontal_zones=8)
doc.page(1).add_layer("zoning", Layer("zoning", canvas, False))
doc.page(1).layer("zoning").add_component_group(zoning.component_group)


filepath = OUTPUT_DIR / "test_document.yaml"

doc.save(filepath)
doc.create_svg(str(OUTPUT_DIR / "test1.svg"), include= IncludeLayer.MASK)
try:
    os.startfile(OUTPUT_DIR / "test1.svg")
except AttributeError:
    pass
