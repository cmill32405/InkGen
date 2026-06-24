from __future__ import annotations

from enum import Enum
from math import isfinite

from InkGen.component import Component


class AutoFitRule(Enum):
    """Strategies for reconciling overflowing table content."""

    EXPAND = "EXPAND"
    FIT = "FIT"
    CUT = "CUT"
    FIXED = "FIXED"


class Table(Component):
    """Abstract description of a table embedded in a document layout."""

    def __init__(
        self,
        *,
        position: tuple[float, float] = (0.0, 0.0),
        autofit: bool = False,
    ) -> None:
        super().__init__()
        self._position = _normalize_position(position)
        self._auto_fit = _normalize_bool(autofit, name="autofit")
        self._autofit_queue: list[tuple[tuple[int, int], AutoFitRule, AutoFitRule]] = []
        self._autofit_suppressed = False

        self._rows: list[Row] = []
        self._columns: list[Column] = []
        self._matrix: list[list[Cell]] = []
        self._padding = (1.0, 1.0, 1.0, 1.0)
        self.cell_padding = 1.0

    @property
    def cell_padding(self) -> tuple[float, float, float, float]:
        """Cell padding as a 4-tuple (top, right, bottom, left).

        Returns:
            Tuple of four floats representing padding in each direction.
        """
        return self._padding

    @cell_padding.setter
    def cell_padding(self, value: float | tuple[float, float, float, float] | list[float]):
        """Set cell padding for all cells.

        Args:
            value: Either a single float (applied to all sides) or a 4-tuple/list
                   of floats representing (top, right, bottom, left) padding.

        Raises:
            ValueError: If value is not a float or a 4-element sequence.
        """
        self._padding = self._normalize_padding(value)

    @property
    def padding_top(self) -> float:
        """Top padding value.

        Returns:
            Top padding in document units.
        """
        return self._padding[0]

    @property
    def padding_right(self) -> float:
        """Right padding value.

        Returns:
            Right padding in document units.
        """
        return self._padding[1]

    @property
    def padding_bottom(self) -> float:
        """Bottom padding value.

        Returns:
            Bottom padding in document units.
        """
        return self._padding[2]

    @property
    def padding_left(self) -> float:
        """Left padding value.

        Returns:
            Left padding in document units.
        """
        return self._padding[3]

    @staticmethod
    def _normalize_padding(value: float | tuple[float, float, float, float] | list[float]) -> tuple[float, float, float, float]:
        return _normalize_padding(value)

    # ------------------------------------------------------------------
    # Core structural helpers
    # ------------------------------------------------------------------
    def add_row(self, *, location: int | None = None, height: float = 10.0) -> Row:
        """Insert a new row at *location* (default end) with the supplied height."""
        insert_at = self._validate_insert_index(location, self.row_count)
        row = Row(self, height)
        new_cells = [Cell(self, insert_at, col_idx) for col_idx in range(self.column_count)]

        self._rows.insert(insert_at, row)
        self._matrix.insert(insert_at, new_cells)
        self._sync_views()
        self._reindex_cells()
        return row

    def add_column(self, *, location: int | None = None, width: float = 10.0) -> Column:
        """Insert a new column at *location* (default end) with the supplied width."""
        insert_at = self._validate_insert_index(location, self.column_count)
        column = Column(self, width)
        if self.row_count:
            for row_idx in range(self.row_count):
                self._matrix[row_idx].insert(insert_at, Cell(self, row_idx, insert_at))
        self._columns.insert(insert_at, column)
        self._sync_views()
        self._reindex_cells()
        return column

    def cell(self, row: int, column: int) -> Cell:
        """Get a cell at the specified row and column.

        Args:
            row: Zero-based row index.
            column: Zero-based column index.

        Returns:
            Cell object at the specified position.

        Raises:
            IndexError: If row or column is out of bounds.
        """
        return self._matrix[row][column]

    def row_cells(self, row: int) -> tuple[Cell, ...]:
        """Get all cells in a specific row.

        Args:
            row: Zero-based row index.

        Returns:
            Tuple of all Cell objects in the row.
        """
        return tuple(self._matrix[row])

    def column_cells(self, column: int) -> tuple[Cell, ...]:
        """Get all cells in a specific column.

        Args:
            column: Zero-based column index.

        Returns:
            Tuple of all Cell objects in the column.
        """
        return tuple(self._matrix[row][column] for row in range(self.row_count))

    def cell_bounds(
        self, row: int, column: int
    ) -> tuple[tuple[float, float], float, float]:
        """Return the top-left coordinate, width, and height for a cell."""
        if not (0 <= row < self.row_count and 0 <= column < self.column_count):
            raise IndexError("Cell coordinates outside table dimensions")
        x = self._position[0] + sum(self.columns[idx].width for idx in range(column))
        y = self._position[1] + sum(self.rows[idx].height for idx in range(row))
        width = float(self.columns[column].width)
        height = float(self.rows[row].height)
        return (x, y), width, height

    # ------------------------------------------------------------------
    # Geometry and layout
    # ------------------------------------------------------------------
    @property
    def position(self) -> tuple[float, float]:
        """Top-left corner position of the table.

        Returns:
            (x, y) coordinates of the table origin.
        """
        return self._position

    @position.setter
    def position(self, value: tuple[float, float]) -> None:
        """Set the table position.

        Args:
            value: (x, y) coordinates for the top-left corner.
        """
        self._position = _normalize_position(value)

    @property
    def width(self) -> float:
        """Total width of the table.

        Returns:
            Sum of all column widths in document units.
        """
        return sum(column.width for column in self._columns)

    @property
    def height(self) -> float:
        """Total height of the table.

        Returns:
            Sum of all row heights in document units.
        """
        return sum(row.height for row in self._rows)

    @property
    def points(self) -> list[tuple[float, float]]:
        """Corner points of the table bounding box.

        Returns:
            List of (x, y) coordinates for the four corners, or a single point
            if the table has zero width or height.
        """
        x, y = self._position
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return [(x, y)]
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

    @property
    def bbox(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Bounding box of the table.

        Returns:
            Tuple of ((min_x, min_y), (max_x, max_y)) coordinates.
        """
        x, y = self._position
        return ((x, y), (x + self.width, y + self.height))

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """Convex hull points of the table.

        Returns:
            List of (x, y) coordinates forming the convex hull (same as points
            for a rectangular table).
        """
        return self.points.copy()

    # ------------------------------------------------------------------
    # Auto-fit
    # ------------------------------------------------------------------
    @property
    def autofit(self) -> bool:
        """Whether automatic fitting is enabled.

        Returns:
            True if autofit is enabled, False otherwise.
        """
        return self._auto_fit

    @autofit.setter
    def autofit(self, state: bool) -> None:
        """Enable or disable automatic fitting.

        Args:
            state: True to enable autofit, False to disable.
        """
        self._auto_fit = _normalize_bool(state, name="autofit")

    @property
    def autofit_queue(self) -> list[tuple[tuple[int, int], AutoFitRule, AutoFitRule]]:
        """Queue of cells pending autofit processing.

        Returns:
            List of ((row, col), row_rule, col_rule) tuples for cells that
            need autofit processing.
        """
        return list(self._autofit_queue)

    def clear_autofit_queue(self) -> None:
        """Clear all pending autofit operations from the queue."""
        self._autofit_queue.clear()

    def _register_autofit(self, row_index: int, column_index: int) -> None:
        if not self._auto_fit or self._autofit_suppressed:
            return
        row_rule = self.rows[row_index].height_rule if self.rows else AutoFitRule.FIXED
        column_rule = self.columns[column_index].width_rule if self.columns else AutoFitRule.FIXED
        entry = ((row_index, column_index), row_rule, column_rule)
        self._autofit_queue.append(entry)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    @property
    def parameters(self) -> dict:
        return {
            "Table": {
                "position": list(self._position),
                "auto_fit": self._auto_fit,
                "rows": [row.parameters for row in self._rows],
                "columns": [column.parameters for column in self._columns],
                "padding": list(self._padding),
                "matrix": [
                    [cell.parameters for cell in row]
                    for row in self._matrix
                ],
            }
        }

    @classmethod
    def create_from_dict(cls, data: dict) -> Table:
        payload = data["Table"] if "Table" in data else data
        table = cls(position=tuple(payload["position"]), autofit=payload["auto_fit"])
        table.cell_padding = payload.get("padding", table.cell_padding)
        table._autofit_suppressed = True
        for column_data in payload.get("columns", []):
            column = table.add_column(width=column_data["width"])
            column.width_rule = AutoFitRule(column_data["width_rule"])
        for row_data in payload.get("rows", []):
            row = table.add_row(height=row_data["height"])
            row.height_rule = AutoFitRule(row_data["height_rule"])
        for row_index, row_payload in enumerate(payload.get("matrix", [])):
            for column_index, cell_payload in enumerate(row_payload):
                cell = table.cell(row_index, column_index)
                for paragraph in cell_payload.get("paragraphs", []):
                    cell._append_paragraph(
                        paragraph["text"],
                        paragraph.get("style_id"),
                        trigger_autofit=False,
                    )
                cell._merged = cell_payload.get("merged", False)
                cell._merge_start = tuple(cell_payload.get("merge_start", (row_index, column_index)))
                cell._merge_end = tuple(cell_payload.get("merge_end", (row_index, column_index)))
                cell.vertical_alignment = cell_payload.get("vertical_alignment", "top")
        table._autofit_suppressed = False
        table.clear_autofit_queue()
        return table

    # ------------------------------------------------------------------
    # Collection accessors
    # ------------------------------------------------------------------
    @property
    def rows(self) -> tuple[Row, ...]:
        """All rows in the table.

        Returns:
            Tuple of Row objects.
        """
        return tuple(self._rows)

    @property
    def columns(self) -> tuple[Column, ...]:
        """All columns in the table.

        Returns:
            Tuple of Column objects.
        """
        return tuple(self._columns)

    @property
    def row_count(self) -> int:
        """Number of rows in the table.

        Returns:
            Total row count.
        """
        return len(self._rows)

    @property
    def column_count(self) -> int:
        """Number of columns in the table.

        Returns:
            Total column count.
        """
        return len(self._columns)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _validate_insert_index(self, location: int | None, upper: int) -> int:
        if location is None:
            return upper
        if not 0 <= location <= upper:
            raise IndexError("Insert location outside valid range")
        return location

    def _sync_views(self) -> None:
        for row_index, row in enumerate(self._rows):
            row._set_cells(self._matrix[row_index])
        for column_index, column in enumerate(self._columns):
            column._set_cells([self._matrix[row][column_index] for row in range(self.row_count)])

    def _reindex_cells(self) -> None:
        for row_index, row in enumerate(self._matrix):
            for column_index, cell in enumerate(row):
                cell._set_position(row_index, column_index)


def _normalize_padding(value: float | tuple[float, float, float, float] | list[float]) -> tuple[float, float, float, float]:
    """Normalize padding value to a 4-tuple.

    Args:
        value: Either a single float (applied to all sides) or a 4-tuple/list of floats.

    Returns:
        A 4-tuple of floats representing (top, right, bottom, left) padding.

    Raises:
        ValueError: If value is not a float or a 4-element sequence.
    """
    if isinstance(value, bool):
        raise TypeError("Padding must be numeric")
    if isinstance(value, (int, float)):
        pad = _coerce_finite_float(value, name="Padding", allow_negative=False)
        return (pad, pad, pad, pad)
    if isinstance(value, (tuple, list)) and len(value) == 4:
        return tuple(
            _coerce_finite_float(v, name="Padding", allow_negative=False)
            for v in value
        )  # type: ignore[arg-type]
    raise ValueError("Padding must be a float or an iterable of four floats")


def _normalize_position(value: tuple[float, float]) -> tuple[float, float]:
    """Normalize a table origin to finite numeric coordinates."""
    if isinstance(value, (str, bytes)):
        raise TypeError("Table position must be a two-value numeric sequence")
    try:
        x, y = value
    except (TypeError, ValueError) as exc:
        raise ValueError("Table position must contain exactly two values") from exc
    return (
        _coerce_finite_float(x, name="Table position"),
        _coerce_finite_float(y, name="Table position"),
    )


def _normalize_bool(value: object, *, name: str) -> bool:
    """Normalize a public table boolean option without truthiness coercion."""
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool")
    return value


def _coerce_finite_float(value: float, *, name: str, allow_negative: bool = True) -> float:
    """Coerce a public table dimension value into a finite float."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be numeric") from exc
    if not isfinite(number):
        raise ValueError(f"{name} must be finite")
    if not allow_negative and number < 0:
        raise ValueError(f"{name} must be non-negative")
    return number


class Row:

    """Row metadata wrapper."""

    def __init__(self, table: Table, height: float) -> None:
        self._table = table
        self._height = _coerce_finite_float(height, name="Row height", allow_negative=False)
        self._height_rule = AutoFitRule.EXPAND
        self._cells: list[Cell] = []

    @property
    def table(self) -> Table:
        """Parent table containing this row.

        Returns:
            Table instance that owns this row.
        """
        return self._table

    @property
    def cells(self) -> tuple[Cell, ...]:
        """All cells in this row.

        Returns:
            Tuple of Cell objects in the row.
        """
        return tuple(self._cells)

    def column(self, index: int) -> Cell:
        """Get a cell at a specific column index.

        Args:
            index: Zero-based column index.

        Returns:
            Cell object at the specified column.

        Raises:
            IndexError: If index is out of bounds.
        """
        return self._cells[index]

    @property
    def height(self) -> float:
        """Row height in document units.

        Returns:
            Height value.
        """
        return self._height

    @height.setter
    def height(self, value: float) -> None:
        """Set the row height.

        Args:
            value: New height value (must be non-negative).

        Raises:
            ValueError: If value is negative.
        """
        self._height = _coerce_finite_float(value, name="Row height", allow_negative=False)

    @property
    def height_rule(self) -> AutoFitRule:
        """Autofit rule for row height adjustment.

        Returns:
            Current AutoFitRule for this row.
        """
        return self._height_rule

    @height_rule.setter
    def height_rule(self, rule: AutoFitRule) -> None:
        """Set the autofit rule for row height.

        Args:
            rule: AutoFitRule to apply (EXPAND, FIT, CUT, or FIXED).

        Raises:
            TypeError: If rule is not an AutoFitRule instance.
        """
        if not isinstance(rule, AutoFitRule):
            raise TypeError("Rule must be an AutoFitRule")
        self._height_rule = rule

    @property
    def parameters(self) -> dict:
        """Serialization parameters for this row.

        Returns:
            Dictionary with height and height_rule values.
        """
        return {
            "height": self._height,
            "height_rule": self._height_rule.value,
        }

    # Internal
    def _set_cells(self, cells: list[Cell]) -> None:
        self._cells = cells


class Column:
    """Column metadata wrapper."""

    def __init__(self, table: Table, width: float) -> None:
        self._table = table
        self._width = _coerce_finite_float(width, name="Column width", allow_negative=False)
        self._width_rule = AutoFitRule.EXPAND
        self._cells: list[Cell] = []

    @property
    def table(self) -> Table:
        """Parent table containing this column.

        Returns:
            Table instance that owns this column.
        """
        return self._table

    @property
    def cells(self) -> tuple[Cell, ...]:
        """All cells in this column.

        Returns:
            Tuple of Cell objects in the column.
        """
        return tuple(self._cells)

    def row(self, index: int) -> Cell:
        """Get a cell at a specific row index.

        Args:
            index: Zero-based row index.

        Returns:
            Cell object at the specified row.

        Raises:
            IndexError: If index is out of bounds.
        """
        return self._cells[index]

    @property
    def width(self) -> float:
        """Column width in document units.

        Returns:
            Width value.
        """
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        """Set the column width.

        Args:
            value: New width value (must be non-negative).

        Raises:
            ValueError: If value is negative.
        """
        self._width = _coerce_finite_float(value, name="Column width", allow_negative=False)

    @property
    def width_rule(self) -> AutoFitRule:
        """Autofit rule for column width adjustment.

        Returns:
            Current AutoFitRule for this column.
        """
        return self._width_rule

    @width_rule.setter
    def width_rule(self, rule: AutoFitRule) -> None:
        """Set the autofit rule for column width.

        Args:
            rule: AutoFitRule to apply (EXPAND, FIT, CUT, or FIXED).

        Raises:
            TypeError: If rule is not an AutoFitRule instance.
        """
        if not isinstance(rule, AutoFitRule):
            raise TypeError("Rule must be an AutoFitRule")
        self._width_rule = rule

    @property
    def parameters(self) -> dict:
        """Serialization parameters for this column.

        Returns:
            Dictionary with width and width_rule values.
        """
        return {
            "width": self._width,
            "width_rule": self._width_rule.value,
        }

    # Internal
    def _set_cells(self, cells: list[Cell]) -> None:
        self._cells = cells


class Cell:
    """Individual table cell tracking content and merge state."""

    _ALLOWED_ALIGNMENTS = {"top", "middle", "bottom"}

    def __init__(self, table: Table, row_index: int, column_index: int) -> None:
        self._table = table
        self._row_index = row_index
        self._column_index = column_index
        self._paragraph_text: list[str] = []
        self._paragraph_styles: list[str | None] = []
        self._merged = False
        self._merge_start: tuple[int, int] = (row_index, column_index)
        self._merge_end: tuple[int, int] = (row_index, column_index)
        self._vertical_alignment = "top"

    @property
    def table(self) -> Table:
        """Parent table containing this cell.

        Returns:
            Table instance that owns this cell.
        """
        return self._table

    @property
    def row_index(self) -> int:
        """Zero-based row index of this cell.

        Returns:
            Row index.
        """
        return self._row_index

    @property
    def column_index(self) -> int:
        """Zero-based column index of this cell.

        Returns:
            Column index.
        """
        return self._column_index

    @property
    def merged(self) -> bool:
        """Whether this cell is part of a merged region.

        Returns:
            True if the cell is merged with other cells, False otherwise.
        """
        return self._merged

    @property
    def merge_start(self) -> tuple[int, int]:
        """Starting position of the merged region.

        Returns:
            (row, column) tuple of the top-left cell in the merge.
        """
        return self._merge_start

    @property
    def merge_end(self) -> tuple[int, int]:
        """Ending position of the merged region.

        Returns:
            (row, column) tuple of the bottom-right cell in the merge.
        """
        return self._merge_end

    @property
    def vertical_alignment(self) -> str:
        """Vertical text alignment within the cell.

        Returns:
            One of 'top', 'middle', or 'bottom'.
        """
        return self._vertical_alignment

    @vertical_alignment.setter
    def vertical_alignment(self, value: str) -> None:
        """Set the vertical text alignment.

        Args:
            value: Alignment value ('top', 'middle', or 'bottom').

        Raises:
            ValueError: If value is not one of the allowed alignments.
        """
        if value not in self._ALLOWED_ALIGNMENTS:
            raise ValueError("Alignment must be one of 'top', 'middle', or 'bottom'")
        self._vertical_alignment = value

    # Paragraph handling ------------------------------------------------
    @property
    def paragraphs(self) -> list[str]:
        """List of paragraph texts in this cell.

        Returns:
            List of text strings, one per paragraph.
        """
        return list(self._paragraph_text)

    @property
    def paragraph_styles(self) -> list[str | None]:
        """Style IDs for each paragraph.

        Returns:
            List of style ID strings (or None) corresponding to each paragraph.
        """
        return list(self._paragraph_styles)

    @property
    def text(self) -> str:
        """All paragraph text joined with newlines.

        Returns:
            Complete cell text as a single string.
        """
        return "\n".join(self._paragraph_text)

    def add_paragraph(self, text: str, *, style_id: str | None = None) -> None:
        """Add a new paragraph to the cell.

        Args:
            text: Text content for the paragraph.
            style_id: Optional style identifier for the paragraph.
        """
        self._append_paragraph(text, style_id, trigger_autofit=True)

    def _append_paragraph(
        self,
        text: str,
        style_id: str | None,
        *,
        trigger_autofit: bool,
    ) -> None:
        if not isinstance(text, str):
            raise TypeError("Paragraph text must be a string")
        self._paragraph_text.append(text)
        self._paragraph_styles.append(style_id)
        if trigger_autofit:
            self._table._register_autofit(self._row_index, self._column_index)

    def remove_paragraph(self, index: int) -> None:
        """Remove a paragraph by index.

        Args:
            index: Zero-based index of the paragraph to remove.

        Raises:
            IndexError: If index is out of bounds.
        """
        del self._paragraph_text[index]
        del self._paragraph_styles[index]

    def paragraph(self, index: int) -> str:
        """Get a specific paragraph by index.

        Args:
            index: Zero-based paragraph index.

        Returns:
            Text content of the paragraph.

        Raises:
            IndexError: If index is out of bounds.
        """
        return self._paragraph_text[index]

    # Merge -------------------------------------------------------------
    def merge(self, other: Cell) -> Cell:
        """Merge this cell with another cell, creating a merged region.

        Args:
            other: Another cell to merge with (must be in the same table).

        Returns:
            The top-left cell of the merged region.

        Raises:
            ValueError: If cells belong to different tables.
        """
        if self.table is not other.table:
            raise ValueError("Cells belong to different tables")
        top = min(self._row_index, other._row_index)
        bottom = max(self._row_index, other._row_index)
        left = min(self._column_index, other._column_index)
        right = max(self._column_index, other._column_index)

        for row in range(top, bottom + 1):
            for column in range(left, right + 1):
                cell = self.table.cell(row, column)
                cell._merged = True
                cell._merge_start = (top, left)
                cell._merge_end = (bottom, right)
        return self.table.cell(top, left)

    @property
    def parameters(self) -> dict:
        return {
            "paragraphs": [
                {"text": text, "style_id": style_id}
                for text, style_id in zip(self._paragraph_text, self._paragraph_styles, strict=False)
            ],
            "merged": self._merged,
            "merge_start": list(self._merge_start),
            "merge_end": list(self._merge_end),
            "vertical_alignment": self._vertical_alignment,
        }

    # Internal
    def _set_position(self, row_index: int, column_index: int) -> None:
        self._row_index = row_index
        self._column_index = column_index
        if self._merged:
            top_row, left_column = self._merge_start
            bottom_row, right_column = self._merge_end
            if not (top_row <= row_index <= bottom_row and left_column <= column_index <= right_column):
                self._merged = False
                self._merge_start = (row_index, column_index)
                self._merge_end = (row_index, column_index)
