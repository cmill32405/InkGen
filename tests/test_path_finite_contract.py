"""Behavioral tests for finite path command coordinate boundaries."""

from __future__ import annotations

from uuid import uuid4

import pytest

from InkGen.component import Path, PathCommand
from InkGen.style import DrawingStyle


def _style() -> DrawingStyle:
    """Return a unique drawing style for path finite-boundary tests."""
    return DrawingStyle(f"path_finite_contract_{uuid4().hex}", stroke="#000000", fill="none")


@pytest.mark.condition("PATH-FINITE-P2")
def test_path_command_preserves_valid_finite_points() -> None:
    """PATH-FINITE-P2: Finite command coordinates preserve public geometry."""
    command = PathCommand(" l ", [(1.25, -2.5), (3.5, 4.25)])

    assert command.type == "L"
    assert command.points == [(1.25, -2.5), (3.5, 4.25)]

    command.add_point((7.0, -1.0))

    assert command.points == [(1.25, -2.5), (3.5, 4.25), (7.0, -1.0)]


@pytest.mark.condition("PATH-FINITE-P2")
def test_path_command_rejects_invalid_constructor_and_setter_points() -> None:
    """PATH-FINITE-P2: Invalid command coordinates fail without mutation."""
    invalid_values = [float("nan"), float("inf"), -float("inf"), True, object(), "bad"]

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            PathCommand("L", [(value, 0.0)])  # type: ignore[list-item]
        with pytest.raises((TypeError, ValueError)):
            PathCommand("L", [(0.0, value)])  # type: ignore[list-item]

    for point in [(0.0,), (0.0, 1.0, 2.0)]:
        with pytest.raises(ValueError, match="Points must contain two numeric values."):
            PathCommand("L", [point])  # type: ignore[list-item]

    command = PathCommand("L", [(0.0, 0.0)])
    before = command.parameters

    for value in invalid_values:
        with pytest.raises((TypeError, ValueError)):
            command.points = [(value, 0.0)]  # type: ignore[list-item]
        assert command.parameters == before

        with pytest.raises((TypeError, ValueError)):
            command.add_point((0.0, value))  # type: ignore[arg-type]
        assert command.parameters == before


@pytest.mark.condition("PATH-FINITE-P2")
def test_path_add_command_dictionary_rejects_nonfinite_coordinates() -> None:
    """PATH-FINITE-P2: Path dictionary insertion consumes finite command boundary."""
    path = Path(_style(), [PathCommand("M", [(0.0, 0.0)])])
    before = path.parameters

    with pytest.raises(ValueError):
        path.add_command({"type": "L", "points": [(float("nan"), 1.0)]})
    assert path.parameters == before

    with pytest.raises(TypeError):
        path.add_command({"type": "L", "points": [(True, 1.0)]})
    assert path.parameters == before
