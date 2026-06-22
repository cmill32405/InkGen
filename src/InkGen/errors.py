"""Project-specific exceptions for InkGen public contracts."""


class IllegalArgumentError(ValueError):
    """Raised when a public argument has an unsupported value."""

    pass


class InvalidConvexHull(ValueError):
    """Raised when boundary points cannot define a valid convex hull."""

    pass


class InvalidPolygonError(ValueError):
    """Raised when polygon coordinates violate the component contract."""

    pass


class InvalidComponentID(ValueError):
    """Raised when a component identifier does not exist in its group."""

    pass


class InvalidComponentGroupID(ValueError):
    """Raised when a component-group identifier does not exist in its layer."""

    pass


class ComponentGroupCollision(ValueError):
    """Raised when a component group overlaps another group unexpectedly."""

    pass


class ComponentGroupOffCanvas(ValueError):
    """Raised when a component group extends beyond its canvas boundary."""

    pass


class IncompatibleCanvas(ValueError):
    """Raised when documents, pages, or layers use incompatible canvases."""

    pass
