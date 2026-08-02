"""Contract tests for standalone, clipped SVG region emission."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree

import matplotlib.font_manager as font_manager
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from InkGen import region_svg
from InkGen.drawing_components import RectangleDrawing, TextDrawing
from InkGen.region_svg import PositionedTextRun, SvgClipWindow, emit_svg_region
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.text_outline import outline_for_text, outline_for_text_bytes

SVG_NS = "http://www.w3.org/2000/svg"
FONT_PATH = Path(font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans")))


@pytest.mark.condition("SVG-REGION-P1")
def test_font_program_bytes_produce_the_same_outline_as_the_source_file() -> None:
    """SVG-REGION-P1: Embedded font bytes preserve exact outline geometry."""
    arguments = {
        "text": "Exact font",
        "size_px": 18.0,
        "x": 12.5,
        "y": 31.0,
        "units": "px",
        "add_one_pixel_margin": False,
    }

    from_path = outline_for_text(font_path=str(FONT_PATH), **arguments)
    from_bytes = outline_for_text_bytes(font_program=FONT_PATH.read_bytes(), **arguments)

    assert from_bytes["svg_path"] == from_path["svg_path"]
    assert from_bytes["bbox"] == from_path["bbox"]
    assert from_bytes["path_bbox"] == from_path["path_bbox"]


@pytest.mark.condition("SVG-REGION-P1")
def test_font_program_byte_api_rejects_wrong_or_empty_storage() -> None:
    """SVG-REGION-P1: The byte API does not reinterpret paths or empty data."""
    with pytest.raises(TypeError, match="font_program must be bytes"):
        outline_for_text_bytes("text", bytearray(b"font"), 12.0)
    with pytest.raises(ValueError, match="font_program must not be empty"):
        outline_for_text_bytes("text", b"", 12.0)


@pytest.mark.condition("SVG-REGION-P1")
def test_region_emit_is_clipped_self_contained_and_uses_text_outlines() -> None:
    """SVG-REGION-P1: A region is complete XML with clipped paths and primitives."""
    style = DrawingStyle(
        f"region-rectangle-{uuid4().hex}",
        stroke="#123456",
        fill="#d0e0f0",
        stroke_width=0.5,
    )
    clip = SvgClipWindow(x=10.0, y=20.0, width=80.0, height=40.0)
    run = PositionedTextRun(
        text="A < B & C",
        position=(14.0, 38.0),
        font_size_px=14.0,
        font_program=FONT_PATH.read_bytes(),
        fill="#102030",
    )

    svg = emit_svg_region(
        clip_window=clip,
        text_runs=[run],
        vector_primitives=[RectangleDrawing((5.0, 15.0), 100.0, 55.0, 0.0, style)],
        background="#ffffff",
    )

    root = ElementTree.fromstring(svg)
    assert root.tag == f"{{{SVG_NS}}}svg"
    assert root.attrib["viewBox"] == "10 20 80 40"
    assert root.attrib["width"] == "80"
    assert root.attrib["height"] == "40"
    clip_rect = root.find(f".//{{{SVG_NS}}}clipPath/{{{SVG_NS}}}rect")
    assert clip_rect is not None
    assert clip_rect.attrib == {"x": "10", "y": "20", "width": "80", "height": "40"}
    clipped_group = root.find(f".//{{{SVG_NS}}}g")
    assert clipped_group is not None
    assert clipped_group.attrib["clip-path"].startswith("url(#inkgen-region-clip-")
    assert root.findall(f".//{{{SVG_NS}}}text") == []
    assert any(path.attrib.get("d") for path in root.findall(f".//{{{SVG_NS}}}path"))
    assert root.find(f".//{{{SVG_NS}}}title").text == "A < B & C"
    assert "font-family" not in svg
    assert "http://" not in svg.replace(SVG_NS, "")
    assert "https://" not in svg


@pytest.mark.condition("SVG-REGION-P1")
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"x": 0.0, "y": 0.0, "width": 0.0, "height": 1.0}, "width must be greater than zero"),
        ({"x": float("nan"), "y": 0.0, "width": 1.0, "height": 1.0}, "x must be finite"),
        ({"x": 0.0, "y": 0.0, "width": 1.0, "height": float("inf")}, "height must be finite"),
    ],
)
def test_region_clip_window_rejects_non_finite_or_empty_geometry(arguments: dict[str, float], message: str) -> None:
    """SVG-REGION-P1: Invalid clip geometry cannot produce ambiguous output."""
    with pytest.raises(ValueError, match=message):
        SvgClipWindow(**arguments)


@pytest.mark.condition("SVG-REGION-P1")
@settings(max_examples=100, deadline=None)
@given(
    x=st.floats(min_value=-1_000_000, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    y=st.floats(min_value=-1_000_000, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    width=st.floats(min_value=1e-6, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    height=st.floats(min_value=1e-6, max_value=1_000_000, allow_nan=False, allow_infinity=False),
)
def test_region_viewport_and_clip_remain_identical_for_finite_windows(x: float, y: float, width: float, height: float) -> None:
    """SVG-REGION-P1: Valid window serialization preserves the clip invariant."""
    svg = emit_svg_region(clip_window=SvgClipWindow(x, y, width, height))
    root = ElementTree.fromstring(svg)
    view_box = tuple(float(value) for value in root.attrib["viewBox"].split())
    clip_rect = root.find(f".//{{{SVG_NS}}}clipPath/{{{SVG_NS}}}rect")
    assert clip_rect is not None
    clip_box = tuple(float(clip_rect.attrib[name]) for name in ("x", "y", "width", "height"))

    assert clip_box == view_box
    assert view_box == pytest.approx((x, y, width, height), rel=1e-14, abs=1e-14)


@pytest.mark.condition("SVG-REGION-P1")
def test_positioned_text_run_requires_exactly_one_supported_font_source() -> None:
    """SVG-REGION-P1: A run cannot silently fall back to a system font."""
    common = {"text": "evidence", "position": (0.0, 10.0), "font_size_px": 10.0}

    with pytest.raises(ValueError, match="exactly one of font_path or font_program"):
        PositionedTextRun(**common)
    with pytest.raises(ValueError, match="exactly one of font_path or font_program"):
        PositionedTextRun(font_path=FONT_PATH, font_program=FONT_PATH.read_bytes(), **common)
    with pytest.raises(ValueError, match="font_program must not be empty"):
        PositionedTextRun(font_program=b"", **common)


@pytest.mark.condition("SVG-REGION-P1")
def test_region_emit_rejects_font_dependent_text_primitives() -> None:
    """SVG-REGION-P1: Ordinary SVG text cannot weaken self-containment."""
    ordinary_text = TextDrawing(
        "system font",
        (1.0, 10.0),
        TextStyle(f"region-text-{uuid4().hex}", Font(size=10.0)),
    )

    with pytest.raises(TypeError, match="PositionedTextRun"):
        emit_svg_region(
            clip_window=SvgClipWindow(0.0, 0.0, 20.0, 20.0),
            text_runs=[],
            vector_primitives=[ordinary_text],
        )


@pytest.mark.condition("SVG-REGION-P1")
def test_region_emit_rejects_external_references_from_primitive_output() -> None:
    """SVG-REGION-P1: Generated fragments cannot load network resources."""

    class ExternalImageComponent:
        def generate_svg(self) -> str:
            return '<image href="https://example.invalid/evidence.png" />'

    class ExternalImagePrimitive:
        def to_component(self, output_format: object) -> ExternalImageComponent:
            del output_format
            return ExternalImageComponent()

    with pytest.raises(ValueError, match="external reference"):
        emit_svg_region(
            clip_window=SvgClipWindow(0.0, 0.0, 20.0, 20.0),
            text_runs=[],
            vector_primitives=[ExternalImagePrimitive()],
        )


@pytest.mark.condition("SVG-REGION-P1")
def test_positioned_text_run_supports_file_fonts_features_and_whitespace() -> None:
    """SVG-REGION-P1: File-backed runs share shaping and preserve empty outlines."""
    run = PositionedTextRun(
        text="   ",
        position=(-2.5, 9.0),
        font_size_px=11.0,
        font_path=FONT_PATH,
        opacity=0.25,
        y_down=False,
        features={"kern": False},
    )

    svg = emit_svg_region(
        clip_window=SvgClipWindow(-5.0, -5.0, 20.0, 20.0),
        text_runs=[run],
    )

    root = ElementTree.fromstring(svg)
    assert root.find(f".//{{{SVG_NS}}}title").text == "   "
    assert root.findall(f".//{{{SVG_NS}}}path") == []
    assert run.font_path == FONT_PATH
    assert run.features == {"kern": False}


@pytest.mark.condition("SVG-REGION-P1")
@pytest.mark.parametrize(
    ("overrides", "exception", "message"),
    [
        ({"text": 7}, TypeError, "text must be a string"),
        ({"position": "0,0"}, TypeError, "position must contain two numeric values"),
        ({"position": (0.0, object())}, TypeError, "position y must be numeric"),
        ({"font_size_px": False}, TypeError, "font_size_px must be numeric"),
        ({"font_size_px": -1.0}, ValueError, "font_size_px must be greater than zero"),
        ({"font_program": bytearray(b"font")}, TypeError, "font_program must be bytes"),
        ({"fill": ""}, TypeError, "fill must be a non-empty SVG paint string"),
        ({"fill": "url(https://example.invalid/a)"}, ValueError, "external reference"),
        ({"opacity": 1.1}, ValueError, "opacity must be between zero and one"),
        ({"y_down": 1}, TypeError, "y_down must be a boolean"),
        ({"features": {"kern": 1}}, TypeError, "features must map strings to booleans"),
    ],
)
def test_positioned_text_run_rejects_invalid_fields(overrides: dict[str, object], exception: type[Exception], message: str) -> None:
    """SVG-REGION-P1: Invalid run fields fail before shaping."""
    arguments: dict[str, object] = {
        "text": "valid",
        "position": (0.0, 10.0),
        "font_size_px": 10.0,
        "font_program": FONT_PATH.read_bytes(),
    }
    arguments.update(overrides)

    with pytest.raises(exception, match=message):
        PositionedTextRun(**arguments)


@pytest.mark.condition("SVG-REGION-P1")
def test_positioned_text_run_rejects_missing_font_file() -> None:
    """SVG-REGION-P1: Missing font paths do not trigger substitution."""
    with pytest.raises(ValueError, match="font_path must identify a readable file"):
        PositionedTextRun(
            text="missing",
            position=(0.0, 10.0),
            font_size_px=10.0,
            font_path=FONT_PATH.with_name("missing-font.ttf"),
        )


@pytest.mark.condition("SVG-REGION-P1")
@pytest.mark.parametrize(
    ("fragment", "exception", "message"),
    [
        ("<path>", ValueError, "malformed XML"),
        ("<text>font dependent</text>", TypeError, "PositionedTextRun"),
        ("<script />", ValueError, "cannot contain script"),
        ("<foreignObject />", ValueError, "cannot contain foreignobject"),
        ('<path style="fill:url(https://example.invalid/a)" />', ValueError, "external reference"),
        ('<style>@import "https://example.invalid/a.css";</style>', ValueError, "external reference"),
        ('<?xml-stylesheet href="https://example.invalid/a.css"?>', ValueError, "processing instruction"),
        ('<path style="@import evil" />', ValueError, "external reference"),
        ('<path onclick="javascript:evil()" />', ValueError, "external reference"),
    ],
)
def test_region_emit_rejects_unsafe_or_malformed_component_fragments(fragment: str, exception: type[Exception], message: str) -> None:
    """SVG-REGION-P1: Primitive XML fails closed at active-content boundaries."""

    class FragmentComponent:
        def generate_svg(self) -> str:
            return fragment

    with pytest.raises(exception, match=message):
        emit_svg_region(
            clip_window=SvgClipWindow(0.0, 0.0, 10.0, 10.0),
            vector_primitives=[FragmentComponent()],
        )


@pytest.mark.condition("SVG-REGION-P1")
def test_region_emit_accepts_internal_and_embedded_component_references() -> None:
    """SVG-REGION-P1: Internal paint and data resources remain self-contained."""

    class EmbeddedComponent:
        def generate_svg(self) -> str:
            return (
                '<defs><linearGradient id="g"><stop offset="0" /></linearGradient></defs>'
                '<path d="M0 0L1 1" style="stroke:url(#g)" />'
                '<image href="data:image/png;base64,AA==" width="1" height="1" />'
            )

    svg = emit_svg_region(
        clip_window=SvgClipWindow(0.0, 0.0, 10.0, 10.0),
        vector_primitives=[EmbeddedComponent()],
    )

    root = ElementTree.fromstring(svg)
    assert root.find(f".//{{{SVG_NS}}}linearGradient") is not None
    assert root.find(f".//{{{SVG_NS}}}image").attrib["href"].startswith("data:")


@pytest.mark.condition("SVG-REGION-P1")
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"clip_window": (0.0, 0.0, 1.0, 1.0)}, "clip_window must be an SvgClipWindow"),
        ({"text_runs": "run"}, "text_runs must be a sequence"),
        ({"vector_primitives": "path"}, "vector_primitives must be a sequence"),
        ({"background": "javascript:evil()"}, "external reference"),
    ],
)
def test_region_emit_rejects_invalid_container_inputs(overrides: dict[str, object], message: str) -> None:
    """SVG-REGION-P1: Public container and background inputs fail explicitly."""
    arguments: dict[str, object] = {
        "clip_window": SvgClipWindow(0.0, 0.0, 10.0, 10.0),
        "text_runs": (),
        "vector_primitives": (),
    }
    arguments.update(overrides)

    with pytest.raises((TypeError, ValueError), match=message):
        emit_svg_region(**arguments)


@pytest.mark.condition("SVG-REGION-P1")
def test_region_emit_rejects_invalid_component_and_text_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """SVG-REGION-P1: Structural protocol violations cannot leak into output."""

    class NotAComponent:
        pass

    class NonStringComponent:
        def generate_svg(self) -> bytes:
            return b"<path />"

    window = SvgClipWindow(0.0, 0.0, 10.0, 10.0)
    with pytest.raises(TypeError, match="SVG-generating component"):
        emit_svg_region(clip_window=window, vector_primitives=[NotAComponent()])
    with pytest.raises(TypeError, match=r"generate_svg\(\) must return a string"):
        emit_svg_region(clip_window=window, vector_primitives=[NonStringComponent()])
    with pytest.raises(TypeError, match="text_runs must contain PositionedTextRun"):
        emit_svg_region(clip_window=window, text_runs=[object()])

    run = PositionedTextRun(
        text="bad outline",
        position=(0.0, 5.0),
        font_size_px=10.0,
        font_program=FONT_PATH.read_bytes(),
    )
    monkeypatch.setattr(region_svg, "outline_for_text_bytes", lambda **_kwargs: {"svg_path": 7})
    with pytest.raises(TypeError, match="text outline svg_path must be a string"):
        emit_svg_region(clip_window=window, text_runs=[run])
