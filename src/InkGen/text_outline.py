# SPDX-License-Identifier: MIT
# Lightweight text→outline pipeline using uharfbuzz + fontTools + svgpathtools + shapely

import math

import uharfbuzz as hb  # shaping
from fontTools.misc.transform import Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont  # font loading
from shapely.geometry import MultiPoint, Polygon
from shapely.geometry import box as shapely_box
from svgpathtools import parse_path

ADD_ONE_PIXEL_MARGIN_DEFAULT = False


def set_add_one_pixel_margin_default(enabled: bool) -> None:
    """Set global default for adding a one-pixel margin around text outlines."""
    global ADD_ONE_PIXEL_MARGIN_DEFAULT
    ADD_ONE_PIXEL_MARGIN_DEFAULT = bool(enabled)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _px_to_units(px, units="mm", dpi=96.0):
    if units.lower() in ("mm", "millimeter", "millimeters"):
        return px * (25.4 / 96.0)   # 1 CSS px = 1/96 in; 25.4 mm/in.
    if units.lower() in ("in", "inch", "inches"):
        return px / 96.0
    return px  # "px"

def sample_path_points(d: str, px_step: float = 0.5, *, units: str = "mm", dpi: float = 96.0):
    step = _px_to_units(px_step, units, dpi)
    path = parse_path(d)
    pts = []
    for seg in path:                                  # <-- iterates ALL segments, all subpaths
        L = seg.length(error=1e-5)
        n = max(1, int(math.ceil(L / step)))
        for i in range(n + 1):
            t = i / n
            z = seg.point(t)
            pts.append((z.real, z.imag))
    return pts

def _shape_with_harfbuzz(font_bytes: bytes, text: str, features: dict[str, bool] | None=None):
    """Return (glyph_ids, positions) shaped with HarfBuzz in font units."""
    face = hb.Face(font_bytes)
    font = hb.Font(face)
    upem = face.upem  # units-per-em
    font.scale = (upem, upem)          # positions in font units
    hb.ot_font_set_funcs(font)

    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()

    if features is None:
        features = {"kern": True, "liga": True}
    hb.shape(font, buf, features)

    infos = buf.glyph_infos
    poss  = buf.glyph_positions

    gids = [info.codepoint for info in infos]
    # cumulative pen position in font units; HarfBuzz gives deltas per glyph
    x, y = 0, 0
    advs = []
    for pos in poss:
        x_offset = pos.x_offset
        y_offset = pos.y_offset
        advs.append((x + x_offset, y + y_offset))
        x += pos.x_advance
        y += pos.y_advance
    return gids, advs, upem

def _glyphs_to_svg_path(
    tt: TTFont,
    gids: list[int],
    positions_fu: list[tuple[int, int]],
    upem: int,
    size_px: float,
    origin: tuple[float, float],
    y_down: bool = True
) -> str:
    """
    Build a single SVG path `d` for all glyph outlines positioned & scaled.
    Coordinates are emitted in the same orientation as SVG (y_down=True flips).
    """
    glyph_set = tt.getGlyphSet()
    pen = SVGPathPen(glyph_set)

    # scale from font units → pixels
    s = size_px / float(upem)
    sy = -s if y_down else s

    # baseline origin
    x0, y0 = origin

    for gid, (px_fu, py_fu) in zip(gids, positions_fu, strict=False):
        gname = tt.getGlyphName(gid)
        # Transform: scale, then translate to pen position and baseline origin.
        # NOTE: HarfBuzz positions are in font units. Convert to px via s.
        t = Transform(s, 0, 0, sy, x0 + px_fu * s, y0 + py_fu * sy)
        tp = TransformPen(pen, t)
        glyph_set[gname].draw(tp)

    return pen.getCommands()

def _sample_svg_path(d: str, step_px: float = 0.75) -> list[tuple[float, float]]:
    """
    Sample the SVG path densely enough that the convex hull & bbox are pixel-tight.
    `step_px` is the target arc-length step in the same user units as `d` (usually px).
    """
    path = parse_path(d)
    pts: list[tuple[float, float]] = []
    for seg in path:
        # ensure at least two points per segment
        seg_len = max(0.0, seg.length(error=1e-4))
        n = max(2, int(math.ceil(seg_len / max(step_px, 1e-6))) + 1)
        for i in range(n):
            z = seg.point(i / (n - 1))
            pts.append((z.real, z.imag))
    # Close any subpath gaps: parse_path already keeps moveto boundaries; sampling covers ends.
    return pts

# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────






def outline_for_text(
    text: str,
    font_path: str,
    size_px: float,
    x: float = 0.0,
    y: float = 0.0,
    dpi: float = 96.0,
    units: str = "mm",              # <- pass your document units here
    add_one_pixel_margin: bool | None = None,
    y_down: bool = True,
    features: dict[str, bool] | None = None,
    sampling_step_px: float = 0.75,
) -> dict[str, object]:
    """
    Returns:
      {
        "svg_path": <str>,
        "points": [(x,y), ...],                     # document units (e.g., mm)
        "bbox": [(xmin,ymin),(xmin,ymax),(xmax,ymax),(xmax,ymin)],
        "convex_hull": [(x,y), ...]                 # document units (e.g., mm)
      }
    """
    tt = TTFont(font_path)
    with open(font_path, "rb") as f:
        font_bytes = f.read()

    if add_one_pixel_margin is None:
        add_one_pixel_margin = ADD_ONE_PIXEL_MARGIN_DEFAULT

    # 1) Shape with HarfBuzz (positions returned in font units)
    gids, pos_fu, upem = _shape_with_harfbuzz(font_bytes, text, features)

    # 2) Build path string 'd' in DOCUMENT units (your _glyphs_to_svg_path already
    #    converts from font units -> px and places at (x, y) in your document,
    #    where your SVG uses mm). Do NOT rescale these numbers again.
    d = _glyphs_to_svg_path(
        tt=tt,
        gids=gids,
        positions_fu=pos_fu,
        upem=upem,
        size_px=size_px,
        origin=(x, y),
        y_down=y_down,
    )

    # Helper: sample path directly in document units
    pts: list[tuple[float, float]] = _sample_svg_path(d, step_px=sampling_step_px)
    # For debug/consistency checks it’s nice to also get a tight path bbox:
    try:
        p = parse_path(d)
        # svgpathtools returns (xmin, xmax, ymin, ymax)
        pxmin, pxmax, pymin, pymax = p.bbox()
        path_bbox = (pxmin, pymin, pxmax, pymax)
    except Exception:
        path_bbox = None

    # 3) Robust convex hull in document units (mm)
    if pts:
        h = MultiPoint(pts).convex_hull
        if getattr(h, "geom_type", "") == "Polygon":
            hull_poly: Polygon = h
        elif h.is_empty:
            hull_poly = Polygon()
        else:
            # LineString/Point – make an area hull; if that still fails, use envelope
            hull_poly = h.buffer(0.0)
            if hull_poly.is_empty or getattr(hull_poly, "geom_type", "") != "Polygon":
                hull_poly = h.envelope
    else:
        # Whitespace/zero-outline fallback from font metrics (document units)
        hmtx = tt["hmtx"]
        adv_fu = sum(hmtx[tt.getGlyphName(gid)][0] for gid in gids)
        try:
            asc_fu = tt["OS/2"].sTypoAscender
            desc_fu = tt["OS/2"].sTypoDescender  # usually negative
        except Exception:
            asc_fu = tt["hhea"].ascent
            desc_fu = -tt["hhea"].descent

        # font-units -> px
        scale_px = size_px / float(upem)
        # px -> document units (mm/in/px) – only this uses CSS px definition
        units_per_px = _px_to_units(1.0, units, dpi)  # e.g., 25.4/96 for mm
        s = scale_px * units_per_px

        left, right = x, x + adv_fu * s
        if y_down:
            top, bottom = y - asc_fu * s, y - desc_fu * s
        else:
            top, bottom = y + asc_fu * s, y + desc_fu * s
        hull_poly = shapely_box(left, top, right, bottom)

    # 4) “Next pixel past the edge” – buffer by 1 CSS px *in document units*
    if add_one_pixel_margin:
        delta = _px_to_units(1.0, units, dpi)  # 1px == 1/96in by CSS, i.e. 25.4/96 mm
        hull_poly = hull_poly.buffer(delta, join_style=2)  # miter joins

    xmin, ymin, xmax, ymax = hull_poly.bounds
    bbox_coords = [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]
    hull_coords = (
        list(hull_poly.exterior.coords)
        if hasattr(hull_poly, "exterior") and not hull_poly.is_empty
        else []
    )

    return {
        "svg_path": d,
        "points": pts,
        "bbox": bbox_coords,
        "convex_hull": hull_coords,
        "path_bbox": path_bbox,  # optional, handy for your debug prints
    }
