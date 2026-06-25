"""Filter Cosmic Ray work items to TRUTH-ANNOTATION-PAYLOAD-P2 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
  (
    module_path = 'src/InkGen/extraction_truth.py'
    AND (
      (
        definition_name = 'from_dict'
        AND start_pos_row BETWEEN 42 AND 56
      )
      OR (
        definition_name IN ('_annotation_payload', '_required_string', '_optional_string', '_optional_string_or_none')
        AND start_pos_row BETWEEN 244 AND 272
      )
    )
  )
  OR (
    module_path = 'src/InkGen/grammar_truth.py'
    AND (
      (
        definition_name = 'from_dict'
        AND start_pos_row BETWEEN 42 AND 55
      )
      OR (
        definition_name IN ('_annotation_payload', '_required_string', '_optional_string', '_optional_string_or_none')
        AND start_pos_row BETWEEN 221 AND 249
      )
    )
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to truth annotation payload checks."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        if clear_results:
            cursor.execute("DELETE FROM work_results")
        cursor.execute(
            f"""
            DELETE FROM work_items
            WHERE job_id NOT IN (
                SELECT job_id FROM mutation_specs WHERE {FILTER_SQL}
            )
            """,
        )
        cursor.execute(
            """
            DELETE FROM mutation_specs
            WHERE job_id NOT IN (SELECT job_id FROM work_items)
            """,
        )
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
