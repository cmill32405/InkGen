"""Renderer-neutral drawing recipes for synthetic engineering drawings.

The classes in this module describe drawing intent separately from any concrete
output backend. A recipe can be materialized as SVG or PDF components without
embedding renderer-specific classes in higher-level synthetic drawing builders.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Protocol

from InkGen.boundary import Canvas
from InkGen.component import Component, ComponentGroup, PathCommand, TextComponent
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


@dataclass(frozen=True)
class RectangleDrawing:
    """Renderer-neutral rectangle primitive."""

    position: tuple[float, float]
    width: float
    height: float
    corner_radii: float | tuple[float, float]
    style: DrawingStyle

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
        """Validate the public group label boundary."""
        if not isinstance(self.group_label, str):
            raise TypeError("group_label must be a string")

    def add_component(self, component: DrawingPrimitive) -> None:
        """Append a renderer-neutral primitive to the group."""
        if not callable(getattr(component, "to_component", None)):
            raise TypeError("component must implement to_component(output_format)")
        self.components.append(component)

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
        payload = data["ZoningDrawing"]
        line_style_payload = payload["line_style"]
        text_style_payload = payload["text_style"]
        line_style_name = line_style_payload["DrawingStyle"]["name"]
        text_style_name = text_style_payload["TextStyle"]["name"]
        line_style = styles.get(line_style_name) or DrawingStyle.create_from_dict(line_style_payload)
        text_style = styles.get(text_style_name) or TextStyle.create_from_dict(text_style_payload)
        return cls(
            Canvas.create_from_dict(payload["canvas"]),
            line_style,
            text_style,
            **payload["parameters"],
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
