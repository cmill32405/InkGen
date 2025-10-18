"""Top-level package for InkGen."""

from .boundary import Boundary, Canvas
from .component import Component, ComponentGroup, StandardDrawingComponent, TextComponent
from .document import Document, Layer, Layers
from .style import DrawingStyle, Font, Style, TextStyle
from .svg_generator import DocumentSVG

__all__ = [
    "Boundary",
    "Canvas",
    "Component",
    "ComponentGroup",
    "Document",
    "DocumentSVG",
    "DrawingStyle",
    "Font",
    "Layer",
    "Layers",
    "StandardDrawingComponent",
    "Style",
    "TextComponent",
    "TextStyle",
]
