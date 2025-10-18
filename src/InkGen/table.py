from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

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
        position: Tuple[float, float] = (0.0, 0.0),
        autofit: bool = False,
    ) -> None:
        super().__init__()
        self._position = (float(position[0]), float(position[1]))
        self._auto_fit = bool(autofit)
        self._autofit_queue: List[Tuple[Tuple[int, int], AutoFitRule, AutoFitRule]] = []
        self._autofit_suppressed = False

        self._rows: List[Row] = []
        self._columns: List[Column] = []
        self._matrix: List[List[Cell]] = []
        self._padding = (1.0, 1.0, 1.0, 1.0)
        self.cell_padding = 1.0

    @property
    def cell_padding(self) -> Tuple[float, float, float, float]:
        return self._padding

    @cell_padding.setter
    def cell_padding(self, value: Union[float, Tuple[float, float, float, float], List[float]]):
        self._padding = self._normalize_padding(value)

    @property
    def padding_top(self) -> float:
        return self._padding[0]

    @property
    def padding_right(self) -> float:
        return self._padding[1]

    @property
    def padding_bottom(self) -> float:
        return self._padding[2]

    @property
    def padding_left(self) -> float:
        return self._padding[3]

    @staticmethod
    def _normalize_padding(value: Union[float, Tuple[float, float, float, float], List[float]]) -> Tuple[float, float, float, float]:
        if isinstance(value, (int, float)):
            pad = float(value)
            return (pad, pad, pad, pad)
        if isinstance(value, (tuple, list)) and len(value) == 4:
            return tuple(float(v) for v in value)  # type: ignore[arg-type]
        raise ValueError("Padding must be a float or an iterable of four floats")

    # ------------------------------------------------------------------
    # Core structural helpers
    # ------------------------------------------------------------------
    def add_row(self, *, location: Optional[int] = None, height: float = 10.0) -> Row:
        """Insert a new row at *location* (default end) with the supplied height."""
        insert_at = self._validate_insert_index(location, self.row_count)
        row = Row(self, height)
        new_cells = [Cell(self, insert_at, col_idx) for col_idx in range(self.column_count)]

        self._rows.insert(insert_at, row)
        self._matrix.insert(insert_at, new_cells)
        self._sync_views()
        self._reindex_cells()
        return row

    def add_column(self, *, location: Optional[int] = None, width: float = 10.0) -> Column:
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

    def cell(self, row: int, column: int) -> "Cell":
        return self._matrix[row][column]

    def row_cells(self, row: int) -> Tuple["Cell", ...]:
        return tuple(self._matrix[row])

    def column_cells(self, column: int) -> Tuple["Cell", ...]:
        return tuple(self._matrix[row][column] for row in range(self.row_count))

    def cell_bounds(
        self, row: int, column: int
    ) -> Tuple[Tuple[float, float], float, float]:
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
    def position(self) -> Tuple[float, float]:
        return self._position

    @position.setter
    def position(self, value: Tuple[float, float]) -> None:
        self._position = (float(value[0]), float(value[1]))

    @property
    def width(self) -> float:
        return sum(column.width for column in self._columns)

    @property
    def height(self) -> float:
        return sum(row.height for row in self._rows)

    @property
    def points(self) -> List[Tuple[float, float]]:
        x, y = self._position
        w, h = self.width, self.height
        if w == 0 or h == 0:
            return [(x, y)]
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

    @property
    def bbox(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        x, y = self._position
        return ((x, y), (x + self.width, y + self.height))

    @property
    def convex_hull(self) -> List[Tuple[float, float]]:
        return self.points.copy()

    # ------------------------------------------------------------------
    # Auto-fit
    # ------------------------------------------------------------------
    @property
    def autofit(self) -> bool:
        return self._auto_fit

    @autofit.setter
    def autofit(self, state: bool) -> None:
        self._auto_fit = bool(state)

    @property
    def autofit_queue(self) -> List[Tuple[Tuple[int, int], AutoFitRule, AutoFitRule]]:
        return list(self._autofit_queue)

    def clear_autofit_queue(self) -> None:
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
    def create_from_dict(cls, data: dict) -> "Table":
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
    def rows(self) -> Tuple["Row", ...]:
        return tuple(self._rows)

    @property
    def columns(self) -> Tuple["Column", ...]:
        return tuple(self._columns)

    @property
    def row_count(self) -> int:
        return len(self._rows)

    @property
    def column_count(self) -> int:
        return len(self._columns)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _validate_insert_index(self, location: Optional[int], upper: int) -> int:
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



@staticmethod
def _normalize_padding(value: Union[float, Tuple[float, float, float, float], List[float]]) -> Tuple[float, float, float, float]:
    if isinstance(value, (int, float)):
        pad = float(value)
        return (pad, pad, pad, pad)
    if isinstance(value, (tuple, list)) and len(value) == 4:
        return tuple(float(v) for v in value)  # type: ignore[arg-type]
    raise ValueError("Padding must be a float or an iterable of four floats")


class Row:

    """Row metadata wrapper."""

    def __init__(self, table: Table, height: float) -> None:
        self._table = table
        self._height = float(height)
        self._height_rule = AutoFitRule.EXPAND
        self._cells: List[Cell] = []

    @property
    def table(self) -> Table:
        return self._table

    @property
    def cells(self) -> Tuple["Cell", ...]:
        return tuple(self._cells)

    def column(self, index: int) -> "Cell":
        return self._cells[index]

    @property
    def height(self) -> float:
        return self._height

    @height.setter
    def height(self, value: float) -> None:
        if value < 0:
            raise ValueError("Row height must be non-negative")
        self._height = float(value)

    @property
    def height_rule(self) -> AutoFitRule:
        return self._height_rule

    @height_rule.setter
    def height_rule(self, rule: AutoFitRule) -> None:
        if not isinstance(rule, AutoFitRule):
            raise TypeError("Rule must be an AutoFitRule")
        self._height_rule = rule

    @property
    def parameters(self) -> dict:
        return {
            "height": self._height,
            "height_rule": self._height_rule.value,
        }

    # Internal
    def _set_cells(self, cells: List["Cell"]) -> None:
        self._cells = cells


class Column:
    """Column metadata wrapper."""

    def __init__(self, table: Table, width: float) -> None:
        self._table = table
        self._width = float(width)
        self._width_rule = AutoFitRule.EXPAND
        self._cells: List[Cell] = []

    @property
    def table(self) -> Table:
        return self._table

    @property
    def cells(self) -> Tuple["Cell", ...]:
        return tuple(self._cells)

    def row(self, index: int) -> "Cell":
        return self._cells[index]

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        if value < 0:
            raise ValueError("Column width must be non-negative")
        self._width = float(value)

    @property
    def width_rule(self) -> AutoFitRule:
        return self._width_rule

    @width_rule.setter
    def width_rule(self, rule: AutoFitRule) -> None:
        if not isinstance(rule, AutoFitRule):
            raise TypeError("Rule must be an AutoFitRule")
        self._width_rule = rule

    @property
    def parameters(self) -> dict:
        return {
            "width": self._width,
            "width_rule": self._width_rule.value,
        }

    # Internal
    def _set_cells(self, cells: List["Cell"]) -> None:
        self._cells = cells


class Cell:
    """Individual table cell tracking content and merge state."""

    _ALLOWED_ALIGNMENTS = {"top", "middle", "bottom"}

    def __init__(self, table: Table, row_index: int, column_index: int) -> None:
        self._table = table
        self._row_index = row_index
        self._column_index = column_index
        self._paragraph_text: List[str] = []
        self._paragraph_styles: List[Optional[str]] = []
        self._merged = False
        self._merge_start: Tuple[int, int] = (row_index, column_index)
        self._merge_end: Tuple[int, int] = (row_index, column_index)
        self._vertical_alignment = "top"

    @property
    def table(self) -> Table:
        return self._table

    @property
    def row_index(self) -> int:
        return self._row_index

    @property
    def column_index(self) -> int:
        return self._column_index

    @property
    def merged(self) -> bool:
        return self._merged

    @property
    def merge_start(self) -> Tuple[int, int]:
        return self._merge_start

    @property
    def merge_end(self) -> Tuple[int, int]:
        return self._merge_end

    @property
    def vertical_alignment(self) -> str:
        return self._vertical_alignment

    @vertical_alignment.setter
    def vertical_alignment(self, value: str) -> None:
        if value not in self._ALLOWED_ALIGNMENTS:
            raise ValueError("Alignment must be one of 'top', 'middle', or 'bottom'")
        self._vertical_alignment = value

    # Paragraph handling ------------------------------------------------
    @property
    def paragraphs(self) -> List[str]:
        return list(self._paragraph_text)

    @property
    def paragraph_styles(self) -> List[Optional[str]]:
        return list(self._paragraph_styles)

    @property
    def text(self) -> str:
        return "\n".join(self._paragraph_text)

    def add_paragraph(self, text: str, *, style_id: Optional[str] = None) -> None:
        self._append_paragraph(text, style_id, trigger_autofit=True)

    def _append_paragraph(
        self,
        text: str,
        style_id: Optional[str],
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
        del self._paragraph_text[index]
        del self._paragraph_styles[index]

    def paragraph(self, index: int) -> str:
        return self._paragraph_text[index]

    # Merge -------------------------------------------------------------
    def merge(self, other: "Cell") -> "Cell":
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
                for text, style_id in zip(self._paragraph_text, self._paragraph_styles)
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
