"""Raster image assets and geometry shared by renderers."""

from __future__ import annotations

import base64
import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from PIL import Image, ImageOps, UnidentifiedImageError

from InkGen.component import PRECISION, Component

_MIME_BY_FORMAT = {
    "BMP": "image/bmp",
    "GIF": "image/gif",
    "JPEG": "image/jpeg",
    "JPG": "image/jpeg",
    "PNG": "image/png",
    "TIFF": "image/tiff",
    "WEBP": "image/webp",
}


def _coerce_image_bytes(data: bytes | bytearray | memoryview) -> bytes:
    """Return immutable image bytes or fail at the asset boundary."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("image data must be bytes-like")
    image_bytes = bytes(data)
    if not image_bytes:
        raise ValueError("image data must not be empty")
    return image_bytes


def _coerce_finite_number(value: object, name: str) -> float:
    """Return a finite numeric value while rejecting booleans."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _coerce_positive_number(value: object, name: str) -> float:
    """Return a finite positive numeric value."""
    number = _coerce_finite_number(value, name)
    if number <= 0.0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def _coerce_position(value: object) -> tuple[float, float]:
    """Return a finite two-coordinate image position."""
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("image position must contain two numeric values")
    return (
        _coerce_finite_number(value[0], "image position coordinate"),
        _coerce_finite_number(value[1], "image position coordinate"),
    )


@dataclass(frozen=True)
class RasterImageAsset:
    """Decoded raster image bytes accepted by InkGen renderers."""

    data: bytes
    format: str
    width: int
    height: int
    mode: str
    source: str | None = None
    orientation: int = 1

    _ALPHA_MODES: ClassVar[set[str]] = {"RGBA", "LA"}

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview, *, source: str | None = None) -> RasterImageAsset:
        """Create an image asset from any Pillow-decodable byte payload."""
        image_bytes = _coerce_image_bytes(data)
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                orientation = _exif_orientation(image)
                normalized = ImageOps.exif_transpose(image)
                normalized.load()
                image_format = (image.format or "PNG").upper()
                width, height = normalized.size
                mode = normalized.mode
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("image data must be a Pillow-decodable raster image") from exc
        if width <= 0 or height <= 0:
            raise ValueError("image dimensions must be positive")
        return cls(image_bytes, image_format, int(width), int(height), mode, source, orientation)

    @classmethod
    def from_file(cls, path: str | Path) -> RasterImageAsset:
        """Create an image asset from a raster image file."""
        image_path = Path(path)
        return cls.from_bytes(image_path.read_bytes(), source=str(image_path))

    @classmethod
    def create_from_dict(cls, data: object) -> RasterImageAsset:
        """Recreate an image asset from serialized parameters."""
        if not isinstance(data, dict) or "RasterImageAsset" not in data:
            raise ValueError("RasterImageAsset data must include RasterImageAsset")
        payload = data["RasterImageAsset"]
        if not isinstance(payload, dict):
            raise TypeError("RasterImageAsset payload must be a mapping")
        encoded = payload.get("data_base64")
        if not isinstance(encoded, str):
            raise TypeError("RasterImageAsset data_base64 must be a string")
        try:
            image_bytes = base64.b64decode(encoded.encode("ascii"), validate=True)
        except ValueError as exc:
            raise ValueError("RasterImageAsset data_base64 must be valid base64") from exc
        source = payload.get("source")
        if source is not None and not isinstance(source, str):
            raise TypeError("RasterImageAsset source must be a string or None")
        return cls.from_bytes(image_bytes, source=source)

    @property
    def mime_type(self) -> str:
        """Return the MIME type for the original image format."""
        return _MIME_BY_FORMAT.get(self.format, f"image/{self.format.lower()}")

    @property
    def has_alpha(self) -> bool:
        """Return whether the decoded image contains transparency metadata."""
        with self.image() as image:
            if image.mode in self._ALPHA_MODES:
                return True
            if image.mode == "P" and "transparency" in image.info:
                return True
            return "A" in image.getbands()

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialization-friendly image asset parameters."""
        return {
            "RasterImageAsset": {
                "data_base64": base64.b64encode(self.data).decode("ascii"),
                "format": self.format,
                "width": self.width,
                "height": self.height,
                "mode": self.mode,
                "source": self.source,
                "orientation": self.orientation,
            }
        }

    @property
    def can_passthrough_jpeg(self) -> bool:
        """Return whether the original JPEG bytes already match displayed pixels."""
        return self.jpeg_passthrough_color_space is not None

    @property
    def jpeg_passthrough_color_space(self) -> str | None:
        """Return the PDF color space for safe JPEG pass-through."""
        if self.format not in {"JPEG", "JPG"} or self.orientation != 1 or self.has_alpha:
            return None
        if self.mode == "RGB":
            return "DeviceRGB"
        if self.mode == "CMYK":
            return "DeviceCMYK"
        return None

    def icc_profile_bytes(self) -> bytes | None:
        """Return embedded ICC profile bytes when the source image carries one."""
        with Image.open(io.BytesIO(self.data)) as image:
            profile = image.info.get("icc_profile")
        return profile if isinstance(profile, bytes) and profile else None

    def image(self) -> Image.Image:
        """Return a loaded EXIF-normalized Pillow image copy for renderer conversion."""
        with Image.open(io.BytesIO(self.data)) as image:
            normalized = ImageOps.exif_transpose(image)
            normalized.load()
            return normalized.copy()

    def png_bytes(self) -> bytes:
        """Return the image normalized to PNG bytes, preserving alpha."""
        with self.image() as image:
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()

    def png_data_uri(self) -> str:
        """Return a PNG data URI suitable for SVG embedding."""
        encoded = base64.b64encode(self.png_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"


class RasterImageComponent(Component):
    """Shared positioned raster image component geometry."""

    def __init__(
        self,
        image: RasterImageAsset,
        position: tuple[float, float],
        width: float | int | None = None,
        height: float | int | None = None,
    ) -> None:
        """Create a positioned raster image component."""
        if not isinstance(image, RasterImageAsset):
            raise TypeError("image must be a RasterImageAsset")
        super().__init__()
        self._image = image
        self._position = _coerce_position(position)
        self._width = _coerce_positive_number(width if width is not None else image.width, "image width")
        self._height = _coerce_positive_number(height if height is not None else image.height, "image height")

    @classmethod
    def create_from_dict(cls, data: object) -> RasterImageComponent:
        """Recreate a raster image component from serialized parameters."""
        if not isinstance(data, dict) or "RasterImageComponent" not in data:
            raise ValueError("RasterImageComponent data must include RasterImageComponent")
        payload = data["RasterImageComponent"]
        if not isinstance(payload, dict):
            raise TypeError("RasterImageComponent payload must be a mapping")
        image = RasterImageAsset.create_from_dict(payload.get("image"))
        return cls(image, payload.get("position"), payload.get("width"), payload.get("height"))

    @property
    def image(self) -> RasterImageAsset:
        """Return the raster image asset."""
        return self._image

    @property
    def position(self) -> tuple[float, float]:
        """Return the top-left image position."""
        return self._position

    @property
    def width(self) -> float:
        """Return the rendered image width."""
        return self._width

    @property
    def height(self) -> float:
        """Return the rendered image height."""
        return self._height

    @property
    def points(self) -> list[tuple[float, float]]:
        """Return the four rendered image corners."""
        x, y = self.position
        points = [(x, y), (x + self.width, y), (x + self.width, y + self.height), (x, y + self.height)]
        return [(float(round(px, PRECISION)), float(round(py, PRECISION))) for px, py in points]

    @property
    def bbox(self) -> list[tuple[float, float]]:
        """Return the rendered image bounding box."""
        return self.points

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """Return the rendered image convex hull."""
        return self.points

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialization-friendly component parameters."""
        return {
            "RasterImageComponent": {
                "image": self.image.parameters,
                "position": self.position,
                "width": self.width,
                "height": self.height,
            }
        }


def _exif_orientation(image: Image.Image) -> int:
    """Return the EXIF orientation tag value when it is well-formed."""
    try:
        orientation = int(image.getexif().get(274, 1))
    except (AttributeError, TypeError, ValueError):
        return 1
    return orientation if 1 <= orientation <= 8 else 1
