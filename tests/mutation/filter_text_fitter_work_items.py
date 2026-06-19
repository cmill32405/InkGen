"""Filter Cosmic Ray work items to the TEXT-FITTER-P1 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/text_fitter.py'
AND (
  (
    definition_name = 'text_bounding_box'
    AND start_pos_row BETWEEN 70 AND 73
  )
  OR (
    definition_name IN (
      '_calculate_inner_boundary',
      'fit'
    )
    AND start_pos_row BETWEEN 196 AND 651
  )
  OR (
    definition_name = '_adaptive_word_wrap'
    AND (
      start_pos_row BETWEEN 217 AND 267
      OR start_pos_row BETWEEN 290 AND 300
    )
  )
  OR (
    definition_name = '_check_fit'
    AND start_pos_row BETWEEN 314 AND 320
  )
  OR (
    definition_name = 'component_to_fitter_shape'
    AND start_pos_row BETWEEN 654 AND 669
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
  definition_name = 'component_to_fitter_shape'
  AND start_pos_row = 666
  AND operator_name = 'core/NumberReplacer'
)
AND NOT (
  definition_name = '_adaptive_word_wrap'
  AND start_pos_row IN (227, 228)
  AND operator_name = 'core/NumberReplacer'
)
AND NOT (
  definition_name = 'fit'
  AND start_pos_row = 562
)
AND NOT (
  definition_name = 'fit'
  AND start_pos_row IN (579, 601, 636)
  AND operator_name = 'core/AddNot'
)
AND NOT (
  definition_name = 'fit'
  AND start_pos_row = 595
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to TEXT-FITTER-P1 proof-critical work items."""
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
