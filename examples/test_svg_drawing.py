import json
import os
from pathlib import Path
from uuid import uuid4

from InkGen.boundary import Canvas
from InkGen.cad_component_groups import Zoning
from InkGen.document import Layer
from InkGen.svg_generator import (
    ComponentGroupSVG,
    DocumentSVG,
    IncludeLayer,
    LineSVG,
    RectangleSVG,
    RegularPolygonSVG,
    TableSVG,
    TextSVG,
)
from InkGen.style import DrawingStyle, Font, TextStyle
from InkGen.table import AutoFitRule, Table

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

PAGE_WIDTH = 420 * 1.4
PAGE_HEIGHT = 297 * 1.4
TOP_MARGIN = 4
BOTTOM_MARGIN = 4
LEFT_MARGIN = 4
RIGHT_MARGIN = 4
V_ZONE_WIDTH = 10
H_ZONE_WIDTH = 8
VERTICAL_ZONES = 8
HORIZONTAL_ZONES = 8


def _unique_style_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}" if prefix else uuid4().hex


def _text_style(
    prefix: str,
    size: float,
    align: str = "center",
    family: str = "Arial",
    weight: str = "normal",
) -> TextStyle:
    style = TextStyle(_unique_style_name(prefix), Font(family, weight=weight, size=size))
    style.text_align = align
    return style



def _center_baseline(row_top: float, row_height: float, style: TextStyle) -> float:
    size = float(style.font.size)
    return row_top + row_height / 2.0 + size * 0.35

def build_document() -> DocumentSVG:
    canvas = Canvas(PAGE_WIDTH, PAGE_HEIGHT, "mm")
    document = DocumentSVG(canvas)
    document.add_page()

    base_layer = document.page(1).layer("base")

    drawing_style = DrawingStyle(_unique_style_name("line"), stroke_width=0.4)
    zoning_text = _text_style("zoning", size=6)

    zoning = Zoning(
        canvas,
        drawing_style,
        zoning_text,
        left_margin=LEFT_MARGIN,
        right_margin=RIGHT_MARGIN,
        top_margin=TOP_MARGIN,
        bottom_margin=BOTTOM_MARGIN,
        v_zone_width=V_ZONE_WIDTH,
        h_zone_width=H_ZONE_WIDTH,
        inner_radius=0.0,
        outer_radius=0.0,
        vertical_zones=VERTICAL_ZONES,
        horizontal_zones=HORIZONTAL_ZONES,
    )
    document.page(1).add_layer("zoning", Layer("zoning", canvas, False))
    document.page(1).layer("zoning").add_component_group(zoning.component_group)

    right_edge = PAGE_WIDTH - RIGHT_MARGIN - V_ZONE_WIDTH
    top_edge = TOP_MARGIN + H_ZONE_WIDTH

    width = 1.8 * (PAGE_WIDTH - RIGHT_MARGIN - LEFT_MARGIN - 2 * V_ZONE_WIDTH) / VERTICAL_ZONES
    height = 23

    revision_table = ComponentGroupSVG("Revision")
    table_outline = RectangleSVG(
        position=(right_edge - width, top_edge),
        width=width,
        height=height,
        corner_radii=0.0,
        style=drawing_style,
    )
    revision_table.add_component(table_outline)

    first_row = top_edge + 8
    second_row = first_row + 5
    third_row = second_row + 5

    tiny_header = _text_style("rev_hdr", size=3, family="Impact")
    small_text = _text_style("rev_row", size=3, family="Arial")

    header_baseline = _center_baseline(top_edge, first_row - top_edge, tiny_header)
    revision_table.add_component(
        TextSVG(text="REVISIONS", position=(right_edge - width / 2, header_baseline), style=tiny_header)
    )

    revision_table.add_component(
        LineSVG(
            point_1=(right_edge - width, first_row),
            point_2=(right_edge, first_row),
            style=drawing_style,
        )
    )

    second_baseline = _center_baseline(first_row, second_row - first_row, tiny_header)
    revision_table.add_component(
        LineSVG(
            point_1=(right_edge - width, second_row),
            point_2=(right_edge, second_row),
            style=drawing_style,
        )
    )
    revision_table.add_component(
        LineSVG(
            point_1=(right_edge - width + 20, first_row),
            point_2=(right_edge - width + 20, second_row),
            style=drawing_style,
        )
    )
    revision_table.add_component(
        TextSVG(text="ZONE", position=(right_edge - width + 10, second_baseline), style=tiny_header)
    )
    revision_table.add_component(
        LineSVG(
            point_1=(right_edge - width + 30, first_row),
            point_2=(right_edge - width + 30, second_row),
            style=drawing_style,
        )
    )
    revision_table.add_component(
        TextSVG(text="REV", position=(right_edge - width + 25, second_baseline), style=tiny_header)
    )
    revision_table.add_component(
        LineSVG(
            point_1=(right_edge - width + 60, first_row),
            point_2=(right_edge - width + 60, second_row),
            style=drawing_style,
        )
    )
    revision_table.add_component(
        TextSVG(text="DESCRIPTION", position=(right_edge - width + 45, second_baseline), style=tiny_header)
    )
    revision_table.add_component(
        LineSVG(
            point_1=(right_edge - width + 73, first_row),
            point_2=(right_edge - width + 73, second_row),
            style=drawing_style,
        )
    )
    revision_table.add_component(
        TextSVG(text="DATE", position=(right_edge - width + 67, second_baseline), style=tiny_header)
    )
    revision_table.add_component(
        TextSVG(text="APPROVED", position=(right_edge - width + 80, second_baseline), style=tiny_header)
    )

    revision_table.add_component(
        LineSVG(
            point_1=(right_edge - width, third_row),
            point_2=(right_edge, third_row),
            style=drawing_style,
        )
    )
    revision_table.add_component(
        LineSVG(
            point_1=(right_edge - width + 20, second_row),
            point_2=(right_edge - width + 20, third_row),
            style=drawing_style,
        )
    )
    revision_table.add_component(
        LineSVG(
            point_1=(right_edge - width + 30, second_row),
            point_2=(right_edge - width + 30, third_row),
            style=drawing_style,
        )
    )

    third_baseline = _center_baseline(second_row, third_row - second_row, small_text)
    revision_table.add_component(
        TextSVG(text="-", position=(right_edge - width + 25, third_baseline), style=small_text)
    )

    base_layer.add_component_group(revision_table)

    _build_title_block(base_layer, drawing_style, top_edge, right_edge, width)
    _build_notes(base_layer, drawing_style)
    _build_free_text(base_layer, drawing_style)
    _build_summary_table(base_layer)

    return document


def _build_title_block(base_layer: Layer, drawing_style: DrawingStyle, top_edge: float, right_edge: float, width: float) -> None:
    title_block = ComponentGroupSVG("TitleBlock")
    bottom_edge = PAGE_HEIGHT - BOTTOM_MARGIN - H_ZONE_WIDTH
    block_height = 22
    block_top = bottom_edge - block_height

    title_block.add_component(
        RectangleSVG(
            position=(right_edge - width, block_top),
            width=width,
            height=block_height,
            corner_radii=0.0,
            style=drawing_style,
        )
    )

    row_offsets = [6, 12, 18]
    for offset in row_offsets:
        title_block.add_component(
            LineSVG(
                point_1=(right_edge - width, block_top + offset),
                point_2=(right_edge, block_top + offset),
                style=drawing_style,
            )
        )

    header = _text_style("title_hdr", size=4, align="left", family="Arial")
    row1_baseline = _center_baseline(block_top, 6, header)
    row2_baseline = _center_baseline(block_top + 6, 6, header)
    row3_baseline = _center_baseline(block_top + 12, 6, header)

    title_block.add_component(
        TextSVG(text="DRAWING TITLE", position=(right_edge - width + 4, row1_baseline), style=header)
    )
    title_block.add_component(
        TextSVG(text="SYNTHETIC CAD ASSEMBLY", position=(right_edge - width + 4, row2_baseline), style=header)
    )
    title_block.add_component(
        TextSVG(text="ASSEMBLY OVERVIEW", position=(right_edge - width + 4, row3_baseline), style=header)
    )

    second_col_x = right_edge - width + 60
    title_block.add_component(
        LineSVG(
            point_1=(second_col_x, block_top),
            point_2=(second_col_x, block_top + block_height),
            style=drawing_style,
        )
    )

    header_center = _text_style("title_cnt", size=4, family="Arial")
    title_block.add_component(
        TextSVG(text="SCALE", position=(second_col_x + 12, row2_baseline), style=header_center)
    )
    title_block.add_component(
        TextSVG(text="2/5", position=(second_col_x + 12, row3_baseline), style=header_center)
    )

    title_block.add_component(
        LineSVG(
            point_1=(right_edge - width + 50, block_top),
            point_2=(right_edge - width + 50, block_top + block_height),
            style=drawing_style,
        )
    )
    title_block.add_component(
        TextSVG(text="SHEET", position=(right_edge - width + 54, row2_baseline), style=header_center)
    )
    title_block.add_component(
        TextSVG(text="10 of 21", position=(right_edge - width + 62, row3_baseline), style=header_center)
    )

    base_layer.add_component_group(title_block)


def _build_notes(base_layer: Layer, drawing_style: DrawingStyle) -> None:
    notes = ComponentGroupSVG("Notes")
    note_dict = {
        1: {"ON": False, "TEXT": [
            "APPLICABLE STANDARDS/SPECIFICATIONS",
            "A. DOD-STD-0011444 (OIL)",
        ]},
        2: {"ON": True, "TEXT": ["TORQUE TO 74 ± 2 FT LBS."]},
        3: {"ON": True, "TEXT": ["TORQUE TO 120 ± 2 FT LBS."]},
        4: {"ON": True, "TEXT": [
            "LOCK FASTENERS USING ASTM D5363,",
            "AN0311, GROUP 03, CLASS 1, GRADE 1",
        ]},
        5: {"ON": True, "TEXT": ["MAXIMUM OIL TEMPERATURE 140 DEG F"]},
        6: {"ON": False, "TEXT": [
            "PRIOR TO FILL VERIFY",
            "OIL CLEANLINESS IS 18/16/13 (ISO 4406)",
        ]},
        7: {"ON": True, "TEXT": ["TORQUE TO 74 ± 2 FT LBS."]},
        9: {"ON": True, "TEXT": ["IN ACCORDANCE WITH ASME F1795"]},
    }

    left_edge = LEFT_MARGIN + V_ZONE_WIDTH + 10
    top_edge = TOP_MARGIN + H_ZONE_WIDTH + 15
    spacing = 8
    note_style = _text_style("note", size=4, align="left", family="Arial")
    notes.add_component(TextSVG(text="NOTES:", position=(left_edge, top_edge), style=note_style))
    position = top_edge + spacing
    for key, value in note_dict.items():
        notes.add_component(TextSVG(text=f"{key}", position=(left_edge, position), style=note_style))
        for idx, text in enumerate(value["TEXT"]):
            if idx > 0:
                position += 6
                notes.add_component(TextSVG(text=f"       {text}", position=(left_edge + 16, position), style=note_style))
            else:
                notes.add_component(TextSVG(text="-", position=(left_edge + 8, position), style=note_style))
                notes.add_component(TextSVG(text=text, position=(left_edge + 16, position), style=note_style))
                if value["ON"]:
                    notes.add_component(
                        RegularPolygonSVG(
                            position=(left_edge + 1.5, position - 1.5),
                            sides=6,
                            radius=4,
                            style=drawing_style,
                            angle=30,
                        )
                    )
        position += spacing

    base_layer.add_component_group(notes)


def _build_free_text(base_layer: Layer, drawing_style: DrawingStyle) -> None:
    free_text = ComponentGroupSVG("FreeText")
    part_number_style = _text_style("part", size=6, align="left", family="Arial")
    annotation_style = _text_style("annot", size=4, align="left", family="Arial")

    right_edge = PAGE_WIDTH - RIGHT_MARGIN - V_ZONE_WIDTH
    bottom_edge = PAGE_HEIGHT - BOTTOM_MARGIN - H_ZONE_WIDTH
    width = 1.8 * (PAGE_WIDTH - RIGHT_MARGIN - LEFT_MARGIN - 2 * V_ZONE_WIDTH) / VERTICAL_ZONES

    free_text.add_component(
        TextSVG(
            text="PART NO.  13454875",
            position=(right_edge - width + 1, bottom_edge - 27),
            style=part_number_style,
        )
    )
    free_text.add_component(
        TextSVG(
            text="CREATED FOR DEMONSTRATION PURPOSES ONLY",
            position=(LEFT_MARGIN + V_ZONE_WIDTH + 10, bottom_edge - 150),
            style=part_number_style,
        )
    )

    annotation_dict = {
        "HEX HEAD SCREW  -  MS353308-305": (73, 145),
        "DRAIN VALVE  -  MS234024-863B": (75, 170),
        "ACCESS PLATE  -  MS986325-462": (85, 205),
        "OIL RESERVOIR  -  MS56214-382": (67, 230),
        "INDUCTION MOTOR  -  MS568823-362B": (262, 67),
        "DRIVE COUPLING  -  MS125848-326": (300, 83),
        "HYDRAULIC PUMP  -  MS369822-125B": (315, 105),
        "SOLENOID VALVE  -  MS226987-412": (330, 121),
        "HEX HEAD SCREW  -  MS353308-308": (329, 138),
        "SIGHT GLASS  -  MS562235-112": (344, 168),
        "HEX HEAD SCREW  -  MS353308-309": (325, 202),
    }

    for text, position in annotation_dict.items():
        free_text.add_component(TextSVG(text=text, position=position, style=annotation_style))

    note_reference = {
        2: (400, 138),
        3: (57, 145),
        4: (66, 145),
        5: (60, 230),
        7: (397, 202),
        8: (399, 121),
    }
    for number, position in note_reference.items():
        free_text.add_component(TextSVG(text=str(number), position=position, style=annotation_style))
        free_text.add_component(
            RegularPolygonSVG(
                position=(position[0] + 1.5, position[1] - 1.5),
                sides=6,
                radius=4,
                style=drawing_style,
                angle=30,
            )
        )

    base_layer.add_component_group(free_text)


def _build_summary_table(base_layer: Layer) -> None:
    table_origin_x = LEFT_MARGIN + V_ZONE_WIDTH + 10
    table_origin_y = PAGE_HEIGHT - BOTTOM_MARGIN - H_ZONE_WIDTH - 40

    table = Table(position=(table_origin_x, table_origin_y))
    table.cell_padding = (1.5, 1.5, 1.5, 1.5)
    for width in (35.0, 60.0, 80.0):
        table.add_column(width=width)
    for height in (8.0, 8.0, 8.0, 8.0):
        table.add_row(height=height)

    header_style = _text_style("tbl_hdr", size=4, family="Arial")
    body_style = _text_style("tbl_body", size=4, align="left", family="Arial")

    header_id = header_style.name
    body_id = body_style.name

    headers = ("ITEM", "DESCRIPTION", "MATERIAL")
    for col, heading in enumerate(headers):
        cell = table.cell(0, col)
        cell.add_paragraph(heading, style_id=header_id)
        cell.vertical_alignment = "middle"

    rows = [
        ("001", "BASE FRAME", "ALUMINUM 6061-T6"),
        ("002", "PUMP ASSEMBLY", "STAINLESS STEEL"),
        ("003", "RESERVOIR", "ANODIZED ALUMINUM"),
    ]

    for row_index, data in enumerate(rows, start=1):
        for col_index, value in enumerate(data):
            table.cell(row_index, col_index).add_paragraph(value, style_id=body_id)
            table.cell(row_index, col_index).vertical_alignment = "middle"

    table.autofit = True
    for row in table.rows:
        row.height_rule = AutoFitRule.EXPAND
    for column in table.columns:
        column.width_rule = AutoFitRule.FIT

    border_style = DrawingStyle(_unique_style_name("tbl_border"), stroke_width=0.2)
    text_style_map = {
        header_id: header_style,
        body_id: body_style,
    }
    table_group = TableSVG.from_table(
        table,
        group_label="BillOfMaterials",
        border_style=border_style,
        text_styles=text_style_map,
    )
    base_layer.add_component_group(table_group)


def save_svg(document: DocumentSVG, filename: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = OUTPUT_DIR / filename
    document.create_svg(str(filepath), include=IncludeLayer.BASE)
    return str(filepath)


def main() -> None:
    document = build_document()
    svg_path = save_svg(document, "test_svg_draw.svg")
    try:
        os.startfile(svg_path)  # type: ignore[attr-defined]
    except AttributeError:
        pass


if __name__ == "__main__":
    main()
