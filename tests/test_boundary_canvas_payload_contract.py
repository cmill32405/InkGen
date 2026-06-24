"""Behavioral tests for boundary and canvas factory payload envelopes."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from InkGen.boundary import Boundary, Canvas
from InkGen.document import Document


def _boundary_payload() -> dict[str, dict[str, object]]:
    """Return a valid serialized boundary payload."""
    return {
        "Boundary": {
            "hull": [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)],
            "outer_boundary": True,
        }
    }


def _canvas_payload() -> dict[str, dict[str, object]]:
    """Return a valid serialized canvas payload."""
    return {"Canvas": {"width": 20.0, "height": 10.0, "units": "mm"}}


@pytest.mark.condition("BOUNDARY-CANVAS-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "key"),
    [
        (Boundary.create_from_dict, "Boundary"),
        (Canvas.create_from_dict, "Canvas"),
    ],
)
def test_boundary_canvas_factories_reject_malformed_payload_roots(
    factory: Callable[[object], object],
    key: str,
) -> None:
    """BOUNDARY-CANVAS-PAYLOAD-P2: Boundary and canvas roots fail explicitly."""
    cases = [
        (object(), TypeError, f"{key} data must be a mapping"),
        ({}, ValueError, f"{key} data must include {key}"),
        ({key: object()}, TypeError, f"{key} payload must be a mapping"),
    ]

    for payload, exception_type, message in cases:
        with pytest.raises(exception_type, match=message):
            factory(payload)


@pytest.mark.condition("BOUNDARY-CANVAS-PAYLOAD-P2")
@pytest.mark.parametrize(
    ("factory", "payload", "message"),
    [
        (Boundary.create_from_dict, {"Boundary": {"outer_boundary": True}}, "Boundary payload must include hull"),
        (
            Boundary.create_from_dict,
            {"Boundary": {"hull": [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]}},
            "Boundary payload must include outer_boundary",
        ),
        (Canvas.create_from_dict, {"Canvas": {"height": 10.0, "units": "mm"}}, "Canvas payload must include width"),
        (Canvas.create_from_dict, {"Canvas": {"width": 20.0, "height": 10.0}}, "Canvas payload must include units"),
    ],
)
def test_boundary_canvas_factories_reject_missing_required_fields(
    factory: Callable[[object], object],
    payload: object,
    message: str,
) -> None:
    """BOUNDARY-CANVAS-PAYLOAD-P2: Required fields fail at the factory boundary."""
    with pytest.raises(ValueError, match=message):
        factory(payload)


@pytest.mark.condition("BOUNDARY-CANVAS-PAYLOAD-P2")
def test_boundary_canvas_factories_preserve_valid_hydration() -> None:
    """BOUNDARY-CANVAS-PAYLOAD-P2: Valid serialized payloads still hydrate."""
    boundary = Boundary.create_from_dict(_boundary_payload())
    canvas = Canvas.create_from_dict(_canvas_payload())

    assert boundary.boundary_type == "outer"
    assert boundary.boundary_points == [(0.0, 0.0), (2.0, 0.0), (0.0, 2.0)]
    assert canvas.width == 20.0
    assert canvas.height == 10.0
    assert canvas.units == "mm"


@pytest.mark.condition("BOUNDARY-CANVAS-PAYLOAD-P2")
def test_canvas_payload_contract_remains_live_in_document_hydration() -> None:
    """BOUNDARY-CANVAS-PAYLOAD-P2: Document hydration consumes Canvas payloads."""
    document = Document.create_from_dict({"Document": {"canvas": _canvas_payload(), "pages": []}})

    assert document.parameters["Document"]["canvas"] == _canvas_payload()

    with pytest.raises(ValueError, match="Canvas payload must include width"):
        Document.create_from_dict({"Document": {"canvas": {"Canvas": {"height": 10.0, "units": "mm"}}, "pages": []}})
