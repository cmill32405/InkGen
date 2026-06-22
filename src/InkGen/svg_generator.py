"""
    Module for creating SVG drawings programatically or via a yaml file.

    Problems:
        CircleSVG needs points, bbox, and convexHull
        SVGComponent needs points, convexHull and a way to offset the position
        fix - https://stackoverflow.com/questions/69313876/how-to-get-points-of-the-svg-paths
        check out svg.path and svgwrite

"""
from __future__ import annotations

import abc
import base64
import math
import os
import sys
from collections.abc import Iterable
from enum import Flag, auto
from xml.sax.saxutils import escape

import numpy as np
from shapely.errors import GEOSException
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from InkGen.boundary import Canvas
from InkGen.component import Arc as ArcComponent
from InkGen.component import (
    Component,
    ComponentGroup,
    PathCommand,
    PolygonalDrawingComponent,
    RegularPolygonDrawingComponent,
    SingleDimensionDrawingComponent,
    StandardDrawingComponent,
    TextComponent,
    WidthHeightDrawingComponent,
    normalize_rectangle_corner_radii,
)
from InkGen.component import CubicBezier as CubicBezierComponent
from InkGen.component import Path as PathComponent
from InkGen.component import QuadraticBezier as QuadraticBezierComponent
from InkGen.document import Document, Layer, Layers
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.svg_utils import flatten_svg
from InkGen.table import AutoFitRule, Table

try:
    from shapely.validation import make_valid as _shapely_make_valid
except ImportError:
    def _normalize_geometry(geom):
        """Normalize geometry using buffer(0) fallback.

        Args:
            geom: Shapely geometry object.

        Returns:
            Normalized geometry.
        """
        return geom.buffer(0)
else:
    def _normalize_geometry(geom):
        """Normalize geometry using shapely's make_valid.

        Args:
            geom: Shapely geometry object.

        Returns:
            Validated and normalized geometry.
        """
        return _shapely_make_valid(geom)

PRECISION = 3


def _primitive_parameters(name: str, *, values: dict[str, object], style: DrawingStyle) -> dict[str, object]:
    """Return a serialization dictionary for a primitive component."""
    payload = dict(values)
    payload["style"] = style.parameters
    return {name: payload}


def _coerce_command_points(points: list[tuple[float, float]]) -> list[str]:
    """Convert points to SVG coordinate strings.

    Args:
        points: List of (x, y) coordinate tuples.

    Returns:
        List of formatted coordinate strings in "x,y" format.
    """
    return [f"{float(x)},{float(y)}" for x, y in points]


def _style_properties(style: DrawingStyle, *, include_fill: bool = True, include_stroke: bool = True) -> str:
    parts = []
    if include_fill:
        fill = getattr(style, "fill", "none")
        parts.append(f"fill:{fill}")
        if fill.lower() != "none" and hasattr(style, "fill_opacity"):
            parts.append(f"fill-opacity:{style.fill_opacity}")
    else:
        parts.append("fill:none")
    if include_stroke:
        stroke = getattr(style, "stroke", "none")
        parts.append(f"stroke:{stroke}")
        if hasattr(style, "stroke_width"):
            parts.append(f"stroke-width:{style.stroke_width}")
        if hasattr(style, "stroke_opacity"):
            parts.append(f"stroke-opacity:{style.stroke_opacity}")
    else:
        parts.append("stroke:none")
    return ";".join(parts)

class DrawingGeneratorInterface(metaclass=abc.ABCMeta):
    """
        Interface to enable Components to create SVG XML outputs to represent them.
    """
    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return (hasattr(__subclass, 'generate_svg') and
                callable(__subclass.generate_svg) or
                NotImplemented)

    @abc.abstractmethod
    def generate_svg(self) -> str:
        """ Generates the XML necessary to add the drawing component to an SVG file.

        Returns
        -------
        str
            XML for DrawingComponent
        """
        raise NotImplementedError


class LabelGenerator(metaclass=abc.ABCMeta):
    """
        Interface to enable component groups to generate bounding boxes with
        labels.
    """
    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return (hasattr(__subclass, 'generate_label') and
                callable(__subclass.generate_label) or
                NotImplemented)

    @abc.abstractmethod
    def generate_label(self) -> dict[str, list[tuple[float, float]]]:
        """ Generates the data for labelling component groups

        Returns
        -------
        Dict[str, List[Tuple[float, float]]]
            Dictionary with the label as the key and bounding box points
            as the value.

        """
        raise NotImplementedError


class SegmentGenerator(metaclass=abc.ABCMeta):
    """
        Interface to enable component groups to generate segmentation masks
        with labels.
    """
    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return (hasattr(__subclass, 'generate_segmentation_mask') and
                callable(__subclass.generate_segmentation_mask) or
                NotImplemented)

    @abc.abstractmethod
    def generate_segmentation_mask(self) -> dict[str, list[tuple[float, float]]]:
        """ Generates the data for segmentation masks of component groups

        Returns
        -------
        Dict[str, List[Tuple[float, float]]]
            Dictionary with the label as the key and convex hull points
            as the value.

        """
        raise NotImplementedError


class RectangleSVG(WidthHeightDrawingComponent, DrawingGeneratorInterface):
    """
        Class to describe rectangles as SVG components.
    """
    def __init__(self,
                 position: tuple[float, float],
                 width: float | int,
                 height: float | int,
                 corner_radii: float | tuple[float, float],
                 style: DrawingStyle):
        """ Instantiate a new rectangle object.

        Parameters
        ----------
        position : Tuple[float, float]
            Top-Left corner of the rectangle
        width : Union[float, int]
            Width of the rectangle
        height : Union[float, int]
            Height of the rectangle
        corner_radii : Union[float, Tuple[float, float]]
            Corner Radi of the Rectangle as either a float (both corners) or a Tuple
            with the Horizontal Radius and Verticle Radius.
        style : DrawingStyle
            Style used to draw the rectangle

        Raises
        ------
        ValueError
            If Radii exceed the width or height
        """

        super().__init__(position, width, height, style)
        self.corner_radii = corner_radii


    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['RectangleSVG']['style'])

        component = cls(data['RectangleSVG']['position'],
                        data['RectangleSVG']['width'],
                        data['RectangleSVG']['height'],
                        data['RectangleSVG']['corner_radii'],
                        style)
        return component

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"RectangleSVG":
                       {"position": self.position,
                        "width": self.width,
                        "height": self.height,
                        "corner_radii": self.corner_radii,
                        "style": self.style.parameters}}
        return parameter_dict

    def _radius_check(self,
                      corner_radii: float | tuple[float, float],
                      width: float,
                      height: float) -> None:
        """ Private method to verify corner radius can be implemented.

        Parameters
        ----------
        corner_radii : Union[float, Tuple[float, float]]
            corner_radius setting for rectangle
        width : float
            width of rectangle
        height : float
            height of rectangle

        Raises
        ------
        TypeError
            If corner radii are not numeric scalar or pair values.
        ValueError
            If corner radii are outside valid rectangle bounds.
        """
        normalize_rectangle_corner_radii(corner_radii, width, height)

    @property
    def corner_radii(self) -> float:
        """ Property for corner radius of the rectangle corners.

        Returns:
            float: corner radius
        """
        return self._corner_radii

    @corner_radii.setter
    def corner_radii(self, value: float) -> None:
        """ Setter to update corner radii.

        Args:
            value (float): new radius.
        """
        self._radius_check(value, self.width, self.height)
        self._corner_radii = value

    def generate_svg(self) -> str:
        """ Creates a single rect object in XML for a SVG file.

        Example:

            <rect
            style="fill:#000000;stroke:#000000;stroke-width:0.2;opacity:0.52189781;fill-opacity:1"
            id="rect1"
            width="75.606575"
            height="63.306942"
            x="64.75396"
            y="91.161995" />

        Returns
        -------
        str
            XML line for SVG file
        """
        style = _style_properties(self.style)

        rx, ry = normalize_rectangle_corner_radii(self.corner_radii, self.width, self.height)
        radius_attributes = " "
        if rx != 0.0 or ry != 0.0:
            radius_attributes = f"""
            rx="{rx}"
            ry="{ry}" """

        return f"""<rect
            style="{style}"
            id="rect{self.id}"
            width="{self.width}"
            height="{self.height}"
            x="{self.position[0]}"
            y="{self.position[1]}"{radius_attributes}/>"""


class LineSVG(StandardDrawingComponent, DrawingGeneratorInterface):
    """
        Class to describe lines as SVG components.
    """
    def __init__(self,
                 point_1: tuple[float, float],
                 point_2: tuple[float, float],
                 style: DrawingStyle):
        """ Instantiate a new line object

        Parameters
        ----------
        point_1 : Tuple[float, float]
            Start point of the line
        point_2 : Tuple[float, float]
            End point of the line
        style : DrawingStyle
            Style used to draw the rectangle

        """

        super().__init__(point_1=point_1, point_2=point_2, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['LineSVG']['style'])
        component = cls(data['LineSVG']['point_1'],
                        data['LineSVG']['point_2'],
                        style)
        return component

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"LineSVG":
                       {"point_1": self.point_1,
                        "point_2": self.point_2,
                        "style": self.style.parameters}}
        return parameter_dict

    def generate_svg(self) -> str:
        """ Creates a single path object (line) in XML for a SVG file.

        Example:

            <path
            style="opacity:0.521898;fill:#000000;stroke:#000000;stroke-width:0.2"
            d="m 32.196103,137.82826 83.565167,-27.4933"
            id="path1" />


        Returns
        -------
        str
            XML line for SVG file
        """
        style = _style_properties(self.style)

        return f"""<path
            style="{style}"
            d="M {self.point_1[0]},{self.point_1[1]} L {self.point_2[0]},{self.point_2[1]}"
            id="path{self.id}" />"""


class ArcSVG(ArcComponent, DrawingGeneratorInterface):
    """SVG representation of an elliptical arc."""

    def __init__(self,
                 center: tuple[float, float],
                 radius_x: float,
                 radius_y: float,
                 start_angle: float,
                 end_angle: float,
                 style: DrawingStyle,
                 rotation: float = 0.0) -> None:
        super().__init__(center=center,
                         radius_x=radius_x,
                         radius_y=radius_y,
                         start_angle=start_angle,
                         end_angle=end_angle,
                         style=style,
                         rotation=rotation)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle = None) -> ArcSVG:
        """Recreate an `ArcSVG` from serialized parameters."""
        if not style:
            style = DrawingStyle.create_from_dict(data['ArcSVG']['style'])
        arc = data['ArcSVG']
        return cls(center=tuple(arc['center']),
                   radius_x=arc['radius_x'],
                   radius_y=arc['radius_y'],
                   start_angle=arc['start_angle'],
                   end_angle=arc['end_angle'],
                   style=style,
                   rotation=arc.get('rotation', 0.0))

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters(
            "ArcSVG",
            values={
                "center": self.center,
                "radius_x": self.radius_x,
                "radius_y": self.radius_y,
                "start_angle": self.start_angle,
                "end_angle": self.end_angle,
                "rotation": self.rotation,
            },
            style=self.style,
        )

    def _arc_flags(self) -> tuple[int, int]:
        delta = self.end_angle - self.start_angle
        sweep_flag = 1 if delta >= 0 else 0
        delta_norm = abs(delta) % 360.0
        if math.isclose(delta_norm, 0.0) and not math.isclose(abs(delta), 0.0):
            delta_norm = 360.0
        large_arc_flag = 1 if delta_norm > 180.0 else 0
        return large_arc_flag, sweep_flag

    def generate_svg(self) -> str:
        style = _style_properties(self.style)
        pts = self.points
        start = pts[0]
        end = pts[-1] if len(pts) > 1 else pts[0]
        large_arc_flag, sweep_flag = self._arc_flags()
        return f"""<path
            style="{style}"
            d="M {start[0]},{start[1]} A {self.radius_x},{self.radius_y} {self.rotation} {large_arc_flag} {sweep_flag} {end[0]},{end[1]}"
            id="path{self.id}" />"""


class QuadraticBezierSVG(QuadraticBezierComponent, DrawingGeneratorInterface):
    """SVG representation of a quadratic Bezier curve."""

    def __init__(self,
                 start_point: tuple[float, float],
                 control_point: tuple[float, float],
                 end_point: tuple[float, float],
                 style: DrawingStyle) -> None:
        super().__init__(start_point=start_point,
                         control_point=control_point,
                         end_point=end_point,
                         style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle = None) -> QuadraticBezierSVG:
        """Recreate a quadratic Bezier primitive from serialized data."""
        if not style:
            style = DrawingStyle.create_from_dict(data['QuadraticBezierSVG']['style'])
        bezier = data['QuadraticBezierSVG']
        return cls(start_point=tuple(bezier['start_point']),
                   control_point=tuple(bezier['control_point']),
                   end_point=tuple(bezier['end_point']),
                   style=style)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters(
            "QuadraticBezierSVG",
            values={
                "start_point": self.start_point,
                "control_point": self.control_point,
                "end_point": self.end_point,
            },
            style=self.style,
        )

    def generate_svg(self) -> str:
        style = _style_properties(self.style)
        start = self.start_point
        control = self.control_point
        end = self.end_point
        return f"""<path
            style="{style}"
            d="M {start[0]},{start[1]} Q {control[0]},{control[1]} {end[0]},{end[1]}"
            id="path{self.id}" />"""


class CubicBezierSVG(CubicBezierComponent, DrawingGeneratorInterface):
    """SVG representation of a cubic Bezier curve."""

    def __init__(self,
                 start_point: tuple[float, float],
                 control_point1: tuple[float, float],
                 control_point2: tuple[float, float],
                 end_point: tuple[float, float],
                 style: DrawingStyle) -> None:
        super().__init__(start_point=start_point,
                         control_point1=control_point1,
                         control_point2=control_point2,
                         end_point=end_point,
                         style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle = None) -> CubicBezierSVG:
        """Recreate a cubic Bezier primitive from serialized data."""
        if not style:
            style = DrawingStyle.create_from_dict(data['CubicBezierSVG']['style'])
        bezier = data['CubicBezierSVG']
        return cls(start_point=tuple(bezier['start_point']),
                   control_point1=tuple(bezier['control_point1']),
                   control_point2=tuple(bezier['control_point2']),
                   end_point=tuple(bezier['end_point']),
                   style=style)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        return _primitive_parameters(
            "CubicBezierSVG",
            values={
                "start_point": self.start_point,
                "control_point1": self.control_point1,
                "control_point2": self.control_point2,
                "end_point": self.end_point,
            },
            style=self.style,
        )

    def generate_svg(self) -> str:
        style = _style_properties(self.style)
        start = self.start_point
        c1 = self.control_point1
        c2 = self.control_point2
        end = self.end_point
        return f"""<path
            style="{style}"
            d="M {start[0]},{start[1]} C {c1[0]},{c1[1]} {c2[0]},{c2[1]} {end[0]},{end[1]}"
            id="path{self.id}" />"""


class PathSVG(PathComponent, DrawingGeneratorInterface):
    """SVG representation of a generic path built from commands."""

    def __init__(self,
                 style: DrawingStyle,
                 commands: list[PathCommand] | None = None) -> None:
        super().__init__(style=style, commands=commands)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle = None) -> PathSVG:
        """Recreate a path primitive from serialized commands."""
        if not style:
            style = DrawingStyle.create_from_dict(data['PathSVG']['style'])
        commands: list[PathCommand] = []
        for cmd in data['PathSVG'].get('commands', []):
            command = PathCommand(cmd['type'], cmd.get('points', []))
            flags = cmd.get('flags')
            if flags:
                command.flags = flags
            commands.append(command)
        return cls(style=style, commands=commands)

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialized geometry/style information."""
        serialized = []
        for command in self.commands:
            entry = dict(command.parameters)
            flags = getattr(command, "flags", None)
            if flags is not None:
                entry["flags"] = flags
            serialized.append(entry)
        return _primitive_parameters(
            "PathSVG",
            values={"commands": serialized},
            style=self.style,
        )

    def _format_command(self, command: PathCommand) -> str:
        points = command.points
        if not points:
            return command.type
        if command.type == "H":
            coords = " ".join(f"{pt[0]}" for pt in points)
        elif command.type == "V":
            coords = " ".join(f"{pt[1]}" for pt in points)
        elif command.type == "A":
            if not points:
                return command.type
            flags = getattr(command, "flags", {"rotation": 0.0, "large_arc": 0, "sweep": 0})
            rotation = flags.get("rotation", 0.0)
            large_arc = flags.get("large_arc", 0)
            sweep = flags.get("sweep", 0)
            radii = flags.get("radii", (0.0, 0.0))
            end_point = points[-1]
            coords = f"{radii[0]},{radii[1]} {rotation} {large_arc} {sweep} {end_point[0]},{end_point[1]}"
            return f"{command.type} {coords}"
        else:
            coords = " ".join(_coerce_command_points(points))
        return f"{command.type} {coords}"

    def generate_svg(self) -> str:
        style = _style_properties(self.style)
        path_data = " ".join(self._format_command(cmd) for cmd in self.commands)
        return f"""<path
            style="{style}"
            d="{path_data}"
            id="path{self.id}" />"""


class RegularPolygonSVG(RegularPolygonDrawingComponent, DrawingGeneratorInterface):
    """
        Class to describe regular polygons (triangle, square, pentagon, etc.) as SVG
        components.
    """
    def __init__(self,
                 position: tuple[float, float],
                 sides: int,
                 radius: float,
                 style: DrawingStyle,
                 angle: float = 0.0,
                 corner_radius: float = 0.0):
        super().__init__(position=position, sides=sides,
                         radius=radius, style=style,
                         angle=angle, corner_radius=corner_radius)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['RegularPolygonSVG']['style'])
        component = cls(data['RegularPolygonSVG']['position'],
                        data['RegularPolygonSVG']['sides'],
                        data['RegularPolygonSVG']['radius'],
                        style,
                        data['RegularPolygonSVG']['angle'],
                        data['RegularPolygonSVG']['corner_radius'],)
        return component

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"RegularPolygonSVG":
                       {"position": self.position,
                        "sides": self.sides,
                        "radius": self.radius,
                        "style": self.style.parameters,
                        "angle": self.angle,
                        "corner_radius": self.corner_radius}}
        return parameter_dict

    def generate_svg(self) -> str:
        """ Creates a single path object (polygon) in XML for a SVG file.

        Example:

            <path
            style="opacity:0.521898;fill:#000000;stroke:#000000;stroke-width:0.2"
            d="M 40.915129,89.501844 103.38376,83.291512 141.37638,118.72694 Z"
            id="path1" />


        Returns
        -------
        str
            XML line for SVG file
        """

        points = ""
        for p in self._get_points():
            points += f"{p[0]}, {p[1]} "

        style = _style_properties(self.style)
        style = f"{style};stroke-linecap:butt;stroke-linejoin:miter"

        return f"""<path
            style="{style}"
            d="M {points} Z"
            id="path{self.id}" />"""


class PolygonalSVG(PolygonalDrawingComponent, DrawingGeneratorInterface):
    """
        Class to describe irregular polygons as SVG components.
    """
    def __init__(self,
                 points: list[tuple[float, float]],
                 style: DrawingStyle):
        super().__init__(points=points, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['PolygonalSVG']['style'])
        component = cls(data['PolygonalSVG']['points'],
                        style)
        return component

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"PolygonalSVG":
                       {"points": self.points,
                        "style": self.style.parameters}}
        return parameter_dict

    def generate_svg(self) -> str:
        """ Creates a single path object (polygon) in XML for a SVG file.

        Example:

            <path
            style="opacity:0.521898;fill:#000000;stroke:#000000;stroke-width:0.2"
            d="M 40.915129,89.501844 103.38376,83.291512 141.37638,118.72694 Z"
            id="path1" />


        Returns
        -------
        str
            XML line for SVG file
        """

        points = ""
        for p in self.points:
            points += f"{p[0]},{p[1]} "

        style = _style_properties(self.style)
        style = f"{style};stroke-linecap:butt;stroke-linejoin:miter"

        return f"""<path
            style="{style}"
            d="M {points}Z"
            id="path{self.id}" />"""


class CircleSVG(SingleDimensionDrawingComponent, DrawingGeneratorInterface):
    """
        Class to describe circles as SVG components.
    """
    def __init__(self,
                 position: tuple[float, float],
                 radius: float,
                 style: DrawingStyle) -> None:
        """_summary_

        Args:
            position (Tuple[float, float]): Center of circle
            radius (float): raidus of the circle
            style (DrawingStyle): Style used to draw the cirle

        Raises:
            ValueError: Raised if radius is not greater than zero.
        """
        super().__init__(position, self._coerce_radius(radius), style)

    @staticmethod
    def _coerce_radius(radius: float | int) -> float:
        """Return a finite positive circle radius or fail at the public boundary."""
        if isinstance(radius, bool):
            raise TypeError("Radii must be numeric.")
        if not isinstance(radius, (float, int)):
            raise ValueError("Radii must be greater than 0")
        numeric = float(radius)
        if not math.isfinite(numeric) or numeric <= 0:
            raise ValueError("Radii must be greater than 0")
        return numeric

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['CircleSVG']['style'])
        component = cls(data['CircleSVG']['position'],
                        data['CircleSVG']['radius'],
                        style)
        return component

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"CircleSVG":
                       {"position": self.position,
                        "radius": self.radius,
                        "style": self.style.parameters}}
        return parameter_dict

    @property
    def radius(self) -> float:
        """ Property to get the radius of the circle.

        Returns:
            float: radius.
        """
        return self.size

    @radius.setter
    def radius(self, radius: float) -> None:
        """ Update radius of cirlce.

        Args:
            radius (float): Radius of circle.

        Raises:
            ValueError: Raised if radius not greater than zero.
        """
        self.size = self._coerce_radius(radius)

    def _rect(self, length: float | int, angle: float | int) -> tuple[float, float]:
        """ Private method to convert polar coordinates to cartesian.

        Args:
            length (Union[float, int]): magnitude
            angle (Union[float, int]): angle from start position.

        Returns:
            Tuple[float, float]: cartesian x and y coordinate.
        """
        x = length * np.cos(np.deg2rad(angle))
        y = length * np.sin(np.deg2rad(angle))
        return (x, y)

    @property
    def points(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points in the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for each
            point in the object.
        """
        num_points = int(3.14159 * 2 * self.radius / 0.2)
        point_rounder = 360 / num_points
        points = []
        for i in range(num_points):
            x_offset, y_offset = self._rect(self.radius, i*point_rounder)
            points.append((round(self.position[0]+x_offset, PRECISION),
                           round(self.position[1]+y_offset, PRECISION)))
        return points

    @property
    def bbox(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points representing the
        bounding box around the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for the
            two points of the bounding box for the object.
        """
        min_pos = (self.position[0]-self.radius,
                   self.position[1]-self.radius)
        max_pos = (self.position[0]+self.radius,
                   self.position[1]+self.radius)
        return [min_pos, max_pos]

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points representing the
        convex hull around the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for the
            for each point of the convex hull of the object.
        """
        return self.points

    def generate_svg(self) -> str:
        """ Creates a single circle object in XML for a SVG file.

        Example:

            <circle
                cx="100"
                cy="100"
                r="50"
                style="stroke:black;fill:none"
                id="circle1" />

        Returns
        -------
        str
            XML line for SVG file
        """
        style = _style_properties(self.style)

        return f"""<circle
            cx="{self.position[0]}"
            cy="{self.position[1]}"
            r="{self.radius}"
            style="{style}"
            id="circle{self.id}" />"""


class TextSVG(TextComponent, DrawingGeneratorInterface):
    """
        Class to describe text as SVG components.
    """
    def __init__(self,
                 text: str,
                 position: tuple[float, float],
                 style: TextStyle):
        """ Instantiate a new text object

        Parameters
        ----------
        text : str
            text to be displayed
        position : Tuple[float, float]
            anchor point for text
        style : DrawingStyle
            Style used to draw the rectangle

        """

        super().__init__(text=text, position=position, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: TextStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = TextStyle.create_from_dict(data['TextSVG']['style'])
        component = cls(data['TextSVG']['text'],
                        data['TextSVG']['position'],
                        style)
        return component

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"TextSVG":
                       {"text": self.text,
                        "position": self.position,
                        "style": self.style.parameters}}
        return parameter_dict

    def generate_svg(self) -> str:
        """ Creates a text object in XML for a SVG file.

        Returns
        -------
        str
            XML line for SVG file

        Example:

        <text
            xml:space="preserve"
            style="font-style:italic;font-size:10.5833px;line-height:1.25;font-family:sans-serif;-inkscape-font-specification:sans-serif;stroke-width:0.265;text-anchor:middle;text-align:center;stroke-dasharray:none"
            x="81.296234"
            y="120.91882"
            id="text1"><tspan
                sodipodi:role="line"
                id="tspan1"
                style="stroke-width:0.265;text-anchor:middle;text-align:center;stroke-dasharray:none"
                x="53.701107"
                y="120.91882">Some Text</tspan></text>
        """
        font_size_pt = float(self.style.font.size)
        font_size_px = font_size_pt * (96.0 / 72.0)
        text_anchor = self.style.text_anchor
        text_align = self.style.text_align
        line_spacing = self.style.line_spacing
        text_fill = self.style.color
        text_style = ";".join([
            f"font-style:{self.style.font.style}",
            f"font-size:{font_size_px:.6f}px",
            f"line-height:{line_spacing}",
            f"font-family:{self.style.font.family}",
            f"fill:{text_fill}",
            "stroke:none",
            f"text-anchor:{text_anchor}",
            f"text-align:{text_align}",
            "stroke-dasharray:none",
        ])
        tspan_style = ";".join([
            f"fill:{text_fill}",
            f"text-anchor:{text_anchor}",
            f"text-align:{text_align}",
            "stroke:none",
            "stroke-dasharray:none",
        ])
        text_content = escape(self.text)

        return f"""<text
            style="{text_style}"
            x="{self.position[0]}"
            y="{self.position[1]}"
            id="text{self.id}"><tspan
                sodipodi:role="line"
                id="tspan{self.id}"
                style="{tspan_style}"
                x="{self.position[0]}"
                y="{self.position[1]}">{text_content}</tspan></text>"""




class SVGComponent(Component, DrawingGeneratorInterface):
    """Embed a flattened external SVG fragment within the document."""

    def __init__(
        self,
        filepath: str | None = None,
        *,
        paths: list[dict[str, object]] | None = None,
        bbox: tuple[tuple[float, float], tuple[float, float]] | None = None,
        position: tuple[float, float] = (0.0, 0.0),
        scale: float = 1.0,
        width: float | None = None,
        height: float | None = None,
        source: str | None = None,
    ) -> None:
        super().__init__()
        if filepath:
            flattened = flatten_svg(filepath)
            self._paths = [{"d": p.d, "style": p.style} for p in flattened.paths]
            self._bbox = flattened.bbox
            self._width = flattened.width
            self._height = flattened.height
            self._source = filepath
        elif paths is not None and bbox is not None:
            self._paths = paths
            self._bbox = self._coerce_bbox(bbox)
            self._width = width
            self._height = height
            self._source = source
        else:
            raise ValueError("Either filepath or paths/bbox must be provided.")

        self.position = position
        self.scale = scale

    @property
    def position(self) -> tuple[float, float]:
        return self._position

    @position.setter
    def position(self, value: tuple[float, float]) -> None:
        x, y = value
        self._position = (
            self._coerce_finite_number(x, "position coordinate"),
            self._coerce_finite_number(y, "position coordinate"),
        )

    @property
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def scale(self, value: float) -> None:
        value = self._coerce_finite_number(value, "scale")
        if value <= 0:
            raise ValueError("scale must be greater than zero.")
        self._scale = value

    @staticmethod
    def _coerce_finite_number(value: float, name: str) -> float:
        """Return a finite float while rejecting booleans and malformed values."""
        if isinstance(value, bool):
            raise TypeError(f"{name} must be numeric, not boolean.")
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} must be numeric.") from error
        if not math.isfinite(number):
            raise ValueError(f"{name} must be finite.")
        return number

    @classmethod
    def _coerce_bbox(
        cls,
        bbox: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Return a finite two-corner bbox."""
        try:
            (min_x, min_y), (max_x, max_y) = bbox
        except (TypeError, ValueError) as error:
            raise ValueError("bbox must contain exactly two coordinate pairs.") from error
        return (
            (
                cls._coerce_finite_number(min_x, "bbox coordinate"),
                cls._coerce_finite_number(min_y, "bbox coordinate"),
            ),
            (
                cls._coerce_finite_number(max_x, "bbox coordinate"),
                cls._coerce_finite_number(max_y, "bbox coordinate"),
            ),
        )

    @property
    def width(self) -> float:
        return (self._bbox[1][0] - self._bbox[0][0]) * self.scale

    @property
    def height(self) -> float:
        return (self._bbox[1][1] - self._bbox[0][1]) * self.scale

    def _scaled_bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        (min_x, min_y), (max_x, max_y) = self._bbox
        px, py = self.position
        scale = self.scale
        return (
            (px + scale * min_x, py + scale * min_y),
            (px + scale * max_x, py + scale * max_y),
        )

    @property
    def points(self) -> list[tuple[float, float]]:
        (min_x, min_y), (max_x, max_y) = self._scaled_bounds()
        corners = [
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
        ]
        return [
            (float(round(x, PRECISION)), float(round(y, PRECISION))) for x, y in corners
        ]

    @property
    def bbox(self) -> tuple[tuple[float, float], tuple[float, float]]:
        scaled = self._scaled_bounds()
        return (
            (float(round(scaled[0][0], PRECISION)), float(round(scaled[0][1], PRECISION))),
            (float(round(scaled[1][0], PRECISION)), float(round(scaled[1][1], PRECISION))),
        )

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        return self.points

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "SVGComponent": {
                "paths": self._paths,
                "bbox": self._bbox,
                "position": list(self.position),
                "scale": self.scale,
                "width": self._width,
                "height": self._height,
                "source": self._source,
            }
        }

    @classmethod
    def create_from_dict(cls, data: dict) -> SVGComponent:
        payload = data["SVGComponent"]
        bbox_data = tuple(tuple(coord) for coord in payload["bbox"])
        return cls(
            paths=payload["paths"],
            bbox=bbox_data,
            position=tuple(payload.get("position", (0.0, 0.0))),
            scale=payload.get("scale", 1.0),
            width=payload.get("width"),
            height=payload.get("height"),
            source=payload.get("source"),
        )

    def generate_svg(self) -> str:
        transforms: list[str] = []
        if not math.isclose(self.position[0], 0.0) or not math.isclose(self.position[1], 0.0):
            transforms.append(f"translate({self.position[0]},{self.position[1]})")
        if not math.isclose(self.scale, 1.0):
            transforms.append(f"scale({self.scale})")
        transform_str = " ".join(transforms)
        transform_attr = f' transform="{transform_str}"' if transforms else ""
        path_markup = []
        for path in self._paths:
            style_attr = f' style="{path["style"]}"' if path.get("style") else ""
            path_markup.append(f'<path d="{path["d"]}"{style_attr} />')
        content = "\n        ".join(path_markup)
        return f"<g{transform_attr}>\n        {content}\n    </g>"
class ComponentGroupSVG(ComponentGroup, LabelGenerator, SegmentGenerator):
    """
        Text to generate labeling data for component groups.
    """
    @classmethod
    def create_from_dict(cls, data: dict, styles: dict=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        group = cls(data['ComponentGroupSVG']['group_label'])
        if styles is None:
            styles = {}

        for c in data['ComponentGroupSVG']['components']:
            style = None
            component_class_name = list(c.keys())[0]
            if 'style' in list(c[component_class_name].keys()):
                style_name = list(c[component_class_name]['style'].keys())[0]
                if c[component_class_name]['style'][style_name]['name'] not in list(styles.keys()):
                    style_class_name = list(c[component_class_name]['style'].keys())[0]
                    style_class = getattr(sys.modules[__name__], style_class_name)
                    style = style_class.create_from_dict(c[component_class_name]['style'])
                    styles[c[component_class_name]['style'][style_name]['name']] = style
                else:
                    style = styles[c[component_class_name]['style'][style_name]['name']]
            component_class = getattr(sys.modules[__name__], component_class_name)
            component = component_class.create_from_dict(c, style)
            group.add_component(component)

        return group

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        comps = []
        for c in self._components.values():
            comps.append(c.parameters)

        parameter_dict = {"ComponentGroupSVG":
                       {"group_label": self.group_label,
                       "components": comps}}
        return parameter_dict

    def generate_label(self) -> dict[str, list[tuple[float, float]]]:
        return {self.group_label: self.bbox}

    def generate_segmentation_mask(self) -> dict[str, list[tuple[float, float]]]:
        return {self.group_label: self.convex_hull}




class TableSVG(ComponentGroupSVG):
    _MIN_SCALE = 0.1

    """Render a :class:`~InkGen.table.Table` into SVG primitives."""

    def __init__(
        self,
        table: Table,
        group_label: str,
        border_style: DrawingStyle,
        text_styles: dict[str, TextStyle],
        cell_padding: float | tuple[float, float, float, float] | None = None,
    ) -> None:
        super().__init__(group_label)
        self._table = table
        self._scaled_styles: dict[tuple[str, float], TextStyle] = {}
        self._cell_style_overrides: dict[tuple[int, int, int], TextStyle] = {}
        self._border_style = border_style
        self._text_styles = text_styles
        padding_tuple = table.cell_padding if cell_padding is None else cell_padding
        self._pad_top, self._pad_right, self._pad_bottom, self._pad_left = self._normalize_padding(padding_tuple)
        self._apply_autofit()
        self._build_components()

    @classmethod
    def from_table(
        cls,
        table: Table,
        *,
        group_label: str | None = None,
        border_style: DrawingStyle,
        text_styles: dict[str, TextStyle],
        cell_padding: float | tuple[float, float, float, float] | None = None,
    ) -> TableSVG:
        """Create a TableSVG from a Table instance.

        Args:
            table: Table object to render.
            group_label: Optional label for the component group. Defaults to
                        "Table_{table.id}" if not provided.
            border_style: Drawing style for table borders.
            text_styles: Dictionary mapping style IDs to TextStyle objects.
            cell_padding: Padding for cells (single float or 4-tuple).

        Returns:
            TableSVG instance ready for rendering.
        """
        label = group_label if group_label is not None else f"Table_{table.id}"
        return cls(table, label, border_style, text_styles, cell_padding)

    @property
    def table(self) -> Table:
        """The underlying Table object.

        Returns:
            Table instance being rendered.
        """
        return self._table

    def _horizontal_position(self, left: float, width: float, pad_left: float, pad_right: float, style: TextStyle) -> float:
        """Calculate horizontal text position based on alignment.

        Args:
            left: Left edge of the cell.
            width: Total cell width.
            pad_left: Left padding.
            pad_right: Right padding.
            style: TextStyle with alignment information.

        Returns:
            X coordinate for text placement.
        """
        align = getattr(style, 'text_align', 'start') or 'start'
        align = align.lower()
        interior = max(width - pad_left - pad_right, 0.0)
        if align in {'center', 'middle'}:
            return left + pad_left + interior / 2.0
        if align in {'end', 'right'}:
            return left + width - pad_right
        return left + pad_left

    @staticmethod
    def _normalize_padding(value: float | tuple[float, float, float, float] | list[float]) -> tuple[float, float, float, float]:
        """Normalize padding value to a 4-tuple.

        Args:
            value: Either a single float (applied to all sides) or a 4-element
                  sequence of floats.

        Returns:
            Tuple of (top, right, bottom, left) padding values.

        Raises:
            ValueError: If value is not a float or a 4-element sequence.
        """
        return Table._normalize_padding(value)

    def _apply_autofit(self) -> None:
        """Apply autofit rules to scale text or expand cells as needed."""
        iterations = 0
        changed = True
        while changed and iterations < 5:
            changed = False
            iterations += 1
            for row_index in range(self._table.row_count):
                row = self._table.rows[row_index]
                for column_index in range(self._table.column_count):
                    column = self._table.columns[column_index]
                    base_lines = self._collect_lines(row_index, column_index, apply_overrides=False)
                    if not base_lines:
                        continue

                    line_heights = [self._line_height(style) for _, style in base_lines]
                    block_height = sum(line_heights)
                    line_widths = [self._measure_text_width(text, style) for text, style in base_lines]
                    max_width = max(line_widths) if line_widths else 0.0
                    available_width = column.width - (self._pad_left + self._pad_right)
                    available_height = row.height - (self._pad_top + self._pad_bottom)

                    width_scale = 1.0
                    if max_width > max(available_width, 1e-6):
                        if column.width_rule == AutoFitRule.EXPAND:
                            required_width = max_width + self._pad_left + self._pad_right
                            if required_width > column.width:
                                column.width = required_width
                                changed = True
                                available_width = column.width - (self._pad_left + self._pad_right)
                        elif column.width_rule == AutoFitRule.FIT:
                            width_scale = min(width_scale, max(available_width, 1e-6) / max_width)

                    height_scale = 1.0
                    if block_height > max(available_height, 1e-6):
                        if row.height_rule == AutoFitRule.EXPAND:
                            required_height = block_height + self._pad_top + self._pad_bottom
                            if required_height > row.height:
                                row.height = required_height
                                changed = True
                                available_height = row.height - (self._pad_top + self._pad_bottom)
                        elif row.height_rule == AutoFitRule.FIT:
                            height_scale = min(height_scale, max(available_height, 1e-6) / block_height)

                    scale = min(width_scale, height_scale)
                    if scale < 0.999 and (column.width_rule == AutoFitRule.FIT or row.height_rule == AutoFitRule.FIT):
                        scale = max(scale, self._MIN_SCALE)
                        for line_idx, (_, style) in enumerate(base_lines):
                            override = self._scale_style(style, scale)
                            self._cell_style_overrides[(row_index, column_index, line_idx)] = override

    def _collect_lines(self, row_index: int, column_index: int, *, apply_overrides: bool) -> list[tuple[str, TextStyle]]:
        """Collect text lines from a cell with their styles.

        Args:
            row_index: Zero-based row index.
            column_index: Zero-based column index.
            apply_overrides: If True, apply autofit scaling overrides.

        Returns:
            List of (text, TextStyle) tuples for each non-empty paragraph.

        Raises:
            KeyError: If a referenced style ID is not in text_styles.
        """
        cell = self._table.cell(row_index, column_index)
        lines: list[tuple[str, TextStyle]] = []
        for idx, (text, style_id) in enumerate(zip(cell.paragraphs, cell.paragraph_styles, strict=False)):
            if not text:
                continue
            style = self._text_styles.get(style_id)
            if style is None:
                raise KeyError(f"Text style '{style_id}' not provided for table rendering")
            if apply_overrides:
                style = self._cell_style_overrides.get((row_index, column_index, idx), style)
            lines.append((text, style))
        return lines

    def _scale_style(self, style: TextStyle, factor: float) -> TextStyle:
        """Create a scaled copy of a text style, caching results.

        Args:
            style: Original TextStyle to scale.
            factor: Scaling factor to apply to font size.

        Returns:
            New TextStyle with scaled font size, other properties copied.
        """
        rounded = round(factor, 4)
        key = (style.name, rounded)
        if key in self._scaled_styles:
            return self._scaled_styles[key]

        font = style.font
        new_font = Font(
            family=font.family,
            style=font.style,
            variant=font.variant,
            stretch=font.stretch,
            weight=font.weight,
            size=float(font.size) * factor,
            custom_font_paths=list(font.custom_font_paths) if font.custom_font_paths else None,
        )
        clone_name = f"{style.name}_scaled_{len(self._scaled_styles)}"
        clone = TextStyle(clone_name, new_font)
        clone.color = style.color
        clone.superscript = style.superscript
        clone.subscript = style.subscript
        clone.text_align = style.text_align
        clone.line_spacing = style.line_spacing
        self._scaled_styles[key] = clone
        return clone

    def _measure_text_width(self, text: str, style: TextStyle) -> float:
        """Estimate text width in document units.

        Args:
            text: Text string to measure.
            style: TextStyle with font information.

        Returns:
            Estimated width in document units (mm).
        """
        size = getattr(style.font, 'size', 10.0)
        try:
            size_value = float(size)
        except (TypeError, ValueError):
            size_value = 10.0
        mm_per_point = 25.4 / 72.0
        base_width = size_value * mm_per_point * 0.6 * len(text)
        space_bonus = text.count(' ') * size_value * mm_per_point * 0.2
        return max(base_width + space_bonus, 0.1)

    def _line_metrics(self, text: str, style: TextStyle) -> tuple[float, float, float]:
        """Calculate line height and baseline offsets for text.

        Args:
            text: Text string to measure.
            style: TextStyle with font information.

        Returns:
            Tuple of (line_height, top_offset, bottom_offset) in document units.
        """
        component = TextSVG(text, (0.0, 0.0), style)
        outline = component._compute_outline()
        points = outline.get('points') or outline.get('bbox') or outline.get('convex_hull') or []
        if not points:
            height = self._line_height(style)
            ascent = self._baseline_shift(style)
            return height, ascent, height - ascent
        ys = [float(pt[1]) for pt in points]
        top = min(ys)
        bottom = max(ys)
        line_height = bottom - top
        top_offset = -top
        bottom_offset = bottom
        return line_height, top_offset, bottom_offset

    def _build_components(self) -> None:
        """Build SVG components for the table (borders and text)."""
        if not self._table.row_count or not self._table.column_count:
            return
        for row_index in range(self._table.row_count):
            for column_index in range(self._table.column_count):
                (x, y), width, height = self._table.cell_bounds(row_index, column_index)
                rectangle = RectangleSVG((x, y), width, height, 0.0, self._border_style)
                self.add_component(rectangle)

                cell = self._table.cell(row_index, column_index)
                lines = self._collect_lines(row_index, column_index, apply_overrides=True)
                if not lines:
                    continue

                pad_top = self._pad_top
                pad_right = self._pad_right
                pad_bottom = self._pad_bottom
                pad_left = self._pad_left

                metrics = []
                baseline_cursor = 0.0
                block_top = None
                block_bottom = None
                for text_value, style in lines:
                    line_height, top_offset, bottom_offset = self._line_metrics(text_value, style)
                    line_top = baseline_cursor - top_offset
                    line_bottom = baseline_cursor + bottom_offset
                    block_top = line_top if block_top is None else min(block_top, line_top)
                    block_bottom = line_bottom if block_bottom is None else max(block_bottom, line_bottom)
                    metrics.append((baseline_cursor, line_height, top_offset, bottom_offset, text_value, style))
                    baseline_cursor += line_height

                block_height = block_bottom - block_top if block_top is not None and block_bottom is not None else 0.0
                vertical_alignment = getattr(cell, "vertical_alignment", "top")

                interior_height = max(height - pad_top - pad_bottom, 0.0)
                if vertical_alignment == "middle":
                    target_top = pad_top + max((interior_height - block_height) / 2.0, 0.0)
                elif vertical_alignment == "bottom":
                    target_top = pad_top + max(interior_height - block_height, 0.0)
                else:
                    target_top = pad_top

                baseline_shift = y + target_top - (block_top or 0.0)
                for baseline_cursor, _line_height, _top_offset, _bottom_offset, text_value, style in metrics:
                    baseline = baseline_shift + baseline_cursor
                    text_x = self._horizontal_position(x, width, pad_left, pad_right, style)
                    self.add_component(TextSVG(text_value, (text_x, baseline), style))

    def _baseline_shift(self, style: TextStyle) -> float:
        """Calculate baseline offset from top of text.

        Args:
            style: TextStyle with font information.

        Returns:
            Distance from top of text to baseline in document units.
        """
        size = getattr(style.font, 'size', 10.0)
        try:
            size_value = float(size)
        except (TypeError, ValueError):
            size_value = 10.0
        mm_per_point = 25.4 / 72.0
        ascent_ratio = 0.78
        return max(size_value * mm_per_point * ascent_ratio, 0.2)

    def _line_height(self, style: TextStyle) -> float:
        """Calculate total line height including spacing.

        Args:
            style: TextStyle with font size and line spacing.

        Returns:
            Total line height in document units.
        """
        size = getattr(style.font, "size", 10.0)
        try:
            size_value = float(size)
        except (TypeError, ValueError):
            size_value = 10.0
        spacing = getattr(style, "line_spacing", 1.0)
        try:
            spacing_value = float(spacing)
        except (TypeError, ValueError):
            spacing_value = 1.0
        mm_per_point = 25.4 / 72.0
        return max(size_value * spacing_value * mm_per_point, 0.1)


class IncludeLayer(Flag):
    BASE = auto()
    LABEL = auto()
    MASK = auto()


class DocumentSVG(Document):
    """ Saves the document as an SVG file.
    """
    @staticmethod
    def _iter_layer_groups(layer: Layer) -> Iterable[ComponentGroup]:
        """Yield every component group in a layer, including repeated labels."""
        return layer.groups()

    def _collect_fonts(self) -> dict[str, str]:
        fonts: dict[str, str] = {}
        for pg in range(1, self.pages + 1):
            page = self.page(pg)
            for layer_name in page.layers:
                layer = page.layer(layer_name)
                for group in self._iter_layer_groups(layer):
                    for component in group.components():
                        font_obj = getattr(getattr(component, "style", None), "font", None)
                        font_path = getattr(font_obj, "font_file", None)
                        family = getattr(font_obj, "family", None)
                        if font_path and family and family not in fonts:
                            fonts[family] = font_path
        return fonts

    def create_svg(self, filepath: str, include: Flag = IncludeLayer.BASE) -> None:
        """
            Creates a SVG file at the filepath location.

            Args:
                filepath (str): file to create or save to.
                include (Flag): one of three options:
                    IncludeLayer.BASE: Just the drawing components
                    IncludeLayer.LABEL: Drawing components with bounding boxes
                                        around groups
                    IncludeLayer.MASK: Drawing components with convex hulls
                                        around groups
        """
        path, base_filename = self._normalize_output_path(filepath)

        if IncludeLayer.LABEL in include:
            self._add_label_layer()

        if IncludeLayer.MASK in include:
            self._add_segmentation_layer()

        font_rules = self._collect_font_rules()

        for pg in range(1, self.pages + 1):
            page = self.page(pg)
            svg_payload = self._assemble_page_svg(page, font_rules)
            target = self._target_filename(path, base_filename, pg)
            self._write_svg(target, svg_payload)

    def _normalize_output_path(self, filepath: str) -> tuple[str, str]:
        path, file = os.path.split(os.path.abspath(filepath))
        if "." in file:
            file = file.split(".")[0]
        if not os.path.exists(path):
            raise ValueError("The file path does not exist.")
        return path, file

    def _collect_font_rules(self) -> list[str]:
        font_sources = self._collect_fonts()
        rules: list[str] = []
        for family, font_path in font_sources.items():
            try:
                with open(font_path, "rb") as font_file:
                    encoded = base64.b64encode(font_file.read()).decode("ascii")
                rule = (
                    f"@font-face {{ font-family: '{family}'; "
                    f"src: url(data:font/truetype;base64,{encoded}) format('truetype'); }}"
                )
                rules.append(rule)
            except OSError:
                continue
        return rules

    def _assemble_page_svg(self, page: Layers, font_rules: list[str]) -> str:
        header = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>\t
<!-- Created with Inkscape (http://www.inkscape.org/) -->\t
\t
<svg
\twidth="{page._canvas.width}{page._canvas.units}"
\theight="{page._canvas.height}{page._canvas.units}"
\tviewBox="0 0 {page._canvas.width} {page._canvas.height}"
\tversion="1.1"
\tid="svg1"
\tinkscape:version="1.3 (0e150ed6c4, 2023-07-21)"
\tsodipodi:docname="boolean.svg"
\txmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
\txmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
\txmlns="http://www.w3.org/2000/svg"
\txmlns:svg="http://www.w3.org/2000/svg">
\t<sodipodi:namedview
    \tid="namedview1"
    \tpagecolor="#ffffff"
    \tbordercolor="#666666"
    \tborderopacity="1.0"
    \tinkscape:showpageshadow="2"
    \tinkscape:pageopacity="0.0"
    \tinkscape:pagecheckerboard="0"
    \tinkscape:deskcolor="#d1d1d1"
    \tinkscape:document-units="{page._canvas.units}"
    \tinkscape:zoom="1"
    \tinkscape:cx="0"
    \tinkscape:cy="0"
    \tinkscape:window-width="1920"
    \tinkscape:window-height="1009"
    \tinkscape:window-x="-8"
    \tinkscape:window-y="-8"
    \tinkscape:window-maximized="1"
\tinkscape:current-layer="layer{page.layer('base').layer_id}" />
\t<defs
    \tid="defs1">"""
        payload = [header]
        if font_rules:
            payload.append("\n\t\t<style type=\"text/css\">\n")
            for rule in font_rules:
                payload.append(f"\t\t\t{rule}\n")
            payload.append("\t\t</style>\n")
        payload.append("\t</defs>\n")
        for lyr in page.layers:
            layer_ = page.layer(lyr)
            payload.append(f"""\t<g
        inkscape:label="Layer {layer_.layer_id}"
        inkscape:groupmode="layer"
        id="layer{layer_.layer_id}">\n""")
            for group in self._iter_layer_groups(layer_):
                for cmp in group.components():
                    payload.append("\t\t")
                    payload.append(cmp.generate_svg())
                    payload.append("\n")
            payload.append("\t</g>\n")
        payload.append("</svg>\n")
        return "".join(payload)

    def _target_filename(self, directory: str, base: str, page_number: int) -> str:
        if self.pages == 1:
            return os.path.join(directory, base + ".svg")
        return os.path.join(directory, f"{base}_page_{page_number}.svg")

    def _write_svg(self, filepath: str, content: str) -> None:
        with open(file=filepath, mode="w", encoding="utf-8") as handle:
            handle.write(content)

    def _compute_model_mask(self, group: ComponentGroup) -> list[tuple[float, float]]:
        """Determine mask polygon for a component group, accounting for stroke width."""
        override = getattr(group, "_mask_override", None)
        if override:
            return list(override)

        components = list(group.components())
        if not components:
            return group.convex_hull

        geometries = []
        max_stroke = 0.0
        for component in components:
            style = getattr(component, "style", None)
            if style is not None and hasattr(style, "stroke_width"):
                try:
                    max_stroke = max(max_stroke, float(getattr(style, "stroke_width", 0.0) or 0.0))
                except (TypeError, ValueError):
                    pass

            geom = None
            if hasattr(component, "polygon"):
                try:
                    geom = component.polygon
                except Exception:
                    geom = None
            if geom is None:
                pts: list[tuple[float, float]] = []
                if hasattr(component, "points"):
                    try:
                        pts = list(component.points)
                    except Exception:
                        pts = []
                if len(pts) >= 3:
                    geom = Polygon(pts)
                elif len(pts) == 2:
                    geom = LineString(pts)
                elif len(pts) == 1:
                    geom = Point(pts[0])
                elif hasattr(component, "bbox"):
                    try:
                        (minx, miny), (maxx, maxy) = component.bbox
                        geom = Polygon([
                            (float(minx), float(miny)),
                            (float(maxx), float(miny)),
                            (float(maxx), float(maxy)),
                            (float(minx), float(maxy)),
                        ])
                    except Exception:
                        geom = None

            if geom is not None and not geom.is_empty:
                try:
                    geometries.append(_normalize_geometry(geom))
                except GEOSException:
                    continue

        if not geometries:
            return group.convex_hull

        try:
            union = unary_union(geometries)
        except GEOSException:
            repaired = [_normalize_geometry(g) for g in geometries if not g.is_empty]
            union = unary_union(repaired) if repaired else None

        if not union or union.is_empty:
            return group.convex_hull
        if union.is_empty:
            return group.convex_hull

        hull_geom = union.convex_hull

        buffer_amount = max_stroke / 2.0
        if buffer_amount > 0.0:
            hull_geom = hull_geom.buffer(buffer_amount, cap_style=2, join_style=2).convex_hull

        if hull_geom.geom_type in {"LineString", "LinearRing"}:
            hull_geom = hull_geom.buffer(max(buffer_amount, 1e-6), cap_style=2, join_style=2)
        elif hull_geom.geom_type == "Point":
            hull_geom = hull_geom.buffer(max(buffer_amount, 1e-6))

        coords: list[tuple[float, float]] = []
        if hasattr(hull_geom, "exterior"):
            coords = [(float(x), float(y)) for x, y in hull_geom.exterior.coords]
        else:
            coords = [(float(x), float(y)) for x, y in getattr(hull_geom, "coords", [])]

        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        return coords

    def _add_modeling_layer(self, model_type: str) -> None:
        colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'magenta',
                  'gray', 'navy', 'maroon', 'teal', 'brown', 'olive', 'lime', 'cyan', 'apricot']

        for pg in range(1, self.pages + 1):
            new_groups: dict[str, dict] = {}
            color_mem = 0
            page = self.page(pg)

            # Always rebuild the target modeling layer from scratch to avoid stale geometry.
            if model_type in page.layers:
                page.remove_layer(model_type)

            for lyr in page.layers:
                layer = page.layer(lyr)
                if not layer.model:
                    continue
                for group in self._iter_layer_groups(layer):
                    entry: dict[str, object] = {
                        'color': colors[color_mem % 16],
                        'mask': self._compute_model_mask(group),
                    }
                    if model_type == 'label':
                        entry['bbox'] = group.bbox

                    label = group.group_label
                    entry_key = label if label not in new_groups else f"{label}_{group.group_id}"
                    new_groups[entry_key] = entry
                    color_mem += 1

            modeling_layer = Layer(model_type, self._canvas, model=False)
            page.add_layer(layer=modeling_layer)
            target_layer = page.layer(model_type)
            for grp, data in new_groups.items():
                group = ComponentGroupSVG(grp)
                fill_style = DrawingStyle(
                    grp + 'fill' + data['color'] + "_" + str(group.group_id),
                    stroke="none",
                    fill=data['color'],
                    fill_opacity=0.1,
                )
                line_style = DrawingStyle(
                    grp + 'line' + data['color'] + "_" + str(group.group_id),
                    stroke_width=0.1,
                    stroke=data['color'],
                    fill_opacity=1,
                )

                if model_type == 'label':
                    position = data['bbox'][0]
                    width = data['bbox'][1][0] - data['bbox'][0][0]
                    height = data['bbox'][1][1] - data['bbox'][0][1]
                    group.add_component(
                        RectangleSVG(position, width, height, corner_radii=0, style=fill_style)
                    )
                    group.add_component(
                        RectangleSVG(position, width, height, corner_radii=0, style=line_style)
                    )
                else:
                    mask_points = data['mask']
                    if mask_points:
                        group.add_component(PolygonalSVG(mask_points, fill_style))
                        group.add_component(PolygonalSVG(mask_points, line_style))

                target_layer.add_component_group(group)

    def _add_segmentation_layer(self) -> None:
        """Private method to incorporate the segmentation mask in the drawing.
        """
        self._add_modeling_layer('mask')

    def _add_label_layer(self) -> None:
        """Private method to incorporate the bounding boxes in the drawing.
        """
        self._add_modeling_layer('label')

    @staticmethod
    def _layer_from_svg_dict(data: dict, styles: dict[str, object]) -> Layer:
        """Recreate a layer containing SVG component groups."""
        canvas = Canvas.create_from_dict(data['Layer']['canvas'])
        layer = Layer(data['Layer']['layer_name'], canvas, data['Layer']['model'])
        for group_payload in data['Layer']['component_groups']:
            if 'ComponentGroupSVG' in group_payload:
                group = ComponentGroupSVG.create_from_dict(group_payload, styles)
            else:
                group = ComponentGroup.create_from_dict(group_payload, styles)
            settings = data['Layer']['group_collision_settings'][group.group_label]
            layer.add_component_group(group, settings['allow_collision'], settings['strict'])
        return layer

    @staticmethod
    def _layers_from_svg_dict(data: dict, styles: dict[str, object]) -> Layers:
        """Recreate the page layer stack with SVG component groups."""
        layers = Layers(Canvas.create_from_dict(data['Layers']['canvas']))
        for layer_name in list(layers.layers):
            layers.remove_layer(layer_name)
        for _, layer_payload in data['Layers']['layers'].items():
            layer = DocumentSVG._layer_from_svg_dict(layer_payload, styles)
            layers.add_layer(layer.layer_name, layer)
        return layers

    @classmethod
    def create_from_dict(cls, data: dict, styles: dict | None = None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if styles is None:
            styles = {}
        document = cls(Canvas.create_from_dict(data['DocumentSVG']['canvas']))
        for pg in range(len(data['DocumentSVG']['pages'])):
            page = cls._layers_from_svg_dict(data['DocumentSVG']['pages'][pg], styles)
            document.add_page(position=-1, page=page)
        return document

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        pages = []
        for page in list(self._pages.keys()):
            pages.append(self.page(page).parameters)
        parameter_dict = {"DocumentSVG":
                       {'canvas': self._canvas.parameters,
                        'pages': pages}}
        return parameter_dict


