"""RASTER-TEXT-P3 conditions for standalone neutral text rasterization."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest

import InkGen.raster_renderer as raster_renderer
from InkGen.baird import BairdParams
from InkGen.boundary import Canvas
from InkGen.drawing_components import DrawingComponentGroup, TextDrawing
from InkGen.raster_renderer import render_and_degrade_drawing_group, render_drawing_group
from InkGen.style import Font, TextStyle


def _style(
    *,
    size: float = 18.0,
    color: str = "#102030",
    align: str = "start",
    visible: bool = True,
    character_spacing: float = 0.0,
    line_spacing: float = 1.0,
) -> TextStyle:
    style = TextStyle(
        f"raster_text_{uuid4().hex}",
        Font(family="DejaVu Sans", size=size),
        visible=visible,
        character_spacing=character_spacing,
    )
    style.color = color
    style.text_align = align
    style.line_spacing = line_spacing
    return style


@pytest.mark.condition("RASTER-TEXT-P3")
def test_single_line_text_renders_through_public_scan_path() -> None:
    """RASTER-TEXT-P3: Neutral text reaches clean and Baird-degraded assets."""
    group = DrawingComponentGroup("text", [TextDrawing("InkGen", (0.25, 0.6), _style(size=24.0))])

    result = render_and_degrade_drawing_group(
        group,
        Canvas(2, 1, "in"),
        BairdParams.clean(),
        seed=17,
        background_rgb=(245, 246, 247),
        dpi=72,
        render_supersample=2,
    )

    assert result.clean.component_count == 1
    with result.clean.asset.image() as clean:
        assert clean.size == (144, 72)
        assert clean.getbbox() is not None
    with result.degraded.asset.image() as degraded:
        assert degraded.getbbox() == (0, 0, 144, 72)
        assert degraded.getextrema() != ((245, 245), (246, 246), (247, 247))


@pytest.mark.condition("RASTER-TEXT-P3")
def test_public_renderer_passes_physical_point_scale(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-TEXT-P3: Point size depends on DPI, not canvas coordinate units."""
    calls: list[tuple[float, float]] = []

    def record_component(
        surface: object,
        component: object,
        scale: float,
        points_scale: float | None = None,
    ) -> None:
        del surface, component
        calls.append((scale, points_scale if points_scale is not None else -1.0))

    monkeypatch.setattr(raster_renderer, "_render_component", record_component)
    render_drawing_group(
        DrawingComponentGroup("text", [TextDrawing("A", (2.0, 3.0), _style())]),
        Canvas(50.8, 25.4, "mm"),
        dpi=72,
        supersample=3,
    )

    assert calls == [(pytest.approx(216.0 / 25.4), 3.0)]


class _RecordingDraw:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def text(self, position: tuple[int, int], text: str, **kwargs: object) -> None:
        self.calls.append({"position": position, "text": text, **kwargs})


@pytest.mark.condition("RASTER-TEXT-P3")
@pytest.mark.parametrize(
    ("align", "anchor"),
    [("start", "ls"), ("center", "ms"), ("end", "rs")],
)
def test_text_uses_baseline_anchor_and_exact_font_file(
    monkeypatch: pytest.MonkeyPatch,
    align: str,
    anchor: str,
) -> None:
    """RASTER-TEXT-P3: Alignment changes the baseline anchor, not geometry."""
    style = _style(size=12.0, align=align)
    expected_font_path = style.font.font_file
    loaded: list[tuple[str, int]] = []
    font_sentinel = object()
    recorder = _RecordingDraw()

    def load_font(path: str, size: int) -> object:
        loaded.append((path, size))
        return font_sentinel

    monkeypatch.setattr(raster_renderer.ImageFont, "truetype", load_font)
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)
    raster_renderer._render_component(
        object(),  # type: ignore[arg-type]
        TextDrawing("A", (1.25, 2.5), style),
        10.0,
        points_scale=2.0,
    )

    assert loaded == [(expected_font_path, 24)]
    assert recorder.calls == [
        {
            "position": (12, 25),
            "text": "A",
            "font": font_sentinel,
            "fill": (16, 32, 48, 255),
            "anchor": anchor,
        }
    ]


@pytest.mark.condition("RASTER-TEXT-MULTILINE-P11")
@pytest.mark.parametrize(
    ("align", "anchor"),
    [("start", "ls"), ("center", "ms"), ("end", "rs")],
)
def test_multiline_text_normalizes_breaks_and_positions_each_baseline(
    monkeypatch: pytest.MonkeyPatch,
    align: str,
    anchor: str,
) -> None:
    """P11: Every normalized line retains alignment and point-scaled spacing."""
    style = _style(size=12.0, align=align, line_spacing=1.25)
    recorder = _RecordingDraw()
    font_sentinel = object()
    monkeypatch.setattr(raster_renderer.ImageFont, "truetype", lambda path, size: font_sentinel)
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)

    raster_renderer._render_component(
        object(),  # type: ignore[arg-type]
        TextDrawing("A\r\nBBB\r", (1.25, 2.5), style),
        10.0,
        points_scale=2.0,
    )

    assert [(call["position"], call["text"], call["anchor"]) for call in recorder.calls] == [
        ((12, 25), "A", anchor),
        ((12, 55), "BBB", anchor),
        ((12, 85), "", anchor),
    ]


@pytest.mark.condition("RASTER-TEXT-MULTILINE-P11")
def test_zero_line_spacing_overlaps_baselines(monkeypatch: pytest.MonkeyPatch) -> None:
    """P11: Zero spacing is valid and places every line on one baseline."""
    recorder = _RecordingDraw()
    monkeypatch.setattr(raster_renderer.ImageFont, "truetype", lambda path, size: object())
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)

    raster_renderer._render_component(
        object(),  # type: ignore[arg-type]
        TextDrawing("A\nB\nC", (1.0, 2.0), _style(line_spacing=0.0)),
        10.0,
        points_scale=2.0,
    )

    assert [call["position"] for call in recorder.calls] == [(10, 20), (10, 20), (10, 20)]


@pytest.mark.condition("RASTER-TEXT-MULTILINE-P11")
def test_multiline_text_renders_through_public_scan_path() -> None:
    """P11: Multiline neutral text reaches clean and degraded raster assets."""
    group = DrawingComponentGroup(
        "multiline_text",
        [TextDrawing("InkGen\nP11", (0.25, 0.35), _style(size=18.0, line_spacing=1.1))],
    )

    result = render_and_degrade_drawing_group(
        group,
        Canvas(2, 1, "in"),
        BairdParams.clean(),
        seed=23,
        background_rgb=(240, 241, 242),
        dpi=72,
        render_supersample=2,
    )

    with result.clean.asset.image() as clean:
        assert clean.getbbox() is not None
        alpha = clean.getchannel("A")
        occupied_rows = [row for row in range(alpha.height) if alpha.crop((0, row, alpha.width, row + 1)).getbbox()]
        assert occupied_rows
        assert max(occupied_rows) - min(occupied_rows) > 18
    with result.degraded.asset.image() as degraded:
        assert degraded.getbbox() == (0, 0, 144, 72)


@pytest.mark.condition("RASTER-TEXT-MULTILINE-P11")
@pytest.mark.parametrize(
    ("live_value", "error_type", "message"),
    [
        (True, TypeError, "line spacing must be numeric"),
        ("1.0", TypeError, "line spacing must be numeric"),
        (float("nan"), ValueError, "line spacing must be finite"),
        (float("inf"), ValueError, "line spacing must be finite"),
        (-0.1, ValueError, "line spacing must be nonnegative"),
    ],
)
def test_live_invalid_line_spacing_fails_before_surface_allocation(
    monkeypatch: pytest.MonkeyPatch,
    live_value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """P11: Hostile live spacing mutation cannot allocate a raster surface."""
    style = _style()
    style._line_spacing = live_value  # type: ignore[assignment]  # noqa: SLF001
    monkeypatch.setattr(
        raster_renderer.Image,
        "new",
        lambda *args, **kwargs: pytest.fail("surface allocated before text validation"),
    )

    with pytest.raises(error_type, match=message):
        render_drawing_group(
            DrawingComponentGroup("invalid_spacing", [TextDrawing("A\nB", (0.25, 0.5), style)]),
            Canvas(2, 1, "in"),
            dpi=72,
        )


@pytest.mark.condition("RASTER-TEXT-MULTILINE-P11")
def test_live_nonstr_text_fails_before_surface_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """P11: Hostile live text mutation cannot allocate a raster surface."""
    drawing = TextDrawing("A\nB", (0.25, 0.5), _style())
    object.__setattr__(drawing, "text", ["A", "B"])
    monkeypatch.setattr(
        raster_renderer.Image,
        "new",
        lambda *args, **kwargs: pytest.fail("surface allocated before text validation"),
    )

    with pytest.raises(TypeError, match="text must be a string"):
        render_drawing_group(
            DrawingComponentGroup("invalid_text", [drawing]),
            Canvas(2, 1, "in"),
            dpi=72,
        )


@pytest.mark.condition("RASTER-TEXT-P3")
def test_direct_text_render_requires_physical_point_scale() -> None:
    """RASTER-TEXT-P3: Private rendering cannot guess point-to-pixel units."""
    with pytest.raises(ValueError, match="points_scale is required"):
        raster_renderer._render_component(  # type: ignore[arg-type]
            object(),
            TextDrawing("A", (1.0, 1.0), _style()),
            10.0,
        )


@pytest.mark.condition("RASTER-TEXT-P3")
def test_subpixel_font_size_clamps_to_one_pixel(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-TEXT-P3: Positive subpixel point sizes remain loadable."""
    loaded_sizes: list[int] = []
    recorder = _RecordingDraw()

    def load_font(path: str, size: int) -> object:
        del path
        loaded_sizes.append(size)
        return object()

    monkeypatch.setattr(raster_renderer.ImageFont, "truetype", load_font)
    monkeypatch.setattr(raster_renderer.ImageDraw, "Draw", lambda surface: recorder)
    raster_renderer._render_component(
        object(),  # type: ignore[arg-type]
        TextDrawing(".", (1.0, 1.0), _style(size=1.0)),
        1.0,
        points_scale=0.01,
    )

    assert loaded_sizes == [1]


@pytest.mark.condition("RASTER-TEXT-P3")
@pytest.mark.parametrize(
    "drawing",
    [
        pytest.param(TextDrawing("", (0.25, 0.5), _style()), id="empty"),
        pytest.param(TextDrawing("\r\n", (0.25, 0.5), _style()), id="empty-lines"),
        pytest.param(TextDrawing("hidden", (0.25, 0.5), _style(visible=False)), id="invisible"),
        pytest.param(TextDrawing("unpainted", (0.25, 0.5), _style(color="none")), id="no-color"),
    ],
)
def test_unpainted_text_is_a_transparent_noop(drawing: TextDrawing) -> None:
    """RASTER-TEXT-P3: Valid unpainted text does not invent pixels."""
    result = render_drawing_group(
        DrawingComponentGroup("unpainted", [drawing]),
        Canvas(2, 1, "in"),
        dpi=72,
    )

    assert result.component_count == 1
    with result.asset.image() as image:
        assert image.getbbox() is None


def _superscript(style: TextStyle) -> None:
    style.superscript = True


def _subscript(style: TextStyle) -> None:
    style.subscript = True


@pytest.mark.condition("RASTER-TEXT-P3")
@pytest.mark.parametrize(
    ("text", "style", "configure", "message"),
    [
        pytest.param("tracked", _style(character_spacing=0.5), None, "character spacing", id="tracking"),
        pytest.param("tracked", _style(character_spacing=-0.5), None, "character spacing", id="negative-tracking"),
        pytest.param("raised", _style(), _superscript, "superscript", id="superscript"),
        pytest.param("lowered", _style(), _subscript, "subscript", id="subscript"),
    ],
)
def test_unsupported_text_presentation_fails_explicitly(
    text: str,
    style: TextStyle,
    configure: Callable[[TextStyle], None] | None,
    message: str,
) -> None:
    """RASTER-TEXT-P3: P3 does not silently ignore unsupported presentation."""
    if configure is not None:
        configure(style)

    with pytest.raises(ValueError, match=message):
        render_drawing_group(
            DrawingComponentGroup("unsupported", [TextDrawing(text, (0.25, 0.5), style)]),
            Canvas(2, 1, "in"),
            dpi=72,
        )


@pytest.mark.condition("RASTER-TEXT-P3")
def test_font_load_failure_has_renderer_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """RASTER-TEXT-P3: Font backend failures identify the raster boundary."""
    monkeypatch.setattr(
        raster_renderer.ImageFont,
        "truetype",
        lambda path, size: (_ for _ in ()).throw(OSError(f"cannot load {path} at {size}")),
    )

    with pytest.raises(ValueError, match="raster text font could not be loaded"):
        render_drawing_group(
            DrawingComponentGroup("text", [TextDrawing("A", (0.25, 0.5), _style())]),
            Canvas(2, 1, "in"),
            dpi=72,
        )
