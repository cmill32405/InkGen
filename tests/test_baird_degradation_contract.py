"""Contract tests for InkGen's standalone Baird degradation pipeline."""

from __future__ import annotations

import io
import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from PIL import Image

from InkGen import (
    BAIRD_INCH_MICRONS,
    BairdDegradationResult,
    BairdParams,
    Canvas,
    ComponentGroupPDF,
    DocumentPDF,
    ImagePDF,
    RasterImageAsset,
    baird_degrade,
    baird_degrade_asset,
    sigma_px_to_um,
    sigma_um_to_px,
)


def _bars(*, height: int = 80, width: int = 120) -> np.ndarray:
    image = np.ones((height, width, 3), dtype=np.float32)
    image[15:20, 12 : width - 12] = 0.0
    image[35:43, 20 : width - 20] = 0.0
    image[58:65, 8 : width - 8] = 0.0
    return image


def _gray(image: np.ndarray) -> np.ndarray:
    return image.mean(axis=2)


def _edge_energy(image: np.ndarray) -> float:
    gray = _gray(image)
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    return float(np.square(dx).mean() + np.square(dy).mean())


def _ink_x_extent(image: np.ndarray) -> int:
    columns = np.where((_gray(image) < 0.5).any(axis=0))[0]
    return int(columns[-1] - columns[0]) if columns.size else 0


def _png_asset(*, alpha: bool = False) -> RasterImageAsset:
    mode = "RGBA" if alpha else "RGB"
    color = (40, 80, 120, 128) if alpha else (40, 80, 120)
    image = Image.new(mode, (20, 12), color)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return RasterImageAsset.from_bytes(output.getvalue(), source="clean.png")


@pytest.mark.condition("BAIRD-P1")
def test_baird_parameter_defaults_and_clean_profile_cover_the_canonical_model() -> None:
    """BAIRD-P1: Public parameters expose the ten canonical defect controls."""
    params = BairdParams()

    assert params.supersample == 3
    assert params.blur == pytest.approx(0.7)
    assert params.threshold == pytest.approx(0.25)
    assert params.binarize is True
    assert params.sensitivity == pytest.approx(0.125)
    assert params.jitter == pytest.approx(0.2)
    assert params.skew_deg == pytest.approx(0.0)
    assert params.x_scale == pytest.approx(1.0)
    assert params.y_scale == pytest.approx(1.0)
    assert params.baseline == pytest.approx(0.0)
    assert params.kern == pytest.approx(0.0)
    assert BairdParams.clean().as_dict() == {
        "supersample": 3,
        "blur": 0.0,
        "threshold": 0.5,
        "binarize": False,
        "sensitivity": 0.0,
        "jitter": 0.0,
        "skew_deg": 0.0,
        "x_scale": 1.0,
        "y_scale": 1.0,
        "baseline": 0.0,
        "kern": 0.0,
    }


@pytest.mark.condition("BAIRD-P1")
@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        ({"supersample": True}, TypeError, "supersample must be an integer"),
        ({"supersample": 0}, ValueError, "supersample must be between"),
        ({"supersample": 17}, ValueError, "supersample must be between"),
        ({"blur": True}, TypeError, "blur must be numeric"),
        ({"blur": object()}, TypeError, "blur must be numeric"),
        ({"blur": -0.1}, ValueError, "blur must be greater than or equal to zero"),
        ({"threshold": 1.1}, ValueError, "threshold must be between zero and one"),
        ({"binarize": 1}, TypeError, "binarize must be a bool"),
        ({"sensitivity": math.inf}, ValueError, "sensitivity must be finite"),
        ({"jitter": -0.1}, ValueError, "jitter must be greater than or equal to zero"),
        ({"skew_deg": math.nan}, ValueError, "skew_deg must be finite"),
        ({"x_scale": 0.0}, ValueError, "x_scale must be greater than zero"),
        ({"y_scale": -1.0}, ValueError, "y_scale must be greater than zero"),
    ],
)
def test_baird_parameters_reject_invalid_numeric_domains(kwargs: dict[str, object], exception: type[Exception], message: str) -> None:
    """BAIRD-P1: Invalid model states fail at construction."""
    with pytest.raises(exception, match=message):
        BairdParams(**kwargs)


@pytest.mark.condition("BAIRD-P1")
def test_baird_sampling_is_seeded_and_stays_in_documented_ranges() -> None:
    """BAIRD-P1: Parameter sampling is reproducible and bounded."""
    first = BairdParams.sample(np.random.default_rng(17), char_recognition=True)
    second = BairdParams.sample(np.random.default_rng(17), char_recognition=True)

    assert first == second
    assert 0.0 <= first.blur
    assert 0.05 <= first.threshold <= 0.95
    assert 0.0 <= first.sensitivity
    assert 0.0 <= first.jitter
    assert 0.85 <= first.x_scale <= 1.15
    assert 0.7 <= first.y_scale <= 1.3
    assert 0.0 <= first.kern <= 0.5


@pytest.mark.condition("BAIRD-P1")
def test_baird_core_is_seed_deterministic_bounded_and_nonmutating() -> None:
    """BAIRD-P1: Equal inputs and RNG seeds produce equal bounded outputs."""
    image = _bars()
    original = image.copy()
    params = BairdParams.sample(np.random.default_rng(3), binarize=False)

    first = baird_degrade(image, params, np.random.default_rng(29))
    second = baird_degrade(image, params, np.random.default_rng(29))

    assert np.array_equal(first, second)
    assert np.array_equal(image, original)
    assert first.shape == image.shape
    assert first.dtype == np.float32
    assert float(first.min()) >= 0.0
    assert float(first.max()) <= 1.0
    assert np.array_equal(first[:, :, 0], first[:, :, 1])
    assert np.array_equal(first[:, :, 1], first[:, :, 2])


@pytest.mark.condition("BAIRD-P1")
def test_baird_core_accepts_grayscale_and_implicit_rng_paths() -> None:
    """BAIRD-P1: Grayscale input and caller-omitted RNG remain valid public paths."""
    grayscale = _gray(_bars(height=1, width=12))

    result = baird_degrade(grayscale, BairdParams(blur=0.2, binarize=False, sensitivity=0.0))

    assert result.shape == (1, 12, 3)
    assert result.dtype == np.float32


@pytest.mark.condition("BAIRD-P1")
def test_baird_parameter_effects_match_the_model_direction() -> None:
    """BAIRD-P1: Blur, sensitivity, threshold, scale, and jitter act as specified."""
    image = _bars()
    quiet = BairdParams.clean()
    sharp = baird_degrade(image, quiet, np.random.default_rng(1))
    blurred = baird_degrade(image, BairdParams(blur=2.5, binarize=False, sensitivity=0.0, jitter=0.0), np.random.default_rng(1))
    noisy = baird_degrade(image, BairdParams(blur=0.0, binarize=False, sensitivity=0.12, jitter=0.0), np.random.default_rng(1))
    low_threshold = baird_degrade(image, BairdParams(blur=1.2, threshold=0.1), np.random.default_rng(1))
    high_threshold = baird_degrade(image, BairdParams(blur=1.2, threshold=0.5), np.random.default_rng(1))
    wide = baird_degrade(image, BairdParams(blur=0.0, binarize=False, sensitivity=0.0, jitter=0.0, x_scale=1.2), np.random.default_rng(1))
    jittered = baird_degrade(image, BairdParams(blur=0.0, binarize=False, sensitivity=0.0, jitter=0.6), np.random.default_rng(1))

    assert np.corrcoef(_gray(image).ravel(), _gray(sharp).ravel())[0, 1] > 0.99
    assert _edge_energy(blurred) < _edge_energy(sharp)
    assert float(_gray(noisy)[:10, :10].std()) > float(_gray(sharp)[:10, :10].std()) + 0.02
    assert float((_gray(low_threshold) < 0.5).mean()) > float((_gray(high_threshold) < 0.5).mean())
    assert _ink_x_extent(wide) > _ink_x_extent(sharp)
    assert not np.array_equal(jittered, sharp)
    assert np.corrcoef(_gray(jittered).ravel(), _gray(sharp).ravel())[0, 1] > 0.75


@pytest.mark.condition("BAIRD-P1")
def test_baird_port_matches_reference_implementation_statistics() -> None:
    """BAIRD-P1: The standalone backend stays numerically aligned with the source port."""
    image = np.ones((8, 10, 3), dtype=np.float32)
    image[2:4, 1:9] = 0.0
    image[6:7, 2:8] = 0.0
    params = BairdParams(
        supersample=3,
        blur=0.7,
        threshold=0.25,
        binarize=False,
        sensitivity=0.04,
        jitter=0.2,
        skew_deg=1.0,
        x_scale=1.04,
        y_scale=0.97,
        baseline=0.1,
        kern=0.2,
    )

    result = baird_degrade(image, params, np.random.default_rng(42))[:, :, 0]

    assert float(result.mean()) == pytest.approx(0.724202036857605, abs=0.001)
    assert float(result.std()) == pytest.approx(0.22790764272212982, abs=0.001)
    expected_pixels = {
        (0, 0): 0.937020480632782,
        (1, 5): 0.789087176322937,
        (2, 2): 0.23236428201198578,
        (3, 7): 0.408608078956604,
        (5, 3): 0.6533240675926208,
        (7, 9): 0.9732005596160889,
    }
    for (row, column), expected in expected_pixels.items():
        assert float(result[row, column]) == pytest.approx(expected, abs=0.003)


@pytest.mark.condition("BAIRD-P1")
@pytest.mark.parametrize(
    ("image", "exception", "message"),
    [
        ("not an array", TypeError, "image must be a NumPy array"),
        (np.empty((0, 2), dtype=np.float32), ValueError, "image dimensions must be positive"),
        (np.ones((2,), dtype=np.float32), ValueError, "image must have shape"),
        (np.ones((2, 2, 2), dtype=np.float32), ValueError, "image must have shape"),
        (np.ones((2, 2), dtype=np.bool_), TypeError, "image values must be numeric"),
        (np.full((2, 2), np.nan, dtype=np.float32), ValueError, "image values must be finite"),
        (np.full((2, 2), 1.1, dtype=np.float32), ValueError, "image values must be between zero and one"),
    ],
)
def test_baird_core_rejects_invalid_images(image: object, exception: type[Exception], message: str) -> None:
    """BAIRD-P1: Ambiguous or invalid image arrays fail before allocation."""
    with pytest.raises(exception, match=message):
        baird_degrade(image, BairdParams.clean())  # type: ignore[arg-type]


@pytest.mark.condition("BAIRD-P1")
def test_baird_core_rejects_invalid_parameters_rng_and_unbounded_prototype() -> None:
    """BAIRD-P1: Runtime dependencies and intermediate allocation are bounded."""
    image = np.ones((501, 501, 3), dtype=np.float32)
    with pytest.raises(TypeError, match="params must be BairdParams"):
        baird_degrade(image, object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="rng must be a numpy.random.Generator"):
        baird_degrade(image, BairdParams.clean(), object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="prototype limit"):
        baird_degrade(image, BairdParams(supersample=16), np.random.default_rng(1))


@pytest.mark.condition("BAIRD-P1")
def test_baird_parameter_sampling_rejects_ambiguous_controls() -> None:
    """BAIRD-P1: Sampling accepts only an explicit NumPy generator and booleans."""
    with pytest.raises(TypeError, match="rng must be a numpy.random.Generator"):
        BairdParams.sample(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="char_recognition must be a bool"):
        BairdParams.sample(np.random.default_rng(1), char_recognition=1)  # type: ignore[arg-type]


@pytest.mark.condition("BAIRD-P2")
def test_baird_asset_pipeline_returns_png_and_reproducibility_manifest() -> None:
    """BAIRD-P2: Public asset degradation produces a renderer-ready PNG result."""
    asset = _png_asset()
    params = BairdParams(blur=0.5, binarize=False, sensitivity=0.03, jitter=0.1)

    first = baird_degrade_asset(asset, params, seed=41)
    second = baird_degrade_asset(asset, params, seed=41)

    assert isinstance(first, BairdDegradationResult)
    assert first.asset.format == "PNG"
    assert first.asset.mode == "RGB"
    assert (first.asset.width, first.asset.height) == (20, 12)
    assert first.asset.data == second.asset.data
    assert first.manifest == second.manifest
    assert first.manifest == {
        "model": "baird_document_image_defect_1992",
        "seed": 41,
        "background_rgb": None,
        "parameters": params.as_dict(),
    }

    renamed = baird_degrade_asset(asset, BairdParams.clean(), seed=2, source="degraded.png")
    assert renamed.asset.source == "degraded.png"


@pytest.mark.condition("BAIRD-P2")
def test_baird_asset_pipeline_requires_explicit_alpha_background() -> None:
    """BAIRD-P2: Transparent input is never silently flattened to white."""
    asset = _png_asset(alpha=True)

    with pytest.raises(ValueError, match="background_rgb is required"):
        baird_degrade_asset(asset, BairdParams.clean(), seed=1)

    result = baird_degrade_asset(asset, BairdParams.clean(), seed=1, background_rgb=(12, 34, 56))
    assert result.manifest["background_rgb"] == [12, 34, 56]
    with result.asset.image() as image:
        pixel = image.getpixel((0, 0))
    assert isinstance(pixel, tuple)
    assert len(pixel) == 3


@pytest.mark.condition("BAIRD-P2")
def test_baird_asset_pipeline_embeds_through_the_live_pdf_path() -> None:
    """BAIRD-P2: A degraded asset remains valid input to InkGen's PDF renderer."""
    result = baird_degrade_asset(_png_asset(), BairdParams(), seed=11)
    canvas = Canvas(40.0, 30.0)
    document = DocumentPDF(canvas)
    document.add_page()
    group = ComponentGroupPDF("degraded_scan")
    group.add_component(ImagePDF(result.asset, (2.0, 3.0), 20.0, 12.0))
    document.page(1).layer("base").add_component_group(group)

    pdf_bytes = document.to_pdf_bytes()

    assert pdf_bytes.startswith(b"%PDF-")
    assert b"/Subtype /Image" in pdf_bytes


@pytest.mark.condition("BAIRD-P2")
@pytest.mark.parametrize("seed", [True, -1, 2**64])
def test_baird_asset_pipeline_rejects_invalid_seeds(seed: object) -> None:
    """BAIRD-P2: Seed values use NumPy's explicit unsigned 64-bit domain."""
    with pytest.raises((TypeError, ValueError), match="seed"):
        baird_degrade_asset(_png_asset(), BairdParams.clean(), seed=seed)  # type: ignore[arg-type]


@pytest.mark.condition("BAIRD-P2")
@pytest.mark.parametrize(
    ("background", "exception"),
    [
        ((1, 2), ValueError),
        ((1, 2, 3.0), TypeError),
        ((1, 2, 256), ValueError),
        ((True, 2, 3), TypeError),
    ],
)
def test_baird_asset_pipeline_rejects_invalid_backgrounds(
    background: object,
    exception: type[Exception],
) -> None:
    """BAIRD-P2: Paper backgrounds use an explicit bounded RGB tuple."""
    with pytest.raises(exception, match="background_rgb"):
        baird_degrade_asset(
            _png_asset(alpha=True),
            BairdParams.clean(),
            seed=1,
            background_rgb=background,  # type: ignore[arg-type]
        )


@pytest.mark.condition("BAIRD-P2")
def test_baird_asset_pipeline_rejects_wrong_public_types() -> None:
    """BAIRD-P2: The public asset and result envelopes reject unrelated types."""
    params = BairdParams.clean()
    asset = _png_asset()
    with pytest.raises(TypeError, match="asset must be a RasterImageAsset"):
        baird_degrade_asset(object(), params, seed=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="params must be BairdParams"):
        baird_degrade_asset(asset, object(), seed=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="asset must be a RasterImageAsset"):
        BairdDegradationResult(object(), params, 1, None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="parameters must be BairdParams"):
        BairdDegradationResult(asset, object(), 1, None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="seed"):
        BairdDegradationResult(asset, params, -1, None)
    with pytest.raises(ValueError, match="background_rgb"):
        BairdDegradationResult(asset, params, 1, (0, 0, 999))


@pytest.mark.condition("BAIRD-P3")
@given(
    sigma_um=st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    dpi=st.floats(min_value=1.0, max_value=4_800.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, deadline=None)
def test_baird_physical_blur_conversion_round_trips(sigma_um: float, dpi: float) -> None:
    """BAIRD-P3: Micron/pixel conversion is algebraically invertible."""
    converted = sigma_px_to_um(sigma_um_to_px(sigma_um, dpi), dpi)
    assert converted == pytest.approx(sigma_um, rel=1e-12, abs=1e-12)


@pytest.mark.condition("BAIRD-P3")
def test_baird_physical_blur_conversion_rejects_invalid_domains() -> None:
    """BAIRD-P3: Physical conversion rejects invalid or non-finite values."""
    assert BAIRD_INCH_MICRONS == 25_400.0
    for value in (0.0, -1.0, math.nan, math.inf):
        with pytest.raises(ValueError):
            sigma_um_to_px(1.0, value)
    with pytest.raises(ValueError):
        sigma_px_to_um(-0.1, 300.0)
