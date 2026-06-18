"""
    Base Classes for Building Components and Component Groups Describing
    various document items.
"""
import itertools
import math
import sys
from collections.abc import Iterator
from copy import deepcopy

import numpy as np
from shapely import MultiPoint, Point, Polygon, get_coordinates
from svgpathtools import parse_path

from InkGen.errors import InvalidComponentID, InvalidPolygonError
from InkGen.style import DrawingStyle, TextStyle
from InkGen.text_outline import ADD_ONE_PIXEL_MARGIN_DEFAULT, outline_for_text

PRECISION = 3
DEFAULT_CURVE_SAMPLES = 32


def normalize_rectangle_corner_radii(
        corner_radii: float | int | tuple[float, float] | list[float],
        width: float | int,
        height: float | int) -> tuple[float, float]:
    """Return validated horizontal and vertical rectangle corner radii."""
    if isinstance(corner_radii, bool):
        raise TypeError("Corner radii must be numeric values.")
    if isinstance(corner_radii, (float, int)):
        rx = float(corner_radii)
        ry = float(corner_radii)
    elif isinstance(corner_radii, (tuple, list)):
        if len(corner_radii) != 2:
            raise TypeError("Corner radii must be a scalar or a pair of numeric values.")
        if any(isinstance(value, bool) or not isinstance(value, (float, int)) for value in corner_radii):
            raise TypeError("Corner radii must be numeric values.")
        rx = float(corner_radii[0])
        ry = float(corner_radii[1])
    else:
        raise TypeError("Corner radii must be either a float or tuple of floats")

    if not math.isfinite(rx) or not math.isfinite(ry):
        raise ValueError("Corner radii must be finite.")
    if rx < 0.0 or ry < 0.0:
        raise ValueError("Corner radii must be greater than or equal to zero.")
    if rx > (float(width) / 2.0) or ry > (float(height) / 2.0):
        raise ValueError("Corner radius should not exceed half the width and height")
    return rx, ry


class Component:
    """
        Base class for creating synthetically generated objects. Includes automatically
        generated id and component type properties.
    """
    id_iter = itertools.count()

    def __init__(self) -> None:
        """
            Instantiates id and component_type based on class name.
        """
        self._id = next(Component.id_iter)
        self._component_type = self.__class__.__name__

    @classmethod
    def create_from_dict(cls, data: dict) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        _ = data
        component = cls()
        return component

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"Component":
                       {}}
        return parameter_dict

    @property
    def id(self) -> int:
        """
            Unique id for each component and inherited types.

        Returns
        -------
        int
            Automatically generated instance id.
        """
        return self._id

    @property
    def component_type(self) -> str:
        """
            Component class name as type indicator.

        Returns
        -------
        str
            Automatically labelled component type
        """
        return self._component_type


class DrawingComponent(Component):
    """
        Component with DrawingStyle information for visualization.
    """
    def __init__(self, style: DrawingStyle) -> None:
        """
            Instantiates component id, type, and sets DrawingStyle object

        Args:
            style (DrawingStyle): Object that defines how the Drawing Component will be displayed.
        """

        self._check_style(style)
        self._style = style

        super().__init__()

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle = None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['DrawingComponent']['style'])
        component = cls(style)
        return component

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"DrawingComponent":
                       {"style": self.style.parameters}}
        return parameter_dict

    def _check_style(self, style: DrawingStyle) -> None:
        """ Verifies DrawingStyle object.

        Args:
            style (DrawingStyle): style object with inforamtion for visualizaing components

        Raises:
            TypeError: raised when DrawingStyle or derivative not passed as argument
        """
        if not isinstance(style, DrawingStyle):
            raise TypeError("style argument must be a DrawingStyle object.")

    @property
    def style(self) -> DrawingStyle:
        """
           Exposes DrawingStyle Object

        Returns:
            DrawingStyle: Object with information for visualizing components
        """
        return self._style

    @style.setter
    def style(self, style: DrawingStyle) -> None:
        """
           Enables updating DrawingStyle object for making changes.

        Args:
            style (DrawingStyle): Object with information for visualizing components
        """
        self._check_style(style)
        self._style = style


class StandardDrawingComponent(DrawingComponent):
    """
        Drawing component with position data for two points defining top
        left and bottom right corners.
    """
    def __init__(self, point_1: tuple[float, float],
                 point_2: tuple[float, float],
                 style: DrawingStyle) -> None:
        """ Create component with two points and drawing style

        Args:
            point_1 (Tuple[float, float]): Top Left Corner of Drawing Component
            point_2 (Tuple[float, float]): Bottom Right Corner of Drawing Component
            style (DrawingStyle): Style Information for Drawing Component
        """
        super().__init__(style = style)
        p1 = Point(point_1)
        p2 = Point(point_2)
        self._check_inputs(p1, p2)

        self._p1 = p1
        self._p2 = p2

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['StandardDrawingComponent']['style'])
        component = cls(data['StandardDrawingComponent']['point_1'],
                        data['StandardDrawingComponent']['point_2'],
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
        parameter_dict = {"StandardDrawingComponent":
                       {"point_1": self.point_1,
                        "point_2": self.point_2,
                        "style": self.style.parameters}}
        return parameter_dict

    def _x(self, point: Point) -> float:
        """ Private method to get the x component of a Point.

        Args:
            point (Point): Point Object, has x and y component.

        Returns:
            float: x component of the Point.
        """
        return point.coords.xy[0][0]

    def _y(self, point: Point) -> float:
        """ Private method to get the y component of a Point.

        Args:
            point (Point): Point Object, has x and y component.

        Returns:
            float: y component of the Point.
        """
        return point.coords.xy[1][0]

    def _check_inputs(self, point_1: Point, point_2: Point) -> None:
        """ Private method to verify valid point coordinates.

        Args:
            point_1 (Tuple[float, float]): Top Left Corner of Drawing Component
            point_2 (Tuple[float, float]): Bottom Right Corner of Drawing Component
        """

        if (
            self._x(point_1) < 0 or self._x(point_2) < 0 or
            self._y(point_1) < 0 or self._y(point_2) < 0
            ):
            raise ValueError("Points must be greater than zero.")

        # Removed this functionality when it became clear that it makes no sense with
        # subclasses needing to be in multiple directions.
        # if self._x(point_1) > self._x(point_2) or self._y(point_1) > self._y(point_2):
        #     raise ValueError("The second Point should always be the larger of the two. \
        #                       For example, point_2.x should be greater than point_2.y")

    @property
    def point_1(self) -> tuple[float, float]:
        """ Property to get the coordinates of the first point.

        Returns:
            Tuple[float, float]: coordinates of first point.
        """
        return (float(round(self._x(self._p1), PRECISION)),
                float(round(self._y(self._p1), PRECISION)))

    @point_1.setter
    def point_1(self, point_1: tuple[float, float]) -> None:
        """ Property setter to change coordinates of first point.

        Args:
            point_1 (Tuple[float, float]): coordinates of first point.
        """
        p1 = Point(point_1)
        self._check_inputs(p1, self._p2)
        self._p1 = p1

    @property
    def point_2(self) -> tuple[float, float]:
        """Property to get the coordinates of the second point.

        Returns:
            Tuple[float, float]: coordinates of second point.
        """
        return (float(round(self._x(self._p2), PRECISION)),
                float(round(self._y(self._p2), PRECISION)))

    @point_2.setter
    def point_2(self, point_2: tuple[float, float]) -> None:
        """ Property setter to change coordinates of second point.

        Args:
            point_2 (Tuple[float, float]): coordinates of second point.
        """
        p2 = Point(point_2)
        self._check_inputs(self._p1, p2)
        self._p2 = p2

    @property
    def points(self) -> list[tuple[float, float]]:
        """
           Exposes full list of points in the drawing component.

        Returns:
            List[Tuple[float, float]]: List of tuples of x, y coordinates.
        """
        return [self.point_1, self.point_2]

    @property
    def bbox(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points representing the
        bounding box around the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for the
            two points of the bounding box for the object.
        """
        return [(self.point_1[0], self.point_1[1]), (self.point_2[0], self.point_2[1])]

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points representing the
        convex hull around the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for the
            for each point of the convex hull of the object.
        """
        return self.points


class SingleDimensionDrawingComponent(StandardDrawingComponent):
    """
        Drawing Component with position and size rather than two points. This class could describe,
            circles with position being center and size being radius or squares with position
            being the upper left corner and size being the length of each side.

    """
    def __init__(self,
                 position: tuple[float, float],
                 size: float | int,
                 style: DrawingStyle
                 ) -> None:
        """ Initializes Single Dimension Drawing Components.

        Args:
            position (Tuple[float, float]): coordinates of object location.
            size (Union[float, int]): generic size information.
            style (DrawingStyle): Style Information for Drawing Component
        """

        point_2 = (position[0] + size, position[1] + size)

        super().__init__(point_1 = position, point_2 = point_2, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['SingleDimensionDrawingComponent']['style'])
        component = cls(data['SingleDimensionDrawingComponent']['position'],
                        data['SingleDimensionDrawingComponent']['size'],
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
        parameter_dict = {"SingleDimensionDrawingComponent":
                       {"position": self.position,
                        "size": self.size,
                        "style": self.style.parameters}}
        return parameter_dict

    @property
    def position(self) -> tuple[float, float]:
        """Property to get coordinates of the position.

        Returns:
            Tuple[float, float]: coordinates of the position.
        """
        return self.point_1

    @position.setter
    def position(self, value: tuple[float, float]) -> None:
        """ Setter to modify coordinates of the position.

        Args:
            value (Tuple[float, float]): New position.
        """
        size = self.size
        self.point_1 = value
        self.size = size

    @property
    def size(self) -> float:
        """Property to get size parameter.

        Returns:
            float: size variable.
        """
        return float(self._x(self._p2) - self._x(self._p1))

    @size.setter
    def size(self, value: float | int) -> None:
        """Update size.

        Args:
            value (Union[float, int]): New size.
        """
        point_2 = Point(self._p1.x + value, self._p1.x + value)
        self.point_2 = point_2

    @property
    def points(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points in the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for each
            point in the object.
        """
        return [self.point_1, self.point_2]

    @property
    def bbox(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points representing the
        bounding box around the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for the
            two points of the bounding box for the object.
        """
        return self.points

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points representing the
        convex hull around the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for the
            for each point of the convex hull of the object.
        """
        return self.points


class WidthHeightDrawingComponent(StandardDrawingComponent):
    """
        Class for Drawing Components with a height and width. Could be rectangles
        or other objects best described by the position, height, and width parameters.

    """
    def __init__(self,
                 position: tuple[float, float],
                 width: float | int,
                 height: float | int,
                 style: DrawingStyle
                 ) -> None:
        """ Initializes the drawing component with position, width, height, and drawing style.

        Args:
            position (Tuple[float, float]): Position of drawing component.
            width (Union[float, int]): width of drawing component.
            height (Union[float, int]): height of drawing component.
            style (DrawingStyle): style information for drawing component
        """
        point_2 = (position[0] + width, position[1] + height)

        super().__init__(point_1 = position, point_2 = point_2, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['WidthHeightDrawingComponent']['style'])
        component = cls(data['WidthHeightDrawingComponent']['position'],
                        data['WidthHeightDrawingComponent']['width'],
                        data['WidthHeightDrawingComponent']['height'],
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
        parameter_dict = {"WidthHeightDrawingComponent":
                       {"position": self.position,
                        "width": float(self.width),
                        "height": float(self.height),
                        "style": self.style.parameters}}
        return parameter_dict

    @property
    def position(self) -> tuple[float, float]:
        """ Property for position coordinates.

        Returns:
            Tuple[float, float]: position coordinates.
        """
        return self.point_1

    @position.setter
    def position(self, value: tuple[float, float]) -> None:
        """ Setter to update position of Drawing Component.

        Args:
            value (Tuple[float, float]): new position coordinates.
        """
        width = self.width
        height = self.height
        self.point_1 = value
        self.point_2 = (value[0]+width, value[1]+height)

    @property
    def height(self) -> float:
        """ Property to get height of Drawing Component.

        Returns:
            float: Height of Drawing Component.
        """
        return self._y(self._p2) - self._y(self._p1)

    @height.setter
    def height(self, value: float) -> None:
        """ Setter to update height of Drawing Component.

        Args:
            value (float): new height.
        """
        point_2 = (self._x(self._p2), self._y(self._p1) + value)
        self.point_2 = point_2

    @property
    def width(self) -> float:
        """ Property to get width of Drawing Component.

        Returns:
            float: Width of Drawing Component.
        """
        return self._x(self._p2) - self._x(self._p1)

    @width.setter
    def width(self, value: float) -> None:
        """ Setter to update width of Drawing Component.

        Args:
            value (float): new width.
        """
        point_2 = (self._x(self._p1) + value, self._y(self._p2))
        self.point_2 = point_2

    @property
    def points(self) -> list[tuple[float, float]]:
        """Read only property to get all 4 points of the object.

        Returns:
            List[Tuple[float, float]]: Each of the four coordinates for a
            complete bounding box.
        """
        points = []
        points.append(self.position)
        points.append((self.position[0]+self.width, self.position[1]))
        points.append((self.position[0]+self.width, self.position[1]+self.height))
        points.append((self.position[0], self.position[1]+self.height))
        return points

    @property
    def bbox(self) -> list[tuple[float, float]]:
        """ Upper and Lower bounds as two coordinates.

        Returns:
            List[Tuple[float, float]]: lower then upper coordinates.
        """
        bounds = [self.position,
                  (self.position[0]+self.width, self.position[1]+self.height)]
        return bounds

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """ Points of the convex hull as a list of coordinates.

        Returns:
            List[Tuple[float, float]]: coordinates of the hull.
        """
        return self.points


class PolarCoordinateDrawingComponent(StandardDrawingComponent):
    """ Class for drawing components better suited to be illustrated as
        vectors with a initial position then a length (magnitude) and
        angle (direction).
    """
    def __init__(self,
                 position: tuple[float, float],
                 length: int | float,
                 angle: int | float,
                 style: DrawingStyle) -> None:
        """ Create new polar coordinate class.

        Args:
            position (Tuple[float, float]): Initial position
            length (Union[int, float]): length of the component.
            angle (Union[int, float]): angle in degrees from the initial position.
            style (DrawingStyle): style information for drawing component
        """
        coords = self._rect(length=length, angle=angle)
        point_2 = (coords[0] + position[0], coords[1] + position[1])

        super().__init__(point_1 = position, point_2 = point_2, style=style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['PolarCoordinateDrawingComponent']['style'])
        component = cls(data['PolarCoordinateDrawingComponent']['position'],
                        data['PolarCoordinateDrawingComponent']['length'],
                        data['PolarCoordinateDrawingComponent']['angle'],
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
        parameter_dict = {"PolarCoordinateDrawingComponent":
                       {"position": self.position,
                        "length": self.length,
                        "angle": self.angle,
                        "style": self.style.parameters}}
        return parameter_dict


    # https://stackoverflow.com/questions/20924085/python-conversion-between-coordinates
    def _polar(self, point: tuple[float, float]) -> tuple[float, float]:
        """ Private method to convert cartesian coordinates to polar.

        Args:
            point (Tuple[float, float]): Cartesian coordinate.

        Returns:
            Tuple[float, float]: Polar coordinate.
        """
        return (np.hypot(point[0], point[1]), np.degrees(np.arctan2(point[1], point[0])))

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

    def _length_angle(self) -> tuple[float, float]:
        """ Private method to calculate length and angle from
            cartesian coordinates.

        Returns:
            Tuple[float, float]: cartesian coordinates.
        """
        x = self.point_2[0] - self.point_1[0]
        y = self.point_2[1] - self.point_1[1]
        length, angle = self._polar((x,y))
        return length, angle

    @property
    def position(self) -> tuple[float, float]:
        """ Property to get position of drawing component.

        Returns:
            Tuple[float, float]: cartesian coordinate of position.
        """
        return self.point_1

    @position.setter
    def position(self, value: tuple[float, float]) -> None:
        """ Setter to update position as cartesian coordinate.

        Args:
            value (Tuple[float, float]): position coordinate.
        """
        point_2 = (self.point_2[0] - self.point_1[0], self.point_2[1] - self.point_1[1])
        self.point_1 = value
        self.point_2 = (value[0]+point_2[0], value[1]+point_2[1])

    @property
    def length(self) -> float:
        """ Property for length of drawing component.

        Returns:
            float: length parameter.
        """
        length, _ = self._length_angle()
        return float(length)

    @length.setter
    def length(self, value: float | int) -> None:
        """ Setter to update length of drawing component.

        Args:
            value (Union[float, int]): New length.
        """
        _, angle = self._length_angle()

        coords = self._rect(length=value, angle=angle)
        self.point_2 = (coords[0] + self.point_1[0], coords[1] + self.point_1[1])

    @property
    def angle(self) -> float:
        """ Property to get angle in degrees of drawing component.

        Returns:
            float: angle in degrees.
        """
        _, angle = self._length_angle()
        return float(round(angle, PRECISION))

    @angle.setter
    def angle(self, value: float | int) -> None:
        """ Setter to update angle of drawing component.

        Args:
            value (Union[float, int]): new angle in degrees.
        """
        length, _ = self._length_angle()

        coords = self._rect(length=length, angle=value)
        self.point_2 = (coords[0] + self.point_1[0], coords[1] + self.point_1[1])

    @property
    def points(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points in the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for each
            point in the object.
        """
        return [self.point_1, self.point_2]

    @property
    def bbox(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points representing the
        bounding box around the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for the
            two points of the bounding box for the object.
        """
        return self.points

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """ Read-only property to get a list of all points representing the
        convex hull around the object.

        Returns:
            List[Tuple(float, float)]: List with a tuple of floats for the
            for each point of the convex hull of the object.
        """
        return self.points


class PolygonalDrawingComponent(DrawingComponent):
    """
       DrawingComponent with mulitple connected points (in order based).
    """

    def __init__(self, points: list[tuple[float, float]], style: DrawingStyle) -> None:
        """
           Instantiates drawing component with list of points and style information.

        Args:
            points (List[Tuple[float, float]]): Ordered list of connected points
                                                representing a polygon.
            style (DrawingStyle): Object with information for visualizing components.
        """

        polygon = self._create_valid_polygon(points)
        if polygon is None:
            raise InvalidPolygonError("Polygon must be a list with 3 or more tuples of \
                                      floating point values representing two dimensional \
                                      cartesian coordinates.")
        self._polygon = polygon

        super().__init__(style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['PolygonalDrawingComponent']['style'])
        component = cls(data['PolygonalDrawingComponent']['points'],
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
        parameter_dict = {"PolygonalDrawingComponent":
                       {"points": self.points,
                        "style": self.style.parameters}}
        return parameter_dict

    def _polygon_check(self, points: list[tuple[float, float]]) -> bool:
        """ Verifies that points represent a valid Tuple.

        Args:
            points (List[Tuple[float, float]]): List of points

        Returns:
            bool: True if valid Polygon.
        """

        return self._create_valid_polygon(points) is not None

    def _create_valid_polygon(self, points: list[tuple[float, float]]) -> Polygon | None:
        if not isinstance(points, (list, tuple)) or len(points) < 3:
            return None

        normalized = []
        for point in points:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                return None
            if any(isinstance(value, bool) for value in point):
                return None
            try:
                x = float(point[0])
                y = float(point[1])
            except (TypeError, ValueError):
                return None
            if not math.isfinite(x) or not math.isfinite(y):
                return None
            normalized.append((x, y))

        polygon = Polygon(normalized)
        if polygon.is_empty or not polygon.is_valid or polygon.area <= 0.0:
            return None
        return polygon

    @property
    def bbox(self) ->  tuple[tuple[float, float], tuple[float, float]]:
        """
           Provides a bounding box around the polygon with lower and upper
           limit coordinates.

        Returns:
            Tuple[Tuple[float, float], Tuple[float, float]]: lower and upper
            limit coordinates
        """
        bounds = self._polygon.bounds
        return ((bounds[0], bounds[1]), (bounds[2], bounds[3]))

    @property
    def points(self) -> list[tuple[float, float]]:
        """
           Exposes full list of points in the polygon.

        Returns:
            List[Tuple[float, float]]: List of tuples of x, y coordinates.
        """
        coordinates = []
        for coord in get_coordinates(self._polygon):
            coordinates.append((float(coord[0]), float(coord[1])))
        return coordinates[:-1]

    @points.setter
    def points(self, value: list[tuple[float, float]]) -> None:
        """
           Replaces all points with a new list of points.

        Args:
            value (List[Tuple[float, float]]): list of points
        """
        polygon = self._create_valid_polygon(value)
        if polygon is None:
            raise InvalidPolygonError("Polygon must be a list with 3 or more tuples of \
                                      floating point values representing two dimensional \
                                      cartesian coordinates.")
        self._polygon = polygon

    @property
    def polygon(self) -> Polygon:
        """ Exposes polygon Object

        Returns:
            Polygon: Polygon object with functions for calculations.
        """
        return self._polygon

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """ Read-only property with list of points defining convex hull of the polygon.

        Returns:
            List[Tuple[float, float]]: List of points representing convex hull.
        """
        coordinates = []
        for coord in get_coordinates(self._polygon.convex_hull):
            coordinates.append((coord[0], coord[1]))
        return coordinates[:-1]

class RegularPolygonDrawingComponent(PolarCoordinateDrawingComponent):
    """ DrawingComponent in a standard Multisided Polygon configuration.
    """
    # Inspirations for this: https://gist.github.com/99991/4fcf3093321ebe29d73bd34cbdb707a2
    # https://pypi.org/project/svgpathtools/
    # regular_polygon function in simple_inkscape_scripting.py
    def __init__(self,
                 position: tuple[float, float],
                 sides: int,
                 radius: float,
                 style: DrawingStyle,
                 angle: float = 0.0,
                 corner_radius: float = 0.0) -> None:
        """ Creates a DrawingComponent in the shap of a regular polygon.

        Parameters
        ----------
        position : Tuple[float, float]
            Center position of the polygon.
        sides : int
            Number of sides in the polygon.
        radius : float
            Radius from the center to a corner of the polygon.
        style : DrawingStyle
            Object with information for visualizing components.
        angle : float, optional
            Rotation of the polygon in degrees, by default 0.0
        round : float, optional
            corner radius for rounded corners, by default 0.0

        Raises
        ------
        ValueError
            Checks that sides argument is 3 or greater
        ValueError
            Checks that round argument is half the radius or less
        """

        self.sides = sides
        if radius <= 0:
            raise ValueError("The radius should be greater than zero.")
        super().__init__(position=position, length=radius, angle=angle, style=style)

        self.corner_radius = corner_radius

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = DrawingStyle.create_from_dict(data['RegularPolygonDrawingComponent']['style'])
        component = cls(data['RegularPolygonDrawingComponent']['position'],
                        data['RegularPolygonDrawingComponent']['sides'],
                        data['RegularPolygonDrawingComponent']['radius'],
                        style,
                        data['RegularPolygonDrawingComponent']['angle'],
                        data['RegularPolygonDrawingComponent']['corner_radius'],)
        return component

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"RegularPolygonDrawingComponent":
                       {"position": self.position,
                        "sides": self.sides,
                        "radius": float(round(self.radius, PRECISION)),
                        "style": self.style.parameters,
                        "angle": float(round(self.angle, PRECISION)),
                        "corner_radius": float(round(self.corner_radius, PRECISION))}}
        return parameter_dict

    def _get_points(self) -> list[tuple[float, float]]:
        """Calculate the corner points of the regular polygon.

        Returns:
            List of (x, y) coordinates for each vertex of the polygon.
        """
        points = []
        for p in range(0, self.sides):
            points.append(self._rect(self.length, (self.angle + 90 + p*360/self.sides)%360))

        for i, p in enumerate(points):
            points[i] = (p[0]+self.position[0], p[1]+self.position[1])

        return points

    @property
    def sides(self) -> int:
        """ Property to retrieve the number of sides in current polygon.

        Returns
        -------
        int
            Number of sides in the polygon
        """
        return self._sides

    @sides.setter
    def sides(self, sides: int) -> None:
        """ Setter to update the number of sides in polygon.

        Parameters
        ----------
        sides : int
            Number of sides in Polygon.

        Raises
        ------
        ValueError
            Value error to check the number of sides in polygon.
        """

        if isinstance(sides, bool) or not isinstance(sides, int):
            raise TypeError("For regular polygon sides must be an integer.")
        if sides >= 3:
            self._sides = sides
        else:
            raise ValueError("For regular polygon use 3 or more sides.")

    @property
    def radius(self) -> float:
        """ Radius from position (center) of polygon to a corner.

        Returns
        -------
        float
            Distance to corner from center.
        """
        return self.length

    @radius.setter
    def radius(self, value: float) -> None:
        """ Setter to update radius of polygon.

        Parameters
        ----------
        value : float
            Distance to corner from center.

        Raises
        ------
        ValueError
            Ensures that radius is greater than zero.
        """
        if value <= 0:
            raise ValueError("The radius should be greater than zero.")
        if hasattr(self, "_corner_radius") and self.corner_radius > (value / 2):
            raise ValueError("The corner rounding should not exceed half the radius.")
        self.length = value

    @property
    def corner_radius(self) -> float:
        """ Radius of polygon corners

        Returns
        -------
        float
            radius of polygon corners
        """
        return self._corner_radius

    @corner_radius.setter
    def corner_radius(self, value: float) -> None:
        """ Corner Radius of the Polygon

        Parameters
        ----------
        value : float
            Corner Radius
        """
        if value < 0:
            raise ValueError("The corner rounding should be non-negative.")
        if value <= (self.radius/2):
            self._corner_radius = value
        else:
            raise ValueError("The corner rounding should not exceed half the radius.")

    @property
    def points(self) -> list[tuple[float, float]]:
        """
           Exposes full list of points in the polygon.

        Returns:
            List[Tuple[float, float]]: List of tuples of x, y coordinates.
        """
        return self._get_points()

    @property
    def bbox(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """
           Provides a bounding box around the polygon with lower and upper
           limit coordinates.

        Returns:
            Tuple[Tuple[float, float], Tuple[float, float]]: lower and upper
            limit coordinates
        """
        polygon = Polygon(self._get_points())
        bounds = polygon.bounds
        return ((bounds[0], bounds[1]), (bounds[2], bounds[3]))

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """ Read-only property with list of points defining convex hull of the polygon.

        Returns:
            List[Tuple[float, float]]: List of points representing convex hull.
        """
        polygon = Polygon(self._get_points())
        coordinates = []
        for coord in get_coordinates(polygon.convex_hull):
            coordinates.append((coord[0], coord[1]))
        return coordinates[:-1]


class PathCommand:
    """
        Representation of a single path command with its associated points.
    """
    VALID_COMMANDS = {"M", "L", "H", "V", "Z", "C", "S", "Q", "T", "A"}

    def __init__(self, command_type: str, points: list[tuple[float, float]] | None = None) -> None:
        self._type = ""
        self._points: list[tuple[float, float]] = []
        self.type = command_type
        self.points = points or []

    def _coerce_point(self, point: tuple[float, float]) -> tuple[float, float]:
        """Validate and normalize a point to a tuple of two floats.

        Args:
            point: Point coordinates as a 2-element sequence.

        Returns:
            Tuple of (x, y) as floats.

        Raises:
            ValueError: If point does not have exactly 2 elements.
        """
        if len(point) != 2:
            raise ValueError("Points must contain two numeric values.")
        return (float(point[0]), float(point[1]))

    @property
    def type(self) -> str:
        """SVG path command type (e.g. M, L, C)."""
        return self._type

    @type.setter
    def type(self, value: str) -> None:
        """Set the path command type.

        Args:
            value: Command type string (e.g., "M", "L", "C").

        Raises:
            TypeError: If value is not a string.
            ValueError: If value is not a valid SVG path command.
        """
        if not isinstance(value, str):
            raise TypeError("Command type must be a string.")
        normalized = value.strip().upper()
        if normalized not in self.VALID_COMMANDS:
            raise ValueError(f"{normalized} is not a supported path command.")
        self._type = normalized

    @property
    def points(self) -> list[tuple[float, float]]:
        """Read-only copy of the points associated with the command.

        Returns:
            List of (x, y) coordinate tuples, rounded to PRECISION.
        """
        return [
            (float(round(x, PRECISION)), float(round(y, PRECISION)))
            for x, y in self._points
        ]

    @points.setter
    def points(self, values: list[tuple[float, float]]) -> None:
        """Set the points for this command.

        Args:
            values: List of (x, y) coordinate tuples.
        """
        self._points = [self._coerce_point(point) for point in values]

    def add_point(self, point: tuple[float, float]) -> None:
        """Append an additional point to the command."""
        self._points.append(self._coerce_point(point))

    @property
    def parameters(self) -> dict:
        """Dictionary representation suitable for serialization."""
        return {"type": self.type, "points": self.points}


class Arc(DrawingComponent):
    """DrawingComponent representing an elliptical arc."""

    def __init__(self,
                 center: tuple[float, float],
                 radius_x: float,
                 radius_y: float,
                 start_angle: float,
                 end_angle: float,
                 style: DrawingStyle,
                 rotation: float = 0.0) -> None:

        self._center = self._coerce_point(center)
        self._radius_x = self._validate_radius(radius_x, "radius_x")
        self._radius_y = self._validate_radius(radius_y, "radius_y")
        self._start_angle = float(start_angle)
        self._end_angle = float(end_angle)
        self._rotation = float(rotation)
        self._samples = max(1, DEFAULT_CURVE_SAMPLES)

        super().__init__(style)

    @staticmethod
    def _coerce_point(point: tuple[float, float]) -> tuple[float, float]:
        if len(point) != 2:
            raise ValueError("Point must contain two numeric values.")
        return (float(point[0]), float(point[1]))

    @staticmethod
    def _validate_radius(value: float, name: str) -> float:
        radius = float(value)
        if radius <= 0:
            raise ValueError(f"{name} must be greater than zero.")
        return radius

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle = None) -> object:
        if not style:
            style = DrawingStyle.create_from_dict(data['Arc']['style'])
        return cls(center=tuple(data['Arc']['center']),
                   radius_x=data['Arc']['radius_x'],
                   radius_y=data['Arc']['radius_y'],
                   start_angle=data['Arc']['start_angle'],
                   end_angle=data['Arc']['end_angle'],
                   style=style,
                   rotation=data['Arc'].get('rotation', 0.0))

    @property
    def parameters(self) -> dict:
        return {"Arc":
                {"center": self.center,
                 "radius_x": float(round(self.radius_x, PRECISION)),
                 "radius_y": float(round(self.radius_y, PRECISION)),
                 "start_angle": float(round(self.start_angle, PRECISION)),
                 "end_angle": float(round(self.end_angle, PRECISION)),
                 "rotation": float(round(self.rotation, PRECISION)),
                 "style": self.style.parameters}}

    @property
    def center(self) -> tuple[float, float]:
        return (float(round(self._center[0], PRECISION)),
                float(round(self._center[1], PRECISION)))

    @center.setter
    def center(self, value: tuple[float, float]) -> None:
        self._center = self._coerce_point(value)

    @property
    def radius_x(self) -> float:
        return self._radius_x

    @radius_x.setter
    def radius_x(self, value: float) -> None:
        self._radius_x = self._validate_radius(value, "radius_x")

    @property
    def radius_y(self) -> float:
        return self._radius_y

    @radius_y.setter
    def radius_y(self, value: float) -> None:
        self._radius_y = self._validate_radius(value, "radius_y")

    @property
    def start_angle(self) -> float:
        return self._start_angle

    @start_angle.setter
    def start_angle(self, value: float) -> None:
        self._start_angle = float(value)

    @property
    def end_angle(self) -> float:
        return self._end_angle

    @end_angle.setter
    def end_angle(self, value: float) -> None:
        self._end_angle = float(value)

    @property
    def rotation(self) -> float:
        return self._rotation

    @rotation.setter
    def rotation(self, value: float) -> None:
        self._rotation = float(value)

    @property
    def points(self) -> list[tuple[float, float]]:
        start = math.radians(self._start_angle)
        end = math.radians(self._end_angle)
        if math.isclose(start, end, abs_tol=1e-9):
            theta_values = [start]
        else:
            theta_values = [
                start + (end - start) * (step / self._samples)
                for step in range(self._samples + 1)
            ]

        rotation = math.radians(self._rotation)
        cos_r = math.cos(rotation)
        sin_r = math.sin(rotation)

        coords = []
        for theta in theta_values:
            x = self._radius_x * math.cos(theta)
            y = self._radius_y * math.sin(theta)
            x_rot = x * cos_r - y * sin_r
            y_rot = x * sin_r + y * cos_r
            coords.append((float(round(self._center[0] + x_rot, PRECISION)),
                           float(round(self._center[1] + y_rot, PRECISION))))
        return coords


class QuadraticBezier(DrawingComponent):
    """DrawingComponent representing a quadratic Bezier curve."""

    def __init__(self,
                 start_point: tuple[float, float],
                 control_point: tuple[float, float],
                 end_point: tuple[float, float],
                 style: DrawingStyle) -> None:

        self._start_point = self._coerce_point(start_point)
        self._control_point = self._coerce_point(control_point)
        self._end_point = self._coerce_point(end_point)
        self._samples = max(1, DEFAULT_CURVE_SAMPLES)

        super().__init__(style)

    @staticmethod
    def _coerce_point(point: tuple[float, float]) -> tuple[float, float]:
        if len(point) != 2:
            raise ValueError("Point must contain two numeric values.")
        return (float(point[0]), float(point[1]))

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle = None) -> object:
        if not style:
            style = DrawingStyle.create_from_dict(data['QuadraticBezier']['style'])
        return cls(start_point=tuple(data['QuadraticBezier']['start_point']),
                   control_point=tuple(data['QuadraticBezier']['control_point']),
                   end_point=tuple(data['QuadraticBezier']['end_point']),
                   style=style)

    @property
    def parameters(self) -> dict:
        return {"QuadraticBezier":
                {"start_point": self.start_point,
                 "control_point": self.control_point,
                 "end_point": self.end_point,
                 "style": self.style.parameters}}

    @property
    def start_point(self) -> tuple[float, float]:
        return (float(round(self._start_point[0], PRECISION)),
                float(round(self._start_point[1], PRECISION)))

    @start_point.setter
    def start_point(self, value: tuple[float, float]) -> None:
        self._start_point = self._coerce_point(value)

    @property
    def control_point(self) -> tuple[float, float]:
        return (float(round(self._control_point[0], PRECISION)),
                float(round(self._control_point[1], PRECISION)))

    @control_point.setter
    def control_point(self, value: tuple[float, float]) -> None:
        self._control_point = self._coerce_point(value)

    @property
    def end_point(self) -> tuple[float, float]:
        return (float(round(self._end_point[0], PRECISION)),
                float(round(self._end_point[1], PRECISION)))

    @end_point.setter
    def end_point(self, value: tuple[float, float]) -> None:
        self._end_point = self._coerce_point(value)

    @property
    def points(self) -> list[tuple[float, float]]:
        coords = []
        for step in range(self._samples + 1):
            t = step / self._samples
            one_minus_t = 1.0 - t
            x = (one_minus_t ** 2) * self._start_point[0] + \
                2 * one_minus_t * t * self._control_point[0] + \
                (t ** 2) * self._end_point[0]
            y = (one_minus_t ** 2) * self._start_point[1] + \
                2 * one_minus_t * t * self._control_point[1] + \
                (t ** 2) * self._end_point[1]
            coords.append((float(round(x, PRECISION)), float(round(y, PRECISION))))
        return coords


class CubicBezier(DrawingComponent):
    """DrawingComponent representing a cubic Bezier curve."""

    def __init__(self,
                 start_point: tuple[float, float],
                 control_point1: tuple[float, float],
                 control_point2: tuple[float, float],
                 end_point: tuple[float, float],
                 style: DrawingStyle) -> None:

        self._start_point = self._coerce_point(start_point)
        self._control_point1 = self._coerce_point(control_point1)
        self._control_point2 = self._coerce_point(control_point2)
        self._end_point = self._coerce_point(end_point)
        self._samples = max(1, DEFAULT_CURVE_SAMPLES)

        super().__init__(style)

    @staticmethod
    def _coerce_point(point: tuple[float, float]) -> tuple[float, float]:
        if len(point) != 2:
            raise ValueError("Point must contain two numeric values.")
        return (float(point[0]), float(point[1]))

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle = None) -> object:
        if not style:
            style = DrawingStyle.create_from_dict(data['CubicBezier']['style'])
        return cls(start_point=tuple(data['CubicBezier']['start_point']),
                   control_point1=tuple(data['CubicBezier']['control_point1']),
                   control_point2=tuple(data['CubicBezier']['control_point2']),
                   end_point=tuple(data['CubicBezier']['end_point']),
                   style=style)

    @property
    def parameters(self) -> dict:
        return {"CubicBezier":
                {"start_point": self.start_point,
                 "control_point1": self.control_point1,
                 "control_point2": self.control_point2,
                 "end_point": self.end_point,
                 "style": self.style.parameters}}

    @property
    def start_point(self) -> tuple[float, float]:
        return (float(round(self._start_point[0], PRECISION)),
                float(round(self._start_point[1], PRECISION)))

    @start_point.setter
    def start_point(self, value: tuple[float, float]) -> None:
        self._start_point = self._coerce_point(value)

    @property
    def control_point1(self) -> tuple[float, float]:
        return (float(round(self._control_point1[0], PRECISION)),
                float(round(self._control_point1[1], PRECISION)))

    @control_point1.setter
    def control_point1(self, value: tuple[float, float]) -> None:
        self._control_point1 = self._coerce_point(value)

    @property
    def control_point2(self) -> tuple[float, float]:
        return (float(round(self._control_point2[0], PRECISION)),
                float(round(self._control_point2[1], PRECISION)))

    @control_point2.setter
    def control_point2(self, value: tuple[float, float]) -> None:
        self._control_point2 = self._coerce_point(value)

    @property
    def end_point(self) -> tuple[float, float]:
        return (float(round(self._end_point[0], PRECISION)),
                float(round(self._end_point[1], PRECISION)))

    @end_point.setter
    def end_point(self, value: tuple[float, float]) -> None:
        self._end_point = self._coerce_point(value)

    @property
    def points(self) -> list[tuple[float, float]]:
        coords = []
        for step in range(self._samples + 1):
            t = step / self._samples
            one_minus_t = 1.0 - t
            x = (one_minus_t ** 3) * self._start_point[0] + \
                3 * (one_minus_t ** 2) * t * self._control_point1[0] + \
                3 * one_minus_t * (t ** 2) * self._control_point2[0] + \
                (t ** 3) * self._end_point[0]
            y = (one_minus_t ** 3) * self._start_point[1] + \
                3 * (one_minus_t ** 2) * t * self._control_point1[1] + \
                3 * one_minus_t * (t ** 2) * self._control_point2[1] + \
                (t ** 3) * self._end_point[1]
            coords.append((float(round(x, PRECISION)), float(round(y, PRECISION))))
        return coords


class Path(DrawingComponent):
    """DrawingComponent composed of SVG-like path commands."""

    def __init__(self,
                 style: DrawingStyle,
                 commands: list[PathCommand] | None = None) -> None:

        self._commands: list[PathCommand] = []
        if commands:
            for command in commands:
                self.add_command(command)

        super().__init__(style)

    @classmethod
    def create_from_dict(cls, data: dict, style: DrawingStyle = None) -> object:
        if not style:
            style = DrawingStyle.create_from_dict(data['Path']['style'])
        commands = []
        for command in data['Path'].get('commands', []):
            commands.append(PathCommand(command['type'], command.get('points', [])))
        return cls(style=style, commands=commands)

    @property
    def parameters(self) -> dict:
        return {"Path":
                {"commands": [cmd.parameters for cmd in self._commands],
                 "style": self.style.parameters}}

    def add_command(self, command: PathCommand | dict) -> None:
        """Append a new command to the path."""
        if isinstance(command, PathCommand):
            self._commands.append(command)
        elif isinstance(command, dict):
            self._commands.append(PathCommand(command['type'], command.get('points', [])))
        else:
            raise TypeError("Command must be a PathCommand or a dictionary.")

    @property
    def commands(self) -> list[PathCommand]:
        return list(self._commands)

    @property
    def points(self) -> list[tuple[float, float]]:
        coords: list[tuple[float, float]] = []
        for command in self._commands:
            coords.extend(command.points)
        return coords


class TextComponent(Component):
    """
        Component for creating text.
    """
    def __init__(self, text: str, position: tuple[float, float], style: TextStyle) -> None:
        """ Instantiat text component.

        Parameters
        ----------
        text : str
            Text information to be displayed.
        position : Tuple[float, float]
            coordinates for text (dependant on style information for alignment: left, center, right)
        TextStyle : TextStyle
            style information including font, color, etc.
        """

        self._outline_cache = None
        self.text = text
        self.position = position
        self.style = style

        super().__init__()

    @classmethod
    def create_from_dict(cls, data: dict, style: TextStyle=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        if not style:
            style = TextStyle.create_from_dict(data['TextComponent']['style'])
        component = cls(data['TextComponent']['text'],
                        data['TextComponent']['position'],
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
        parameter_dict = {"TextComponent":
                       {"text": self.text,
                        "position": self.position,
                        "style": self.style.parameters}}
        return parameter_dict

    @property
    def text(self) -> str:
        """ String of text to be displayed.

        Returns:
            str: string of text.
        """
        return self._text

    @text.setter
    def text(self, value: str | int | float | complex | bool) -> None:
        """Update text to be displayed

        Args:
            value (str): new string.

        Raises:
            ValueError: If object other than str is passed.
        """

        if isinstance(value, (str, int, float, complex, bool)):
            self._text = str(value)
            self._outline_cache = None
        else:
            raise TypeError("Text argument should be a string or a non-iterable built in type.")

    @property
    def position(self) -> tuple[float, float]:
        """ Coordinates for text dependant on alignment.

        Returns
        -------
        Tuple[float, float]
            Coordinates.
        """
        return (round(self._position[0], PRECISION), round(self._position[1], PRECISION))

    @position.setter
    def position(self, value: tuple[float, float]) -> None:
        """ Setter to update text location coordinates.

        Parameters
        ----------
        value : Tuple[float, float]
            Coordinates.
        """

        if isinstance(value, (tuple, list, set)) and len(value) == 2:
            self._position = value
            self._outline_cache = None

    @property
    def style(self) -> TextStyle:
        """ Set the style attributes for the text (e.g., font-family, font-size, etc.)

        Returns
        -------
        TextStyle
            Style object
        """
        return self._style

    @style.setter
    def style(self, value: TextStyle) -> None:
        """ Enables changing the style object.

        Parameters
        ----------
        value : TextStyle
            Style object with information about the text such as font, size, opacity, etc.

        Raises
        ------
        ValueError
            Raised if TextStyle not passed as argument.
        """
        if isinstance(value, TextStyle):
            self._style = value
            self._outline_cache = None
        else:
            raise TypeError("style attribute requires a TextStyle object")

    def _compute_outline(self):
        """Compute and cache the outline information for this text."""
        if self._outline_cache is not None:
            return self._outline_cache

        # Canvas is in millimeters; TextStyle.Font.size is **points**
        size_pt = float(self.style.font.size)
        size_px = size_pt * (96.0 / 72.0)  # pt -> CSS px (1pt=1/72in, 1px=1/96in)

        try:
            outline = outline_for_text(
                text=self._text,
                font_path=self.style.font.font_file,
                size_px=size_px,
                x=self.position[0],
                y=self.position[1],
                dpi=96.0,
                units="mm",
                add_one_pixel_margin=ADD_ONE_PIXEL_MARGIN_DEFAULT,
                y_down=True,
                features={"kern": True, "liga": True},
            )
        except Exception:  # pragma: no cover - graceful fallback for missing font tooling
            outline = None

        if not outline or not any(outline.get(key) for key in ("points", "convex_hull", "bbox", "path_bbox")):
            outline = self._fallback_outline(size_pt)
        else:
            outline = self._align_outline_to_anchor(outline)

        self._outline_cache = outline
        return self._outline_cache

    def _fallback_outline(self, size_pt: float) -> dict:
        """Return an approximate rectangular outline when precise shaping fails."""
        mm_per_point = 25.4 / 72.0
        height = max(size_pt * mm_per_point, 0.5)
        width = max(len(self._text) * size_pt * mm_per_point * 0.6, height * 0.5)

        anchor_x, anchor_y = float(self.position[0]), float(self.position[1])
        align = getattr(self.style, "text_align", "start") or "start"
        if align == "center":
            left = anchor_x - width / 2.0
        elif align == "end":
            left = anchor_x - width
        else:
            left = anchor_x
        top = anchor_y - height

        rect = [
            (left, top),
            (left + width, top),
            (left + width, top + height),
            (left, top + height),
        ]
        return {"points": rect, "convex_hull": rect, "bbox": rect}

    def _align_outline_to_anchor(self, outline: dict) -> dict:
        """Adjust the outline geometry so it reflects the rendered alignment."""
        align = getattr(self.style, "text_align", "start") or "start"
        if align not in {"center", "end"}:
            return outline

        span = self._outline_span(outline)
        if span is None:
            return outline

        left, right = span
        width = right - left
        if width <= 0:
            return outline

        anchor_x = float(self.position[0])
        if align == "center":
            expected_left = anchor_x - width / 2.0
        else:  # align == "end"
            expected_left = anchor_x - width

        dx = expected_left - left
        if abs(dx) <= 1e-6:
            return outline

        return self._translate_outline(outline, dx, 0.0)

    @staticmethod
    def _outline_span(outline: dict) -> tuple[float, float] | None:
        for key in ("convex_hull", "bbox", "points"):
            pts = outline.get(key)
            if pts:
                xs = [float(pt[0]) for pt in pts]
                if xs:
                    return min(xs), max(xs)

        path_bbox = outline.get("path_bbox")
        if path_bbox:
            xmin, _, xmax, _ = path_bbox
            return float(xmin), float(xmax)
        return None

    @staticmethod
    def _translate_outline(outline: dict, dx: float, dy: float) -> dict:
        shifted = deepcopy(outline)

        def _shift(points):
            return [(float(x) + dx, float(y) + dy) for x, y in points]

        if shifted.get("points"):
            shifted["points"] = _shift(shifted["points"])
        if shifted.get("convex_hull"):
            shifted["convex_hull"] = _shift(shifted["convex_hull"])
        if shifted.get("bbox"):
            shifted["bbox"] = _shift(shifted["bbox"])

        if shifted.get("path_bbox"):
            xmin, ymin, xmax, ymax = shifted["path_bbox"]
            shifted["path_bbox"] = (xmin + dx, ymin + dy, xmax + dx, ymax + dy)

        svg_path = shifted.get("svg_path")
        if svg_path:
            try:
                path = parse_path(svg_path)
                path = path.translated(complex(dx, dy))
                shifted["svg_path"] = path.d()
            except Exception:
                pass

        return shifted

    @property
    def points(self) -> list[tuple[float, float]]:
        """Expose the outline-derived points for the text in document units."""

        outline = self._compute_outline()
        hull = outline.get("convex_hull") or []
        if hull:
            hull_coords = list(hull)
            if len(hull_coords) > 1 and hull_coords[0] == hull_coords[-1]:
                hull_coords = hull_coords[:-1]
            return hull_coords
        pts = outline.get("points") or []
        if pts:
            return pts
        bbox = outline.get("bbox") or []
        return list(bbox)

    @property
    def bbox(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Bounding box derived from the text outline."""

        outline = self._compute_outline()
        bbox = outline.get("bbox") or []
        if bbox:
            return (tuple(bbox[0]), tuple(bbox[2])) if len(bbox) >= 3 else tuple(bbox)
        return ((self.position[0], self.position[1]), (self.position[0], self.position[1]))

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """Read-only property returning the convex hull of the text outline."""

        outline = self._compute_outline()
        hull = outline.get("convex_hull") or []
        hull_coords = list(hull)
        if len(hull_coords) > 1 and hull_coords[0] == hull_coords[-1]:
            hull_coords = hull_coords[:-1]
        return hull_coords


class ComponentGroup:
    """
        A collection of components that makes up a labelled object in a document.
    """
    grp_id_iter = itertools.count()

    def __init__(self, group_label: str) -> None:
        """
            Instantiates group_id and group_label which serves as the object
            detection/segmentation label for document AI models.
        """
        self._grp_id = next(ComponentGroup.grp_id_iter)
        if isinstance(group_label, str):
            self._group_label = group_label
        else:
            raise TypeError("group_label argument must be a string")

        self._components = {}

    @classmethod
    def create_from_dict(cls, data: dict, styles: dict=None) -> object:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            object: instance of the class.
        """
        group = cls(data['ComponentGroup']['group_label'])
        if styles is None:
            styles = {}

        for c in data['ComponentGroup']['components']:
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

        parameter_dict = {"ComponentGroup":
                       {"group_label": self.group_label,
                       "components": comps}}
        return parameter_dict

    def add_component(self, component: Component) -> None:
        """ Add a component to the Component Group.

        Args:
            component (Component): Object from the Component
            class or a derivative.
        """

        if isinstance(component, Component):
            self._components[component.id] = component

    def remove_component(self, component_id: int) -> None:
        """ Removes a component from the Component Group.

        Args:
            component_id (int): Id native to the component object,
            automatically assigned on its instantiation.
        """

        if component_id in list(self._components):
            del self._components[component_id]
        else:
            raise InvalidComponentID(f"There does not exist a component in \
                                     this group with id {component_id}")

    def get_component(self, component_id: int) -> Component:
        """ Access component object stored in component group.

        Args:
            component_id (int): id of component (generated on instantiation)

        Returns:
            Component: Object of the Component class or derivative
        """
        if component_id in list(self._components):
            return self._components[component_id]
        else:
            raise InvalidComponentID(f"There does not exist a component in \
                                     this group with id {component_id}")

    def components(self) -> Iterator[Component]:
        """ Generator for iterating over all components in the group.

        Returns:
            Component: next Component object in the component group.
        """

        yield from self._components.values()

    @property
    def group_id(self) -> int:
        """
            Unique id for each component group.

        Returns
        -------
        int
            Automatically generated instance id.
        """
        return self._grp_id

    @property
    def group_label(self) -> str:
        """
            Name assigned to group on instantiation, to represent
            the document AI model label.

        Returns
        -------
        str
            Label provided for group on instantiation.
        """
        return self._group_label

    def _create_multipoint(self) -> MultiPoint:
        """ Private class for building a multipoint object to be used for
            calculations of convex hull, bounding box, and points outputs.

        Returns:
            MultiPoint: Shapely Multipoint object (with relevant methods)
        """
        points = []
        for component in self._components.values():
            if hasattr(component, "points"):
                points.extend(component.points)

        multi = MultiPoint(points)
        return multi

    @property
    def points(self) -> list[tuple[float, float]]:
        """ List of all the points in the group.

        Returns:
            List[Tuple[float, float]]: List of coordinates.
        """

        multi = self._create_multipoint()

        coordinates = []
        for coord in get_coordinates(multi):
            coordinates.append((coord[0], coord[1]))
        return coordinates

    @property
    def bbox(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """ Bounding box of object (minx, miny) and (maxx, maxy).

            Returns:
                Tuple[Tuple[float, float], Tuple[float, float]]: min and max tuples
        """

        multi = self._create_multipoint()
        bounds = multi.bounds

        return ((bounds[0], bounds[1]), (bounds[2], bounds[3]))

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """ Read-only property with list of points defining convex hull of the points
            in the group.

        Returns:
            List[Tuple[float, float]]: List of points representing convex hull.
        """

        multi = self._create_multipoint()
        coordinates = []
        for coord in get_coordinates(multi.convex_hull):
            coordinates.append((coord[0], coord[1]))
        return coordinates[:-1]


