"""Renderer-neutral drawing recipes for synthetic engineering drawings.

The classes in this module describe drawing intent separately from any concrete
output backend. A recipe can be materialized as SVG or PDF components without
embedding renderer-specific classes in higher-level synthetic drawing builders.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Protocol

from InkGen.boundary import Canvas
from InkGen.component import (
    Component,
    ComponentGroup,
    PathCommand,
    PolygonalDrawingComponent,
    TextComponent,
    normalize_rectangle_corner_radii,
)
from InkGen.style import DrawingStyle, TextStyle


class OutputFormat(str, Enum):
    """Supported concrete output backends for neutral drawing recipes."""

    SVG = "svg"
    PDF = "pdf"


class DrawingPrimitive(Protocol):
    """Protocol for primitives that can materialize to a renderer component."""

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create a concrete InkGen component for the requested backend."""


def normalize_output_format(output_format: OutputFormat | str) -> OutputFormat:
    """Normalize a backend selector and fail loudly for unsupported formats."""
    if isinstance(output_format, OutputFormat):
        return output_format
    if not isinstance(output_format, str):
        raise TypeError("output_format must be an OutputFormat or string")
    try:
        return OutputFormat(output_format.lower())
    except ValueError as exc:
        raise ValueError(f"Unsupported output format: {output_format!r}") from exc


def _require_drawing_style(style: object, owner: str) -> None:
    """Fail when a renderer-neutral drawing primitive receives the wrong style kind."""
    if not isinstance(style, DrawingStyle):
        raise TypeError(f"{owner} style must be a DrawingStyle")


def _require_text_style(style: object, owner: str) -> None:
    """Fail when a renderer-neutral text primitive receives the wrong style kind."""
    if not isinstance(style, TextStyle):
        raise TypeError(f"{owner} style must be a TextStyle")


def _coerce_text_value(value: object) -> str:
    """Normalize renderer-neutral text to the scalar text component contract."""
    if isinstance(value, (str, int, float, complex, bool)):
        return str(value)
    raise TypeError("TextDrawing text must be a string or a non-iterable built in type")


def _coerce_point_pair(value: object, *, name: str) -> tuple[float, float]:
    """Normalize renderer-neutral point payloads to finite numeric pairs."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
        raise ValueError(f"{name} must contain two numeric values")
    if any(isinstance(coordinate, bool) for coordinate in value):
        raise TypeError(f"{name} coordinates must be numeric values")
    try:
        x = float(value[0])
        y = float(value[1])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain two numeric values") from exc
    if not isfinite(x) or not isfinite(y):
        raise ValueError(f"{name} coordinates must be finite")
    return x, y


def _coerce_non_negative_point_pair(value: object, *, name: str) -> tuple[float, float]:
    """Normalize point payloads that use the nonnegative drawing component contract."""
    x, y = _coerce_point_pair(value, name=name)
    if x < 0 or y < 0:
        raise ValueError(f"{name} coordinates must be greater than or equal to zero")
    return x, y


def _coerce_finite_float(value: object, *, name: str) -> float:
    """Normalize renderer-neutral scalar payloads to finite floats."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be numeric") from exc
    if not isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _coerce_finite_positive_float(value: object, *, name: str) -> float:
    """Normalize renderer-neutral scalar payloads to finite positive floats."""
    number = _coerce_finite_float(value, name=name)
    if number <= 0.0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def _coerce_regular_polygon_sides(value: object) -> int:
    """Normalize renderer-neutral regular polygon side counts."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("RegularPolygonDrawing sides must be an integer")
    if value < 3:
        raise ValueError("RegularPolygonDrawing sides must be 3 or greater")
    return value


@dataclass(frozen=True)
class RectangleDrawing:
    """Renderer-neutral rectangle primitive."""

    position: tuple[float, float]
    width: float
    height: float
    corner_radii: float | tuple[float, float]
    style: DrawingStyle

    def __post_init__(self) -> None:
        """Validate the neutral rectangle geometry and style boundary."""
        position = _coerce_point_pair(self.position, name="RectangleDrawing position")
        width = _coerce_finite_non_negative_float(self.width, name="RectangleDrawing width")
        height = _coerce_finite_non_negative_float(self.height, name="RectangleDrawing height")
        normalize_rectangle_corner_radii(self.corner_radii, width, height)
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)
        _require_drawing_style(self.style, "RectangleDrawing")

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create a rectangle component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import RectangleSVG

            return RectangleSVG(self.position, self.width, self.height, self.corner_radii, self.style)
        from InkGen.pdf_generator import RectanglePDF

        return RectanglePDF(self.position, self.width, self.height, self.corner_radii, self.style)


@dataclass(frozen=True)
class LineDrawing:
    """Renderer-neutral line primitive."""

    point_1: tuple[float, float]
    point_2: tuple[float, float]
    style: DrawingStyle

    def __post_init__(self) -> None:
        """Validate the neutral line geometry and style boundary."""
        point_1 = _coerce_non_negative_point_pair(self.point_1, name="LineDrawing point_1")
        point_2 = _coerce_non_negative_point_pair(self.point_2, name="LineDrawing point_2")
        object.__setattr__(self, "point_1", point_1)
        object.__setattr__(self, "point_2", point_2)
        _require_drawing_style(self.style, "LineDrawing")

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create a line component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import LineSVG

            return LineSVG(self.point_1, self.point_2, self.style)
        from InkGen.pdf_generator import LinePDF

        return LinePDF(self.point_1, self.point_2, self.style)


@dataclass(frozen=True)
class TextDrawing:
    """Renderer-neutral text primitive."""

    text: str
    position: tuple[float, float]
    style: TextStyle

    def __post_init__(self) -> None:
        """Validate the neutral text payload and style boundary."""
        position = _coerce_point_pair(self.position, name="TextDrawing position")
        object.__setattr__(self, "text", _coerce_text_value(self.text))
        object.__setattr__(self, "position", position)
        _require_text_style(self.style, "TextDrawing")

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create a text component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import TextSVG

            return TextSVG(self.text, self.position, self.style)
        from InkGen.pdf_generator import TextPDF

        return TextPDF(self.text, self.position, self.style)


@dataclass(frozen=True)
class ArcDrawing:
    """Renderer-neutral elliptical arc primitive."""

    center: tuple[float, float]
    radius_x: float
    radius_y: float
    start_angle: float
    end_angle: float
    style: DrawingStyle
    rotation: float = 0.0

    def __post_init__(self) -> None:
        """Validate the neutral arc geometry and style boundary."""
        center = _coerce_point_pair(self.center, name="ArcDrawing center")
        radius_x = _coerce_finite_positive_float(self.radius_x, name="ArcDrawing radius_x")
        radius_y = _coerce_finite_positive_float(self.radius_y, name="ArcDrawing radius_y")
        start_angle = _coerce_finite_float(self.start_angle, name="ArcDrawing start_angle")
        end_angle = _coerce_finite_float(self.end_angle, name="ArcDrawing end_angle")
        rotation = _coerce_finite_float(self.rotation, name="ArcDrawing rotation")
        object.__setattr__(self, "center", center)
        object.__setattr__(self, "radius_x", radius_x)
        object.__setattr__(self, "radius_y", radius_y)
        object.__setattr__(self, "start_angle", start_angle)
        object.__setattr__(self, "end_angle", end_angle)
        object.__setattr__(self, "rotation", rotation)
        _require_drawing_style(self.style, "ArcDrawing")

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create an arc component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import ArcSVG

            return ArcSVG(self.center, self.radius_x, self.radius_y, self.start_angle, self.end_angle, self.style, self.rotation)
        from InkGen.pdf_generator import ArcPDF

        return ArcPDF(self.center, self.radius_x, self.radius_y, self.start_angle, self.end_angle, self.style, self.rotation)


@dataclass(frozen=True)
class QuadraticBezierDrawing:
    """Renderer-neutral quadratic Bezier primitive."""

    start_point: tuple[float, float]
    control_point: tuple[float, float]
    end_point: tuple[float, float]
    style: DrawingStyle

    def __post_init__(self) -> None:
        """Validate the neutral quadratic Bezier geometry and style boundary."""
        start_point = _coerce_point_pair(self.start_point, name="QuadraticBezierDrawing start_point")
        control_point = _coerce_point_pair(self.control_point, name="QuadraticBezierDrawing control_point")
        end_point = _coerce_point_pair(self.end_point, name="QuadraticBezierDrawing end_point")
        object.__setattr__(self, "start_point", start_point)
        object.__setattr__(self, "control_point", control_point)
        object.__setattr__(self, "end_point", end_point)
        _require_drawing_style(self.style, "QuadraticBezierDrawing")

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create a quadratic Bezier component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import QuadraticBezierSVG

            return QuadraticBezierSVG(self.start_point, self.control_point, self.end_point, self.style)
        from InkGen.pdf_generator import QuadraticBezierPDF

        return QuadraticBezierPDF(self.start_point, self.control_point, self.end_point, self.style)


@dataclass(frozen=True)
class CubicBezierDrawing:
    """Renderer-neutral cubic Bezier primitive."""

    start_point: tuple[float, float]
    control_point1: tuple[float, float]
    control_point2: tuple[float, float]
    end_point: tuple[float, float]
    style: DrawingStyle

    def __post_init__(self) -> None:
        """Validate the neutral cubic Bezier geometry and style boundary."""
        start_point = _coerce_point_pair(self.start_point, name="CubicBezierDrawing start_point")
        control_point1 = _coerce_point_pair(self.control_point1, name="CubicBezierDrawing control_point1")
        control_point2 = _coerce_point_pair(self.control_point2, name="CubicBezierDrawing control_point2")
        end_point = _coerce_point_pair(self.end_point, name="CubicBezierDrawing end_point")
        object.__setattr__(self, "start_point", start_point)
        object.__setattr__(self, "control_point1", control_point1)
        object.__setattr__(self, "control_point2", control_point2)
        object.__setattr__(self, "end_point", end_point)
        _require_drawing_style(self.style, "CubicBezierDrawing")

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create a cubic Bezier component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import CubicBezierSVG

            return CubicBezierSVG(self.start_point, self.control_point1, self.control_point2, self.end_point, self.style)
        from InkGen.pdf_generator import CubicBezierPDF

        return CubicBezierPDF(self.start_point, self.control_point1, self.control_point2, self.end_point, self.style)


@dataclass(frozen=True)
class PathDrawing:
    """Renderer-neutral SVG-style path primitive."""

    style: DrawingStyle
    commands: Sequence[PathCommand] | None = None

    def __post_init__(self) -> None:
        """Validate the public path command collection boundary."""
        _require_drawing_style(self.style, "PathDrawing")
        if self.commands is None:
            return
        if isinstance(self.commands, (str, bytes)) or not isinstance(self.commands, Sequence):
            raise TypeError("PathDrawing commands must be a sequence of PathCommand objects")
        commands = list(self.commands)
        if not all(isinstance(command, PathCommand) for command in commands):
            raise TypeError("PathDrawing commands must contain only PathCommand objects")
        object.__setattr__(self, "commands", commands)

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create a path component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import PathSVG

            return PathSVG(self.style, commands=self.commands)
        from InkGen.pdf_generator import PathPDF

        return PathPDF(self.style, commands=self.commands)


@dataclass(frozen=True)
class RegularPolygonDrawing:
    """Renderer-neutral regular polygon primitive."""

    position: tuple[float, float]
    sides: int
    radius: float
    style: DrawingStyle
    angle: float = 0.0
    corner_radius: float = 0.0

    def __post_init__(self) -> None:
        """Validate the neutral regular polygon geometry and style boundary."""
        position = _coerce_non_negative_point_pair(self.position, name="RegularPolygonDrawing position")
        sides = _coerce_regular_polygon_sides(self.sides)
        radius = _coerce_finite_positive_float(self.radius, name="RegularPolygonDrawing radius")
        angle = _coerce_finite_float(self.angle, name="RegularPolygonDrawing angle")
        corner_radius = _coerce_finite_non_negative_float(self.corner_radius, name="RegularPolygonDrawing corner_radius")
        if corner_radius > (radius / 2.0):
            raise ValueError("RegularPolygonDrawing corner_radius must not exceed half the radius")
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "sides", sides)
        object.__setattr__(self, "radius", radius)
        object.__setattr__(self, "angle", angle)
        object.__setattr__(self, "corner_radius", corner_radius)
        _require_drawing_style(self.style, "RegularPolygonDrawing")

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create a regular polygon component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import RegularPolygonSVG

            return RegularPolygonSVG(self.position, self.sides, self.radius, self.style, self.angle, self.corner_radius)
        from InkGen.pdf_generator import RegularPolygonPDF

        return RegularPolygonPDF(self.position, self.sides, self.radius, self.style, self.angle, self.corner_radius)


@dataclass(frozen=True)
class PolygonalDrawing:
    """Renderer-neutral irregular polygon primitive."""

    points: list[tuple[float, float]]
    style: DrawingStyle

    def __post_init__(self) -> None:
        """Validate the neutral polygon geometry and style boundary."""
        _require_drawing_style(self.style, "PolygonalDrawing")
        concrete = PolygonalDrawingComponent(self.points, self.style)
        object.__setattr__(self, "points", concrete.points)

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create an irregular polygon component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import PolygonalSVG

            return PolygonalSVG(self.points, self.style)
        from InkGen.pdf_generator import PolygonalPDF

        return PolygonalPDF(self.points, self.style)


@dataclass(frozen=True)
class CircleDrawing:
    """Renderer-neutral circle primitive."""

    position: tuple[float, float]
    radius: float
    style: DrawingStyle

    def __post_init__(self) -> None:
        """Validate the neutral circle geometry and style boundary."""
        position = _coerce_non_negative_point_pair(self.position, name="CircleDrawing position")
        radius = _coerce_finite_positive_float(self.radius, name="CircleDrawing radius")
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "radius", radius)
        _require_drawing_style(self.style, "CircleDrawing")

    def to_component(self, output_format: OutputFormat | str) -> Component:
        """Create a circle component for the requested backend."""
        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import CircleSVG

            return CircleSVG(self.position, self.radius, self.style)
        from InkGen.pdf_generator import CirclePDF

        return CirclePDF(self.position, self.radius, self.style)


@dataclass
class DrawingComponentGroup:
    """Renderer-neutral collection of drawing primitives."""

    group_label: str
    components: list[DrawingPrimitive] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the public group construction boundary."""
        if not isinstance(self.group_label, str):
            raise TypeError("group_label must be a string")
        if isinstance(self.components, (str, bytes)) or not isinstance(self.components, Sequence):
            raise TypeError("components must be a sequence of drawing primitives")
        components = list(self.components)
        for component in components:
            self._validate_component(component)
        self.components = components

    def add_component(self, component: DrawingPrimitive) -> None:
        """Append a renderer-neutral primitive to the group."""
        self._validate_component(component)
        self.components.append(component)

    @staticmethod
    def _validate_component(component: DrawingPrimitive) -> None:
        """Validate that an object follows the renderer-neutral primitive boundary."""
        if not callable(getattr(component, "to_component", None)):
            raise TypeError("component must implement to_component(output_format)")

    def to_group(self, output_format: OutputFormat | str) -> ComponentGroup:
        """Materialize the recipe as a concrete InkGen component group."""
        from InkGen.grammar_truth import copy_grammar_truth_annotations

        target = normalize_output_format(output_format)
        if target is OutputFormat.SVG:
            from InkGen.svg_generator import ComponentGroupSVG

            group: ComponentGroup = ComponentGroupSVG(self.group_label)
        else:
            from InkGen.pdf_generator import ComponentGroupPDF

            group = ComponentGroupPDF(self.group_label)
        copy_grammar_truth_annotations(self, group)
        for component in self.components:
            self._validate_component(component)
            concrete = component.to_component(target)
            if not isinstance(concrete, Component):
                raise TypeError("to_component(output_format) must return an InkGen Component")
            copy_grammar_truth_annotations(component, concrete)
            group.add_component(concrete)
        return group


class ZoningDrawing:
    """Renderer-neutral zoning overlay for synthetic engineering drawings."""

    _PARAMETERS = {
        "margins",
        "h_margins",
        "v_margins",
        "left_margin",
        "right_margin",
        "top_margin",
        "bottom_margin",
        "zone_width",
        "h_zone_width",
        "v_zone_width",
        "left_zone_width",
        "right_zone_width",
        "top_zone_width",
        "bottom_zone_width",
        "inner_radius",
        "outer_radius",
        "horizontal_zones",
        "vertical_zones",
        "first_horizontal_char",
        "first_vertical_char",
    }
    _POSITIVE_REALS = {
        "margins",
        "h_margins",
        "v_margins",
        "left_margin",
        "right_margin",
        "top_margin",
        "bottom_margin",
        "zone_width",
        "h_zone_width",
        "v_zone_width",
        "left_zone_width",
        "right_zone_width",
        "top_zone_width",
        "bottom_zone_width",
        "inner_radius",
        "outer_radius",
    }
    _EVEN_INTS = {"horizontal_zones", "vertical_zones"}
    _ZONE_CHARS = {"first_horizontal_char", "first_vertical_char"}
    _VALID_ZONE_CHARS = set(range(65, 91)) | set(range(97, 123)) | set(range(48, 58))

    def __init__(self, canvas: Canvas, line_style: DrawingStyle, text_style: TextStyle, **kwargs: object) -> None:
        """Create a zoning overlay recipe from renderer-neutral primitives."""
        if not isinstance(canvas, Canvas):
            raise TypeError("canvas argument must be a Canvas object")
        if not isinstance(line_style, DrawingStyle):
            raise TypeError("line_style argument must be a DrawingStyle object")
        if not isinstance(text_style, TextStyle):
            raise TypeError("text_style argument must be a TextStyle object")

        self._canvas = canvas
        self._line_style = line_style
        self._text_style = text_style
        self._parameters = dict.fromkeys(self._PARAMETERS)
        self._margins: list[float] = []
        self._widths: list[float] = []
        self._sizes: dict[str, tuple[float, float, float]] = {}
        self._group = DrawingComponentGroup("Zoning")

        self._set_defaults()
        self._apply_parameters(kwargs)
        self._set_margins()
        self._get_character_sizes()
        self._set_zoning_widths()
        self._create_zoning()

    @property
    def drawing_group(self) -> DrawingComponentGroup:
        """Return the renderer-neutral component group recipe."""
        return self._group

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return a serialization-friendly description of this zoning recipe."""
        valid_parameters = {key: value for key, value in self._parameters.items() if value is not None}
        return {
            "ZoningDrawing": {
                "canvas": self._canvas.parameters,
                "line_style": self._line_style.parameters,
                "text_style": self._text_style.parameters,
                "parameters": valid_parameters,
            }
        }

    def to_group(self, output_format: OutputFormat | str) -> ComponentGroup:
        """Materialize the zoning overlay for SVG or PDF output."""
        return self._group.to_group(output_format)

    @classmethod
    def create_from_dict(cls, data: dict[str, object], styles: dict[str, object] | None = None) -> ZoningDrawing:
        """Recreate a zoning recipe from serialized parameters."""
        if styles is None:
            styles = {}
        if not isinstance(styles, Mapping):
            raise TypeError("styles must be a mapping or None")
        payload = _zoning_payload(data)
        line_style_payload = _zoning_required_mapping(payload, "line_style")
        text_style_payload = _zoning_required_mapping(payload, "text_style")
        line_style_name = _zoning_style_name(line_style_payload, "DrawingStyle", "line_style")
        text_style_name = _zoning_style_name(text_style_payload, "TextStyle", "text_style")
        line_style = styles.get(line_style_name) or DrawingStyle.create_from_dict(line_style_payload)
        text_style = styles.get(text_style_name) or TextStyle.create_from_dict(text_style_payload)
        if not isinstance(line_style, DrawingStyle):
            raise TypeError(f"style override for {line_style_name!r} must be a DrawingStyle")
        if not isinstance(text_style, TextStyle):
            raise TypeError(f"style override for {text_style_name!r} must be a TextStyle")
        return cls(
            Canvas.create_from_dict(_zoning_required_field(payload, "canvas")),
            line_style,
            text_style,
            **_zoning_required_mapping(payload, "parameters"),
        )

    def _apply_parameters(self, kwargs: dict[str, object]) -> None:
        for key, value in kwargs.items():
            if key not in self._PARAMETERS:
                raise KeyError(f"{key} is not a valid parameter.")
            if key in self._POSITIVE_REALS and value is not None:
                value = _coerce_finite_non_negative_float(value, name=key)
            if key in self._EVEN_INTS and value is not None and (not isinstance(value, int) or value % 2 != 0 or value <= 0):
                raise ValueError(f"{key} should be an even integer")
            if key in self._ZONE_CHARS and value is not None and (not isinstance(value, int) or value not in self._VALID_ZONE_CHARS):
                raise ValueError(f"{key} should be an int between 65 and 90 or 97 and 123 or between 48 and 57")
            self._parameters[key] = value
        self._validate_zone_label_ranges()

    def _validate_zone_label_ranges(self) -> None:
        """Reject zoning label sequences that leave their alphanumeric range."""
        for char_key, count_key in (
            ("first_horizontal_char", "horizontal_zones"),
            ("first_vertical_char", "vertical_zones"),
        ):
            first_code = int(self._parameters[char_key])
            zone_count = int(self._parameters[count_key])
            if not _zone_label_sequence_fits(first_code, zone_count):
                raise ValueError(f"{char_key} and {count_key} should produce alphanumeric ASCII labels")

    def _set_defaults(self) -> None:
        self._parameters["inner_radius"] = 0.0
        self._parameters["outer_radius"] = 0.0
        horizontal_zones = self._canvas.width / 25
        self._parameters["horizontal_zones"] = int(horizontal_zones - (horizontal_zones % 2))
        vertical_zones = self._canvas.height / 25
        self._parameters["vertical_zones"] = int(vertical_zones - (vertical_zones % 2))
        self._parameters["first_horizontal_char"] = 49
        self._parameters["first_vertical_char"] = 65

    def _get_character_sizes(self) -> None:
        text_comp = TextComponent("_", (0, 0), self._text_style)
        for index in range(32, 255):
            character = chr(index)
            text_comp.text = character
            width = float(text_comp.bbox[1][0] - text_comp.bbox[0][0])
            height = float(text_comp.bbox[1][1] - text_comp.bbox[0][1])
            baseline_offset = float(-0.5 * (text_comp.bbox[0][1] + text_comp.bbox[1][1]))
            self._sizes[character] = (width, height, baseline_offset)

    def _set_margins(self) -> None:
        self._margins = [5.0, 5.0, 5.0, 5.0]
        priority = [
            ["left_margin", "v_margins", "margins"],
            ["top_margin", "h_margins", "margins"],
            ["right_margin", "v_margins", "margins"],
            ["bottom_margin", "h_margins", "margins"],
        ]
        for index, priority_group in enumerate(priority):
            for key in priority_group:
                if self._parameters[key] is not None:
                    self._margins[index] = float(self._parameters[key])
                    break
        self._parameters["left_margin"] = self._margins[0]
        self._parameters["top_margin"] = self._margins[1]
        self._parameters["right_margin"] = self._margins[2]
        self._parameters["bottom_margin"] = self._margins[3]

    def _set_zoning_widths(self) -> None:
        char_widths = max(self._sizes["A"][0], self._sizes["W"][0], self._sizes["Y"][0])
        self._widths = [char_widths + 4.0, char_widths + 4.0, char_widths + 4.0, char_widths + 4.0]
        priority = [
            ["left_zone_width", "v_zone_width", "zone_width"],
            ["top_zone_width", "h_zone_width", "zone_width"],
            ["right_zone_width", "v_zone_width", "zone_width"],
            ["bottom_zone_width", "h_zone_width", "zone_width"],
        ]
        for index, priority_group in enumerate(priority):
            for key in priority_group:
                if self._parameters[key] is not None:
                    self._widths[index] = float(self._parameters[key])
                    break
        self._parameters["left_zone_width"] = self._widths[0]
        self._parameters["top_zone_width"] = self._widths[1]
        self._parameters["right_zone_width"] = self._widths[2]
        self._parameters["bottom_zone_width"] = self._widths[3]

    def _create_zoning(self) -> None:
        left, top, right, bottom = self._margins
        left_width, top_width, right_width, bottom_width = self._widths
        inner_width = self._canvas.width - left - left_width - right - right_width
        inner_height = self._canvas.height - top - top_width - bottom - bottom_width

        self._group.add_component(
            RectangleDrawing(
                (left, top),
                self._canvas.width - right - left,
                self._canvas.height - top - bottom,
                self._parameters["outer_radius"],
                self._line_style,
            )
        )
        self._group.add_component(
            RectangleDrawing(
                (left + left_width, top + top_width),
                inner_width,
                inner_height,
                self._parameters["inner_radius"],
                self._line_style,
            )
        )

        vertical_mid_point = top + top_width + (inner_height / 2.0)
        self._add_horizontal_zone_lines(vertical_mid_point, inner_height)
        self._add_vertical_zone_labels(vertical_mid_point, inner_height)

        horizontal_mid_point = left + left_width + (inner_width / 2.0)
        self._add_vertical_zone_lines(horizontal_mid_point, inner_width)
        self._add_horizontal_zone_labels(inner_width)

    def _add_horizontal_zone_lines(self, vertical_mid_point: float, inner_height: float) -> None:
        left, _, right, _ = self._margins
        left_width, top_width, right_width, bottom_width = self._widths
        self._group.add_component(LineDrawing((left, vertical_mid_point), (left + left_width, vertical_mid_point), self._line_style))
        self._group.add_component(
            LineDrawing(
                (self._canvas.width - right - right_width, vertical_mid_point),
                (self._canvas.width - right, vertical_mid_point),
                self._line_style,
            )
        )
        offset = inner_height / int(self._parameters["vertical_zones"])
        for multiplier in range(1, int(self._parameters["vertical_zones"] / 2)):
            for delta in (offset * multiplier, -offset * multiplier):
                y_pos = vertical_mid_point + delta
                self._group.add_component(LineDrawing((left, y_pos), (left + left_width, y_pos), self._line_style))
                self._group.add_component(
                    LineDrawing(
                        (self._canvas.width - right - right_width, y_pos),
                        (self._canvas.width - right, y_pos),
                        self._line_style,
                    )
                )

    def _add_vertical_zone_labels(self, vertical_mid_point: float, inner_height: float) -> None:
        left, top, right, _ = self._margins
        left_width, top_width, right_width, _ = self._widths
        offset = inner_height / int(self._parameters["vertical_zones"])
        baseline_offset = self._sizes[chr(int(self._parameters["first_vertical_char"]))][2]
        first_letter_vertical = self._canvas.height - top - top_width - (offset / 2.0) + baseline_offset
        left_letter_horizontal = left + left_width / 2.0
        right_letter_horizontal = self._canvas.width - right - right_width / 2.0
        for multiplier in range(int(self._parameters["vertical_zones"])):
            character = chr(int(self._parameters["first_vertical_char"]) + multiplier)
            y_pos = first_letter_vertical - offset * multiplier
            self._group.add_component(TextDrawing(character, (left_letter_horizontal, y_pos), self._text_style))
            self._group.add_component(TextDrawing(character, (right_letter_horizontal, y_pos), self._text_style))

    def _add_vertical_zone_lines(self, horizontal_mid_point: float, inner_width: float) -> None:
        left, top, right, bottom = self._margins
        _, top_width, _, bottom_width = self._widths
        self._group.add_component(LineDrawing((horizontal_mid_point, top), (horizontal_mid_point, top + top_width), self._line_style))
        self._group.add_component(
            LineDrawing(
                (horizontal_mid_point, self._canvas.height - bottom - bottom_width),
                (horizontal_mid_point, self._canvas.height - bottom),
                self._line_style,
            )
        )
        offset = inner_width / int(self._parameters["horizontal_zones"])
        for multiplier in range(1, int(self._parameters["horizontal_zones"] / 2)):
            for delta in (offset * multiplier, -offset * multiplier):
                x_pos = horizontal_mid_point + delta
                self._group.add_component(LineDrawing((x_pos, top), (x_pos, top + top_width), self._line_style))
                self._group.add_component(
                    LineDrawing(
                        (x_pos, self._canvas.height - bottom - bottom_width),
                        (x_pos, self._canvas.height - bottom),
                        self._line_style,
                    )
                )

    def _add_horizontal_zone_labels(self, inner_width: float) -> None:
        _, top, right, bottom = self._margins
        _, top_width, right_width, bottom_width = self._widths
        offset = inner_width / int(self._parameters["horizontal_zones"])
        baseline_offset = self._sizes[chr(int(self._parameters["first_horizontal_char"]))][2]
        top_number_vertical = top + top_width / 2.0 + baseline_offset
        bottom_number_vertical = self._canvas.height - bottom - bottom_width / 2.0 + baseline_offset
        first_number_horizontal = self._canvas.width - right - right_width - offset / 2.0
        for multiplier in range(int(self._parameters["horizontal_zones"])):
            character = chr(multiplier + int(self._parameters["first_horizontal_char"]))
            x_pos = first_number_horizontal - offset * multiplier
            self._group.add_component(TextDrawing(character, (x_pos, top_number_vertical), self._text_style))
            self._group.add_component(TextDrawing(character, (x_pos, bottom_number_vertical), self._text_style))


def _zoning_payload(data: object) -> Mapping[str, object]:
    """Return the serialized zoning payload or fail explicitly."""
    if not isinstance(data, Mapping):
        raise TypeError("ZoningDrawing data must be a mapping")
    if "ZoningDrawing" not in data:
        raise ValueError("ZoningDrawing data must include ZoningDrawing")
    payload = data["ZoningDrawing"]
    if not isinstance(payload, Mapping):
        raise TypeError("ZoningDrawing payload must be a mapping")
    return payload


def _zoning_required_field(payload: Mapping[str, object], name: str) -> object:
    """Return a required serialized zoning field or fail explicitly."""
    if name not in payload:
        raise ValueError(f"ZoningDrawing payload must include {name}")
    return payload[name]


def _zoning_required_mapping(payload: Mapping[str, object], name: str) -> Mapping[str, object]:
    """Return a required serialized zoning mapping field or fail explicitly."""
    value = _zoning_required_field(payload, name)
    if not isinstance(value, Mapping):
        raise TypeError(f"ZoningDrawing {name} must be a mapping")
    return value


def _zoning_style_name(payload: Mapping[str, object], style_key: str, field_name: str) -> str:
    """Return a serialized zoning style name or fail explicitly."""
    if style_key not in payload:
        raise ValueError(f"ZoningDrawing {field_name} must include {style_key}")
    style_payload = payload[style_key]
    if not isinstance(style_payload, Mapping):
        raise TypeError(f"ZoningDrawing {field_name} entry must be a mapping")
    style_name = style_payload.get("name")
    if not isinstance(style_name, str):
        raise TypeError(f"ZoningDrawing {field_name} name must be a string")
    return style_name


def _zone_label_sequence_fits(first_code: int, zone_count: int) -> bool:
    """Return whether a zoning label run stays inside one ASCII label range."""
    ranges = ((48, 57), (65, 90), (97, 122))
    for lower, upper in ranges:
        if lower <= first_code <= upper:
            return first_code + zone_count - 1 <= upper
    return False


def _coerce_finite_non_negative_float(value: object, *, name: str) -> float:
    """Coerce a public zoning dimension into a finite non-negative float."""
    if isinstance(value, bool):
        raise TypeError(f"{name} should be a finite non-negative number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} should be a finite non-negative number") from exc
    if not isfinite(number):
        raise ValueError(f"{name} should be a finite non-negative number")
    if number < 0:
        raise ValueError(f"{name} should be a finite non-negative number")
    return number
