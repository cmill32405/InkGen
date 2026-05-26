"""Top-level package for InkGen."""

from .boundary import Boundary, Canvas
from .cad_component_groups import Zoning
from .component import Component, ComponentGroup, StandardDrawingComponent, TextComponent
from .document import Document, Layer, Layers
from .document_outputs import DocumentOutputFormat, FlowDocument
from .drawing_components import (
    ArcDrawing,
    CircleDrawing,
    CubicBezierDrawing,
    DrawingComponentGroup,
    LineDrawing,
    OutputFormat,
    PathDrawing,
    PolygonalDrawing,
    QuadraticBezierDrawing,
    RectangleDrawing,
    RegularPolygonDrawing,
    TextDrawing,
)
from .dxf_generator import DXFDocument, DXFRenderContext
from .paragraph import LineSpacingRule, Paragraph, ParagraphAlignment, ParagraphLine, TabStop
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
    "ArcDrawing",
    "AutoFitRule",
    "Boundary",
    "Canvas",
    "CircleSVG",
    "CircleDrawing",
    "Component",
    "ComponentGroup",
    "ComponentGroupSVG",
    "CubicBezierSVG",
    "CubicBezierDrawing",
    "Document",
    "DocumentOutputFormat",
    "DocumentSVG",
    "DrawingStyle",
    "DrawingComponentGroup",
    "DXFDocument",
    "DXFRenderContext",
    "FlowDocument",
    "FitterShape",
    "FittingResult",
    "Font",
    "IncludeLayer",
    "Layer",
    "Layers",
    "LineSVG",
    "LineDrawing",
    "LineSpacingRule",
    "OutputFormat",
    "PathSVG",
    "PathDrawing",
    "Paragraph",
    "ParagraphAlignment",
    "ParagraphLine",
    "PolygonalSVG",
    "PolygonalDrawing",
    "QuadraticBezierSVG",
    "QuadraticBezierDrawing",
    "RectangleSVG",
    "RectangleDrawing",
    "RegularPolygonSVG",
    "RegularPolygonDrawing",
    "StandardDrawingComponent",
    "Style",
    "SVGComponent",
    "Table",
    "TableSVG",
    "TabStop",
    "TextBlock",
    "TextComponent",
    "TextFitter",
    "TextStyle",
    "TextSVG",
    "TextDrawing",
    "Zoning",
    "component_to_fitter_shape",
    "outline_for_text",
]
