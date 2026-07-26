"""Renderer-neutral linear-gradient fill values."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class GradientStop:
    """One color stop in a normalized linear gradient."""

    offset: float
    color: str

    def __post_init__(self) -> None:
        """Validate and normalize the stop offset and RGB color."""
        if isinstance(self.offset, bool) or not isinstance(self.offset, (int, float)):
            raise TypeError("gradient stop offset must be a finite number")
        offset = float(self.offset)
        if not math.isfinite(offset):
            raise ValueError("gradient stop offset must be finite")
        if not 0.0 <= offset <= 1.0:
            raise ValueError("gradient stop offset must be between 0.0 and 1.0")
        if not isinstance(self.color, str):
            raise TypeError("gradient stop color must be a #rrggbb string")
        color = self.color.lower()
        if len(color) != 7 or not color.startswith("#") or any(character not in "0123456789abcdef" for character in color[1:]):
            raise ValueError("gradient stop color must be a #rrggbb string")
        object.__setattr__(self, "offset", offset)
        object.__setattr__(self, "color", color)

    @classmethod
    def from_value(cls, value: object) -> GradientStop:
        """Create a stop from a stop instance or two-item sequence."""
        if isinstance(value, cls):
            return value
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
            raise TypeError("gradient stops must contain offset/color pairs")
        return cls(value[0], value[1])  # type: ignore[arg-type]

    def to_list(self) -> list[object]:
        """Return the public serialization shape for this stop."""
        return [self.offset, self.color]


@dataclass(frozen=True)
class LinearGradientFill:
    """A reusable linear-gradient definition with canvas-space angle semantics."""

    stops: tuple[GradientStop, ...]
    angle_deg: float = 0.0

    def __init__(self, stops: Sequence[GradientStop | Sequence[object]], angle_deg: float = 0.0) -> None:
        """Create a linear gradient from ordered stops and a CCW angle."""
        if isinstance(stops, (str, bytes)) or not isinstance(stops, Sequence):
            raise TypeError("gradient stops must be a sequence")
        normalized_stops = tuple(GradientStop.from_value(stop) for stop in stops)
        if len(normalized_stops) < 2:
            raise ValueError("linear gradients require at least two stops")
        if any(left.offset >= right.offset for left, right in zip(normalized_stops, normalized_stops[1:], strict=False)):
            raise ValueError("gradient stop offsets must be strictly increasing")
        if isinstance(angle_deg, bool) or not isinstance(angle_deg, (int, float)):
            raise TypeError("gradient angle_deg must be a finite number")
        angle = float(angle_deg)
        if not math.isfinite(angle):
            raise ValueError("gradient angle_deg must be finite")
        object.__setattr__(self, "stops", normalized_stops)
        object.__setattr__(self, "angle_deg", angle % 360.0)

    @classmethod
    def from_dict(cls, data: object) -> LinearGradientFill:
        """Recreate a linear gradient from its public parameter mapping."""
        if not isinstance(data, Mapping):
            raise TypeError("linear gradient data must be a mapping")
        if data.get("kind") != "linear":
            raise ValueError("linear gradient kind must be 'linear'")
        if "stops" not in data:
            raise ValueError("linear gradient data must include stops")
        return cls(data["stops"], data.get("angle_deg", 0.0))  # type: ignore[arg-type]

    @property
    def parameters(self) -> dict[str, object]:
        """Return the canonical renderer-neutral gradient payload."""
        return {
            "kind": "linear",
            "stops": [stop.to_list() for stop in self.stops],
            "angle_deg": self.angle_deg,
        }

    def extended_stops(self) -> tuple[GradientStop, ...]:
        """Return stops extended to offsets zero and one for PDF functions."""
        stops = list(self.stops)
        if stops[0].offset != 0.0:
            stops.insert(0, GradientStop(0.0, stops[0].color))
        if stops[-1].offset != 1.0:
            stops.append(GradientStop(1.0, stops[-1].color))
        return tuple(stops)

    def axis_for_box(
        self,
        position: tuple[float, float],
        width: float,
        height: float,
    ) -> tuple[float, float, float, float]:
        """Return a full-coverage gradient axis in top-left canvas coordinates."""
        x, y = (float(position[0]), float(position[1]))
        width_value = float(width)
        height_value = float(height)
        if not all(math.isfinite(value) for value in (x, y, width_value, height_value)):
            raise ValueError("gradient rectangle geometry must be finite")
        if width_value <= 0.0 or height_value <= 0.0:
            raise ValueError("gradient rectangles must have positive width and height")

        radians = math.radians(self.angle_deg)
        direction_x = _zero_near_origin(math.cos(radians))
        direction_y = _zero_near_origin(-math.sin(radians))
        center_x = x + width_value / 2.0
        center_y = y + height_value / 2.0
        half_span = abs(direction_x) * width_value / 2.0 + abs(direction_y) * height_value / 2.0
        return (
            _zero_near_origin(center_x - direction_x * half_span),
            _zero_near_origin(center_y - direction_y * half_span),
            _zero_near_origin(center_x + direction_x * half_span),
            _zero_near_origin(center_y + direction_y * half_span),
        )


def coerce_linear_gradient(value: object | None) -> LinearGradientFill | None:
    """Normalize an optional public gradient value."""
    if value is None:
        return None
    if isinstance(value, LinearGradientFill):
        return value
    return LinearGradientFill.from_dict(value)


def _zero_near_origin(value: float) -> float:
    """Remove floating-point trigonometric residue around zero."""
    return 0.0 if abs(value) < 1e-12 else value
