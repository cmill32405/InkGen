"""Dependency-free PDF rendering backend for InkGen documents.

This module mirrors the SVG renderer with PDF-specific mixins over the existing
geometry, document, and style model. It intentionally uses only the Python
standard library so InkGen does not gain another PDF dependency.
"""

from __future__ import annotations

import abc
import hashlib
import math
import os
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fontTools.ttLib import TTFont

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
from InkGen.image_assets import RasterImageAsset, RasterImageComponent
from InkGen.pdf_render_contract import ensure_builtin_pdf_component, ensure_pdf_group
from InkGen.style import DrawingStyle, TextStyle
from InkGen.svg_generator import LabelGenerator, SegmentGenerator

PDF_FIXED_DATE = "D:20000101000000Z"
PDF_GENERIC_FONT_FAMILIES = {"serif", "sans-serif", "monospace", "cursive", "fantasy"}
PDF_WINANSI_FIRST_CHAR = 32
PDF_WINANSI_LAST_CHAR = 126
PDF_PAGE_BOX_NAMES = {
    "crop": "CropBox",
    "cropbox": "CropBox",
    "bleed": "BleedBox",
    "bleedbox": "BleedBox",
    "trim": "TrimBox",
    "trimbox": "TrimBox",
    "art": "ArtBox",
    "artbox": "ArtBox",
}


@dataclass(frozen=True)
class _PDFOutlineEntry:
    """Validated PDF outline item metadata."""

    title: str
    page_number: int
    left: float
    top: float | None
    zoom: float | None
    parent: str | None = None


@dataclass(frozen=True)
class _PDFUriLinkAnnotation:
    """Validated PDF URI link annotation metadata."""

    page_number: int
    rect: tuple[float, float, float, float]
    uri: str


@dataclass(frozen=True)
class _PDFPageLinkAnnotation:
    """Validated PDF internal page link annotation metadata."""

    page_number: int
    rect: tuple[float, float, float, float]
    target_page_number: int
    left: float
    top: float | None
    zoom: float | None


@dataclass(frozen=True)
class _PDFNamedDestination:
    """Validated PDF named destination metadata."""

    name: str
    page_number: int
    left: float
    top: float | None
    zoom: float | None


@dataclass(frozen=True)
class _PDFNamedDestinationLinkAnnotation:
    """Validated PDF link annotation targeting a named destination."""

    page_number: int
    rect: tuple[float, float, float, float]
    destination_name: str


@dataclass(frozen=True)
class _PDFTextAnnotation:
    """Validated PDF text annotation metadata."""

    page_number: int
    rect: tuple[float, float, float, float]
    contents: str
    title: str | None
    open: bool


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
    font_registry: _PDFFontRegistry | None = None
    image_registry: _PDFImageRegistry | None = None
    graphics_state_registry: _PDFGraphicsStateRegistry | None = None

    def font_resource_name(self, style: TextStyle) -> str:
        """Return the PDF font resource name for a text style."""
        if self.font_registry is None:
            return "F1"
        return self.font_registry.resource_name_for_style(style)

    def image_resource_name(self, image: RasterImageAsset) -> str:
        """Return the PDF image XObject resource name for an image asset."""
        if self.image_registry is None:
            return "Im1"
        return self.image_registry.resource_name_for_asset(image)

    def graphics_state_resource_name(self, *, stroke_opacity: float = 1.0, fill_opacity: float = 1.0) -> str | None:
        """Return a PDF ExtGState resource name for non-opaque drawing opacity."""
        if self.graphics_state_registry is None:
            return None
        return self.graphics_state_registry.resource_name_for_opacity(stroke_opacity=stroke_opacity, fill_opacity=fill_opacity)


@dataclass(frozen=True)
class _PDFImagePayload:
    """Prepared PDF image samples and color metadata."""

    color_samples: bytes
    alpha_samples: bytes | None
    color_filter: str
    color_space: str
    icc_profile: bytes | None = None


@dataclass(frozen=True)
class _PDFFontResource:
    """PDF font resource metadata for standard or embedded fonts."""

    resource_name: str
    base_font: str
    font_file: str | None = None
    font_data: bytes | None = None
    font_file_key: str | None = None
    widths: tuple[int, ...] = ()
    font_bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    ascent: int = 0
    descent: int = 0
    cap_height: int = 0
    italic_angle: float = 0.0
    stem_v: int = 80

    @property
    def is_embedded(self) -> bool:
        """Return whether this font needs embedded PDF font objects."""
        return self.font_file is not None and self.font_data is not None and self.font_file_key is not None


class _PDFFontRegistry:
    """Deterministic registry for PDF text font resources."""

    def __init__(self) -> None:
        self._resource_by_key: dict[tuple[str, str], str] = {}
        self._resource_by_name: dict[str, _PDFFontResource] = {}

    def resource_name_for_style(self, style: TextStyle) -> str:
        """Return a stable resource name for the style's PDF font."""
        resource = _pdf_embedded_font_for_style(style)
        if resource is None:
            return self.resource_name_for_base_font(_pdf_base_font_for_style(style))
        return self._resource_name_for_resource(("embedded", resource.font_file or resource.base_font), resource)

    def resource_name_for_base_font(self, base_font: str) -> str:
        """Return a stable resource name for a PDF Standard 14 base font."""
        resource = _PDFFontResource(resource_name="", base_font=base_font)
        return self._resource_name_for_resource(("standard", base_font), resource)

    def _resource_name_for_resource(self, key: tuple[str, str], resource: _PDFFontResource) -> str:
        """Return a stable resource name for a concrete font resource."""
        if key not in self._resource_by_key:
            resource_name = f"F{len(self._resource_by_key) + 1}"
            self._resource_by_key[key] = resource_name
            self._resource_by_name[resource_name] = _PDFFontResource(
                resource_name=resource_name,
                base_font=resource.base_font,
                font_file=resource.font_file,
                font_data=resource.font_data,
                font_file_key=resource.font_file_key,
                widths=resource.widths,
                font_bbox=resource.font_bbox,
                ascent=resource.ascent,
                descent=resource.descent,
                cap_height=resource.cap_height,
                italic_angle=resource.italic_angle,
                stem_v=resource.stem_v,
            )
        return self._resource_by_key[key]

    def resources(self) -> tuple[_PDFFontResource, ...]:
        """Return PDF font resources in deterministic insertion order."""
        return tuple(self._resource_by_name.values())


class _PDFImageRegistry:
    """Deterministic registry for PDF image XObject resources."""

    def __init__(self) -> None:
        self._resource_by_digest: dict[str, str] = {}
        self._asset_by_resource: dict[str, RasterImageAsset] = {}

    def resource_name_for_asset(self, asset: RasterImageAsset) -> str:
        """Return a stable resource name for an image asset."""
        digest = hashlib.sha256(asset.data).hexdigest()
        if digest not in self._resource_by_digest:
            resource_name = f"Im{len(self._resource_by_digest) + 1}"
            self._resource_by_digest[digest] = resource_name
            self._asset_by_resource[resource_name] = asset
        return self._resource_by_digest[digest]

    def resources(self) -> tuple[tuple[str, RasterImageAsset], ...]:
        """Return resource-name/image-asset pairs in deterministic insertion order."""
        return tuple(self._asset_by_resource.items())


class _PDFGraphicsStateRegistry:
    """Deterministic registry for PDF external graphics-state resources."""

    def __init__(self) -> None:
        self._resource_by_opacity: dict[tuple[float, float], str] = {}

    def resource_name_for_opacity(self, *, stroke_opacity: float = 1.0, fill_opacity: float = 1.0) -> str | None:
        """Return a resource name for non-default stroke/fill opacity values."""
        stroke_alpha = _opacity_value(stroke_opacity, "stroke_opacity")
        fill_alpha = _opacity_value(fill_opacity, "fill_opacity")
        if stroke_alpha == 1.0 and fill_alpha == 1.0:
            return None
        key = (stroke_alpha, fill_alpha)
        if key not in self._resource_by_opacity:
            self._resource_by_opacity[key] = f"GS{len(self._resource_by_opacity) + 1}"
        return self._resource_by_opacity[key]

    def resources(self) -> tuple[tuple[str, float, float], ...]:
        """Return graphics-state resource definitions in deterministic order."""
        by_name = {name: key for key, name in self._resource_by_opacity.items()}
        return tuple((name, by_name[name][0], by_name[name][1]) for name in sorted(by_name, key=lambda value: int(value[2:])))


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


def _coerce_pdf_page_label(label: object) -> str:
    """Return a PDF literal-string-safe page label."""
    if not isinstance(label, str):
        raise TypeError("page label must be a string")
    if not label:
        raise ValueError("page label must not be empty")
    try:
        label.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise ValueError("page label must be encodable as latin-1") from exc
    return label


def _coerce_pdf_page_box_name(name: object) -> str:
    """Return the canonical PDF page-box dictionary key."""
    if not isinstance(name, str):
        raise TypeError("page box name must be a string")
    normalized = name.removeprefix("/").lower()
    if normalized not in PDF_PAGE_BOX_NAMES:
        raise ValueError("page box name must be CropBox, BleedBox, TrimBox, or ArtBox")
    return PDF_PAGE_BOX_NAMES[normalized]


def _coerce_pdf_page_box(
    box: object,
    *,
    canvas_width: float,
    canvas_height: float,
) -> tuple[float, float, float, float]:
    """Return a validated PDF page box in bottom-left page coordinates."""
    if isinstance(box, (str, bytes)) or not isinstance(box, Sequence) or len(box) != 4:
        raise TypeError("page box must be a four-number sequence")
    values = []
    for value in box:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError("page box coordinates must be finite numbers")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("page box coordinates must be finite numbers")
        values.append(number)
    left, bottom, right, top = values
    if not (0.0 <= left < right <= canvas_width and 0.0 <= bottom < top <= canvas_height):
        raise ValueError("page box must fit inside the page MediaBox with positive area")
    return left, bottom, right, top


def _coerce_pdf_outline_title(title: object) -> str:
    """Return a PDF literal-string-safe outline title."""
    if not isinstance(title, str):
        raise TypeError("outline title must be a string")
    if not title:
        raise ValueError("outline title must not be empty")
    try:
        title.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise ValueError("outline title must be encodable as latin-1") from exc
    return title


def _coerce_pdf_destination_name(name: object) -> str:
    """Return a PDF literal-string-safe named destination key."""
    if not isinstance(name, str):
        raise TypeError("named destination must be a string")
    if not name:
        raise ValueError("named destination must not be empty")
    try:
        name.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise ValueError("named destination must be encodable as latin-1") from exc
    return name


def _coerce_pdf_destination_number(value: object, name: str, *, owner: str = "outline") -> float:
    """Return a finite PDF destination coordinate or zoom value."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{owner} {name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{owner} {name} must be a finite number")
    return number


def _coerce_pdf_outline_destination_token(value: float | None) -> str:
    """Return a PDF outline destination number or null token."""
    if value is None:
        return "null"
    return _number(value)


def _coerce_pdf_uri(uri: object) -> str:
    """Return a PDF literal-string-safe URI target."""
    if not isinstance(uri, str):
        raise TypeError("URI link target must be a string")
    if not uri:
        raise ValueError("URI link target must not be empty")
    try:
        uri.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise ValueError("URI link target must be encodable as latin-1") from exc
    return uri


def _coerce_pdf_annotation_text(value: object, name: str) -> str:
    """Return a PDF literal-string-safe annotation text field."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value:
        raise ValueError(f"{name} must not be empty")
    try:
        value.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} must be encodable as latin-1") from exc
    return value


def _coerce_pdf_annotation_open(value: object) -> bool:
    """Return a strict PDF text annotation open-state flag."""
    if not isinstance(value, bool):
        raise TypeError("text annotation open must be a boolean")
    return value


def _coerce_pdf_link_rect(
    rect: object,
    *,
    canvas_width: float,
    canvas_height: float,
) -> tuple[float, float, float, float]:
    """Return a validated PDF annotation rectangle in bottom-left page coordinates."""
    return _coerce_pdf_page_box(rect, canvas_width=canvas_width, canvas_height=canvas_height)


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


def _opacity_value(value: float | int, name: str) -> float:
    """Return a validated PDF opacity value."""
    opacity = float(value)
    if math.isfinite(opacity) and not isinstance(value, bool) and 0.0 <= opacity <= 1.0:
        return opacity
    raise ValueError(f"{name} must be a finite number between 0.0 and 1.0")


def _pdf_extgstate_object(*, stroke_opacity: float, fill_opacity: float) -> str:
    """Build a PDF ExtGState dictionary for stroke and fill opacity."""
    stroke_alpha = _opacity_value(stroke_opacity, "stroke_opacity")
    fill_alpha = _opacity_value(fill_opacity, "fill_opacity")
    return f"<< /Type /ExtGState /CA {_number(stroke_alpha)} /ca {_number(fill_alpha)} >>"


def _pdf_stroke_presentation_operators(style: DrawingStyle) -> list[str]:
    """Return PDF stroke dash, cap, join, and miter operators for a style."""
    operators: list[str] = []
    dasharray = getattr(style, "stroke_dasharray", ())
    if dasharray:
        dash_values = " ".join(_number(value) for value in dasharray)
        dash_offset = getattr(style, "stroke_dash_offset", 0.0)
        operators.append(f"[{dash_values}] {_number(dash_offset)} d")
    linecap = getattr(style, "stroke_linecap", "butt")
    if linecap != "butt":
        operators.append(f"{ {'round': 1, 'square': 2}[linecap] } J")
    linejoin = getattr(style, "stroke_linejoin", "miter")
    if linejoin != "miter":
        operators.append(f"{ {'round': 1, 'bevel': 2}[linejoin] } j")
    miterlimit = getattr(style, "stroke_miterlimit", 10.0)
    if miterlimit != 10.0:
        operators.append(f"{_number(miterlimit)} M")
    return operators


def _pdf_image_payload(asset: RasterImageAsset) -> _PDFImagePayload:
    """Return color samples, optional alpha samples, and PDF color metadata."""
    color_space = asset.jpeg_passthrough_color_space
    if color_space is not None:
        return _PDFImagePayload(asset.data, None, "DCTDecode", color_space, asset.icc_profile_bytes())
    with asset.image() as image:
        rgba = image.convert("RGBA")
        color = rgba.convert("RGB").tobytes()
        alpha = rgba.getchannel("A").tobytes()
    if all(value == 255 for value in alpha):
        return _PDFImagePayload(color, None, "FlateDecode", "DeviceRGB")
    return _PDFImagePayload(color, alpha, "FlateDecode", "DeviceRGB")


def _pdf_image_xobject(
    *,
    width: int,
    height: int,
    color_space: str,
    samples: bytes,
    smask_object_id: int | None = None,
    filter_name: str = "FlateDecode",
) -> bytes:
    """Build a PDF image XObject stream."""
    payload = zlib.compress(samples) if filter_name == "FlateDecode" else samples
    dictionary = (
        f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
        f"/ColorSpace {_pdf_color_space_token(color_space)} /BitsPerComponent 8 /Filter /{filter_name} /Length {len(payload)}"
    )
    if smask_object_id is not None:
        dictionary += f" /SMask {smask_object_id} 0 R"
    dictionary += " >>"
    return dictionary.encode("ascii") + b"\nstream\n" + payload + b"\nendstream"


def _pdf_color_space_token(color_space: str) -> str:
    """Return a PDF color-space token for name or array-style color spaces."""
    if color_space.startswith("["):
        return color_space
    return f"/{color_space}"


def _pdf_icc_profile_object(profile: bytes, *, components: int, alternate: str) -> bytes:
    """Build a compressed ICC profile stream object."""
    compressed = zlib.compress(profile)
    dictionary = f"<< /N {components} /Alternate /{alternate} /Filter /FlateDecode /Length {len(compressed)} >>"
    return dictionary.encode("ascii") + b"\nstream\n" + compressed + b"\nendstream"


def _pdf_embedded_font_for_style(style: TextStyle) -> _PDFFontResource | None:
    """Return embedded font metadata for named installed fonts when available."""
    font = getattr(style, "font", None)
    if font is None or _pdf_requested_family_is_generic(font):
        return None
    try:
        font_file = str(font.font_file)
    except (AttributeError, OSError, ValueError):
        return None
    if not font_file or not os.path.isfile(font_file):
        return None
    try:
        return _pdf_embedded_font_resource(font_file)
    except (KeyError, OSError, ValueError, TypeError):
        return None


def _pdf_requested_family_is_generic(font: object) -> bool:
    """Return whether the requested family should stay on PDF Standard fonts."""
    requested = getattr(font, "requested_family", getattr(font, "family", "sans-serif"))
    families = requested if isinstance(requested, list) else [requested]
    return all(str(family).lower() in PDF_GENERIC_FONT_FAMILIES for family in families)


def _pdf_embedded_font_resource(font_file: str) -> _PDFFontResource:
    """Build a PDF embedded-font resource from a TrueType/OpenType file."""
    font = TTFont(font_file, fontNumber=0)
    try:
        units_per_em = int(font["head"].unitsPerEm)
        if units_per_em <= 0:
            raise ValueError("font units per em must be positive")
        postscript_name = font["name"].getDebugName(6) or os.path.splitext(os.path.basename(font_file))[0]
        base_font = _pdf_name(str(postscript_name))
        cmap = font.getBestCmap() or {}
        hmtx = font["hmtx"].metrics
        widths = tuple(
            _pdf_glyph_width(code, cmap, hmtx, units_per_em) for code in range(PDF_WINANSI_FIRST_CHAR, PDF_WINANSI_LAST_CHAR + 1)
        )
        head = font["head"]
        hhea = font["hhea"]
        os2 = font["OS/2"] if "OS/2" in font else None
        post = font["post"] if "post" in font else None
        font_file_key = "FontFile2" if "glyf" in font else "FontFile3"
    finally:
        font.close()
    with open(font_file, "rb") as handle:
        font_data = handle.read()
    return _PDFFontResource(
        resource_name="",
        base_font=base_font,
        font_file=font_file,
        font_data=font_data,
        font_file_key=font_file_key,
        widths=widths,
        font_bbox=(
            _pdf_font_unit(head.xMin, units_per_em),
            _pdf_font_unit(head.yMin, units_per_em),
            _pdf_font_unit(head.xMax, units_per_em),
            _pdf_font_unit(head.yMax, units_per_em),
        ),
        ascent=_pdf_font_unit(hhea.ascent, units_per_em),
        descent=_pdf_font_unit(hhea.descent, units_per_em),
        cap_height=_pdf_font_unit(getattr(os2, "sCapHeight", hhea.ascent), units_per_em),
        italic_angle=float(getattr(post, "italicAngle", 0.0)),
        stem_v=80,
    )


def _pdf_glyph_width(codepoint: int, cmap: dict[int, str], metrics: Mapping[str, tuple[int, int]], units_per_em: int) -> int:
    """Return a 1000-unit PDF width for one WinAnsi codepoint."""
    glyph_name = cmap.get(codepoint)
    if glyph_name is None:
        return 0
    return _pdf_font_unit(metrics.get(glyph_name, (0, 0))[0], units_per_em)


def _pdf_font_unit(value: float | int, units_per_em: int) -> int:
    """Scale a font design-unit value to PDF's 1000-unit text space."""
    return int(round(float(value) * 1000.0 / float(units_per_em)))


def _pdf_name(value: str) -> str:
    """Return a PDF name body with unsafe bytes hex-escaped."""
    encoded = value.encode("ascii", errors="ignore") or b"EmbeddedFont"
    allowed = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    return "".join(chr(byte) if byte in allowed else f"#{byte:02X}" for byte in encoded)


def _pdf_font_file_object(resource: _PDFFontResource) -> bytes:
    """Build an embedded font-file stream object."""
    if resource.font_data is None or resource.font_file_key is None:
        raise ValueError("embedded font resources require font data")
    compressed = zlib.compress(resource.font_data)
    subtype = " /Subtype /OpenType" if resource.font_file_key == "FontFile3" else ""
    dictionary = f"<< /Length {len(compressed)} /Filter /FlateDecode{subtype} >>"
    return dictionary.encode("ascii") + b"\nstream\n" + compressed + b"\nendstream"


def _pdf_font_descriptor_object(resource: _PDFFontResource, font_file_object_id: int) -> str:
    """Build a PDF font descriptor object for an embedded font."""
    x_min, y_min, x_max, y_max = resource.font_bbox
    return (
        f"<< /Type /FontDescriptor /FontName /{resource.base_font} /Flags 32 "
        f"/FontBBox [{x_min} {y_min} {x_max} {y_max}] "
        f"/ItalicAngle {_number(resource.italic_angle)} /Ascent {resource.ascent} "
        f"/Descent {resource.descent} /CapHeight {resource.cap_height} /StemV {resource.stem_v} "
        f"/{resource.font_file_key} {font_file_object_id} 0 R >>"
    )


def _pdf_tounicode_cmap_object() -> bytes:
    """Build a deterministic ToUnicode CMap for InkGen's WinAnsi text domain."""
    entries = "\n".join(f"<{code:02X}> <{code:04X}>" for code in range(PDF_WINANSI_FIRST_CHAR, PDF_WINANSI_LAST_CHAR + 1))
    payload = (
        "/CIDInit /ProcSet findresource begin\n"
        "12 dict begin\n"
        "begincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /InkGen-WinAnsi-UCS2 def\n"
        "/CMapType 2 def\n"
        "1 begincodespacerange\n"
        f"<{PDF_WINANSI_FIRST_CHAR:02X}> <{PDF_WINANSI_LAST_CHAR:02X}>\n"
        "endcodespacerange\n"
        f"{PDF_WINANSI_LAST_CHAR - PDF_WINANSI_FIRST_CHAR + 1} beginbfchar\n"
        f"{entries}\n"
        "endbfchar\n"
        "endcmap\n"
        "CMapName currentdict /CMap defineresource pop\n"
        "end\n"
        "end\n"
    ).encode("ascii")
    return b"<< /Length " + str(len(payload)).encode("ascii") + b" >>\nstream\n" + payload + b"endstream"


def _pdf_font_object(
    resource: _PDFFontResource,
    descriptor_object_id: int | None = None,
    tounicode_object_id: int | None = None,
) -> str:
    """Build a PDF font object for standard or embedded resources."""
    tounicode = f" /ToUnicode {tounicode_object_id} 0 R" if tounicode_object_id is not None else ""
    if not resource.is_embedded:
        return f"<< /Type /Font /Subtype /Type1 /BaseFont /{resource.base_font} /Encoding /WinAnsiEncoding{tounicode} >>"
    if descriptor_object_id is None:
        raise ValueError("embedded font resources require a descriptor object id")
    widths = " ".join(str(width) for width in resource.widths)
    return (
        f"<< /Type /Font /Subtype /TrueType /BaseFont /{resource.base_font} "
        f"/FirstChar {PDF_WINANSI_FIRST_CHAR} /LastChar {PDF_WINANSI_LAST_CHAR} "
        f"/Widths [{widths}] /FontDescriptor {descriptor_object_id} 0 R "
        f"/Encoding /WinAnsiEncoding{tounicode} >>"
    )


def _pdf_base_font_for_style(style: TextStyle) -> str:
    """Map an InkGen text style to a built-in PDF Standard 14 base font."""
    font = getattr(style, "font", None)
    family = str(getattr(font, "family", "Helvetica")).lower()
    font_style = str(getattr(font, "style", "normal")).lower()
    font_weight = getattr(font, "weight", "normal")
    weight_text = str(font_weight).lower()
    is_bold = weight_text in {"bold", "heavy", "black", "demibold", "semibold", "extra bold"} or (
        isinstance(font_weight, int) and not isinstance(font_weight, bool) and font_weight >= 600
    )
    is_italic = font_style in {"italic", "oblique"}

    if "courier" in family or "mono" in family:
        if is_bold and is_italic:
            return "Courier-BoldOblique"
        if is_bold:
            return "Courier-Bold"
        if is_italic:
            return "Courier-Oblique"
        return "Courier"
    if "times" in family or "serif" in family:
        if is_bold and is_italic:
            return "Times-BoldItalic"
        if is_bold:
            return "Times-Bold"
        if is_italic:
            return "Times-Italic"
        return "Times-Roman"
    if is_bold and is_italic:
        return "Helvetica-BoldOblique"
    if is_bold:
        return "Helvetica-Bold"
    if is_italic:
        return "Helvetica-Oblique"
    return "Helvetica"


def _style_operators(
    style: DrawingStyle,
    *,
    fill: bool = True,
    stroke: bool = True,
    context: PDFRenderContext | None = None,
) -> list[str]:
    """Emit PDF graphics-state operators for an InkGen drawing style."""
    operators: list[str] = []
    if context is not None:
        graphics_state = context.graphics_state_resource_name(
            stroke_opacity=getattr(style, "stroke_opacity", 1.0) if stroke else 1.0,
            fill_opacity=getattr(style, "fill_opacity", 1.0) if fill else 1.0,
        )
        if graphics_state is not None:
            operators.append(f"/{graphics_state} gs")
    if stroke:
        stroke_color = _color_components(getattr(style, "stroke", "none"))
        if stroke_color is not None:
            operators.append(f"{_number(stroke_color[0])} {_number(stroke_color[1])} {_number(stroke_color[2])} RG")
        operators.append(f"{_number(getattr(style, 'stroke_width', 0.0))} w")
        operators.extend(_pdf_stroke_presentation_operators(style))
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


def _drawing_pdf(
    style: DrawingStyle,
    path_operators: list[str],
    *,
    fill: bool = True,
    stroke: bool = True,
    context: PDFRenderContext | None = None,
) -> str:
    """Wrap a path with style and paint operators."""
    operators = ["q"]
    operators.extend(_style_operators(style, fill=fill, stroke=stroke, context=context))
    operators.extend(path_operators)
    operators.append(_paint_operator(style, fill=fill, stroke=stroke))
    operators.append("Q")
    return "\n".join(operators)


def _primitive_parameters(name: str, *, values: dict[str, object], style: DrawingStyle | TextStyle) -> dict[str, dict[str, object]]:
    """Return a serialization dictionary for a PDF primitive component."""
    payload = dict(values)
    payload["style"] = style.parameters
    return {name: payload}


def _pdf_payload(data: object, key: str) -> Mapping[str, object]:
    """Return the serialized PDF component payload for a class key or fail explicitly."""
    if not isinstance(data, Mapping):
        raise TypeError(f"{key} data must be a mapping")
    if key not in data:
        raise ValueError(f"{key} data must include {key}")
    payload = data[key]
    if not isinstance(payload, Mapping):
        raise TypeError(f"{key} payload must be a mapping")
    return payload


def _pdf_required_field(payload: Mapping[str, object], name: str, owner: str) -> object:
    """Return a required serialized PDF component field or fail explicitly."""
    if name not in payload:
        raise ValueError(f"{owner} payload must include {name}")
    return payload[name]


def _pdf_optional_sequence(payload: Mapping[str, object], name: str, owner: str) -> Sequence[object]:
    """Return an optional serialized PDF sequence field or fail explicitly."""
    value = payload.get(name, [])
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{owner} {name} must be a sequence")
    return value


def _pdf_required_sequence(payload: Mapping[str, object], name: str, owner: str) -> Sequence[object]:
    """Return a required serialized PDF sequence field or fail explicitly."""
    value = _pdf_required_field(payload, name, owner)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{owner} {name} must be a sequence")
    return value


def _pdf_required_mapping(payload: Mapping[str, object], name: str, owner: str) -> Mapping[str, object]:
    """Return a required serialized PDF mapping field or fail explicitly."""
    value = _pdf_required_field(payload, name, owner)
    if not isinstance(value, Mapping):
        raise TypeError(f"{owner} {name} must be a mapping")
    return value


def _pdf_optional_mapping(payload: Mapping[str, object], name: str, owner: str) -> Mapping[object, object]:
    """Return an optional serialized PDF mapping field or fail explicitly."""
    value = payload.get(name, {})
    if not isinstance(value, Mapping):
        raise TypeError(f"{owner} {name} must be a mapping")
    return value


def _pdf_page_number_key(value: object, owner: str) -> int:
    """Return a positive one-based page number from a serialized page metadata key."""
    if isinstance(value, bool):
        raise TypeError(f"{owner} page number keys must be positive integers")
    if isinstance(value, int):
        page_number = value
    elif isinstance(value, str) and value.isdecimal():
        page_number = int(value)
    else:
        raise TypeError(f"{owner} page number keys must be positive integers")
    if page_number < 1:
        raise ValueError(f"{owner} page number keys must be positive integers")
    return page_number


def _pdf_single_mapping_entry(payload: object, owner: str) -> tuple[str, Mapping[str, object]]:
    """Return the single typed payload entry for a PDF group child or style."""
    if not isinstance(payload, Mapping):
        raise TypeError(f"{owner} entry must be a mapping")
    if len(payload) != 1:
        raise ValueError(f"{owner} entry must contain one type")
    entry_type = next(iter(payload))
    if not isinstance(entry_type, str):
        raise TypeError(f"{owner} type must be a string")
    entry_payload = payload[entry_type]
    if not isinstance(entry_payload, Mapping):
        raise TypeError(f"{owner} payload must be a mapping")
    return entry_type, entry_payload


def _pdf_style_entry(payload: object) -> tuple[str, Mapping[str, object], str, type]:
    """Return a validated PDF child style envelope."""
    style_type, style_payload = _pdf_single_mapping_entry(payload, "PDF component style")
    style_name = style_payload.get("name")
    if not isinstance(style_name, str):
        raise TypeError("PDF component style name must be a string")
    style_class = globals().get(style_type)
    if style_class not in (DrawingStyle, TextStyle):
        raise ValueError(f"Unsupported PDF component style payload type: {style_type}")
    return style_type, style_payload, style_name, style_class


def _path_command_from_dict(data: object) -> PathCommand:
    """Recreate a PathCommand from serialized command parameters."""
    if not isinstance(data, Mapping):
        raise TypeError("PathPDF command payload must be a mapping")
    command_type = _pdf_required_field(data, "type", "PathPDF command")
    if not isinstance(command_type, str):
        raise TypeError("PathPDF command type must be a string")
    command = PathCommand(command_type, data.get("points", []))
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
        payload = _pdf_payload(data, "RectanglePDF")
        if style is None:
            style = DrawingStyle.create_from_dict(_pdf_required_field(payload, "style", "RectanglePDF"))
        return cls(
            _pdf_required_field(payload, "position", "RectanglePDF"),
            _pdf_required_field(payload, "width", "RectanglePDF"),
            _pdf_required_field(payload, "height", "RectanglePDF"),
            _pdf_required_field(payload, "corner_radii", "RectanglePDF"),
            style,
        )

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
        return _drawing_pdf(self.style, path, context=context)


class LinePDF(StandardDrawingComponent, PDFGeneratorInterface):
    """PDF representation of a line component."""

    def __init__(self, point_1: tuple[float, float], point_2: tuple[float, float], style: DrawingStyle) -> None:
        """Create a PDF line between two points."""
        super().__init__(point_1=point_1, point_2=point_2, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> LinePDF:
        """Recreate a LinePDF from serialized parameters."""
        payload = _pdf_payload(data, "LinePDF")
        if style is None:
            style = DrawingStyle.create_from_dict(_pdf_required_field(payload, "style", "LinePDF"))
        return cls(
            tuple(_pdf_required_field(payload, "point_1", "LinePDF")),
            tuple(_pdf_required_field(payload, "point_2", "LinePDF")),
            style,
        )

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
        return _drawing_pdf(self.style, path, fill=False, context=context)


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
        payload = _pdf_payload(data, "ArcPDF")
        if style is None:
            style = DrawingStyle.create_from_dict(_pdf_required_field(payload, "style", "ArcPDF"))
        return cls(
            center=tuple(_pdf_required_field(payload, "center", "ArcPDF")),
            radius_x=_pdf_required_field(payload, "radius_x", "ArcPDF"),
            radius_y=_pdf_required_field(payload, "radius_y", "ArcPDF"),
            start_angle=_pdf_required_field(payload, "start_angle", "ArcPDF"),
            end_angle=_pdf_required_field(payload, "end_angle", "ArcPDF"),
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
        return _drawing_pdf(self.style, _path_from_points(list(self.points), close=False), fill=False, context=context)


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
        payload = _pdf_payload(data, "QuadraticBezierPDF")
        if style is None:
            style = DrawingStyle.create_from_dict(_pdf_required_field(payload, "style", "QuadraticBezierPDF"))
        return cls(
            tuple(_pdf_required_field(payload, "start_point", "QuadraticBezierPDF")),
            tuple(_pdf_required_field(payload, "control_point", "QuadraticBezierPDF")),
            tuple(_pdf_required_field(payload, "end_point", "QuadraticBezierPDF")),
            style,
        )

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
        return _drawing_pdf(self.style, path, fill=False, context=context)


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
        payload = _pdf_payload(data, "CubicBezierPDF")
        if style is None:
            style = DrawingStyle.create_from_dict(_pdf_required_field(payload, "style", "CubicBezierPDF"))
        return cls(
            tuple(_pdf_required_field(payload, "start_point", "CubicBezierPDF")),
            tuple(_pdf_required_field(payload, "control_point1", "CubicBezierPDF")),
            tuple(_pdf_required_field(payload, "control_point2", "CubicBezierPDF")),
            tuple(_pdf_required_field(payload, "end_point", "CubicBezierPDF")),
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
        return _drawing_pdf(self.style, path, fill=False, context=context)


class PathPDF(PathComponent, PDFGeneratorInterface):
    """PDF representation of a generic path built from commands."""

    def __init__(self, style: DrawingStyle, commands: list[PathCommand] | None = None) -> None:
        """Create a PDF path from SVG-style path commands."""
        super().__init__(style=style, commands=commands)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> PathPDF:
        """Recreate a PathPDF from serialized parameters."""
        payload = _pdf_payload(data, "PathPDF")
        if style is None:
            style = DrawingStyle.create_from_dict(_pdf_required_field(payload, "style", "PathPDF"))
        commands = [_path_command_from_dict(command) for command in _pdf_optional_sequence(payload, "commands", "PathPDF")]
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
        return _drawing_pdf(self.style, self._command_operators(), context=context)


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
        payload = _pdf_payload(data, "RegularPolygonPDF")
        if style is None:
            style = DrawingStyle.create_from_dict(_pdf_required_field(payload, "style", "RegularPolygonPDF"))
        return cls(
            tuple(_pdf_required_field(payload, "position", "RegularPolygonPDF")),
            _pdf_required_field(payload, "sides", "RegularPolygonPDF"),
            _pdf_required_field(payload, "radius", "RegularPolygonPDF"),
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
        return _drawing_pdf(self.style, _path_from_points(self._get_points(), close=True), context=context)


class PolygonalPDF(PolygonalDrawingComponent, PDFGeneratorInterface):
    """PDF representation of an irregular polygon."""

    def __init__(self, points: list[tuple[float, float]], style: DrawingStyle) -> None:
        """Create a PDF polygon from explicit points."""
        super().__init__(points=points, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> PolygonalPDF:
        """Recreate a PolygonalPDF from serialized parameters."""
        payload = _pdf_payload(data, "PolygonalPDF")
        if style is None:
            style = DrawingStyle.create_from_dict(_pdf_required_field(payload, "style", "PolygonalPDF"))
        return cls([tuple(point) for point in _pdf_required_field(payload, "points", "PolygonalPDF")], style)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters("PolygonalPDF", values={"points": self.points}, style=self.style)

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators for this polygon."""
        return _drawing_pdf(self.style, _path_from_points(list(self.points), close=True), context=context)


class CirclePDF(SingleDimensionDrawingComponent, PDFGeneratorInterface):
    """PDF representation of a circle component."""

    def __init__(self, position: tuple[float, float], radius: float, style: DrawingStyle) -> None:
        """Create a PDF circle."""
        super().__init__(position, self._coerce_radius(radius), style)

    @staticmethod
    def _coerce_radius(radius: float | int) -> float:
        """Return a finite positive circle radius or fail at the public boundary."""
        if isinstance(radius, bool):
            raise TypeError("Radii must be numeric.")
        if not isinstance(radius, (float, int)):
            raise ValueError("Radii must be greater than 0")
        numeric = float(radius)
        if not math.isfinite(numeric) or numeric <= 0:
            raise ValueError("Radii must be greater than 0")
        return numeric

    @property
    def radius(self) -> float:
        """Return the circle radius."""
        return self.size

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle | None = None) -> CirclePDF:
        """Recreate a CirclePDF from serialized parameters."""
        payload = _pdf_payload(data, "CirclePDF")
        if style is None:
            style = DrawingStyle.create_from_dict(_pdf_required_field(payload, "style", "CirclePDF"))
        return cls(tuple(_pdf_required_field(payload, "position", "CirclePDF")), _pdf_required_field(payload, "radius", "CirclePDF"), style)

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
        return _drawing_pdf(self.style, path, context=context)


class TextPDF(TextComponent, PDFGeneratorInterface):
    """PDF representation of a text component."""

    def __init__(self, text: str, position: tuple[float, float], style: TextStyle) -> None:
        """Create a PDF text component."""
        super().__init__(text=text, position=position, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: TextStyle | None = None) -> TextPDF:
        """Recreate a TextPDF from serialized parameters."""
        payload = _pdf_payload(data, "TextPDF")
        if style is None:
            style = TextStyle.create_from_dict(_pdf_required_field(payload, "style", "TextPDF"))
        return cls(_pdf_required_field(payload, "text", "TextPDF"), tuple(_pdf_required_field(payload, "position", "TextPDF")), style)

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
        font_resource = context.font_resource_name(self.style) if context is not None else "F1"
        return "\n".join(
            [
                "q",
                f"{_number(color[0])} {_number(color[1])} {_number(color[2])} rg",
                "BT",
                f"/{font_resource} {_number(size)} Tf",
                f"1 0 0 -1 {_number(x)} {_number(y)} Tm",
                f"({escaped}) Tj",
                "ET",
                "Q",
            ]
        )


class ImagePDF(RasterImageComponent, PDFGeneratorInterface):
    """PDF raster image component using an image XObject resource."""

    def __init__(
        self,
        image: RasterImageAsset,
        position: tuple[float, float],
        width: float | int | None = None,
        height: float | int | None = None,
    ) -> None:
        """Create a PDF raster image component."""
        super().__init__(image, position, width, height)

    @classmethod
    def create_from_dict(cls, data: object, style: object | None = None) -> ImagePDF:
        """Recreate an ImagePDF from serialized parameters."""
        del style
        payload = _pdf_payload(data, "ImagePDF")
        return cls(
            RasterImageAsset.create_from_dict(_pdf_required_field(payload, "image", "ImagePDF")),
            _pdf_required_field(payload, "position", "ImagePDF"),
            _pdf_required_field(payload, "width", "ImagePDF"),
            _pdf_required_field(payload, "height", "ImagePDF"),
        )

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized image geometry and data."""
        return {
            "ImagePDF": {
                "image": self.image.parameters,
                "position": self.position,
                "width": self.width,
                "height": self.height,
            }
        }

    def generate_pdf(self, context: PDFRenderContext | None = None) -> str:
        """Generate PDF operators that draw this image resource upright."""
        resource = context.image_resource_name(self.image) if context is not None else "Im1"
        x, y = self.position
        return "\n".join(
            [
                "q",
                f"{_number(self.width)} 0 0 -{_number(self.height)} {_number(x)} {_number(y + self.height)} cm",
                f"/{resource} Do",
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
    ImagePDF,
)


def _pdf_component_class(component_type: str) -> type:
    """Return a supported built-in PDF component class by serialized type name."""
    component_class = globals().get(component_type)
    if component_class not in PDF_RENDER_COMPONENT_TYPES:
        raise ValueError(f"Unsupported PDF component payload type: {component_type}")
    return component_class


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
        payload = _pdf_payload(data, "ComponentGroupPDF")
        group = cls(_pdf_required_field(payload, "group_label", "ComponentGroupPDF"))
        restore_extraction_truth_annotations(group, payload.get("extraction_truth", []))
        restore_grammar_truth_annotations(group, payload.get("grammar_truth", []))
        if styles is None:
            styles = {}
        component_annotations = payload.get("component_extraction_truth", [])
        component_grammar_annotations = payload.get("component_grammar_truth", [])
        for index, component_data in enumerate(_pdf_required_sequence(payload, "components", "ComponentGroupPDF")):
            style = None
            component_class_name, component_payload = _pdf_single_mapping_entry(component_data, "PDF component")
            if "style" in component_payload:
                _, _, stored_name, style_class = _pdf_style_entry(component_payload["style"])
                if stored_name not in styles:
                    style = style_class.create_from_dict(component_payload["style"])
                    styles[stored_name] = style
                else:
                    style = styles[stored_name]
            component_class = _pdf_component_class(component_class_name)
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

    def __init__(self, canvas: Canvas) -> None:
        """Create a PDF document with optional PDF-specific page metadata."""
        super().__init__(canvas)
        self._pdf_page_labels: dict[int, str] = {}
        self._pdf_page_boxes: dict[int, dict[str, tuple[float, float, float, float]]] = {}
        self._pdf_outlines: list[_PDFOutlineEntry] = []
        self._pdf_uri_links: list[_PDFUriLinkAnnotation] = []
        self._pdf_page_links: list[_PDFPageLinkAnnotation] = []
        self._pdf_named_destinations: dict[str, _PDFNamedDestination] = {}
        self._pdf_named_destination_links: list[_PDFNamedDestinationLinkAnnotation] = []
        self._pdf_text_annotations: list[_PDFTextAnnotation] = []

    @staticmethod
    def _iter_layer_groups(layer: Layer, *, sort: bool = False) -> tuple[ComponentGroup, ...]:
        """Return every stored group in a layer, including repeated labels."""
        groups = layer.groups()
        if sort:
            return tuple(sorted(groups, key=lambda group: (group.group_label, group.group_id)))
        return groups

    def add_page(self, position: int = -1, page: Layers | None = None) -> None:
        """Add a page and shift PDF-specific page metadata with inserted pages."""
        page_number = self._validate_insert_position(position)
        if page is not None:
            if not isinstance(page, Layers):
                raise TypeError("page argument take a Layers object")
            self._page_canvas_compatibility(page)
        if page_number >= 1:
            self._shift_pdf_page_metadata_for_insert(page_number)
        super().add_page(position=position, page=page)

    def remove_page(self, position: int) -> None:
        """Remove a page and shift PDF-specific page metadata with remaining pages."""
        page_number = self._validate_existing_position(position)
        super().remove_page(page_number)
        self._shift_pdf_page_metadata_for_removal(page_number)

    def add_outline(
        self,
        title: str,
        page_number: int,
        *,
        left: float | int = 0.0,
        top: float | int | None = None,
        zoom: float | int | None = None,
        parent: str | None = None,
    ) -> None:
        """Add a PDF outline entry that targets an existing page."""
        page_number = self._validate_existing_position(page_number)
        outline_title = _coerce_pdf_outline_title(title)
        parent_title = None
        if parent is not None:
            parent_title = _coerce_pdf_outline_title(parent)
            matches = [outline for outline in self._pdf_outlines if outline.parent is None and outline.title == parent_title]
            if len(matches) != 1:
                raise ValueError("outline parent must match exactly one existing top-level outline")
        elif any(outline.parent == outline_title for outline in self._pdf_outlines):
            raise ValueError("outline title conflicts with an existing child outline parent")
        left_value = _coerce_pdf_destination_number(left, "left")
        top_value = None if top is None else _coerce_pdf_destination_number(top, "top")
        zoom_value = None if zoom is None else _coerce_pdf_destination_number(zoom, "zoom")
        self._pdf_outlines.append(_PDFOutlineEntry(outline_title, page_number, left_value, top_value, zoom_value, parent_title))

    def clear_outlines(self) -> None:
        """Remove all PDF outline entries from the document."""
        self._pdf_outlines.clear()

    def outlines(self) -> tuple[dict[str, object], ...]:
        """Return serialized flat PDF outline entries in insertion order."""
        return tuple(self._outline_entry_payload(outline) for outline in self._pdf_outlines)

    def add_uri_link(self, page_number: int, rect: Sequence[float | int], uri: str) -> None:
        """Add a URI link annotation to an existing page."""
        page_number = self._validate_existing_position(page_number)
        page = self.page(page_number)
        link_rect = _coerce_pdf_link_rect(rect, canvas_width=page._canvas.width, canvas_height=page._canvas.height)
        target_uri = _coerce_pdf_uri(uri)
        self._pdf_uri_links.append(_PDFUriLinkAnnotation(page_number, link_rect, target_uri))

    def clear_uri_links(self) -> None:
        """Remove all PDF URI link annotations from the document."""
        self._pdf_uri_links.clear()

    def uri_links(self) -> tuple[dict[str, object], ...]:
        """Return serialized URI link annotations in insertion order."""
        return tuple(self._uri_link_payload(link) for link in self._pdf_uri_links)

    def add_page_link(
        self,
        page_number: int,
        rect: Sequence[float | int],
        target_page_number: int,
        *,
        left: float | int = 0.0,
        top: float | int | None = None,
        zoom: float | int | None = None,
    ) -> None:
        """Add an internal page link annotation to an existing page."""
        page_number = self._validate_existing_position(page_number)
        target_page_number = self._validate_existing_position(target_page_number)
        page = self.page(page_number)
        link_rect = _coerce_pdf_link_rect(rect, canvas_width=page._canvas.width, canvas_height=page._canvas.height)
        link_left = _coerce_pdf_destination_number(left, "left", owner="page link")
        link_top = None if top is None else _coerce_pdf_destination_number(top, "top", owner="page link")
        link_zoom = None if zoom is None else _coerce_pdf_destination_number(zoom, "zoom", owner="page link")
        self._pdf_page_links.append(_PDFPageLinkAnnotation(page_number, link_rect, target_page_number, link_left, link_top, link_zoom))

    def clear_page_links(self) -> None:
        """Remove all PDF internal page link annotations from the document."""
        self._pdf_page_links.clear()

    def page_links(self) -> tuple[dict[str, object], ...]:
        """Return serialized internal page link annotations in insertion order."""
        return tuple(self._page_link_payload(link) for link in self._pdf_page_links)

    def add_named_destination(
        self,
        name: str,
        page_number: int,
        *,
        left: float | int = 0.0,
        top: float | int | None = None,
        zoom: float | int | None = None,
    ) -> None:
        """Add or replace a named destination targeting an existing page."""
        destination_name = _coerce_pdf_destination_name(name)
        page_number = self._validate_existing_position(page_number)
        destination_left = _coerce_pdf_destination_number(left, "left", owner="named destination")
        destination_top = None if top is None else _coerce_pdf_destination_number(top, "top", owner="named destination")
        destination_zoom = None if zoom is None else _coerce_pdf_destination_number(zoom, "zoom", owner="named destination")
        self._pdf_named_destinations[destination_name] = _PDFNamedDestination(
            destination_name,
            page_number,
            destination_left,
            destination_top,
            destination_zoom,
        )

    def clear_named_destinations(self) -> None:
        """Remove all PDF named destinations and links that target them."""
        self._pdf_named_destinations.clear()
        self._pdf_named_destination_links.clear()

    def named_destinations(self) -> tuple[dict[str, object], ...]:
        """Return serialized named destinations sorted by destination name."""
        return tuple(self._named_destination_payload(destination) for destination in self._sorted_named_destinations())

    def add_named_destination_link(self, page_number: int, rect: Sequence[float | int], destination_name: str) -> None:
        """Add a link annotation to an existing named destination."""
        page_number = self._validate_existing_position(page_number)
        destination_name = _coerce_pdf_destination_name(destination_name)
        if destination_name not in self._pdf_named_destinations:
            raise ValueError("named destination link target must exist")
        page = self.page(page_number)
        link_rect = _coerce_pdf_link_rect(rect, canvas_width=page._canvas.width, canvas_height=page._canvas.height)
        self._pdf_named_destination_links.append(_PDFNamedDestinationLinkAnnotation(page_number, link_rect, destination_name))

    def clear_named_destination_links(self) -> None:
        """Remove all PDF link annotations targeting named destinations."""
        self._pdf_named_destination_links.clear()

    def named_destination_links(self) -> tuple[dict[str, object], ...]:
        """Return serialized named destination link annotations in insertion order."""
        return tuple(self._named_destination_link_payload(link) for link in self._pdf_named_destination_links)

    def add_text_annotation(
        self,
        page_number: int,
        rect: Sequence[float | int],
        contents: str,
        *,
        title: str | None = None,
        open: bool = False,
    ) -> None:
        """Add a PDF text annotation to an existing page."""
        page_number = self._validate_existing_position(page_number)
        page = self.page(page_number)
        annotation_rect = _coerce_pdf_link_rect(rect, canvas_width=page._canvas.width, canvas_height=page._canvas.height)
        annotation_contents = _coerce_pdf_annotation_text(contents, "text annotation contents")
        annotation_title = None if title is None else _coerce_pdf_annotation_text(title, "text annotation title")
        annotation_open = _coerce_pdf_annotation_open(open)
        self._pdf_text_annotations.append(
            _PDFTextAnnotation(page_number, annotation_rect, annotation_contents, annotation_title, annotation_open)
        )

    def clear_text_annotations(self) -> None:
        """Remove all PDF text annotations."""
        self._pdf_text_annotations.clear()

    def text_annotations(self) -> tuple[dict[str, object], ...]:
        """Return serialized PDF text annotations in insertion order."""
        return tuple(self._text_annotation_payload(annotation) for annotation in self._pdf_text_annotations)

    def set_page_label(self, page_number: int, label: str | None) -> None:
        """Set or clear a PDF page label for an existing page."""
        page_number = self._validate_existing_position(page_number)
        if label is None:
            self._pdf_page_labels.pop(page_number, None)
            return
        self._pdf_page_labels[page_number] = _coerce_pdf_page_label(label)

    def page_label(self, page_number: int) -> str | None:
        """Return the explicit PDF page label for a page, if one is set."""
        page_number = self._validate_existing_position(page_number)
        return self._pdf_page_labels.get(page_number)

    def set_page_box(
        self,
        page_number: int,
        box_name: str,
        box: Sequence[float | int] | None,
    ) -> None:
        """Set or clear an additional PDF page box for an existing page."""
        page_number = self._validate_existing_position(page_number)
        canonical_name = _coerce_pdf_page_box_name(box_name)
        if box is None:
            page_boxes = self._pdf_page_boxes.get(page_number)
            if page_boxes is not None:
                page_boxes.pop(canonical_name, None)
                if not page_boxes:
                    del self._pdf_page_boxes[page_number]
            return
        page = self.page(page_number)
        page_box = _coerce_pdf_page_box(box, canvas_width=page._canvas.width, canvas_height=page._canvas.height)
        self._pdf_page_boxes.setdefault(page_number, {})[canonical_name] = page_box

    def page_box(self, page_number: int, box_name: str) -> tuple[float, float, float, float] | None:
        """Return an explicit PDF page box for a page, if one is set."""
        page_number = self._validate_existing_position(page_number)
        canonical_name = _coerce_pdf_page_box_name(box_name)
        return self._pdf_page_boxes.get(page_number, {}).get(canonical_name)

    def _shift_pdf_page_metadata_for_insert(self, page_number: int) -> None:
        """Shift PDF-specific page metadata when a page is inserted."""
        self._pdf_page_labels = {index + 1 if index >= page_number else index: label for index, label in self._pdf_page_labels.items()}
        self._pdf_page_boxes = {index + 1 if index >= page_number else index: boxes for index, boxes in self._pdf_page_boxes.items()}
        self._pdf_outlines = [
            _PDFOutlineEntry(
                outline.title,
                outline.page_number + 1 if outline.page_number >= page_number else outline.page_number,
                outline.left,
                outline.top,
                outline.zoom,
                outline.parent,
            )
            for outline in self._pdf_outlines
        ]
        self._pdf_uri_links = [
            _PDFUriLinkAnnotation(
                link.page_number + 1 if link.page_number >= page_number else link.page_number,
                link.rect,
                link.uri,
            )
            for link in self._pdf_uri_links
        ]
        self._pdf_page_links = [
            _PDFPageLinkAnnotation(
                link.page_number + 1 if link.page_number >= page_number else link.page_number,
                link.rect,
                link.target_page_number + 1 if link.target_page_number >= page_number else link.target_page_number,
                link.left,
                link.top,
                link.zoom,
            )
            for link in self._pdf_page_links
        ]
        self._pdf_named_destinations = {
            name: _PDFNamedDestination(
                destination.name,
                destination.page_number + 1 if destination.page_number >= page_number else destination.page_number,
                destination.left,
                destination.top,
                destination.zoom,
            )
            for name, destination in self._pdf_named_destinations.items()
        }
        self._pdf_named_destination_links = [
            _PDFNamedDestinationLinkAnnotation(
                link.page_number + 1 if link.page_number >= page_number else link.page_number,
                link.rect,
                link.destination_name,
            )
            for link in self._pdf_named_destination_links
        ]
        self._pdf_text_annotations = [
            _PDFTextAnnotation(
                annotation.page_number + 1 if annotation.page_number >= page_number else annotation.page_number,
                annotation.rect,
                annotation.contents,
                annotation.title,
                annotation.open,
            )
            for annotation in self._pdf_text_annotations
        ]

    def _shift_pdf_page_metadata_for_removal(self, page_number: int) -> None:
        """Shift PDF-specific page metadata when a page is removed."""
        self._pdf_page_labels = {
            index - 1 if index > page_number else index: label for index, label in self._pdf_page_labels.items() if index != page_number
        }
        self._pdf_page_boxes = {
            index - 1 if index > page_number else index: boxes for index, boxes in self._pdf_page_boxes.items() if index != page_number
        }
        self._pdf_outlines = [
            _PDFOutlineEntry(
                outline.title,
                outline.page_number - 1 if outline.page_number > page_number else outline.page_number,
                outline.left,
                outline.top,
                outline.zoom,
                outline.parent,
            )
            for outline in self._pdf_outlines
            if outline.page_number != page_number
        ]
        top_level_titles = {outline.title for outline in self._pdf_outlines if outline.parent is None}
        self._pdf_outlines = [outline for outline in self._pdf_outlines if outline.parent is None or outline.parent in top_level_titles]
        self._pdf_uri_links = [
            _PDFUriLinkAnnotation(
                link.page_number - 1 if link.page_number > page_number else link.page_number,
                link.rect,
                link.uri,
            )
            for link in self._pdf_uri_links
            if link.page_number != page_number
        ]
        self._pdf_page_links = [
            _PDFPageLinkAnnotation(
                link.page_number - 1 if link.page_number > page_number else link.page_number,
                link.rect,
                link.target_page_number - 1 if link.target_page_number > page_number else link.target_page_number,
                link.left,
                link.top,
                link.zoom,
            )
            for link in self._pdf_page_links
            if link.page_number != page_number and link.target_page_number != page_number
        ]
        removed_destination_names = {
            name for name, destination in self._pdf_named_destinations.items() if destination.page_number == page_number
        }
        self._pdf_named_destinations = {
            name: _PDFNamedDestination(
                destination.name,
                destination.page_number - 1 if destination.page_number > page_number else destination.page_number,
                destination.left,
                destination.top,
                destination.zoom,
            )
            for name, destination in self._pdf_named_destinations.items()
            if destination.page_number != page_number
        }
        self._pdf_named_destination_links = [
            _PDFNamedDestinationLinkAnnotation(
                link.page_number - 1 if link.page_number > page_number else link.page_number,
                link.rect,
                link.destination_name,
            )
            for link in self._pdf_named_destination_links
            if link.page_number != page_number and link.destination_name not in removed_destination_names
        ]
        self._pdf_text_annotations = [
            _PDFTextAnnotation(
                annotation.page_number - 1 if annotation.page_number > page_number else annotation.page_number,
                annotation.rect,
                annotation.contents,
                annotation.title,
                annotation.open,
            )
            for annotation in self._pdf_text_annotations
            if annotation.page_number != page_number
        ]

    def _page_label_dictionary(self) -> str:
        """Return a PDF PageLabels number-tree dictionary for explicit labels."""
        entries = " ".join(
            f"{page_number - 1} << /P ({_escape_pdf_string(label)}) >>" for page_number, label in sorted(self._pdf_page_labels.items())
        )
        return f"<< /Nums [{entries}] >>"

    def _page_box_operators(self, page_number: int) -> str:
        """Return additional PDF page-box dictionary entries for a page."""
        boxes = self._pdf_page_boxes.get(page_number, {})
        return " ".join(
            f"/{name} [{_number(left)} {_number(bottom)} {_number(right)} {_number(top)}]"
            for name, (left, bottom, right, top) in sorted(boxes.items())
        )

    @staticmethod
    def _outline_entry_payload(outline: _PDFOutlineEntry) -> dict[str, object]:
        """Return serialized data for a validated PDF outline entry."""
        payload: dict[str, object] = {
            "title": outline.title,
            "page_number": outline.page_number,
            "left": outline.left,
        }
        if outline.top is not None:
            payload["top"] = outline.top
        if outline.zoom is not None:
            payload["zoom"] = outline.zoom
        if outline.parent is not None:
            payload["parent"] = outline.parent
        return payload

    @staticmethod
    def _outline_destination(outline: _PDFOutlineEntry, page_ids_by_number: Mapping[int, int]) -> str:
        """Return a PDF outline destination array."""
        page_id = page_ids_by_number[outline.page_number]
        return (
            f"[{page_id} 0 R /XYZ {_number(outline.left)} "
            f"{_coerce_pdf_outline_destination_token(outline.top)} {_coerce_pdf_outline_destination_token(outline.zoom)}]"
        )

    @staticmethod
    def _outline_objects(
        *,
        outline_root_id: int,
        outline_item_ids: Sequence[int],
        outlines: Sequence[_PDFOutlineEntry],
        page_ids_by_number: Mapping[int, int],
    ) -> dict[int, str]:
        """Return PDF outline object payloads keyed by object id."""
        objects: dict[int, str] = {}
        object_ids_by_index = dict(enumerate(outline_item_ids))
        top_level_indices = [index for index, outline in enumerate(outlines) if outline.parent is None]
        child_indices_by_parent: dict[str, list[int]] = {}
        for index, outline in enumerate(outlines):
            if outline.parent is not None:
                child_indices_by_parent.setdefault(outline.parent, []).append(index)
        first_id = object_ids_by_index[top_level_indices[0]]
        last_id = object_ids_by_index[top_level_indices[-1]]
        objects[outline_root_id] = f"<< /Type /Outlines /First {first_id} 0 R /Last {last_id} 0 R /Count {len(outlines)} >>"
        top_index_by_title = {outlines[index].title: index for index in top_level_indices}
        for index, (object_id, outline) in enumerate(zip(outline_item_ids, outlines, strict=True)):
            if outline.parent is None:
                siblings = top_level_indices
                parent_id = outline_root_id
                children = child_indices_by_parent.get(outline.title, [])
            else:
                siblings = child_indices_by_parent[outline.parent]
                parent_id = object_ids_by_index[top_index_by_title[outline.parent]]
                children = []
            sibling_position = siblings.index(index)
            prev_link = f" /Prev {object_ids_by_index[siblings[sibling_position - 1]]} 0 R" if sibling_position > 0 else ""
            next_link = f" /Next {object_ids_by_index[siblings[sibling_position + 1]]} 0 R" if sibling_position + 1 < len(siblings) else ""
            child_links = ""
            if children:
                child_links = (
                    f" /First {object_ids_by_index[children[0]]} 0 R /Last {object_ids_by_index[children[-1]]} 0 R /Count {len(children)}"
                )
            destination = DocumentPDF._outline_destination(outline, page_ids_by_number)
            objects[object_id] = (
                f"<< /Title ({_escape_pdf_string(outline.title)}) /Parent {parent_id} 0 R"
                f"{prev_link}{next_link}{child_links} /Dest {destination} >>"
            )
        return objects

    @staticmethod
    def _uri_link_payload(link: _PDFUriLinkAnnotation) -> dict[str, object]:
        """Return serialized data for a validated URI link annotation."""
        return {
            "page_number": link.page_number,
            "rect": list(link.rect),
            "uri": link.uri,
        }

    def _uri_links_by_page(self) -> dict[int, tuple[_PDFUriLinkAnnotation, ...]]:
        """Return URI link annotations grouped by page in insertion order."""
        links_by_page: dict[int, list[_PDFUriLinkAnnotation]] = {}
        for link in self._pdf_uri_links:
            links_by_page.setdefault(link.page_number, []).append(link)
        return {page_number: tuple(links) for page_number, links in links_by_page.items()}

    @staticmethod
    def _uri_link_annotation_object(link: _PDFUriLinkAnnotation) -> str:
        """Return a PDF URI link annotation object dictionary."""
        left, bottom, right, top = link.rect
        rect = f"[{_number(left)} {_number(bottom)} {_number(right)} {_number(top)}]"
        uri = _escape_pdf_string(link.uri)
        return f"<< /Type /Annot /Subtype /Link /Rect {rect} /Border [0 0 0] /A << /S /URI /URI ({uri}) >> >>"

    @staticmethod
    def _page_link_payload(link: _PDFPageLinkAnnotation) -> dict[str, object]:
        """Return serialized data for a validated internal page link annotation."""
        payload: dict[str, object] = {
            "page_number": link.page_number,
            "rect": list(link.rect),
            "target_page_number": link.target_page_number,
            "left": link.left,
        }
        if link.top is not None:
            payload["top"] = link.top
        if link.zoom is not None:
            payload["zoom"] = link.zoom
        return payload

    def _page_links_by_page(self) -> dict[int, tuple[_PDFPageLinkAnnotation, ...]]:
        """Return internal page link annotations grouped by source page."""
        links_by_page: dict[int, list[_PDFPageLinkAnnotation]] = {}
        for link in self._pdf_page_links:
            links_by_page.setdefault(link.page_number, []).append(link)
        return {page_number: tuple(links) for page_number, links in links_by_page.items()}

    @staticmethod
    def _page_link_annotation_object(link: _PDFPageLinkAnnotation, page_ids_by_number: Mapping[int, int]) -> str:
        """Return a PDF internal page link annotation object dictionary."""
        left, bottom, right, top = link.rect
        rect = f"[{_number(left)} {_number(bottom)} {_number(right)} {_number(top)}]"
        page_id = page_ids_by_number[link.target_page_number]
        destination = (
            f"[{page_id} 0 R /XYZ {_number(link.left)} "
            f"{_coerce_pdf_outline_destination_token(link.top)} {_coerce_pdf_outline_destination_token(link.zoom)}]"
        )
        return f"<< /Type /Annot /Subtype /Link /Rect {rect} /Border [0 0 0] /Dest {destination} >>"

    def _sorted_named_destinations(self) -> tuple[_PDFNamedDestination, ...]:
        """Return named destinations sorted by PDF name-tree key."""
        return tuple(self._pdf_named_destinations[name] for name in sorted(self._pdf_named_destinations))

    @staticmethod
    def _named_destination_payload(destination: _PDFNamedDestination) -> dict[str, object]:
        """Return serialized data for a validated named destination."""
        payload: dict[str, object] = {
            "name": destination.name,
            "page_number": destination.page_number,
            "left": destination.left,
        }
        if destination.top is not None:
            payload["top"] = destination.top
        if destination.zoom is not None:
            payload["zoom"] = destination.zoom
        return payload

    @staticmethod
    def _named_destination_link_payload(link: _PDFNamedDestinationLinkAnnotation) -> dict[str, object]:
        """Return serialized data for a validated named destination link annotation."""
        return {
            "page_number": link.page_number,
            "rect": list(link.rect),
            "destination_name": link.destination_name,
        }

    def _named_destination_links_by_page(self) -> dict[int, tuple[_PDFNamedDestinationLinkAnnotation, ...]]:
        """Return named destination link annotations grouped by source page."""
        links_by_page: dict[int, list[_PDFNamedDestinationLinkAnnotation]] = {}
        for link in self._pdf_named_destination_links:
            links_by_page.setdefault(link.page_number, []).append(link)
        return {page_number: tuple(links) for page_number, links in links_by_page.items()}

    @staticmethod
    def _named_destination_object(destination: _PDFNamedDestination, page_ids_by_number: Mapping[int, int]) -> str:
        """Return a PDF destination array for a named destination."""
        page_id = page_ids_by_number[destination.page_number]
        return (
            f"[{page_id} 0 R /XYZ {_number(destination.left)} "
            f"{_coerce_pdf_outline_destination_token(destination.top)} {_coerce_pdf_outline_destination_token(destination.zoom)}]"
        )

    def _names_dictionary(self, page_ids_by_number: Mapping[int, int]) -> str:
        """Return a PDF Names dictionary for named destinations."""
        destination_entries = " ".join(
            f"({_escape_pdf_string(destination.name)}) {self._named_destination_object(destination, page_ids_by_number)}"
            for destination in self._sorted_named_destinations()
        )
        return f"<< /Dests << /Names [{destination_entries}] >> >>"

    @staticmethod
    def _named_destination_link_annotation_object(link: _PDFNamedDestinationLinkAnnotation) -> str:
        """Return a PDF link annotation object targeting a named destination."""
        left, bottom, right, top = link.rect
        rect = f"[{_number(left)} {_number(bottom)} {_number(right)} {_number(top)}]"
        destination = _escape_pdf_string(link.destination_name)
        return f"<< /Type /Annot /Subtype /Link /Rect {rect} /Border [0 0 0] /Dest ({destination}) >>"

    @staticmethod
    def _text_annotation_payload(annotation: _PDFTextAnnotation) -> dict[str, object]:
        """Return serialized data for a validated PDF text annotation."""
        payload: dict[str, object] = {
            "page_number": annotation.page_number,
            "rect": list(annotation.rect),
            "contents": annotation.contents,
        }
        if annotation.title is not None:
            payload["title"] = annotation.title
        if annotation.open:
            payload["open"] = annotation.open
        return payload

    def _text_annotations_by_page(self) -> dict[int, tuple[_PDFTextAnnotation, ...]]:
        """Return PDF text annotations grouped by page in insertion order."""
        annotations_by_page: dict[int, list[_PDFTextAnnotation]] = {}
        for annotation in self._pdf_text_annotations:
            annotations_by_page.setdefault(annotation.page_number, []).append(annotation)
        return {page_number: tuple(annotations) for page_number, annotations in annotations_by_page.items()}

    @staticmethod
    def _text_annotation_object(annotation: _PDFTextAnnotation) -> str:
        """Return a PDF text annotation object dictionary."""
        left, bottom, right, top = annotation.rect
        rect = f"[{_number(left)} {_number(bottom)} {_number(right)} {_number(top)}]"
        title = f" /T ({_escape_pdf_string(annotation.title)})" if annotation.title is not None else ""
        open_state = " /Open true" if annotation.open else ""
        contents = _escape_pdf_string(annotation.contents)
        return f"<< /Type /Annot /Subtype /Text /Rect {rect}{title} /Contents ({contents}){open_state} >>"

    def create_pdf(self, filepath: str | os.PathLike[str]) -> None:
        """Create a deterministic PDF file at the requested path."""
        path = _normalize_output_filepath(filepath)
        with open(path, "wb") as handle:
            handle.write(self.to_pdf_bytes())

    def to_pdf_bytes(self) -> bytes:
        """Render this document to deterministic PDF bytes."""
        writer = _PDFObjectWriter()
        catalog_id = 1
        pages_id = 2
        info_id = 3
        page_ids: list[int] = []
        object_id = 4
        font_registry = _PDFFontRegistry()
        image_registry = _PDFImageRegistry()
        graphics_state_registry = _PDFGraphicsStateRegistry()
        rendered_pages: list[tuple[Layers, str]] = []

        writer.set_object(
            info_id,
            (
                "<< /Creator (InkGen) /Producer (InkGen dependency-free PDF backend) "
                f"/CreationDate ({PDF_FIXED_DATE}) /ModDate ({PDF_FIXED_DATE}) >>"
            ),
        )

        for page_number in range(1, self.pages + 1):
            page = self.page(page_number)
            content = self._render_page_content(page, font_registry, image_registry, graphics_state_registry)
            rendered_pages.append((page, content))

        font_object_ids: dict[str, int] = {}
        for resource in font_registry.resources():
            if resource.is_embedded:
                font_file_object_id = object_id
                writer.set_object(font_file_object_id, _pdf_font_file_object(resource))
                descriptor_object_id = object_id + 1
                writer.set_object(descriptor_object_id, _pdf_font_descriptor_object(resource, font_file_object_id))
                tounicode_object_id = object_id + 2
                writer.set_object(tounicode_object_id, _pdf_tounicode_cmap_object())
                font_object_id = object_id + 3
                writer.set_object(font_object_id, _pdf_font_object(resource, descriptor_object_id, tounicode_object_id))
                font_object_ids[resource.resource_name] = font_object_id
                object_id += 4
            else:
                tounicode_object_id = object_id
                writer.set_object(tounicode_object_id, _pdf_tounicode_cmap_object())
                font_object_id = object_id + 1
                font_object_ids[resource.resource_name] = font_object_id
                writer.set_object(font_object_id, _pdf_font_object(resource, tounicode_object_id=tounicode_object_id))
                object_id += 2

        image_object_ids: dict[str, int] = {}
        for resource_name, asset in image_registry.resources():
            image_payload = _pdf_image_payload(asset)
            color_space = image_payload.color_space
            if image_payload.icc_profile is not None:
                components = 4 if image_payload.color_space == "DeviceCMYK" else 3
                icc_object_id = object_id
                writer.set_object(
                    icc_object_id,
                    _pdf_icc_profile_object(
                        image_payload.icc_profile,
                        components=components,
                        alternate=image_payload.color_space,
                    ),
                )
                color_space = f"[/ICCBased {icc_object_id} 0 R]"
                object_id += 1
            smask_object_id = None
            if image_payload.alpha_samples is not None:
                smask_object_id = object_id
                writer.set_object(
                    smask_object_id,
                    _pdf_image_xobject(
                        width=asset.width,
                        height=asset.height,
                        color_space="DeviceGray",
                        samples=image_payload.alpha_samples,
                    ),
                )
                object_id += 1
            image_object_ids[resource_name] = object_id
            writer.set_object(
                object_id,
                _pdf_image_xobject(
                    width=asset.width,
                    height=asset.height,
                    color_space=color_space,
                    samples=image_payload.color_samples,
                    smask_object_id=smask_object_id,
                    filter_name=image_payload.color_filter,
                ),
            )
            object_id += 1

        graphics_state_object_ids: dict[str, int] = {}
        for resource_name, stroke_opacity, fill_opacity in graphics_state_registry.resources():
            graphics_state_object_ids[resource_name] = object_id
            writer.set_object(
                object_id,
                _pdf_extgstate_object(stroke_opacity=stroke_opacity, fill_opacity=fill_opacity),
            )
            object_id += 1

        resource_sections: list[str] = []
        if font_object_ids:
            font_entries = " ".join(f"/{resource_name} {font_object_ids[resource_name]} 0 R" for resource_name in font_object_ids)
            resource_sections.append(f"/Font << {font_entries} >>")
        if image_object_ids:
            image_entries = " ".join(f"/{resource_name} {image_object_ids[resource_name]} 0 R" for resource_name in image_object_ids)
            resource_sections.append(f"/XObject << {image_entries} >>")
        if graphics_state_object_ids:
            graphics_state_entries = " ".join(
                f"/{resource_name} {graphics_state_object_ids[resource_name]} 0 R" for resource_name in graphics_state_object_ids
            )
            resource_sections.append(f"/ExtGState << {graphics_state_entries} >>")
        resources = f"<< {' '.join(resource_sections)} >>" if resource_sections else "<< >>"

        page_ids_by_number: dict[int, int] = {}
        uri_links_by_page = self._uri_links_by_page()
        page_links_by_page = self._page_links_by_page()
        named_destination_links_by_page = self._named_destination_links_by_page()
        text_annotations_by_page = self._text_annotations_by_page()
        page_plans = []
        for page_number, (page, content) in enumerate(rendered_pages, start=1):
            content_bytes = content.encode("latin-1")
            content_id = object_id
            page_id = object_id + 1
            page_annotations = (
                tuple(uri_links_by_page.get(page_number, ()))
                + tuple(page_links_by_page.get(page_number, ()))
                + tuple(named_destination_links_by_page.get(page_number, ()))
                + tuple(text_annotations_by_page.get(page_number, ()))
            )
            annotation_ids = list(range(object_id + 2, object_id + 2 + len(page_annotations)))
            object_id += 2 + len(page_annotations)
            page_ids.append(page_id)
            page_ids_by_number[page_number] = page_id
            page_plans.append((page_number, page, content_bytes, content_id, page_id, page_annotations, annotation_ids))

        for page_number, page, content_bytes, content_id, page_id, page_annotations, annotation_ids in page_plans:
            page_box_entries = self._page_box_operators(page_number)
            page_boxes = f" {page_box_entries}" if page_box_entries else ""
            annotations = f" /Annots [{' '.join(f'{annotation_id} 0 R' for annotation_id in annotation_ids)}]" if annotation_ids else ""
            writer.set_object(
                content_id, b"<< /Length " + str(len(content_bytes)).encode("ascii") + b" >>\nstream\n" + content_bytes + b"\nendstream"
            )
            writer.set_object(
                page_id,
                (
                    f"<< /Type /Page /Parent {pages_id} 0 R "
                    f"/MediaBox [0 0 {_number(page._canvas.width)} {_number(page._canvas.height)}]{page_boxes} "
                    f"/Resources {resources} "
                    f"/Contents {content_id} 0 R{annotations} >>"
                ),
            )
            for annotation_id, link in zip(annotation_ids, page_annotations, strict=True):
                if isinstance(link, _PDFUriLinkAnnotation):
                    writer.set_object(annotation_id, self._uri_link_annotation_object(link))
                elif isinstance(link, _PDFPageLinkAnnotation):
                    writer.set_object(annotation_id, self._page_link_annotation_object(link, page_ids_by_number))
                elif isinstance(link, _PDFNamedDestinationLinkAnnotation):
                    writer.set_object(annotation_id, self._named_destination_link_annotation_object(link))
                else:
                    writer.set_object(annotation_id, self._text_annotation_object(link))

        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        writer.set_object(pages_id, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
        page_labels = f" /PageLabels {self._page_label_dictionary()}" if self._pdf_page_labels else ""
        names = f" /Names {self._names_dictionary(page_ids_by_number)}" if self._pdf_named_destinations else ""
        outlines = ""
        if self._pdf_outlines:
            outline_root_id = object_id
            outline_item_ids = list(range(object_id + 1, object_id + 1 + len(self._pdf_outlines)))
            object_id += 1 + len(self._pdf_outlines)
            for outline_object_id, outline_payload in self._outline_objects(
                outline_root_id=outline_root_id,
                outline_item_ids=outline_item_ids,
                outlines=self._pdf_outlines,
                page_ids_by_number=page_ids_by_number,
            ).items():
                writer.set_object(outline_object_id, outline_payload)
            outlines = f" /Outlines {outline_root_id} 0 R /PageMode /UseOutlines"
        writer.set_object(catalog_id, f"<< /Type /Catalog /Pages {pages_id} 0 R{page_labels}{names}{outlines} >>")
        return writer.build(root_id=catalog_id, info_id=info_id)

    def _render_page_content(
        self,
        page: Layers,
        font_registry: _PDFFontRegistry | None = None,
        image_registry: _PDFImageRegistry | None = None,
        graphics_state_registry: _PDFGraphicsStateRegistry | None = None,
    ) -> str:
        context = PDFRenderContext(
            canvas_height=page._canvas.height,
            font_registry=font_registry,
            image_registry=image_registry,
            graphics_state_registry=graphics_state_registry,
        )
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
        payload = _pdf_payload(data, "DocumentPDF")
        document = cls(Canvas.create_from_dict(_pdf_required_field(payload, "canvas", "DocumentPDF")))
        restore_extraction_truth_annotations(document, payload.get("extraction_truth", []))
        restore_grammar_truth_annotations(document, payload.get("grammar_truth", []))
        for page_payload in _pdf_required_sequence(payload, "pages", "DocumentPDF"):
            page = _layers_pdf_from_dict(page_payload, styles)
            document.add_page(position=-1, page=page)
        for page_key, label in _pdf_optional_mapping(payload, "page_labels", "DocumentPDF").items():
            document.set_page_label(_pdf_page_number_key(page_key, "DocumentPDF page_labels"), label)  # type: ignore[arg-type]
        for page_key, page_boxes in _pdf_optional_mapping(payload, "page_boxes", "DocumentPDF").items():
            page_number = _pdf_page_number_key(page_key, "DocumentPDF page_boxes")
            if not isinstance(page_boxes, Mapping):
                raise TypeError("DocumentPDF page_boxes entries must be mappings")
            for box_name, box in page_boxes.items():
                document.set_page_box(page_number, box_name, box)  # type: ignore[arg-type]
        for outline_payload in _pdf_optional_sequence(payload, "outlines", "DocumentPDF"):
            if not isinstance(outline_payload, Mapping):
                raise TypeError("DocumentPDF outlines entries must be mappings")
            title = _pdf_required_field(outline_payload, "title", "DocumentPDF outline")
            page_number = _pdf_required_field(outline_payload, "page_number", "DocumentPDF outline")
            left = outline_payload.get("left", 0.0)
            top = outline_payload.get("top")
            zoom = outline_payload.get("zoom")
            parent = outline_payload.get("parent")
            document.add_outline(title, page_number, left=left, top=top, zoom=zoom, parent=parent)  # type: ignore[arg-type]
        for link_payload in _pdf_optional_sequence(payload, "uri_links", "DocumentPDF"):
            if not isinstance(link_payload, Mapping):
                raise TypeError("DocumentPDF uri_links entries must be mappings")
            page_number = _pdf_required_field(link_payload, "page_number", "DocumentPDF URI link")
            rect = _pdf_required_field(link_payload, "rect", "DocumentPDF URI link")
            uri = _pdf_required_field(link_payload, "uri", "DocumentPDF URI link")
            document.add_uri_link(page_number, rect, uri)  # type: ignore[arg-type]
        for link_payload in _pdf_optional_sequence(payload, "page_links", "DocumentPDF"):
            if not isinstance(link_payload, Mapping):
                raise TypeError("DocumentPDF page_links entries must be mappings")
            page_number = _pdf_required_field(link_payload, "page_number", "DocumentPDF page link")
            rect = _pdf_required_field(link_payload, "rect", "DocumentPDF page link")
            target_page_number = _pdf_required_field(link_payload, "target_page_number", "DocumentPDF page link")
            left = link_payload.get("left", 0.0)
            top = link_payload.get("top")
            zoom = link_payload.get("zoom")
            document.add_page_link(page_number, rect, target_page_number, left=left, top=top, zoom=zoom)  # type: ignore[arg-type]
        for destination_payload in _pdf_optional_sequence(payload, "named_destinations", "DocumentPDF"):
            if not isinstance(destination_payload, Mapping):
                raise TypeError("DocumentPDF named_destinations entries must be mappings")
            name = _pdf_required_field(destination_payload, "name", "DocumentPDF named destination")
            page_number = _pdf_required_field(destination_payload, "page_number", "DocumentPDF named destination")
            left = destination_payload.get("left", 0.0)
            top = destination_payload.get("top")
            zoom = destination_payload.get("zoom")
            document.add_named_destination(name, page_number, left=left, top=top, zoom=zoom)  # type: ignore[arg-type]
        for link_payload in _pdf_optional_sequence(payload, "named_destination_links", "DocumentPDF"):
            if not isinstance(link_payload, Mapping):
                raise TypeError("DocumentPDF named_destination_links entries must be mappings")
            page_number = _pdf_required_field(link_payload, "page_number", "DocumentPDF named destination link")
            rect = _pdf_required_field(link_payload, "rect", "DocumentPDF named destination link")
            destination_name = _pdf_required_field(link_payload, "destination_name", "DocumentPDF named destination link")
            document.add_named_destination_link(page_number, rect, destination_name)  # type: ignore[arg-type]
        for annotation_payload in _pdf_optional_sequence(payload, "text_annotations", "DocumentPDF"):
            if not isinstance(annotation_payload, Mapping):
                raise TypeError("DocumentPDF text_annotations entries must be mappings")
            page_number = _pdf_required_field(annotation_payload, "page_number", "DocumentPDF text annotation")
            rect = _pdf_required_field(annotation_payload, "rect", "DocumentPDF text annotation")
            contents = _pdf_required_field(annotation_payload, "contents", "DocumentPDF text annotation")
            title = annotation_payload.get("title")
            open_state = annotation_payload.get("open", False)
            document.add_text_annotation(page_number, rect, contents, title=title, open=open_state)  # type: ignore[arg-type]
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
        if self._pdf_page_labels:
            document_payload["page_labels"] = {str(page_number): label for page_number, label in sorted(self._pdf_page_labels.items())}
        if self._pdf_page_boxes:
            document_payload["page_boxes"] = {
                str(page_number): {box_name: list(box) for box_name, box in sorted(page_boxes.items())}
                for page_number, page_boxes in sorted(self._pdf_page_boxes.items())
            }
        if self._pdf_outlines:
            document_payload["outlines"] = [self._outline_entry_payload(outline) for outline in self._pdf_outlines]
        if self._pdf_uri_links:
            document_payload["uri_links"] = [self._uri_link_payload(link) for link in self._pdf_uri_links]
        if self._pdf_page_links:
            document_payload["page_links"] = [self._page_link_payload(link) for link in self._pdf_page_links]
        if self._pdf_named_destinations:
            document_payload["named_destinations"] = [
                self._named_destination_payload(destination) for destination in self._sorted_named_destinations()
            ]
        if self._pdf_named_destination_links:
            document_payload["named_destination_links"] = [
                self._named_destination_link_payload(link) for link in self._pdf_named_destination_links
            ]
        if self._pdf_text_annotations:
            document_payload["text_annotations"] = [self._text_annotation_payload(annotation) for annotation in self._pdf_text_annotations]
        return {"DocumentPDF": document_payload}


def _normalize_output_filepath(filepath: object) -> str:
    """Return an absolute output path or fail at the PDF writer boundary."""
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


def _layer_pdf_from_dict(data: dict, styles: dict[str, object]) -> Layer:
    """Recreate a Layer containing ComponentGroupPDF instances."""
    payload = _pdf_payload(data, "Layer")
    layer = Layer(
        _pdf_required_field(payload, "layer_name", "Layer"),
        Canvas.create_from_dict(_pdf_required_field(payload, "canvas", "Layer")),
        _pdf_required_field(payload, "model", "Layer"),
    )
    collision_settings = _pdf_required_mapping(payload, "group_collision_settings", "Layer")
    for group_payload in _pdf_required_sequence(payload, "component_groups", "Layer"):
        group = ComponentGroupPDF.create_from_dict(group_payload, styles)
        settings = collision_settings.get(group.group_label, {})
        if not isinstance(settings, Mapping):
            raise TypeError("Layer group collision setting entries must be mappings")
        allow_collision = _pdf_required_field(settings, "allow_collision", "Layer group collision settings")
        strict = _pdf_required_field(settings, "strict", "Layer group collision settings")
        layer.add_component_group(group, allow_collision, strict)
    return layer


def _layers_pdf_from_dict(data: dict, styles: dict[str, object]) -> Layers:
    """Recreate a Layers page containing PDF component groups."""
    payload = _pdf_payload(data, "Layers")
    layers = Layers(Canvas.create_from_dict(_pdf_required_field(payload, "canvas", "Layers")))
    for layer_name in list(layers.layers):
        layers.remove_layer(layer_name)
    for layer_payload in _pdf_required_mapping(payload, "layers", "Layers").values():
        layer = _layer_pdf_from_dict(layer_payload, styles)
        layers.add_layer(layer=layer)
    return layers
