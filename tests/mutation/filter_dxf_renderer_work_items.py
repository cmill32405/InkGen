"""Filter Cosmic Ray work items to the DXF-P1 renderer proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/dxf_generator.py'
AND (
  (definition_name = 'point' AND start_pos_row IN (37, 39))
  OR (definition_name = 'add_group' AND start_pos_row IN (52, 54, 55))
  OR (definition_name = 'to_dxf_string' AND start_pos_row IN (76, 78, 79))
  OR (definition_name = 'create_dxf' AND start_pos_row IN (85, 87, 88))
  OR (definition_name = '_component_to_entities' AND start_pos_row IN (92, 94, 97, 99, 101, 104, 107, 109, 111, 113))
  OR (definition_name = '_rectangle_points' AND start_pos_row IN (121, 122, 124, 125, 143))
  OR (definition_name = 'append' AND start_pos_row IN (130, 131, 132))
  OR (definition_name = '_append_corner_arc' AND start_pos_row IN (157, 158, 159, 161, 162, 164, 165))
  OR (definition_name = '_line_entity' AND start_pos_row IN (169, 170, 175, 176, 178, 179))
  OR (definition_name = '_lwpolyline_entity' AND start_pos_row IN (189, 190, 192, 193, 194, 195))
  OR (definition_name = '_text_entity' AND start_pos_row IN (200, 201, 206, 207, 209, 210))
  OR (definition_name = '_circle_entity' AND start_pos_row IN (216, 221, 222, 224))
  OR (definition_name = '_pairs' AND start_pos_row IN (231, 232, 233, 234))
  OR (definition_name = '_format_value' AND start_pos_row IN (238, 239, 240, 241))
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND (
  operator_name = 'core/NumberReplacer'
  OR operator_name = 'core/AddNot'
  OR operator_name LIKE 'core/ReplaceComparisonOperator_%'
  OR operator_name LIKE 'core/ReplaceUnaryOperator_%'
  OR operator_name IN (
    'core/ReplaceBinaryOperator_Add_Sub',
    'core/ReplaceBinaryOperator_Sub_Add',
    'core/ReplaceBinaryOperator_Mul_Div',
    'core/ReplaceBinaryOperator_Mul_Sub',
    'core/ReplaceBinaryOperator_Div_Mul',
    'core/ReplaceBinaryOperator_Div_Sub'
  )
  OR operator_name = 'core/ReplaceAndWithOr'
  OR operator_name = 'core/ReplaceOrWithAnd'
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to DXF-P1 renderer proof-critical work items."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        if clear_results:
            cursor.execute("DELETE FROM work_results")
        cursor.execute(f"DELETE FROM work_items WHERE job_id NOT IN (SELECT job_id FROM mutation_specs WHERE {FILTER_SQL})")
        cursor.execute("DELETE FROM mutation_specs WHERE job_id NOT IN (SELECT job_id FROM work_items)")
        after = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
    return before, after


def main() -> None:
    """Run the command-line filter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", type=Path)
    parser.add_argument("--clear-results", action="store_true")
    args = parser.parse_args()

    before, after = filter_work_items(args.db_path, clear_results=args.clear_results)
    print(f"work_items: {before} -> {after}")


if __name__ == "__main__":
    main()
