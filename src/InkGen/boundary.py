"""Classes for defining and checking boundaries such as the size of a sheet."""

from __future__ import annotations

from math import isfinite

from shapely import MultiPoint, Polygon, get_coordinates
from shapely.errors import GEOSException

from InkGen.errors import IllegalArgumentError, InvalidConvexHull


def _coerce_finite_number(value: float | int, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"The {name} argument should be a float or int")

    number = float(value)
    if not isfinite(number):
        raise IllegalArgumentError(f"The {name} argument should be finite")
    return number


def _coerce_positive_number(value: float | int, name: str) -> float:
    number = _coerce_finite_number(value, name)
    if number <= 0:
        raise IllegalArgumentError(f"The {name} argument should be greater than zero")
    return number


def _normalize_hull(hull: list[tuple[float, float]], name: str = "hull") -> list[tuple[float, float]]:
    if isinstance(hull, (str, bytes)):
        raise InvalidConvexHull(f"The {name} argument must be coordinate pairs")

    try:
        raw_points = list(hull)
    except TypeError as exc:
        raise InvalidConvexHull(f"The {name} argument must be coordinate pairs") from exc

    if len(raw_points) < 3:
        raise InvalidConvexHull(f"The {name} argument must include at least three coordinate pairs")

    points = []
    for index, point in enumerate(raw_points):
        if isinstance(point, (str, bytes)):
            raise InvalidConvexHull(f"The {name} argument must be coordinate pairs")
        try:
            x, y = point
        except (TypeError, ValueError) as exc:
            raise InvalidConvexHull(f"The {name} argument must be coordinate pairs") from exc

        try:
            points.append(
                (
                    _coerce_finite_number(x, f"{name}[{index}][0]"),
                    _coerce_finite_number(y, f"{name}[{index}][1]"),
                )
            )
        except (IllegalArgumentError, TypeError) as exc:
            raise InvalidConvexHull(f"The {name} argument must contain finite numeric coordinate pairs") from exc

    if len(set(points)) < 3:
        raise InvalidConvexHull(f"The {name} argument must include at least three distinct coordinate pairs")

    if points[0] == points[-1]:
        points = points[:-1]

    return points


class Boundary:
    """
    Class for storing boundary information for constraining component points.
    """

    def __init__(self, hull: list[tuple[float, float]], outer_boundary: bool = False) -> None:
        """Create a boundary wrapper around a convex hull."""
        if not isinstance(outer_boundary, bool):
            raise TypeError("The outer_boundary argument is required to be a boolean.")

        self._outer = outer_boundary
        try:
            self._boundary_points = _normalize_hull(hull)
            self._boundary_polygon = MultiPoint(self._boundary_points).convex_hull
        except GEOSException as exc:
            raise InvalidConvexHull("The hull argument is not a valid convex hull") from exc

        if self._boundary_polygon.is_empty or self._boundary_polygon.area <= 0 or not self._hull_check():
            raise InvalidConvexHull("The hull argument is not a valid convex hull")

    @classmethod
    def create_from_dict(cls, data: dict) -> Boundary:
        """Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            Boundary: instance of the class.
        """
        boundary = cls(data["Boundary"]["hull"], data["Boundary"]["outer_boundary"])
        return boundary

    @property
    def parameters(self) -> dict:
        """Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"Boundary": {"hull": self.boundary_points, "outer_boundary": self._outer}}
        return parameter_dict

    def _hull_check(self) -> bool:
        """Verify that the boundary polygon is a valid convex hull.

        Returns:
            bool: True if the polygon is a valid convex hull, False otherwise.
        """
        hull = {tuple(point) for point in get_coordinates(self._boundary_polygon.convex_hull)}
        for point in self._boundary_points:
            if point not in hull:
                return False
        return True

    @property
    def boundary_points(self) -> list[tuple[float, float]]:
        """Provides access to the hull points as read-only values.

        Returns
        -------
        list[tuple[float, float]]
            List of x, y coordinates for each point of the hull.
        """
        return self._boundary_points.copy()

    @property
    def boundary_type(self) -> str:
        """Provides read-only access to the boundary limits.

        "outer" indicates that outside the hull is off limits and "inner" that the
        inside of the hull is off limits.

        Returns
        -------
        str
            Either "outer" or "inner" depending on whether the limit is outside
            (outer) the hull or inside (inner).
        """
        if self._outer:
            return "outer"
        return "inner"

    def boundary_check(self, points: list[tuple[float, float]], strict: bool = False) -> bool:
        """Verify that the provided points respect the boundary constraints.

        Args:
            points: Coordinates to check against the boundary.
            strict: If False, points on the boundary line are acceptable.

        Returns:
            bool: True if there is no interference between the points provided and the boundary.
        """

        if not isinstance(strict, bool):
            raise TypeError("The strict argument is required to be a boolean.")

        try:
            raw_points = list(points)
        except TypeError as exc:
            raise InvalidConvexHull("The points argument must be coordinate pairs") from exc

        if not raw_points:
            return False

        points_geometry = MultiPoint(_normalize_hull(raw_points, "points"))
        polygon = Polygon(get_coordinates(points_geometry.convex_hull))
        if self._outer:
            if strict:
                return polygon.contains_properly(self._boundary_polygon.convex_hull)
            return polygon.contains(self._boundary_polygon.convex_hull)

        if strict:
            return self._boundary_polygon.convex_hull.contains_properly(polygon)
        return self._boundary_polygon.convex_hull.contains(points_geometry)


class Canvas(Boundary):
    """
    Class for storing information about a drawing space including the
    dimensions and units of the space.
    """

    def __init__(self, canvas_width: float | int, canvas_height: float | int, units: str = "mm") -> None:
        """
            Creates Canvas object to store dimensions and unit of measure for a space.

        Parameters
        ----------
        canvas_width : Union[float, int]
            Width of the canvas
        canvas_height : Union[float, int]
            Height of the canvas
        units : str, optional
            Canvas units (mm or in), by default "mm"

        Raises
        ------
        TypeError
            Raises TypeError if the width argument is not a float or int
        TypeError
            Raises TypeError if the height argument is not a float or int
        IllegalArgumentError
            Raises a IllegalArgumentError if the units argument is not one of the
            following values: mm, in, metric, imperial, millimeters, inches, millimeter, or inch
        """

        width = _coerce_positive_number(canvas_width, "canvas_width")
        height = _coerce_positive_number(canvas_height, "canvas_height")

        if not isinstance(units, str):
            raise TypeError("The units argument should be a string")

        if units.lower() in ["mm", "metric", "millimeters", "millimeter"]:
            self._units = "mm"
        elif units.lower() in ["in", "imperial", "inches", "inch"]:
            self._units = "in"
        else:
            raise IllegalArgumentError(
                f"{units} is not a valid value for the units argument.  \
                                       Use mm, in, metric, or imperial."
            )

        super().__init__([(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)])

    @classmethod
    def create_from_dict(cls, data: dict) -> Canvas:
        """Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            Canvas: instance of the class.
        """
        canvas = cls(canvas_width=data["Canvas"]["width"], canvas_height=data["Canvas"]["height"], units=data["Canvas"]["units"])
        return canvas

    @property
    def width(self) -> float:
        """Readonly property for canvas width.

        Returns
        -------
        float
            Canvas width
        """
        return self._boundary_polygon.bounds[2]

    @property
    def height(self) -> float:
        """Readonly property for canvas height

        Returns
        -------
        float
            Canvas Height
        """
        return self._boundary_polygon.bounds[3]

    @property
    def units(self) -> str:
        """Readonly property for canvas unit of measure

        Returns
        -------
        str
            mm or in
        """
        return self._units

    @property
    def parameters(self) -> dict:
        """Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"Canvas": {"width": float(self.width), "height": float(self.height), "units": self.units}}
        return parameter_dict
