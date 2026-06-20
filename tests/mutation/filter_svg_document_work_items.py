"""Filter Cosmic Ray work items to the SVG-DOC-P1 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/svg_generator.py'
AND (
  (definition_name = 'IncludeLayer' AND start_pos_row BETWEEN 1643 AND 1646)
  OR (definition_name = '_iter_layer_groups' AND start_pos_row BETWEEN 1654 AND 1656)
  OR (definition_name = 'create_svg' AND start_pos_row IN (1686, 1688, 1689, 1691, 1692, 1696, 1699, 1700))
  OR (definition_name = '_normalize_output_path' AND start_pos_row IN (1704, 1705, 1706, 1707, 1708))
  OR (definition_name = '_target_filename' AND start_pos_row IN (1786, 1787, 1788))
  OR (definition_name = '_write_svg' AND start_pos_row IN (1791, 1792))
  OR (definition_name = '_add_modeling_layer' AND start_pos_row IN (1896, 1897, 1901, 1902, 1908, 1909, 1912, 1913, 1934, 1935, 1936, 1937, 1945, 1946, 1947, 1948, 1950))
  OR (definition_name = '_add_segmentation_layer' AND start_pos_row BETWEEN 1952 AND 1955)
  OR (definition_name = '_add_label_layer' AND start_pos_row BETWEEN 1957 AND 1960)
  OR (definition_name = '_layer_from_svg_dict' AND start_pos_row BETWEEN 1963 AND 1975)
  OR (definition_name = '_layers_from_svg_dict' AND start_pos_row BETWEEN 1977 AND 1986)
  OR (definition_name = 'create_from_dict' AND start_pos_row BETWEEN 1988 AND 2001)
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
    'core/ReplaceBinaryOperator_Div_Mul'
  )
  OR operator_name = 'core/ReplaceAndWithOr'
  OR operator_name = 'core/ReplaceOrWithAnd'
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to SVG-DOC-P1 proof-critical work items."""
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
