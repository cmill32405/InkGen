"""Fast exact witnesses for raster path fill P12 mutation workers."""

from __future__ import annotations

import hashlib

from PIL import Image, ImageDraw

from InkGen.component import PathCommand
from InkGen.drawing_components import PathDrawing
from InkGen.raster_renderer import _render_nonzero_path_fill, _render_path_component, _scaled_path_subpaths
from InkGen.style import DrawingStyle

FILL = (192, 32, 16, 255)


def _surface(size: tuple[int, int] = (10, 10)) -> Image.Image:
    return Image.new("RGBA", size, (0, 0, 0, 0))


def _render(
    subpaths: list[list[tuple[float, float]]],
    fill: tuple[int, int, int, int] = FILL,
    *,
    scale: float = 1.0,
    size: tuple[int, int] = (10, 10),
) -> Image.Image:
    surface = _surface(size)
    _render_nonzero_path_fill(surface, subpaths, scale, fill)
    return surface


def _allocation_calls(
    subpaths: list[list[tuple[float, float]]],
    fill: tuple[int, int, int, int],
    *,
    scale: float,
    size: tuple[int, int],
) -> list[tuple[str, tuple[int, int], object]]:
    original_new = Image.new
    surface = original_new("RGBA", size, (0, 0, 0, 0))
    calls: list[tuple[str, tuple[int, int], object]] = []

    def recording_new(
        mode: str,
        image_size: tuple[int, int],
        color: object = 0,
    ) -> Image.Image:
        calls.append((mode, image_size, color))
        return original_new(mode, image_size, color)

    Image.new = recording_new
    try:
        _render_nonzero_path_fill(surface, subpaths, scale, fill)
    finally:
        Image.new = original_new
    return calls


def _assert_fill_witnesses() -> None:
    triangle = [(1, 1), (8, 1), (1, 8)]
    assert _render([triangle]).getpixel((2, 2)) == FILL
    assert _render([[*triangle, triangle[0]]]).tobytes() == _render([triangle]).tobytes()

    outer = [(1, 1), (9, 1), (9, 9), (1, 9)]
    inner_same = [(3, 3), (7, 3), (7, 7), (3, 7)]
    inner_opposite = [(3, 3), (3, 7), (7, 7), (7, 3)]
    assert _render([outer, inner_same]).getpixel((5, 5)) == FILL
    assert _render([outer, inner_opposite]).getpixel((5, 5)) == (0, 0, 0, 0)

    bow_tie = [(1, 1), (9, 9), (1, 9), (9, 1)]
    bow_tie_image = _render([bow_tie])
    assert bow_tie_image.getpixel((5, 2)) == FILL
    assert bow_tie_image.getpixel((2, 5)) == (0, 0, 0, 0)

    clipped = _render([[(-5, -5), (15, -5), (15, 15), (-5, 15)]], (16, 32, 48, 255))
    assert clipped.getbbox() == (0, 0, 10, 10)
    assert clipped.getpixel((0, 0)) == (16, 32, 48, 255)
    assert clipped.getpixel((9, 9)) == (16, 32, 48, 255)

    assert _render([]).getbbox() is None
    assert _render([[(2, 2)]]).getbbox() is None
    assert _render([[(2, 2)], triangle]).tobytes() == _render([triangle]).tobytes()
    assert _render([[(1, 1), (5, 1), (8, 1)]]).getbbox() is None
    assert _render([[(-8, 2), (-4, 2), (-4, 8), (-8, 8)]]).getbbox() is None
    assert _render([[(-2, 1), (0.5, 1), (0.5, 8), (-2, 8)]]).getbbox() is None
    assert _render([[(1, -2), (8, -2), (8, 0.5), (1, 0.5)]]).getbbox() is None

    horizontal_y = float("3.7")
    horizontal_y_copy = horizontal_y + 0.0
    horizontal = [(2.2, horizontal_y), (7.6, horizontal_y_copy), (4.8, 8.1)]
    assert _render([horizontal], scale=1.7, size=(20, 20)).getpixel((8, 9)) == FILL

    reentering = [
        (2, -8),
        (3, -7),
        (2, 2),
        (8, 2),
        (8, 8),
        (2, 8),
    ]
    reentering_image = _render([reentering])
    assert reentering_image.getpixel((5, 5)) == FILL
    assert hashlib.sha256(reentering_image.tobytes()).hexdigest() == ("0251e99a611a624d5b12a0eb3049151040ee3a7df9b99247fbe6b593842c684d")

    assert _render([[(2, -8), (8, -8), (8, -2), (2, -2)]]).getbbox() is None

    tall = [(2, 2), (4, 2), (4, 15), (2, 15)]
    assert _render([tall], size=(20, 20)).getpixel((3, 10)) == FILL

    alpha = _render([[(1, 1), (8, 1), (8, 8), (1, 8)]], (255, 0, 0, 128))
    assert alpha.getpixel((4, 4)) == (255, 0, 0, 128)

    fractional = [
        [(0.2, 1.3), (18.7, 0.4), (20.2, 15.6), (2.1, 17.4)],
        [(5.3, 4.2), (5.8, 12.9), (14.4, 13.6), (15.1, 3.8)],
        [(-3.2, 7.4), (4.1, 20.3), (8.6, 8.2)],
    ]
    fractional_image = _render(
        fractional,
        (23, 97, 181, 173),
        scale=1.7,
        size=(37, 29),
    )
    assert hashlib.sha256(fractional_image.tobytes()).hexdigest() == ("faba3e945eac3412e85039ed2aead671610dc9378ec5b351c05744882652ddd0")

    translated = [
        [(4.2, 3.7), (13.8, 4.4), (15.1, 11.6), (5.3, 13.2)],
        [(7.1, 6.2), (7.6, 10.1), (11.9, 10.6), (12.4, 5.8)],
    ]
    translated_image = _render(
        translated,
        (71, 29, 203, 149),
        scale=2.3,
        size=(41, 37),
    )
    assert hashlib.sha256(translated_image.tobytes()).hexdigest() == ("c72e2b3227d232f91276095d47c7e7e89fd5a574362827ccf1f4bd9f3bc97b00")
    assert _allocation_calls(
        translated,
        (71, 29, 203, 149),
        scale=2.3,
        size=(41, 37),
    ) == [
        ("L", (25, 21), 0),
        ("RGB", (25, 21), (71, 29, 203)),
    ]
    assert _allocation_calls(
        [[(-5, -5), (15, -5), (15, 15), (-5, 15)]],
        (16, 32, 48, 255),
        scale=1.0,
        size=(10, 10),
    ) == [
        ("L", (10, 10), 0),
        ("RGB", (10, 10), (16, 32, 48)),
    ]
    assert (
        _allocation_calls(
            [[(-2, 1), (0.5, 1), (0.5, 8), (-2, 8)]],
            FILL,
            scale=1.0,
            size=(10, 10),
        )
        == []
    )
    assert (
        _allocation_calls(
            [[(1, -2), (8, -2), (8, 0.5), (1, 0.5)]],
            FILL,
            scale=1.0,
            size=(10, 10),
        )
        == []
    )

    large_rows = [
        [(10, 260), (20, 260), (20, 270), (10, 270)],
        [(30, 280), (40, 280), (40, 290), (30, 290)],
    ]
    large_rows_image = _render(large_rows, size=(300, 300))
    assert large_rows_image.getpixel((15, 265)) == FILL
    assert large_rows_image.getpixel((15, 275)) == (0, 0, 0, 0)

    large_columns = [
        [(260.1, 10), (260.2, 10), (260.2, 20), (260.1, 20)],
        [(270, 30), (280, 30), (280, 40), (270, 40)],
    ]
    large_columns_image = _render(large_columns, size=(300, 50))
    assert large_columns_image.getpixel((260, 15)) == (0, 0, 0, 0)
    assert large_columns_image.getpixel((275, 35)) == FILL


def _assert_scaled_path_witnesses() -> None:
    style = DrawingStyle("p12_mutation", stroke="none", fill="#c02010", stroke_width=0.0)
    path = PathDrawing(style, [PathCommand("M", [(1, 2)]), PathCommand("L", [(3, 4)])])
    assert _scaled_path_subpaths(path, 2.0) == [[(2.0, 4.0), (6.0, 8.0)]]

    overflow = PathDrawing(style, [PathCommand("M", [(1e308, 1)])])
    try:
        _scaled_path_subpaths(overflow, 300.0)
    except ValueError as exc:
        assert str(exc) == "raster path geometry must remain finite after scaling"
    else:
        raise AssertionError("scaled overflow was accepted")


def _assert_path_component_witnesses() -> None:
    path = PathDrawing(
        DrawingStyle("p12_wiring", stroke="none", fill="#c02010", stroke_width=0.0),
        [
            PathCommand("M", [(1, 1)]),
            PathCommand("L", [(8, 1), (8, 8), (1, 8)]),
            PathCommand("Z"),
        ],
    )

    fill_only = _surface()
    _render_path_component(fill_only, ImageDraw.Draw(fill_only), path, 1.0, FILL, None, 0)
    assert fill_only.getpixel((4, 4)) == FILL
    assert fill_only.getpixel((0, 0)) == (0, 0, 0, 0)

    stroke_only = _surface()
    _render_path_component(
        stroke_only,
        ImageDraw.Draw(stroke_only),
        path,
        1.0,
        None,
        (0, 0, 255, 255),
        1,
    )
    assert stroke_only.getpixel((1, 1)) == (0, 0, 255, 255)
    assert stroke_only.getpixel((4, 4)) == (0, 0, 0, 0)

    fill_and_stroke = _surface()
    _render_path_component(
        fill_and_stroke,
        ImageDraw.Draw(fill_and_stroke),
        path,
        1.0,
        (255, 0, 0, 128),
        (0, 0, 255, 128),
        1,
    )
    assert fill_and_stroke.getpixel((1, 1)) == (85, 0, 170, 192)
    assert fill_and_stroke.getpixel((4, 4)) == (255, 0, 0, 128)
    assert fill_and_stroke.getpixel((0, 0)) == (0, 0, 0, 0)


if __name__ == "__main__":
    _assert_fill_witnesses()
    _assert_scaled_path_witnesses()
    _assert_path_component_witnesses()
