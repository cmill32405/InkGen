"""Standalone, clipped, self-contained SVG region emission."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from html import escape
from os import PathLike
from pathlib import Path
from typing import Protocol
from xml.etree import ElementTree

from InkGen.component import TextComponent
from InkGen.drawing_components import OutputFormat
from InkGen.text_outline import outline_for_text, outline_for_text_bytes

_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
_URL_REFERENCE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)


class _SvgGeneratingComponent(Protocol):
    """Structural contract for an InkGen SVG component."""

    def generate_svg(self) -> str:
        """Return an SVG element fragment."""


class _NeutralDrawingPrimitive(Protocol):
    """Structural contract for a renderer-neutral InkGen primitive."""

    def to_component(self, output_format: OutputFormat | str) -> object:
        """Materialize this primitive for one output backend."""


def _finite_number(value: object, *, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _positive_number(value: object, *, name: str) -> float:
    number = _finite_number(value, name=name)
    if number <= 0.0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def _coordinate_pair(value: object, *, name: str) -> tuple[float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
        raise TypeError(f"{name} must contain two numeric values")
    return (
        _finite_number(value[0], name=f"{name} x"),
        _finite_number(value[1], name=f"{name} y"),
    )


def _number(value: float) -> str:
    if value == 0.0:
        return "0"
    return format(value, ".15g")


def _self_contained_paint(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{name} must be a non-empty SVG paint string")
    lowered = value.lower()
    if "url(" in lowered or "javascript:" in lowered:
        raise ValueError(f"{name} must not contain an external reference")
    return value


@dataclass(frozen=True)
class SvgClipWindow:
    """Rectangular SVG user-space window used for viewport and clipping."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite_number(self.x, name="x"))
        object.__setattr__(self, "y", _finite_number(self.y, name="y"))
        object.__setattr__(self, "width", _positive_number(self.width, name="width"))
        object.__setattr__(self, "height", _positive_number(self.height, name="height"))


@dataclass(frozen=True)
class PositionedTextRun:
    """Text and exact font source to materialize as positioned SVG outlines."""

    text: str
    position: tuple[float, float]
    font_size_px: float
    font_path: str | PathLike[str] | None = None
    font_program: bytes | None = None
    fill: str = "#000000"
    opacity: float = 1.0
    y_down: bool = True
    features: Mapping[str, bool] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("text must be a string")
        object.__setattr__(self, "position", _coordinate_pair(self.position, name="position"))
        object.__setattr__(self, "font_size_px", _positive_number(self.font_size_px, name="font_size_px"))
        if (self.font_path is None) == (self.font_program is None):
            raise ValueError("exactly one of font_path or font_program must be provided")
        if self.font_path is not None:
            path = Path(self.font_path)
            if not path.is_file():
                raise ValueError(f"font_path must identify a readable file: {path}")
            object.__setattr__(self, "font_path", path)
        if self.font_program is not None:
            if not isinstance(self.font_program, bytes):
                raise TypeError("font_program must be bytes")
            if not self.font_program:
                raise ValueError("font_program must not be empty")
        object.__setattr__(self, "fill", _self_contained_paint(self.fill, name="fill"))
        opacity = _finite_number(self.opacity, name="opacity")
        if not 0.0 <= opacity <= 1.0:
            raise ValueError("opacity must be between zero and one")
        object.__setattr__(self, "opacity", opacity)
        if not isinstance(self.y_down, bool):
            raise TypeError("y_down must be a boolean")
        if self.features is not None:
            features = dict(self.features)
            if not all(isinstance(name, str) and isinstance(enabled, bool) for name, enabled in features.items()):
                raise TypeError("features must map strings to booleans")
            object.__setattr__(self, "features", features)

    def outline(self) -> dict[str, object]:
        """Return exact SVG outline evidence for this run."""
        arguments = {
            "text": self.text,
            "size_px": self.font_size_px,
            "x": self.position[0],
            "y": self.position[1],
            "units": "px",
            "add_one_pixel_margin": False,
            "y_down": self.y_down,
            "features": None if self.features is None else dict(self.features),
        }
        if self.font_program is not None:
            return outline_for_text_bytes(font_program=self.font_program, **arguments)
        return outline_for_text(font_path=str(self.font_path), **arguments)


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _reference_is_internal(value: str) -> bool:
    normalized = value.strip().strip("'\"")
    return normalized.startswith("#") or normalized.lower().startswith("data:")


def _validate_self_contained_fragment(fragment: str) -> None:
    lowered_fragment = fragment.lower()
    if "<?" in fragment:
        raise ValueError("self-contained SVG cannot contain a processing instruction")
    if "javascript:" in lowered_fragment or "@import" in lowered_fragment:
        raise ValueError("SVG primitive contains an external reference")
    for match in _URL_REFERENCE.finditer(fragment):
        if not _reference_is_internal(match.group(2)):
            raise ValueError("SVG primitive contains an external reference")
    try:
        wrapper = ElementTree.fromstring(f"<wrapper>{fragment}</wrapper>")
    except ElementTree.ParseError as exc:
        raise ValueError("SVG primitive generated malformed XML") from exc
    for element in wrapper.iter():
        tag = _local_name(element.tag).lower()
        if tag == "text":
            raise TypeError("font-dependent text primitives are not allowed; use PositionedTextRun")
        if tag in {"script", "foreignobject"}:
            raise ValueError(f"self-contained SVG cannot contain {tag}")
        for attribute, value in element.attrib.items():
            attribute_name = _local_name(attribute).lower()
            if attribute_name == "href" and not _reference_is_internal(value):
                raise ValueError("SVG primitive contains an external reference")


def _render_primitive(primitive: _NeutralDrawingPrimitive | _SvgGeneratingComponent) -> str:
    concrete: object = primitive
    materialize = getattr(primitive, "to_component", None)
    if callable(materialize):
        concrete = materialize(OutputFormat.SVG)
    if isinstance(concrete, TextComponent):
        raise TypeError("font-dependent text primitives are not allowed; use PositionedTextRun")
    generate = getattr(concrete, "generate_svg", None)
    if not callable(generate):
        raise TypeError("vector_primitives must materialize to an SVG-generating component")
    fragment = generate()
    if not isinstance(fragment, str):
        raise TypeError("generate_svg() must return a string")
    _validate_self_contained_fragment(fragment)
    return fragment


def _render_text_run(run: PositionedTextRun) -> str:
    if not isinstance(run, PositionedTextRun):
        raise TypeError("text_runs must contain PositionedTextRun objects")
    path_data = run.outline()["svg_path"]
    if not isinstance(path_data, str):
        raise TypeError("text outline svg_path must be a string")
    title = escape(run.text)
    path = ""
    if path_data:
        path = (
            f'<path d="{escape(path_data, quote=True)}" fill="{escape(run.fill, quote=True)}" '
            f'fill-opacity="{_number(run.opacity)}" fill-rule="nonzero" stroke="none" />'
        )
    return f'<g aria-label="{escape(run.text, quote=True)}"><title>{title}</title>{path}</g>'


def emit_svg_region(
    *,
    clip_window: SvgClipWindow,
    text_runs: Sequence[PositionedTextRun] = (),
    vector_primitives: Sequence[_NeutralDrawingPrimitive | _SvgGeneratingComponent] = (),
    background: str | None = None,
) -> str:
    """Emit complete SVG for a clipped set of exact text and drawing evidence.

    Font-backed text is converted to paths, so the result does not depend on
    fonts installed on the viewing system. Primitive fragments may use only
    internal fragment identifiers or embedded ``data:`` resources.
    """
    if not isinstance(clip_window, SvgClipWindow):
        raise TypeError("clip_window must be an SvgClipWindow")
    if isinstance(text_runs, (str, bytes)) or not isinstance(text_runs, Sequence):
        raise TypeError("text_runs must be a sequence")
    if isinstance(vector_primitives, (str, bytes)) or not isinstance(vector_primitives, Sequence):
        raise TypeError("vector_primitives must be a sequence")
    background_fragment = ""
    if background is not None:
        paint = _self_contained_paint(background, name="background")
        background_fragment = (
            f'<rect x="{_number(clip_window.x)}" y="{_number(clip_window.y)}" '
            f'width="{_number(clip_window.width)}" height="{_number(clip_window.height)}" '
            f'fill="{escape(paint, quote=True)}" stroke="none" />'
        )
    primitive_fragments = "".join(_render_primitive(primitive) for primitive in vector_primitives)
    text_fragments = "".join(_render_text_run(run) for run in text_runs)
    clip_id = "inkgen-region-clip-0"
    x = _number(clip_window.x)
    y = _number(clip_window.y)
    width = _number(clip_window.width)
    height = _number(clip_window.height)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="{_SVG_NAMESPACE}" width="{width}" height="{height}" '
        f'viewBox="{x} {y} {width} {height}" overflow="hidden">'
        f'<defs><clipPath id="{clip_id}" clipPathUnits="userSpaceOnUse">'
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" />'
        "</clipPath></defs>"
        f'<g clip-path="url(#{clip_id})">{background_fragment}{primitive_fragments}{text_fragments}</g>'
        "</svg>"
    )
