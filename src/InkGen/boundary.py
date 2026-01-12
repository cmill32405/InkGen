"""Classes for defining and checking boundaries such as the size of a sheet."""

from __future__ import annotations

from shapely import MultiPoint, Polygon, get_coordinates

from InkGen.errors import IllegalArgumentError, InvalidConvexHull


class Boundary:
    """
        Class for storing boundary information for constraining component points.
    """

    def __init__(self, hull: list[tuple[float, float]], outer_boundary: bool = False) -> None:
        """Create a boundary wrapper around a convex hull."""
        if not isinstance(outer_boundary, bool):
            raise TypeError("The outer_boundary argument is required to be a boolean.")

        self._outer = outer_boundary
        self._boundary_polygon = Polygon(hull)

        if not self._hull_check():
            raise InvalidConvexHull("The hull argument is not a valid convex hull")

    @classmethod
    def create_from_dict(cls, data: dict) -> Boundary:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            Boundary: instance of the class.
        """
        boundary = cls(data['Boundary']['hull'], data['Boundary']['outer_boundary'])
        return boundary

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"Boundary":
                       {"hull": self.boundary_points,
                        "outer_boundary": self._outer}}
        return parameter_dict

    def _hull_check(self) -> bool:
        """Verify that the boundary polygon is a valid convex hull.

        Returns:
            bool: True if the polygon is a valid convex hull, False otherwise.
        """
        hull = get_coordinates(self._boundary_polygon.convex_hull)
        for point in get_coordinates(self._boundary_polygon):
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
        coordinates = []
        for coord in get_coordinates(self._boundary_polygon):
            coordinates.append((coord[0], coord[1]))
        return coordinates[:-1]

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

        points_geometry = MultiPoint(points)
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

    def __init__(self,
                 canvas_width: float | int,
                 canvas_height: float | int,
                 units: str = "mm") -> None:
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

        if not isinstance(canvas_width, (int, float)):
            raise TypeError("The canvas_width argument should be a float or int")

        if not isinstance(canvas_height, (int, float)):
            raise TypeError("The canvas_height argument should be a float or int")

        if units.lower() in ["mm", "metric", "millimeters", "millimeter"]:
            self._units = "mm"
        elif units.lower() in ["in", "imperial", "inches", "inch"]:
            self._units = "in"
        else:
            raise IllegalArgumentError(f"{units} is not a valid value for the units argument.  \
                                       Use mm, in, metric, or imperial.")

        super().__init__([(0,0),
                          (canvas_width, 0),
                          (0, canvas_height),
                          (canvas_width, canvas_height)])

    @classmethod
    def create_from_dict(cls, data: dict) -> Canvas:
        """ Class method to recreate the object from its serialization dict.

        Args:
            data (dict): Dictionary created via obj.parameters property.

        Returns:
            Canvas: instance of the class.
        """
        canvas = cls(canvas_width=data["Canvas"]["width"],
                        canvas_height=data["Canvas"]["height"],
                        units=data["Canvas"]["units"])
        return canvas

    @property
    def width(self) -> float:
        """ Readonly property for canvas width.

        Returns
        -------
        float
            Canvas width
        """
        extrema = get_coordinates(self._boundary_polygon)[3]
        return extrema[0]

    @property
    def height(self) -> float:
        """ Readonly property for canvas height

        Returns
        -------
        float
            Canvas Height
        """
        extrema = get_coordinates(self._boundary_polygon)[3]
        return extrema[1]

    @property
    def units(self) -> str:
        """ Readonly property for canvas unit of measure

        Returns
        -------
        str
            mm or in
        """
        return self._units

    @property
    def parameters(self) -> dict:
        """ Parameters for the object as a dictionary for serialization.

        Returns:
            dict: dictionary with class name as top level key, that
            includes a dictionary with each parameter name as key and
            value as value.
        """
        parameter_dict = {"Canvas":
                       {"width": float(self.width),
                        "height": float(self.height),
                        "units": self.units}}
        return parameter_dict
