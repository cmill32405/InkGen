"""
Utility helpers for working with external SVG assets.

Currently provides a flattening routine that collects path geometry,
applies any transforms, normalises coordinates to the origin, and exposes
basic metadata needed by the generator module.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from svgpathtools import Path, svg2paths2


@dataclass(frozen=True)
class FlattenedPath:
    """A single SVG path with its original styling information."""

    d: str
    style: str | None


@dataclass(frozen=True)
class FlattenedSVG:
    """Container describing the normalised geometry extracted from an SVG."""

    paths: list[FlattenedPath]
    bbox: tuple[tuple[float, float], tuple[float, float]]
    width: float | None
    height: float | None


def _style_from_attributes(attributes: dict[str, str]) -> str | None:
    style = attributes.get("style")
    if style:
        return style
    parts: list[str] = []
    if "fill" in attributes:
        parts.append(f"fill:{attributes['fill']}")
    if "stroke" in attributes:
        parts.append(f"stroke:{attributes['stroke']}")
    if "stroke-width" in attributes:
        parts.append(f"stroke-width:{attributes['stroke-width']}")
    if "fill-opacity" in attributes:
        parts.append(f"fill-opacity:{attributes['fill-opacity']}")
    if "stroke-opacity" in attributes:
        parts.append(f"stroke-opacity:{attributes['stroke-opacity']}")
    return ";".join(parts) if parts else None


def _parse_length(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        cleaned = "".join(ch for ch in value if ch.isdigit() or ch in {".", "-", "e", "E"})
        return float(cleaned)
    except ValueError:
        return None


def _collect_bbox(paths: Iterable[Path]) -> tuple[tuple[float, float], tuple[float, float]]:
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")
    for path in paths:
        try:
            bbox = path.bbox()
        except ValueError:
            continue
        xmin, xmax, ymin, ymax = bbox
        min_x = min(min_x, xmin)
        max_x = max(max_x, xmax)
        min_y = min(min_y, ymin)
        max_y = max(max_y, ymax)
    if min_x is float("inf"):
        return (0.0, 0.0), (0.0, 0.0)
    return (float(min_x), float(min_y)), (float(max_x), float(max_y))


def flatten_svg(filepath: str) -> FlattenedSVG:
    """
    Flatten an SVG document into a list of absolute path commands.

    The function applies all transforms, normalises the geometry so the
    upper-left corner of the bounding box is at the origin, and preserves
    style information for each path.
    """
    paths, attributes, svg_attributes = svg2paths2(filepath)
    if not paths:
        raise ValueError("No vector paths found in SVG.")

    bbox = _collect_bbox(paths)
    (min_x, min_y), (max_x, max_y) = bbox
    offset = complex(-min_x, -min_y)

    flattened_paths: list[FlattenedPath] = []
    translated_paths: list[Path] = []
    for path, attr in zip(paths, attributes, strict=False):
        translated = path.translated(offset)
        translated_paths.append(translated)
        flattened_paths.append(
            FlattenedPath(
                d=translated.d(),
                style=_style_from_attributes(attr),
            )
        )

    normalised_bbox = _collect_bbox(translated_paths)
    width = _parse_length(svg_attributes.get("width"))
    height = _parse_length(svg_attributes.get("height"))
    return FlattenedSVG(
        paths=flattened_paths,
        bbox=normalised_bbox,
        width=width,
        height=height,
    )
