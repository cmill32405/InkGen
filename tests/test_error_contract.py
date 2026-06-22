"""Public exception contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

import InkGen
import InkGen.errors as errors
from InkGen.boundary import Boundary, Canvas
from InkGen.component import ComponentGroup, PolygonalDrawingComponent, WidthHeightDrawingComponent
from InkGen.document import Document, Layer, Layers
from InkGen.style import DrawingStyle

PUBLIC_EXCEPTION_NAMES = (
    "IllegalArgumentError",
    "InvalidConvexHull",
    "InvalidPolygonError",
    "InvalidComponentID",
    "InvalidComponentGroupID",
    "ComponentGroupCollision",
    "ComponentGroupOffCanvas",
    "IncompatibleCanvas",
)


def _style(name: str) -> DrawingStyle:
    """Return a named drawing style for live exception paths."""
    return DrawingStyle(f"{name}_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("ERRORS-P1")
def test_project_exceptions_are_plain_value_errors() -> None:
    """ERRORS-P1: Project exceptions preserve ValueError semantics."""
    for name in PUBLIC_EXCEPTION_NAMES:
        exception_type = getattr(errors, name)
        exception = exception_type("contract message")

        assert issubclass(exception_type, ValueError)
        assert issubclass(exception_type, Exception)
        assert exception.args == ("contract message",)
        assert str(exception) == "contract message"


@pytest.mark.condition("ERRORS-P1")
def test_project_exceptions_are_exported_from_package_root() -> None:
    """ERRORS-P1: Root exception exports alias the canonical error module classes."""
    for name in PUBLIC_EXCEPTION_NAMES:
        assert name in InkGen.__all__
        assert getattr(InkGen, name) is getattr(errors, name)


@pytest.mark.condition("ERRORS-P1")
def test_exception_contracts_are_live_in_existing_failure_paths() -> None:
    """ERRORS-P1: Existing public failure paths raise the documented exception classes."""
    with pytest.raises(InkGen.IllegalArgumentError):
        Canvas(10.0, 10.0, "px")

    with pytest.raises(InkGen.InvalidConvexHull):
        Boundary(None)  # type: ignore[arg-type]

    with pytest.raises(InkGen.InvalidPolygonError):
        PolygonalDrawingComponent([(0.0, 0.0), (1.0, 1.0)], _style("error_polygon"))

    component_group = ComponentGroup("parts")
    with pytest.raises(InkGen.InvalidComponentID):
        component_group.get_component(-1)

    layer = Layer("base", Canvas(20.0, 20.0, "mm"))
    with pytest.raises(InkGen.InvalidComponentGroupID):
        layer.remove_component_group("missing")

    first = ComponentGroup("first")
    first.add_component(WidthHeightDrawingComponent((2.0, 2.0), 8.0, 8.0, _style("error_first")))
    second = ComponentGroup("second")
    second.add_component(WidthHeightDrawingComponent((4.0, 4.0), 2.0, 2.0, _style("error_second")))
    layer.add_component_group(first, allow_collision=False)
    with pytest.raises(InkGen.ComponentGroupCollision):
        layer.add_component_group(second, allow_collision=False)

    off_canvas = ComponentGroup("off_canvas")
    off_canvas.add_component(WidthHeightDrawingComponent((18.0, 18.0), 8.0, 8.0, _style("error_off_canvas")))
    with pytest.raises(InkGen.ComponentGroupOffCanvas):
        layer.add_component_group(off_canvas)

    document = Document(Canvas(30.0, 30.0, "mm"))
    incompatible_page = Layers(Canvas(40.0, 30.0, "mm"))
    with pytest.raises(InkGen.IncompatibleCanvas):
        document.add_page(page=incompatible_page)
