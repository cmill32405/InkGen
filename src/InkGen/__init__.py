"""Top-level package for InkGen."""

from .boundary import Boundary, Canvas
from .cad_component_groups import Zoning
from .component import Component, ComponentGroup, StandardDrawingComponent, TextComponent
from .document import Document, Layer, Layers
from .style import DrawingStyle, Font, Style, TextStyle
from .svg_generator import (
    ArcSVG,
    CircleSVG,
    ComponentGroupSVG,
    CubicBezierSVG,
    DocumentSVG,
    IncludeLayer,
    LineSVG,
    PathSVG,
    PolygonalSVG,
    QuadraticBezierSVG,
    RectangleSVG,
    RegularPolygonSVG,
    SVGComponent,
    TableSVG,
    TextSVG,
)
from .table import AutoFitRule, Table
from .text_fitter import (
    FitterShape,
    FittingResult,
    TextBlock,
    TextFitter,
    component_to_fitter_shape,
)
from .text_outline import outline_for_text

__version__ = "0.1.0"

__all__ = [
    "ArcSVG",
    "AutoFitRule",
    "Boundary",
    "Canvas",
    "CircleSVG",
    "Component",
    "ComponentGroup",
    "ComponentGroupSVG",
    "CubicBezierSVG",
    "Document",
    "DocumentSVG",
    "DrawingStyle",
    "FitterShape",
    "FittingResult",
    "Font",
    "IncludeLayer",
    "Layer",
    "Layers",
    "LineSVG",
    "PathSVG",
    "PolygonalSVG",
    "QuadraticBezierSVG",
    "RectangleSVG",
    "RegularPolygonSVG",
    "StandardDrawingComponent",
    "Style",
    "SVGComponent",
    "Table",
    "TableSVG",
    "TextBlock",
    "TextComponent",
    "TextFitter",
    "TextStyle",
    "Zoning",
    "component_to_fitter_shape",
    "outline_for_text",
]
