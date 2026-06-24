"""Filter Cosmic Ray work items to the TEXT-OUTLINE-P1 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/text_outline.py'
AND (
  (
    definition_name IN (
      '_require_bool',
      'set_add_one_pixel_margin_default',
      '_px_to_units',
      'sample_path_points'
    )
    AND start_pos_row BETWEEN 15 AND 65
  )
  OR (
    definition_name = 'outline_for_text'
    AND (
      start_pos_row BETWEEN 215 AND 218
      OR start_pos_row BETWEEN 254 AND 278
      OR start_pos_row BETWEEN 288 AND 290
    )
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND (
  operator_name = 'core/NumberReplacer'
  OR operator_name = 'core/AddNot'
  OR operator_name LIKE 'core/ReplaceComparisonOperator_%'
  OR operator_name LIKE 'core/ReplaceUnaryOperator_%'
  OR operator_name = 'core/ReplaceAndWithOr'
  OR operator_name = 'core/ReplaceOrWithAnd'
)
AND NOT (
  definition_name = 'sample_path_points'
  AND start_pos_row IN (50, 46, 62)
  AND operator_name = 'core/NumberReplacer'
)
AND NOT (
  definition_name = 'outline_for_text'
  AND start_pos_row IN (254, 255, 260, 261, 266, 269, 272, 275, 278)
)
AND NOT (
  definition_name = 'outline_for_text'
  AND start_pos_row = 290
  AND operator_name = 'core/NumberReplacer'
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to TEXT-OUTLINE-P1 proof-critical work items."""
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
