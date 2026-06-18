"""Filter Cosmic Ray work items to the PARAGRAPH-P1 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/paragraph.py'
AND (
  (
    definition_name = '__post_init__'
    AND start_pos_row IN (48, 49, 50)
  )
  OR (
    definition_name = 'position'
    AND start_pos_row BETWEEN 164 AND 170
  )
  OR (
    definition_name = 'first_line_indent'
    AND start_pos_row = 211
  )
  OR (
    definition_name = 'line_spacing'
    AND start_pos_row = 265
  )
  OR (
    definition_name = 'outline_level'
    AND start_pos_row BETWEEN 321 AND 324
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 414 AND 433
  )
  OR (
    definition_name = '_validate_non_negative'
    AND start_pos_row = 516
  )
  OR (
    definition_name = '_coerce_finite_float'
    AND start_pos_row BETWEEN 525 AND 546
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND NOT (
  definition_name = '_coerce_finite_float'
  AND start_pos_row BETWEEN 525 AND 531
  AND operator_name = 'core/ReplaceBinaryOperator_Mul_Div'
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to PARAGRAPH-P1 proof-critical work items."""
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
