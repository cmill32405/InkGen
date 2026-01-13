# InkGen Architecture Diagrams

This document provides class diagrams for the InkGen architecture in both Markdown text format and Mermaid diagram format. The diagrams are based on the Draw.io source file and verified against the actual codebase.

**Note:** All Mermaid diagrams are available in separate files in the `diagrams/` directory:
- [base-classes.mmd](diagrams/base-classes.mmd) - Diagram 1: Base Classes
- [component-hierarchy.mmd](diagrams/component-hierarchy.mmd) - Complete Component Hierarchy
- [document-structure.mmd](diagrams/document-structure.mmd) - Diagram 2: Document Structure
- [table-structure.mmd](diagrams/table-structure.mmd) - Diagram 3: Table Structure
- [svg-components.mmd](diagrams/svg-components.mmd) - Diagram 4: SVG Components (simplified)
- [svg-generators.mmd](diagrams/svg-generators.mmd) - Complete SVG Generator Classes
- [text-fitting.mmd](diagrams/text-fitting.mmd) - Text Fitting Classes
- [utilities.mmd](diagrams/utilities.mmd) - Utility Classes

## Diagram 1: Base Classes

This diagram shows the core component hierarchy and style classes.

### Markdown Class Hierarchy

```
Component (base class)
├── id_iter: int (class variable)
├── _id: int
├── _component_type: str
├── __init__(): None
├── create_from_dict(dict): object (class method)
├── parameters: dict (read-only property)
├── id: int (read-only property)
└── component_type: str (read-only property)

DrawingComponent extends Component
├── _style: DrawingStyle
├── __init__(DrawingStyle): None
├── _check_style(DrawingStyle): None
├── create_from_dict(dict, DrawingStyle): object (class method)
├── parameters: dict (read-only property)
└── style: DrawingStyle (property with setter)

TextComponent extends Component
├── _text: str
├── _position: Tuple[float, float]
├── _style: TextStyle
├── __init__(str, Tuple[float, float], TextStyle): None
├── create_from_dict(dict, TextStyle): object (class method)
├── parameters: dict (read-only property)
├── text: str (property with setter)
├── position: Tuple[float, float] (property with setter)
└── style: TextStyle (property with setter)

Style (base class)
├── id_iter: int (class variable)
├── _id: int
├── _name: str
├── __init__(str): None
├── create_from_dict(dict): Style (class method)
├── parameters: dict (read-only property)
├── id: int (read-only property)
└── name: str (read-only property)

DrawingStyle extends Style
├── _stroke: str
├── _stroke_width: float
├── _fill: str
├── _stroke_opacity: float
├── _fill_opacity: float
├── __init__(str, str, float, str, float, float): None
├── create_from_dict(dict): DrawingStyle (class method)
├── parameters: dict (read-only property)
├── stroke: str (property with setter)
├── stroke_width: float (property with setter)
├── fill: str (property with setter)
├── stroke_opacity: float (property with setter)
└── fill_opacity: float (property with setter)

TextStyle extends Style
├── font: Font
├── color: str
├── superscript: bool
├── subscript: bool
├── text_align: str
├── line_spacing: float
├── __init__(str, Font): None
├── create_from_dict(dict): TextStyle (class method)
└── parameters: dict (read-only property)

Font
├── _platform: str
├── _font_paths: List[str]
├── _font_manager: font_manager
├── _font: int
├── __init__(...): None
├── create_from_dict(dict): Font (class method)
├── parameters: dict (read-only property)
├── configuration: str (read-only property)
├── family: str (property with setter)
├── font_file: str (read-only property)
├── style: str (property with setter)
├── variant: str (property with setter)
├── stretch: Union[str, int] (property with setter)
├── weight: Union[str, int] (property with setter)
└── size: Union[str, float] (property with setter)
```

### Mermaid Diagram

See [diagrams/base-classes.mmd](diagrams/base-classes.mmd) for the Mermaid diagram.

## Diagram 2: Document Structure

This diagram shows the document, layer, and boundary classes.

### Markdown Class Hierarchy

```
Boundary
├── _outer: bool
├── _boundary_polygon: Polygon
├── __init__(list[tuple[float, float]], bool): None
├── create_from_dict(dict): Boundary (class method)
├── parameters: dict (read-only property)
├── boundary_points: list[tuple[float, float]] (read-only property)
├── boundary_type: str (read-only property)
└── boundary_check(list[tuple[float, float]], bool): bool

Canvas extends Boundary
├── _width: float
├── _height: float
├── _units: str
├── __init__(float, float, str): None
├── create_from_dict(dict): Canvas (class method)
├── parameters: dict (read-only property)
├── width: float (read-only property)
├── height: float (read-only property)
└── units: str (read-only property)

Layer
├── id_iter: int (class variable)
├── _id: int
├── _name: str
├── _canvas: Canvas
├── _model: bool
├── _group_names: Dict[str, int]
├── _component_groups: Dict[int, ComponentGroup]
├── _group_boundaries: Dict[int, Boundary]
├── _group_collision_settings: Dict[str, dict]
├── __init__(str, Canvas, bool): None
├── create_from_dict(dict, dict): Layer (class method)
├── parameters: dict (read-only property)
├── _create_boundary(ComponentGroup): None
├── _check_bounds(ComponentGroup, bool): bool
├── add_component_group(ComponentGroup, bool, bool): None
├── remove_component_group(int | str): None
├── component_groups: Dict[str, int] (read-only property)
├── model: bool (read-only property)
├── group(int): ComponentGroup
├── layer_id: int (read-only property)
├── layer_name: str (read-only property)
└── canvas: Canvas (read-only property)

Layers
├── _canvas: Canvas
├── _layers: Dict[int, Layer]
├── _layer_name_to_id_map: Dict[str, int]
├── __init__(Canvas): None
├── create_from_dict(dict, dict): Layers (class method)
├── parameters: dict (read-only property)
├── add_layer(Layer): None
├── remove_layer(str | int): None
├── layer(str | int): Layer
└── layers: list[str] (read-only property)

Document
├── _canvas: Canvas
├── _pages: Dict[int, Layers]
├── __init__(Canvas): None
├── create_from_dict(dict, dict): Document (class method)
├── parameters: dict (read-only property)
├── add_page(int, Layers): None
├── remove_page(int): None
├── page(int): Layers
└── pages: int (read-only property)

ComponentGroup
├── _group_label: str
├── _components: List[Component]
├── __init__(str): None
├── create_from_dict(dict, dict): ComponentGroup (class method)
├── parameters: dict (read-only property)
├── add_component(Component): None
├── remove_component(int): None
├── component(int): Component
├── group_id: int (read-only property)
├── group_label: str (read-only property)
├── points: list[tuple[float, float]] (read-only property)
├── bbox: tuple (read-only property)
└── convex_hull: list[tuple[float, float]] (read-only property)
```

### Mermaid Diagram

See [diagrams/document-structure.mmd](diagrams/document-structure.mmd) for the Mermaid diagram.

## Diagram 3: Table Structure

This diagram shows the table, row, column, and cell classes.

### Markdown Class Hierarchy

```
Table
├── _position: Tuple[float, float]
├── _rows: List[Row]
├── _columns: List[Column]
├── _matrix: List[List[Cell]]
├── _padding: Tuple[float, float, float, float]
├── _auto_fit: bool
├── _autofit_queue: list
├── __init__(Tuple[float, float], bool): None
├── create_from_dict(dict): Table (class method)
├── parameters: dict (read-only property)
├── cell_padding: Tuple[float, float, float, float] (property with setter)
├── padding_top: float (read-only property)
├── padding_right: float (read-only property)
├── padding_bottom: float (read-only property)
├── padding_left: float (read-only property)
├── add_row(int, float): Row
├── add_column(int, float): Column
├── cell(int, int): Cell
├── row_cells(int): Tuple[Cell, ...]
├── column_cells(int): Tuple[Cell, ...]
├── cell_bounds(int, int): Tuple[Tuple[float, float], float, float]
├── position: Tuple[float, float] (property with setter)
├── width: float (read-only property)
├── height: float (read-only property)
├── points: list[tuple[float, float]] (read-only property)
├── bbox: tuple (read-only property)
├── convex_hull: list[tuple[float, float]] (read-only property)
├── autofit: bool (property with setter)
├── autofit_queue: list (read-only property)
├── clear_autofit_queue(): None
├── rows: Tuple[Row, ...] (read-only property)
├── columns: Tuple[Column, ...] (read-only property)
├── row_count: int (read-only property)
└── column_count: int (read-only property)

Row
├── _table: Table
├── _height: float
├── _height_rule: AutoFitRule
├── _cells: List[Cell]
├── __init__(Table, float): None
├── table: Table (read-only property)
├── cells: Tuple[Cell, ...] (read-only property)
├── column(int): Cell
├── height: float (property with setter)
└── height_rule: AutoFitRule (property with setter)

Column
├── _table: Table
├── _width: float
├── _width_rule: AutoFitRule
├── _cells: List[Cell]
├── __init__(Table, float): None
├── table: Table (read-only property)
├── cells: Tuple[Cell, ...] (read-only property)
├── row(int): Cell
├── width: float (property with setter)
└── width_rule: AutoFitRule (property with setter)

Cell
├── _table: Table
├── _row_index: int
├── _column_index: int
├── _merged: bool
├── _merge_start: Tuple[int, int]
├── _merge_end: Tuple[int, int]
├── _vertical_alignment: str
├── _paragraph_text: List[str]
├── _paragraph_styles: List[str | None]
├── __init__(Table, int, int): None
├── table: Table (read-only property)
├── row_index: int (read-only property)
├── column_index: int (read-only property)
├── merged: bool (read-only property)
├── merge_start: Tuple[int, int] (read-only property)
├── merge_end: Tuple[int, int] (read-only property)
├── vertical_alignment: str (property with setter)
├── paragraphs: List[str] (read-only property)
├── paragraph_styles: List[str | None] (read-only property)
├── text: str (read-only property)
├── add_paragraph(str, str): None
├── remove_paragraph(int): None
├── paragraph(int): str
└── merge(Cell): Cell
```

### Mermaid Diagram

See [diagrams/table-structure.mmd](diagrams/table-structure.mmd) for the Mermaid diagram.

## Diagram 4: SVG Components

This diagram shows the SVG generation classes that implement the DrawingGeneratorInterface.

### Markdown Class Hierarchy

```
DrawingGeneratorInterface (abstract interface)
└── generate_svg(): str

WidthHeightDrawingComponent extends DrawingComponent
├── _position: Tuple[float, float]
├── _width: float
├── _height: float
├── __init__(Tuple[float, float], float, float, DrawingStyle): None
├── create_from_dict(dict, DrawingStyle): object (class method)
├── parameters: dict (read-only property)
├── position: Tuple[float, float] (property with setter)
├── width: float (property with setter)
└── height: float (property with setter)

StandardDrawingComponent extends DrawingComponent
├── _point_1: Tuple[float, float]
├── _point_2: Tuple[float, float]
├── __init__(Tuple[float, float], Tuple[float, float], DrawingStyle): None
├── _check_inputs(Point, Point): None
├── create_from_dict(dict, DrawingStyle): object (class method)
├── parameters: dict (read-only property)
├── point_1: Tuple[float, float] (property with setter)
├── point_2: Tuple[float, float] (property with setter)
├── points: List[Tuple[float, float]] (read-only property)
└── bbox: Tuple[Tuple[float, float], Tuple[float, float]] (read-only property)

RegularPolygonDrawingComponent extends DrawingComponent
├── _center_position: Tuple[float, float]
├── _sides: int
├── _radius: float
├── _angle: float
├── _round: float
├── __init__(Tuple[float, float], int, float, float, float, float, DrawingStyle): None
├── create_from_dict(dict, DrawingStyle): object (class method)
├── parameters: dict (read-only property)
├── sides: int (property with setter)
├── center_position: Tuple[float, float] (property with setter)
├── radius: float (property with setter)
├── angle: float (property with setter)
├── corner_radius: float (property with setter)
├── points: List[Tuple[float, float]] (read-only property)
└── bbox: Tuple[Tuple[float, float], Tuple[float, float]] (read-only property)

RectangleSVG extends WidthHeightDrawingComponent, implements DrawingGeneratorInterface
├── _corner_radius: float
├── __init__(Tuple[float, float], float, float, float, DrawingStyle): None
├── create_from_dict(dict, DrawingStyle): RectangleSVG (class method)
├── parameters: dict (read-only property)
├── generate_svg(): str
└── corner_radius: float (property with setter)

LineSVG extends StandardDrawingComponent, implements DrawingGeneratorInterface
├── __init__(Tuple[float, float], float, float, DrawingStyle): None
├── create_from_dict(dict, DrawingStyle): LineSVG (class method)
├── parameters: dict (read-only property)
└── generate_svg(): str

RegularPolygonSVG extends RegularPolygonDrawingComponent, implements DrawingGeneratorInterface
├── __init__(int, Tuple[float, float], float, float, float, DrawingStyle): None
├── create_from_dict(dict, DrawingStyle): RegularPolygonSVG (class method)
├── parameters: dict (read-only property)
└── generate_svg(): str

TextSVG extends TextComponent, implements DrawingGeneratorInterface
├── __init__(str, Tuple[float, float], TextStyle): None
├── create_from_dict(dict, TextStyle): TextSVG (class method)
├── parameters: dict (read-only property)
└── generate_svg(): str

ComponentGroupSVG extends ComponentGroup, implements LabelGenerator, SegmentGenerator
├── __init__(str): None
├── create_from_dict(dict, dict): ComponentGroupSVG (class method)
├── parameters: dict (read-only property)
├── generate_svg(): str
├── generate_label(): dict
└── generate_segmentation_mask(): dict

TableSVG extends ComponentGroupSVG
├── _table: Table
├── _border_style: DrawingStyle
├── _text_styles: dict[str, TextStyle]
├── __init__(Table, str, DrawingStyle, dict, ...): None
├── from_table(Table, ...): TableSVG (class method)
├── table: Table (read-only property)
└── generate_svg(): str

DocumentSVG extends Document
├── __init__(Canvas): None
├── create_from_dict(dict, dict): DocumentSVG (class method)
├── parameters: dict (read-only property)
└── create_svg(str, ...): None
```

## Diagram 5: Complete Component Hierarchy

This diagram shows the full inheritance tree for all component classes, including intermediate classes and path-related components.

### Markdown Class Hierarchy

```
Component (base class)
├── DrawingComponent extends Component
│   ├── StandardDrawingComponent extends DrawingComponent
│   │   ├── SingleDimensionDrawingComponent extends StandardDrawingComponent
│   │   ├── WidthHeightDrawingComponent extends StandardDrawingComponent
│   │   └── PolarCoordinateDrawingComponent extends StandardDrawingComponent
│   │       └── RegularPolygonDrawingComponent extends PolarCoordinateDrawingComponent
│   ├── PolygonalDrawingComponent extends DrawingComponent
│   ├── Arc extends DrawingComponent
│   ├── QuadraticBezier extends DrawingComponent
│   ├── CubicBezier extends DrawingComponent
│   └── Path extends DrawingComponent
│       └── uses PathCommand
├── TextComponent extends Component
└── ComponentGroup extends Component

PathCommand (standalone)
├── _type: str
├── _points: List[Tuple[float, float]]
├── type: str (property with setter)
└── points: List[Tuple[float, float]] (property with setter)
```

### Mermaid Diagram

See [diagrams/component-hierarchy.mmd](diagrams/component-hierarchy.mmd) for the complete component hierarchy diagram.

## Diagram 6: Complete SVG Generator Classes

This diagram shows all SVG generation classes including all shape types and interfaces.

### Markdown Class Hierarchy

```
DrawingGeneratorInterface (abstract interface)
└── generate_svg(): str

LabelGenerator (abstract interface)
└── generate_label(): dict

SegmentGenerator (abstract interface)
└── generate_segmentation_mask(): dict

IncludeLayer (enum)
├── BASE
├── LABEL
└── MASK

SVG Classes implementing DrawingGeneratorInterface:
├── RectangleSVG extends WidthHeightDrawingComponent
├── CircleSVG extends SingleDimensionDrawingComponent
├── LineSVG extends StandardDrawingComponent
├── RegularPolygonSVG extends RegularPolygonDrawingComponent
├── PolygonalSVG extends PolygonalDrawingComponent
├── ArcSVG extends Arc
├── QuadraticBezierSVG extends QuadraticBezier
├── CubicBezierSVG extends CubicBezier
├── PathSVG extends Path
├── TextSVG extends TextComponent
├── SVGComponent extends Component
└── ComponentGroupSVG extends ComponentGroup, implements LabelGenerator, SegmentGenerator
    └── TableSVG extends ComponentGroupSVG
```

### Mermaid Diagram

See [diagrams/svg-generators.mmd](diagrams/svg-generators.mmd) for the complete SVG generator classes diagram.

## Diagram 7: Text Fitting Classes

This diagram shows the text fitting utilities for fitting text into shapes.

### Markdown Class Hierarchy

```
FitterShape (dataclass)
├── polygon: ShapelyPolygon
├── line_thickness_range: Tuple[float, float]
└── padding: float

TextBlock (dataclass)
├── text: str
├── font_path: str
├── font_size_range: Tuple[int, int]
├── min_font_size_px: int
└── max_line_width: float | None

FittingResult (dataclass)
├── original_shape: FitterShape (read-only)
├── fitted_text_lines: List[str] (read-only)
├── line_positions: List[Tuple[float, float]] (read-only)
├── line_widths: List[float] (read-only)
├── font_size: float (read-only)
├── final_line_thickness: float (read-only)
├── text_geometry: BaseGeometry (read-only)
├── text_convex_hull: ShapelyPolygon (read-only)
└── text_bounding_box: ShapelyPolygon (read-only property)

TextFitter
├── rng: Random
├── _pil_font_cache: Dict
├── __init__(Random): None
├── component_to_fitter_shape(Component): FitterShape
└── fit(TextBlock, FitterShape): FittingResult
```

### Mermaid Diagram

See [diagrams/text-fitting.mmd](diagrams/text-fitting.mmd) for the text fitting classes diagram.

## Diagram 8: Utility Classes

This diagram shows utility classes for SVG processing and CAD components.

### Markdown Class Hierarchy

```
FlattenedPath (dataclass)
├── d: str (read-only)
└── style: str | None (read-only)

FlattenedSVG (dataclass)
├── paths: List[FlattenedPath] (read-only)
├── bbox: Tuple[Tuple[float, float], Tuple[float, float]] (read-only)
├── width: float | None (read-only)
└── height: float | None (read-only)

Zoning
├── _canvas: Canvas
├── _line_style: DrawingStyle
├── _text_style: TextStyle
├── _group: ComponentGroup
├── _parameters: Dict
├── __init__(Canvas, DrawingStyle, TextStyle, **kwargs): None
├── group: ComponentGroup (read-only property)
└── parameters: dict (read-only property)
```

### Mermaid Diagram

See [diagrams/utilities.mmd](diagrams/utilities.mmd) for the utility classes diagram.
```
