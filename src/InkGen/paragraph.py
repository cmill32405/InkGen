"""Renderer-neutral paragraph layout model.

This module provides a paragraph object shaped like the existing table model:
it stores layout parameters, validates Word-like paragraph settings, serializes
cleanly, and can materialize text lines into renderer-neutral drawing recipes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from InkGen.component import Component
from InkGen.drawing_components import DrawingComponentGroup, TextDrawing
from InkGen.style import TextStyle


class ParagraphAlignment(str, Enum):
    """Horizontal paragraph alignment options."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class LineSpacingRule(str, Enum):
    """Line-spacing rule names modeled after common word processors."""

    SINGLE = "single"
    ONE_AND_HALF = "one_and_half"
    DOUBLE = "double"
    MULTIPLE = "multiple"
    EXACTLY = "exactly"
    AT_LEAST = "at_least"


@dataclass(frozen=True)
class TabStop:
    """A paragraph tab stop measured from the paragraph content left edge."""

    position: float
    alignment: ParagraphAlignment = ParagraphAlignment.LEFT
    leader: str | None = None

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError("Tab stop position must be non-negative")
        if not isinstance(self.alignment, ParagraphAlignment):
            object.__setattr__(self, "alignment", ParagraphAlignment(self.alignment))

    @property
    def parameters(self) -> dict[str, object]:
        """Return serialization parameters for this tab stop."""
        return {
            "position": float(self.position),
            "alignment": self.alignment.value,
            "leader": self.leader,
        }

    @classmethod
    def create_from_dict(cls, data: dict[str, object]) -> TabStop:
        """Recreate a tab stop from serialized parameters."""
        return cls(
            position=float(data["position"]),
            alignment=ParagraphAlignment(str(data.get("alignment", ParagraphAlignment.LEFT.value))),
            leader=data.get("leader"),
        )


@dataclass(frozen=True)
class ParagraphLine:
    """A laid-out paragraph line with baseline position and estimated width."""

    text: str
    position: tuple[float, float]
    width: float
    line_index: int

    @property
    def parameters(self) -> dict[str, object]:
        """Return serialization parameters for this laid-out line."""
        return {
            "text": self.text,
            "position": [self.position[0], self.position[1]],
            "width": self.width,
            "line_index": self.line_index,
        }


class Paragraph(Component):
    """Word-like paragraph model that can emit renderer-neutral text lines."""

    _NON_NEGATIVE_FIELDS = {
        "width",
        "left_indent",
        "right_indent",
        "space_before",
        "space_after",
    }

    def __init__(
        self,
        text: str = "",
        *,
        position: tuple[float, float] = (0.0, 0.0),
        width: float = 100.0,
        style: TextStyle,
        alignment: ParagraphAlignment | str = ParagraphAlignment.LEFT,
        first_line_indent: float = 0.0,
        hanging_indent: float = 0.0,
        left_indent: float = 0.0,
        right_indent: float = 0.0,
        space_before: float = 0.0,
        space_after: float = 0.0,
        line_spacing: float = 1.0,
        line_spacing_rule: LineSpacingRule | str = LineSpacingRule.MULTIPLE,
        keep_together: bool = False,
        keep_with_next: bool = False,
        page_break_before: bool = False,
        widow_control: bool = True,
        outline_level: int = 0,
        tab_stops: list[TabStop] | None = None,
    ) -> None:
        """Create a paragraph with Word-like spacing, alignment, and pagination settings."""
        super().__init__()
        self.text = text
        self.position = position
        self.width = width
        self.style = style
        self.alignment = alignment
        self.first_line_indent = first_line_indent
        self.hanging_indent = hanging_indent
        self.left_indent = left_indent
        self.right_indent = right_indent
        self.space_before = space_before
        self.space_after = space_after
        self.line_spacing = line_spacing
        self.line_spacing_rule = line_spacing_rule
        self.keep_together = keep_together
        self.keep_with_next = keep_with_next
        self.page_break_before = page_break_before
        self.widow_control = widow_control
        self.outline_level = outline_level
        self._tab_stops = tuple(tab_stops or [])

    @property
    def text(self) -> str:
        """Paragraph text."""
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Paragraph text must be a string")
        self._text = value

    @property
    def position(self) -> tuple[float, float]:
        """Top-left paragraph position."""
        return self._position

    @position.setter
    def position(self, value: tuple[float, float]) -> None:
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise ValueError("Position must be a two-value tuple")
        self._position = (float(value[0]), float(value[1]))

    @property
    def width(self) -> float:
        """Paragraph frame width."""
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        self._width = self._validate_non_negative("width", value)

    @property
    def style(self) -> TextStyle:
        """Default text style for paragraph lines."""
        return self._style

    @style.setter
    def style(self, value: TextStyle) -> None:
        if not isinstance(value, TextStyle):
            raise TypeError("style must be a TextStyle")
        self._style = value

    @property
    def alignment(self) -> ParagraphAlignment:
        """Paragraph horizontal alignment."""
        return self._alignment

    @alignment.setter
    def alignment(self, value: ParagraphAlignment | str) -> None:
        if isinstance(value, ParagraphAlignment):
            self._alignment = value
        else:
            self._alignment = ParagraphAlignment(str(value).lower())

    @property
    def first_line_indent(self) -> float:
        """Additional indent applied only to the first line."""
        return self._first_line_indent

    @first_line_indent.setter
    def first_line_indent(self, value: float) -> None:
        self._first_line_indent = float(value)

    @property
    def hanging_indent(self) -> float:
        """Indent subtracted from lines after the first line."""
        return self._hanging_indent

    @hanging_indent.setter
    def hanging_indent(self, value: float) -> None:
        self._hanging_indent = self._validate_non_negative("hanging_indent", value)

    @property
    def left_indent(self) -> float:
        """Left paragraph indent."""
        return self._left_indent

    @left_indent.setter
    def left_indent(self, value: float) -> None:
        self._left_indent = self._validate_non_negative("left_indent", value)

    @property
    def right_indent(self) -> float:
        """Right paragraph indent."""
        return self._right_indent

    @right_indent.setter
    def right_indent(self, value: float) -> None:
        self._right_indent = self._validate_non_negative("right_indent", value)

    @property
    def space_before(self) -> float:
        """Space before the first line."""
        return self._space_before

    @space_before.setter
    def space_before(self, value: float) -> None:
        self._space_before = self._validate_non_negative("space_before", value)

    @property
    def space_after(self) -> float:
        """Space after the final line."""
        return self._space_after

    @space_after.setter
    def space_after(self, value: float) -> None:
        self._space_after = self._validate_non_negative("space_after", value)

    @property
    def line_spacing(self) -> float:
        """Line spacing value interpreted by `line_spacing_rule`."""
        return self._line_spacing

    @line_spacing.setter
    def line_spacing(self, value: float) -> None:
        if not isinstance(value, (float, int)) or value <= 0:
            raise ValueError("line_spacing must be greater than zero")
        self._line_spacing = float(value)

    @property
    def line_spacing_rule(self) -> LineSpacingRule:
        """Rule used to interpret line spacing."""
        return self._line_spacing_rule

    @line_spacing_rule.setter
    def line_spacing_rule(self, value: LineSpacingRule | str) -> None:
        if isinstance(value, LineSpacingRule):
            self._line_spacing_rule = value
        else:
            self._line_spacing_rule = LineSpacingRule(str(value).lower())

    @property
    def keep_together(self) -> bool:
        """Whether the paragraph prefers all lines on one page."""
        return self._keep_together

    @keep_together.setter
    def keep_together(self, value: bool) -> None:
        self._keep_together = self._validate_bool("keep_together", value)

    @property
    def keep_with_next(self) -> bool:
        """Whether the paragraph should stay with the following paragraph."""
        return self._keep_with_next

    @keep_with_next.setter
    def keep_with_next(self, value: bool) -> None:
        self._keep_with_next = self._validate_bool("keep_with_next", value)

    @property
    def page_break_before(self) -> bool:
        """Whether layout should start this paragraph on a new page."""
        return self._page_break_before

    @page_break_before.setter
    def page_break_before(self, value: bool) -> None:
        self._page_break_before = self._validate_bool("page_break_before", value)

    @property
    def widow_control(self) -> bool:
        """Whether layout should avoid single first/last lines across pages."""
        return self._widow_control

    @widow_control.setter
    def widow_control(self, value: bool) -> None:
        self._widow_control = self._validate_bool("widow_control", value)

    @property
    def outline_level(self) -> int:
        """Paragraph outline level, where 0 is body text."""
        return self._outline_level

    @outline_level.setter
    def outline_level(self, value: int) -> None:
        if not isinstance(value, int) or not 0 <= value <= 9:
            raise ValueError("outline_level must be an integer between 0 and 9")
        self._outline_level = value

    @property
    def tab_stops(self) -> tuple[TabStop, ...]:
        """Configured tab stops."""
        return self._tab_stops

    def add_tab_stop(
        self,
        position: float,
        *,
        alignment: ParagraphAlignment | str = ParagraphAlignment.LEFT,
        leader: str | None = None,
    ) -> TabStop:
        """Add a tab stop to the paragraph."""
        if not isinstance(alignment, ParagraphAlignment):
            alignment = ParagraphAlignment(str(alignment).lower())
        stop = TabStop(float(position), alignment, leader)
        self._tab_stops = tuple(sorted((*self._tab_stops, stop), key=lambda item: item.position))
        return stop

    def remove_tab_stop(self, index: int) -> None:
        """Remove a tab stop by index."""
        stops = list(self._tab_stops)
        del stops[index]
        self._tab_stops = tuple(stops)

    @property
    def content_width(self) -> float:
        """Available content width after left and right indents."""
        return max(self.width - self.left_indent - self.right_indent, 0.0)

    @property
    def points(self) -> list[tuple[float, float]]:
        """Paragraph bounding rectangle points."""
        x, y = self.position
        return [(x, y), (x + self.width, y), (x + self.width, y + self.height), (x, y + self.height)]

    @property
    def bbox(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Paragraph bounding box."""
        x, y = self.position
        return ((x, y), (x + self.width, y + self.height))

    @property
    def convex_hull(self) -> list[tuple[float, float]]:
        """Paragraph convex hull."""
        return self.points.copy()

    @property
    def height(self) -> float:
        """Estimated paragraph height including before/after spacing."""
        line_count = max(len(self.layout_lines()), 1)
        return self.space_before + self.space_after + line_count * self._line_height()

    @property
    def parameters(self) -> dict[str, dict[str, object]]:
        """Return serialization parameters for this paragraph."""
        return {
            "Paragraph": {
                "text": self.text,
                "position": [self.position[0], self.position[1]],
                "width": self.width,
                "style": self.style.parameters,
                "alignment": self.alignment.value,
                "first_line_indent": self.first_line_indent,
                "hanging_indent": self.hanging_indent,
                "left_indent": self.left_indent,
                "right_indent": self.right_indent,
                "space_before": self.space_before,
                "space_after": self.space_after,
                "line_spacing": self.line_spacing,
                "line_spacing_rule": self.line_spacing_rule.value,
                "keep_together": self.keep_together,
                "keep_with_next": self.keep_with_next,
                "page_break_before": self.page_break_before,
                "widow_control": self.widow_control,
                "outline_level": self.outline_level,
                "tab_stops": [stop.parameters for stop in self.tab_stops],
            }
        }

    @classmethod
    def create_from_dict(cls, data: dict[str, object], styles: dict[str, TextStyle] | None = None) -> Paragraph:
        """Recreate a paragraph from serialized parameters."""
        payload = data["Paragraph"] if "Paragraph" in data else data
        styles = styles or {}
        style_payload = payload["style"]
        style_name = style_payload["TextStyle"]["name"]
        style = styles.get(style_name) or TextStyle.create_from_dict(style_payload)
        return cls(
            str(payload["text"]),
            position=tuple(payload["position"]),
            width=float(payload["width"]),
            style=style,
            alignment=ParagraphAlignment(str(payload["alignment"])),
            first_line_indent=float(payload["first_line_indent"]),
            hanging_indent=float(payload["hanging_indent"]),
            left_indent=float(payload["left_indent"]),
            right_indent=float(payload["right_indent"]),
            space_before=float(payload["space_before"]),
            space_after=float(payload["space_after"]),
            line_spacing=float(payload["line_spacing"]),
            line_spacing_rule=LineSpacingRule(str(payload["line_spacing_rule"])),
            keep_together=bool(payload["keep_together"]),
            keep_with_next=bool(payload["keep_with_next"]),
            page_break_before=bool(payload["page_break_before"]),
            widow_control=bool(payload["widow_control"]),
            outline_level=int(payload["outline_level"]),
            tab_stops=[TabStop.create_from_dict(stop) for stop in payload.get("tab_stops", [])],
        )

    def layout_lines(self) -> tuple[ParagraphLine, ...]:
        """Lay out paragraph text into baseline-positioned lines."""
        line_texts = self._wrap_text()
        lines = []
        line_height = self._line_height()
        baseline = self.position[1] + self.space_before + self._baseline_shift()
        for index, text in enumerate(line_texts):
            line_width = self._measure_text(text)
            available_width = self._available_width(index)
            left_edge = self.position[0] + self.left_indent + self._line_indent(index)
            if self.alignment is ParagraphAlignment.CENTER:
                x_pos = left_edge + max((available_width - line_width) / 2.0, 0.0)
            elif self.alignment is ParagraphAlignment.RIGHT:
                x_pos = left_edge + max(available_width - line_width, 0.0)
            else:
                x_pos = left_edge
            lines.append(ParagraphLine(text=text, position=(x_pos, baseline + index * line_height), width=line_width, line_index=index))
        return tuple(lines)

    def to_drawing_group(self, group_label: str = "Paragraph") -> DrawingComponentGroup:
        """Materialize this paragraph as renderer-neutral text drawing primitives."""
        group = DrawingComponentGroup(group_label)
        for line in self.layout_lines():
            group.add_component(TextDrawing(line.text, line.position, self.style))
        return group

    def _wrap_text(self) -> list[str]:
        paragraphs = self.text.splitlines() or [""]
        wrapped: list[str] = []
        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                wrapped.append("")
                continue
            current = words[0]
            line_index = len(wrapped)
            for word in words[1:]:
                candidate = f"{current} {word}"
                if self._measure_text(candidate) <= self._available_width(line_index):
                    current = candidate
                else:
                    wrapped.append(current)
                    line_index += 1
                    current = word
            wrapped.append(current)
        return wrapped

    def _available_width(self, line_index: int) -> float:
        return max(self.content_width - self._line_indent(line_index), 0.1)

    def _line_indent(self, line_index: int) -> float:
        if line_index == 0:
            return self.first_line_indent
        return max(-self.hanging_indent, -self.left_indent)

    def _measure_text(self, text: str) -> float:
        size = float(self.style.font.size)
        mm_per_point = 25.4 / 72.0
        average_char_width = size * mm_per_point * 0.55
        space_bonus = text.count(" ") * size * mm_per_point * 0.15
        return max(len(text) * average_char_width + space_bonus, 0.0)

    def _line_height(self) -> float:
        base = float(self.style.font.size) * (25.4 / 72.0)
        if self.line_spacing_rule is LineSpacingRule.SINGLE:
            return base
        if self.line_spacing_rule is LineSpacingRule.ONE_AND_HALF:
            return base * 1.5
        if self.line_spacing_rule is LineSpacingRule.DOUBLE:
            return base * 2.0
        if self.line_spacing_rule is LineSpacingRule.EXACTLY:
            return self.line_spacing
        if self.line_spacing_rule is LineSpacingRule.AT_LEAST:
            return max(base, self.line_spacing)
        return base * self.line_spacing

    def _baseline_shift(self) -> float:
        return float(self.style.font.size) * (25.4 / 72.0) * 0.78

    def _validate_non_negative(self, name: str, value: float) -> float:
        if not isinstance(value, (float, int)) or value < 0:
            raise ValueError(f"{name} must be non-negative")
        return float(value)

    @staticmethod
    def _validate_bool(name: str, value: bool) -> bool:
        if not isinstance(value, bool):
            raise TypeError(f"{name} must be a bool")
        return value
