"""Filter Cosmic Ray work items to NEUTRAL-PRIMITIVE-STYLE-P2 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/drawing_components.py'
AND (
  (
    definition_name IN ('_require_drawing_style', '_require_text_style')
    AND start_pos_row BETWEEN 47 AND 56
  )
  OR (
    definition_name = '__post_init__'
    AND (
      start_pos_row BETWEEN 69 AND 71
      OR start_pos_row BETWEEN 93 AND 95
      OR start_pos_row BETWEEN 117 AND 119
      OR start_pos_row BETWEEN 145 AND 147
      OR start_pos_row BETWEEN 170 AND 172
      OR start_pos_row BETWEEN 196 AND 198
      OR start_pos_row BETWEEN 219 AND 221
      OR start_pos_row BETWEEN 254 AND 256
      OR start_pos_row BETWEEN 277 AND 279
      OR start_pos_row BETWEEN 301 AND 303
    )
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to neutral primitive style items."""
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
