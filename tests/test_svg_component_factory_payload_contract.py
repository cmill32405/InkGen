"""Behavioral tests for standalone SVGComponent factory payload envelopes."""

from __future__ import annotations

import pytest

from InkGen.svg_generator import SVGComponent


def _payload() -> dict[str, dict[str, object]]:
    """Return a valid serialized SVGComponent payload."""
    return {
        "SVGComponent": {
            "paths": [{"d": "M 0 0 L 10 0", "style": "fill:#123456"}],
            "bbox": ((0.0, 0.0), (10.0, 5.0)),
            "position": [3.0, 4.0],
            "scale": 1.5,
            "width": 10.0,
            "height": 5.0,
            "source": "asset.svg",
        }
    }


@pytest.mark.condition("SVG-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("payload", "exception_type", "message"),
    [
        (object(), TypeError, "SVGComponent data must be a mapping"),
        ({}, ValueError, "SVGComponent data must include SVGComponent"),
        ({"SVGComponent": object()}, TypeError, "SVGComponent payload must be a mapping"),
        ({"SVGComponent": {"bbox": ((0.0, 0.0), (10.0, 5.0))}}, ValueError, "SVGComponent payload must include paths"),
        ({"SVGComponent": {"paths": []}}, ValueError, "SVGComponent payload must include bbox"),
        (
            {"SVGComponent": {"paths": "bad", "bbox": ((0.0, 0.0), (10.0, 5.0))}},
            TypeError,
            "SVGComponent paths must be a sequence",
        ),
    ],
)
def test_svg_component_factory_rejects_malformed_root_payloads(
    payload: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """SVG-COMPONENT-FACTORY-PAYLOAD-P2: Roots and required fields fail explicitly."""
    with pytest.raises(exception_type, match=message):
        SVGComponent.create_from_dict(payload)


@pytest.mark.condition("SVG-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("path_entry", "exception_type", "message"),
    [
        (object(), TypeError, "SVGComponent path entries must be mappings"),
        ({}, ValueError, "SVGComponent path payload must include d"),
        ({"d": object()}, TypeError, "SVGComponent path d must be a string"),
        ({"d": "M 0 0", "style": object()}, TypeError, "SVGComponent path style must be a string or None"),
    ],
)
def test_svg_component_factory_rejects_malformed_path_entries(
    path_entry: object,
    exception_type: type[Exception],
    message: str,
) -> None:
    """SVG-COMPONENT-FACTORY-PAYLOAD-P2: Serialized path entries fail before rendering."""
    payload = _payload()
    payload["SVGComponent"]["paths"] = [path_entry]

    with pytest.raises(exception_type, match=message):
        SVGComponent.create_from_dict(payload)


@pytest.mark.condition("SVG-COMPONENT-FACTORY-PAYLOAD-P2")
@pytest.mark.parametrize(
    "bbox",
    [
        object(),
        ((0.0, 0.0),),
        ((0.0, 0.0), (float("nan"), 5.0)),
    ],
)
def test_svg_component_factory_routes_bbox_to_existing_geometry_boundary(bbox: object) -> None:
    """SVG-COMPONENT-FACTORY-PAYLOAD-P2: Bbox payloads still use finite geometry validation."""
    payload = _payload()
    payload["SVGComponent"]["bbox"] = bbox

    with pytest.raises((TypeError, ValueError)):
        SVGComponent.create_from_dict(payload)


@pytest.mark.condition("SVG-COMPONENT-FACTORY-PAYLOAD-P2")
def test_svg_component_factory_preserves_valid_round_trip_and_markup() -> None:
    """SVG-COMPONENT-FACTORY-PAYLOAD-P2: Valid serialized SVGComponent payloads hydrate."""
    payload = _payload()

    component = SVGComponent.create_from_dict(payload)

    assert component.parameters == payload
    assert component.points == [(3.0, 4.0), (18.0, 4.0), (18.0, 11.5), (3.0, 11.5)]
    assert '<g transform="translate(3.0,4.0) scale(1.5)">' in component.generate_svg()
    assert '<path d="M 0 0 L 10 0" style="fill:#123456" />' in component.generate_svg()


@pytest.mark.condition("SVG-COMPONENT-FACTORY-PAYLOAD-P2")
def test_svg_component_factory_preserves_optional_transform_defaults() -> None:
    """SVG-COMPONENT-FACTORY-PAYLOAD-P2: Omitted transform fields use neutral defaults."""
    payload = _payload()
    del payload["SVGComponent"]["position"]
    del payload["SVGComponent"]["scale"]

    component = SVGComponent.create_from_dict(payload)

    assert component.position == (0.0, 0.0)
    assert component.scale == 1.0
    assert component.points == [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]
    assert component.generate_svg().startswith("<g>\n")
