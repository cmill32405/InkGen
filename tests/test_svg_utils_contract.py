"""SVG utility contract tests."""

from __future__ import annotations

import pytest
from svgpathtools import Line, Path

from InkGen.svg_generator import SVGComponent
from InkGen.svg_utils import _collect_bbox, _parse_length, _style_from_attributes, flatten_svg


def _write_svg(path, body: str, *, width: str = "100px", height: str = "40px") -> None:
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
{body}
</svg>""",
        encoding="utf-8",
    )


@pytest.mark.condition("SVG-UTILS-P1")
def test_svg_utils_style_and_length_parsing_contract() -> None:
    """SVG-UTILS-P1: Style and length parsing preserve public metadata."""
    assert _style_from_attributes({"style": "fill:red;stroke:blue", "fill": "green"}) == "fill:red;stroke:blue"
    assert (
        _style_from_attributes(
            {
                "fill": "#112233",
                "stroke": "none",
                "stroke-width": "0.5",
                "fill-opacity": "0.25",
                "stroke-opacity": "0.75",
            }
        )
        == "fill:#112233;stroke:none;stroke-width:0.5;fill-opacity:0.25;stroke-opacity:0.75"
    )
    assert _style_from_attributes({}) is None
    assert _parse_length(None) is None
    assert _parse_length("12.5px") == 12.5
    assert _parse_length("-3.25mm") == -3.25
    assert _parse_length("1e2px") == 100.0
    assert _parse_length("auto") is None


@pytest.mark.condition("SVG-UTILS-P1")
def test_svg_utils_collect_bbox_handles_empty_and_invalid_paths() -> None:
    """SVG-UTILS-P1: Bbox collection returns a finite zero bbox when no path contributes geometry."""
    empty_path = Path()
    line_path = Path(Line(3 + 4j, 8 + 10j))

    assert _collect_bbox([]) == ((0.0, 0.0), (0.0, 0.0))
    assert _collect_bbox([empty_path]) == ((0.0, 0.0), (0.0, 0.0))
    assert _collect_bbox([empty_path, line_path]) == ((3.0, 4.0), (8.0, 10.0))


@pytest.mark.condition("SVG-UTILS-P1")
def test_flatten_svg_normalizes_transformed_paths_and_preserves_metadata(tmp_path) -> None:
    """SVG-UTILS-P1: SVG flattening normalizes geometry and preserves style/size metadata."""
    svg_file = tmp_path / "asset.svg"
    _write_svg(
        svg_file,
        """
<path d="M 10 20 L 30 20 L 30 35 Z" style="fill:#445566;stroke:none" />
<path d="M 2 3 L 7 3" transform="translate(5,7)" fill="none" stroke="#000000" stroke-width="0.2" />
""",
        width="120.5px",
        height="2.5e1mm",
    )

    flattened = flatten_svg(str(svg_file))

    assert flattened.width == 120.5
    assert flattened.height == 25.0
    (min_x, min_y), (max_x, max_y) = flattened.bbox
    assert min_x == pytest.approx(0.0)
    assert min_y == pytest.approx(0.0)
    assert max_x == pytest.approx(28.0)
    assert max_y == pytest.approx(32.0)
    assert [path.style for path in flattened.paths] == [
        "fill:#445566;stroke:none",
        "fill:none;stroke:#000000;stroke-width:0.2",
    ]
    assert "M 8.0,17.0" in flattened.paths[0].d
    assert "M 0.0,0.0" in flattened.paths[1].d


@pytest.mark.condition("SVG-UTILS-P1")
def test_flatten_svg_rejects_files_without_vector_paths(tmp_path) -> None:
    """SVG-UTILS-P1: SVG flattening fails loudly when no path geometry exists."""
    svg_file = tmp_path / "empty.svg"
    _write_svg(svg_file, "")

    with pytest.raises(ValueError, match="No vector paths found in SVG"):
        flatten_svg(str(svg_file))


@pytest.mark.condition("SVG-UTILS-P1")
def test_svg_component_uses_flattened_svg_live_path(tmp_path) -> None:
    """SVG-UTILS-P1: SVGComponent consumes flattened SVG output in its live path."""
    svg_file = tmp_path / "asset.svg"
    _write_svg(svg_file, '<path d="M 10 20 L 30 20 L 30 35 Z" fill="#123456" />')

    component = SVGComponent(filepath=str(svg_file), position=(5.0, 6.0), scale=2.0)

    assert component.points[0] == (pytest.approx(5.0), pytest.approx(6.0))
    assert component.points[2] == (pytest.approx(45.0), pytest.approx(36.0))
    assert component.parameters["SVGComponent"]["width"] == 100.0
    assert component.parameters["SVGComponent"]["height"] == 40.0
    assert "fill:#123456" in component.generate_svg()


@pytest.mark.condition("SVG-COMPONENT-FINITE-P2")
def test_svg_component_rejects_invalid_position_and_scale_boundaries() -> None:
    """SVG-COMPONENT-FINITE-P2: Embedded SVG transforms accept only finite numeric scalars."""
    paths = [{"d": "M 0 0 L 10 0", "style": None}]
    bbox = ((0.0, 0.0), (10.0, 5.0))

    for position in [
        (float("nan"), 0.0),
        (0.0, float("inf")),
        (True, 0.0),
        ("bad", 0.0),
        (0.0,),
    ]:
        with pytest.raises((TypeError, ValueError)):
            SVGComponent(paths=paths, bbox=bbox, position=position)  # type: ignore[arg-type]

    for scale in [float("nan"), float("inf"), -float("inf"), True, 0.0, -1.0, "bad"]:
        with pytest.raises((TypeError, ValueError)):
            SVGComponent(paths=paths, bbox=bbox, scale=scale)  # type: ignore[arg-type]

    component = SVGComponent(paths=paths, bbox=bbox, position=(1.0, 2.0), scale=2.0)
    before = component.parameters

    with pytest.raises(ValueError):
        component.position = (float("-inf"), 2.0)
    assert component.parameters == before

    with pytest.raises(TypeError):
        component.scale = False  # type: ignore[assignment]
    assert component.parameters == before


@pytest.mark.condition("SVG-COMPONENT-FINITE-P2")
def test_svg_component_rejects_invalid_bbox_boundaries_and_deserialized_values() -> None:
    """SVG-COMPONENT-FINITE-P2: Bbox and serialized transforms cannot inject non-finite geometry."""
    paths = [{"d": "M 0 0 L 10 0", "style": None}]

    for bbox in [
        ((0.0, 0.0), (float("nan"), 5.0)),
        ((0.0, True), (10.0, 5.0)),
        ((0.0, 0.0),),
        "bad",
    ]:
        with pytest.raises((TypeError, ValueError)):
            SVGComponent(paths=paths, bbox=bbox)  # type: ignore[arg-type]

    payload = {
        "SVGComponent": {
            "paths": paths,
            "bbox": ((0.0, 0.0), (10.0, 5.0)),
            "position": [3.0, 4.0],
            "scale": 1.5,
            "width": None,
            "height": None,
            "source": None,
        }
    }

    component = SVGComponent.create_from_dict(payload)

    assert component.points == [(3.0, 4.0), (18.0, 4.0), (18.0, 11.5), (3.0, 11.5)]
    assert '<g transform="translate(3.0,4.0) scale(1.5)">' in component.generate_svg()

    payload["SVGComponent"]["scale"] = float("nan")
    with pytest.raises(ValueError):
        SVGComponent.create_from_dict(payload)
