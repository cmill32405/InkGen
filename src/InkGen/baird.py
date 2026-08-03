"""Standalone implementation of Baird's document image defect model.

The module consumes clean float raster images and applies Baird's canonical
high-resolution prototype, Gaussian point-spread, perturbed sampling,
sensitivity, and threshold stages. It deliberately does not render PDF pages;
callers provide a clean raster directly or use :func:`baird_degrade_asset`.
"""

from __future__ import annotations

import io
import logging
import math
from dataclasses import asdict, dataclass
from typing import TypeAlias

import numpy as np
from PIL import Image

from InkGen.image_assets import RasterImageAsset

log = logging.getLogger(__name__)

BairdImage: TypeAlias = np.ndarray
BAIRD_INCH_MICRONS: float = 25_400.0
_MAX_SUPERSAMPLE = 16
_MAX_PROTOTYPE_PIXELS = 64_000_000
_MODEL_NAME = "baird_document_image_defect_1992"


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _nonnegative_number(value: object, name: str) -> float:
    number = _finite_number(value, name)
    if number < 0.0:
        raise ValueError(f"{name} must be greater than or equal to zero")
    return number


def _positive_number(value: object, name: str) -> float:
    number = _finite_number(value, name)
    if number <= 0.0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def sigma_um_to_px(sigma_um: float, dpi: float) -> float:
    """Convert a nonnegative physical Gaussian sigma in microns to pixels."""
    sigma = _nonnegative_number(sigma_um, "sigma_um")
    resolution = _positive_number(dpi, "dpi")
    return sigma * (resolution / BAIRD_INCH_MICRONS)


def sigma_px_to_um(sigma_px: float, dpi: float) -> float:
    """Convert a nonnegative Gaussian sigma in pixels to physical microns."""
    sigma = _nonnegative_number(sigma_px, "sigma_px")
    resolution = _positive_number(dpi, "dpi")
    return sigma * (BAIRD_INCH_MICRONS / resolution)


@dataclass(frozen=True, slots=True)
class BairdParams:
    """Validated parameters for Baird's document image defect model.

    Blur, jitter, baseline, and kern use output-pixel units. Skew uses degrees;
    scale values are multiplicative; threshold and sensitivity use normalized
    intensity units where white is one and black is zero.
    """

    supersample: int = 3
    blur: float = 0.7
    threshold: float = 0.25
    binarize: bool = True
    sensitivity: float = 0.125
    jitter: float = 0.2
    skew_deg: float = 0.0
    x_scale: float = 1.0
    y_scale: float = 1.0
    baseline: float = 0.0
    kern: float = 0.0

    def __post_init__(self) -> None:
        """Reject invalid or unbounded model states at construction."""
        if isinstance(self.supersample, (bool, np.bool_)) or not isinstance(self.supersample, (int, np.integer)):
            raise TypeError("supersample must be an integer")
        supersample = int(self.supersample)
        if not 1 <= supersample <= _MAX_SUPERSAMPLE:
            raise ValueError(f"supersample must be between 1 and {_MAX_SUPERSAMPLE}")
        if not isinstance(self.binarize, (bool, np.bool_)):
            raise TypeError("binarize must be a bool")

        object.__setattr__(self, "supersample", supersample)
        object.__setattr__(self, "binarize", bool(self.binarize))
        object.__setattr__(self, "blur", _nonnegative_number(self.blur, "blur"))
        object.__setattr__(self, "sensitivity", _nonnegative_number(self.sensitivity, "sensitivity"))
        object.__setattr__(self, "jitter", _nonnegative_number(self.jitter, "jitter"))
        object.__setattr__(self, "skew_deg", _finite_number(self.skew_deg, "skew_deg"))
        object.__setattr__(self, "x_scale", _positive_number(self.x_scale, "x_scale"))
        object.__setattr__(self, "y_scale", _positive_number(self.y_scale, "y_scale"))
        object.__setattr__(self, "baseline", _finite_number(self.baseline, "baseline"))
        object.__setattr__(self, "kern", _finite_number(self.kern, "kern"))
        threshold = _finite_number(self.threshold, "threshold")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between zero and one")
        object.__setattr__(self, "threshold", threshold)

    @classmethod
    def clean(cls) -> BairdParams:
        """Return the model's near-identity profile for clean baselines."""
        return cls(
            blur=0.0,
            threshold=0.5,
            binarize=False,
            sensitivity=0.0,
            jitter=0.0,
            skew_deg=0.0,
            x_scale=1.0,
            y_scale=1.0,
            baseline=0.0,
            kern=0.0,
        )

    @classmethod
    def sample(
        cls,
        rng: np.random.Generator,
        *,
        char_recognition: bool = False,
        supersample: int = 3,
        binarize: bool = True,
    ) -> BairdParams:
        """Sample parameters from the distributions documented by Baird."""
        if not isinstance(rng, np.random.Generator):
            raise TypeError("rng must be a numpy.random.Generator")
        if not isinstance(char_recognition, bool):
            raise TypeError("char_recognition must be a bool")
        skew_se = 1.4 if char_recognition else 0.7
        baseline_se = 0.06 if char_recognition else 0.03
        x_scale = rng.uniform(0.85, 1.15) if char_recognition else float(np.clip(rng.normal(1.0, 0.05), 0.7, 1.3))
        return cls(
            supersample=supersample,
            blur=float(max(0.0, rng.normal(0.7, 0.3))),
            threshold=float(np.clip(rng.normal(0.25, 0.04), 0.05, 0.95)),
            binarize=binarize,
            sensitivity=float(max(0.0, rng.normal(0.125, 0.04))),
            jitter=float(max(0.0, rng.normal(0.2, 0.1))),
            skew_deg=float(rng.normal(0.0, skew_se)),
            x_scale=float(x_scale),
            y_scale=float(np.clip(rng.normal(1.0, 0.05), 0.7, 1.3)),
            baseline=float(rng.normal(0.0, baseline_se) * 8.0),
            kern=float(rng.uniform(0.0, 0.5)),
        )

    def as_dict(self) -> dict[str, int | float | bool]:
        """Return a stable serialization-friendly parameter mapping."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BairdDegradationResult:
    """A degraded raster asset and the inputs required to reproduce it."""

    asset: RasterImageAsset
    parameters: BairdParams
    seed: int
    background_rgb: tuple[int, int, int] | None

    def __post_init__(self) -> None:
        """Validate the public result envelope."""
        if not isinstance(self.asset, RasterImageAsset):
            raise TypeError("asset must be a RasterImageAsset")
        if not isinstance(self.parameters, BairdParams):
            raise TypeError("parameters must be BairdParams")
        _validate_seed(self.seed)
        if self.background_rgb is not None:
            _validate_background(self.background_rgb)

    @property
    def manifest(self) -> dict[str, object]:
        """Return deterministic provenance for the degradation operation."""
        return {
            "model": _MODEL_NAME,
            "seed": self.seed,
            "background_rgb": list(self.background_rgb) if self.background_rgb is not None else None,
            "parameters": self.parameters.as_dict(),
        }


def baird_degrade(
    image: BairdImage,
    params: BairdParams,
    rng: np.random.Generator | None = None,
) -> BairdImage:
    """Apply Baird's degradation model to a normalized grayscale or RGB array.

    The result is an ``(H, W, 3)`` float32 array in ``[0, 1]`` with replicated
    luminance channels. The input is never mutated. Supplying an RNG makes all
    stochastic stages deterministic for that generator state.
    """
    gray = _validated_gray_image(image)
    if not isinstance(params, BairdParams):
        raise TypeError("params must be BairdParams")
    if rng is None:
        rng = np.random.default_rng()
    elif not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator or None")

    height, width = gray.shape
    scale = params.supersample
    prototype_pixels = height * width * scale * scale
    if prototype_pixels > _MAX_PROTOTYPE_PIXELS:
        raise ValueError(f"image and supersample exceed the {_MAX_PROTOTYPE_PIXELS}-pixel prototype limit")

    log.debug("Applying Baird degradation to %dx%d raster at %dx supersampling", width, height, scale)
    prototype = _resize_bilinear(gray, width * scale, height * scale)
    if params.blur > 0.0:
        prototype = _gaussian_blur(prototype, params.blur * scale)

    grid_x, grid_y = np.meshgrid(
        np.arange(width, dtype=np.float32),
        np.arange(height, dtype=np.float32),
    )
    center_x, center_y = width / 2.0, height / 2.0
    horizontal = (grid_x + 0.5) - center_x
    vertical = (grid_y + 0.5) - center_y
    theta = -math.radians(params.skew_deg)
    cosine, sine = math.cos(theta), math.sin(theta)
    source_x = (cosine * horizontal + sine * vertical) / params.x_scale
    source_y = (-sine * horizontal + cosine * vertical) / params.y_scale
    source_x = source_x + params.kern
    source_y = source_y + params.baseline
    if params.jitter > 0.0:
        source_x = source_x + rng.normal(0.0, params.jitter, (height, width)).astype(np.float32)
        source_y = source_y + rng.normal(0.0, params.jitter, (height, width)).astype(np.float32)

    map_x = ((source_x + center_x) * scale).astype(np.float32)
    map_y = ((source_y + center_y) * scale).astype(np.float32)
    sampled = _sample_bilinear(prototype, map_x, map_y, border_value=1.0)
    if params.sensitivity > 0.0:
        sampled = sampled + rng.normal(0.0, params.sensitivity, (height, width)).astype(np.float32)
    sampled = np.clip(sampled, 0.0, 1.0).astype(np.float32, copy=False)
    if params.binarize:
        sampled = np.where(1.0 - sampled >= params.threshold, 0.0, 1.0).astype(np.float32)

    return np.repeat(sampled[:, :, None], 3, axis=2)


def baird_degrade_asset(
    asset: RasterImageAsset,
    params: BairdParams,
    *,
    seed: int,
    background_rgb: tuple[int, int, int] | None = None,
    source: str | None = None,
) -> BairdDegradationResult:
    """Degrade an image asset and return a PNG plus reproducibility manifest.

    Alpha-bearing assets require an explicit RGB background because a scanned
    page has a physical substrate and Baird's grayscale model has no alpha
    channel. Opaque assets do not require a background.
    """
    if not isinstance(asset, RasterImageAsset):
        raise TypeError("asset must be a RasterImageAsset")
    if not isinstance(params, BairdParams):
        raise TypeError("params must be BairdParams")
    normalized_seed = _validate_seed(seed)
    background = _validate_background(background_rgb) if background_rgb is not None else None
    if asset.has_alpha and background is None:
        raise ValueError("background_rgb is required for an alpha-bearing raster asset")

    with asset.image() as decoded:
        if asset.has_alpha:
            rgba = decoded.convert("RGBA")
            substrate = Image.new("RGBA", rgba.size, (*background, 255))
            rgb = Image.alpha_composite(substrate, rgba).convert("RGB")
        else:
            rgb = decoded.convert("RGB")
        clean = np.asarray(rgb, dtype=np.float32) / 255.0

    degraded = baird_degrade(clean, params, np.random.default_rng(normalized_seed))
    pixels = np.rint(degraded * 255.0).astype(np.uint8)
    output = io.BytesIO()
    Image.fromarray(pixels).save(output, format="PNG")
    degraded_asset = RasterImageAsset.from_bytes(
        output.getvalue(),
        source=asset.source if source is None else source,
    )
    return BairdDegradationResult(degraded_asset, params, normalized_seed, background)


def _validated_gray_image(image: object) -> np.ndarray:
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a NumPy array")
    if image.ndim == 2:
        gray = image
    elif image.ndim == 3 and image.shape[2] == 3:
        gray = image.mean(axis=2)
    else:
        raise ValueError("image must have shape (H, W) or (H, W, 3)")
    if gray.shape[0] <= 0 or gray.shape[1] <= 0:
        raise ValueError("image dimensions must be positive")
    if not np.issubdtype(gray.dtype, np.number) or np.issubdtype(gray.dtype, np.bool_):
        raise TypeError("image values must be numeric")
    gray = np.asarray(gray, dtype=np.float32)
    if not np.isfinite(gray).all():
        raise ValueError("image values must be finite")
    if np.any(gray < 0.0) or np.any(gray > 1.0):
        raise ValueError("image values must be between zero and one")
    return gray


def _resize_bilinear(image: np.ndarray, width: int, height: int) -> np.ndarray:
    source_height, source_width = image.shape
    x = ((np.arange(width, dtype=np.float32) + 0.5) * (source_width / width)) - 0.5
    y = ((np.arange(height, dtype=np.float32) + 0.5) * (source_height / height)) - 0.5
    map_x, map_y = np.meshgrid(x, y)
    return _sample_bilinear(image, map_x, map_y, border_value=None)


def _sample_bilinear(
    image: np.ndarray,
    map_x: np.ndarray,
    map_y: np.ndarray,
    *,
    border_value: float | None,
) -> np.ndarray:
    height, width = image.shape
    x0 = np.floor(map_x).astype(np.int64)
    y0 = np.floor(map_y).astype(np.int64)
    x1 = x0 + 1
    y1 = y0 + 1
    fraction_x = map_x - x0
    fraction_y = map_y - y0
    weights = (
        ((1.0 - fraction_x) * (1.0 - fraction_y), x0, y0),
        (fraction_x * (1.0 - fraction_y), x1, y0),
        ((1.0 - fraction_x) * fraction_y, x0, y1),
        (fraction_x * fraction_y, x1, y1),
    )
    if border_value is None:
        result = np.zeros(map_x.shape, dtype=np.float32)
        for weight, x_index, y_index in weights:
            result += weight * image[np.clip(y_index, 0, height - 1), np.clip(x_index, 0, width - 1)]
        return result

    result = np.full(map_x.shape, border_value, dtype=np.float32)
    for weight, x_index, y_index in weights:
        valid = (x_index >= 0) & (x_index < width) & (y_index >= 0) & (y_index < height)
        clipped = image[np.clip(y_index, 0, height - 1), np.clip(x_index, 0, width - 1)]
        result += weight * (clipped - border_value) * valid
    return result


def _gaussian_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    radius = max(1, int(math.ceil(4.0 * sigma)))
    coordinates = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-(coordinates * coordinates) / (2.0 * sigma * sigma))
    kernel /= kernel.sum()
    horizontal = _convolve_axis(image, kernel, axis=1)
    return _convolve_axis(horizontal, kernel, axis=0)


def _convolve_axis(image: np.ndarray, kernel: np.ndarray, *, axis: int) -> np.ndarray:
    radius = kernel.size // 2
    pad = ((radius, radius), (0, 0)) if axis == 0 else ((0, 0), (radius, radius))
    mode = "reflect" if image.shape[axis] > 1 else "edge"
    padded = np.pad(image, pad, mode=mode)
    windows = np.lib.stride_tricks.sliding_window_view(padded, kernel.size, axis=axis)
    return np.einsum("...k,k->...", windows, kernel, optimize=True).astype(np.float32)


def _validate_seed(seed: object) -> int:
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)):
        raise TypeError("seed must be an integer")
    normalized = int(seed)
    if not 0 <= normalized < 2**64:
        raise ValueError("seed must be between 0 and 2**64 - 1")
    return normalized


def _validate_background(value: object) -> tuple[int, int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError("background_rgb must contain three integer channels")
    channels: list[int] = []
    for channel in value:
        if isinstance(channel, (bool, np.bool_)) or not isinstance(channel, (int, np.integer)):
            raise TypeError("background_rgb channels must be integers")
        normalized = int(channel)
        if not 0 <= normalized <= 255:
            raise ValueError("background_rgb channels must be between 0 and 255")
        channels.append(normalized)
    return channels[0], channels[1], channels[2]
