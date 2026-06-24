"""Filter Cosmic Ray work items to PDF-COMPONENT-FACTORY-PAYLOAD-P2 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/pdf_generator.py'
AND (
  (
    definition_name IN ('_pdf_payload', '_pdf_required_field', '_pdf_optional_sequence', '_path_command_from_dict')
    AND start_pos_row BETWEEN 235 AND 270
  )
  OR (
    definition_name = 'create_from_dict'
    AND (
      start_pos_row BETWEEN 291 AND 300
      OR start_pos_row BETWEEN 343 AND 350
      OR start_pos_row BETWEEN 393 AND 404
      OR start_pos_row BETWEEN 443 AND 451
      OR start_pos_row BETWEEN 491 AND 500
      OR start_pos_row BETWEEN 539 AND 543
      OR start_pos_row BETWEEN 633 AND 643
      OR start_pos_row BETWEEN 675 AND 678
      OR start_pos_row BETWEEN 717 AND 720
      OR start_pos_row BETWEEN 753 AND 756
    )
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to PDF component factory payload items."""
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
