"""Filter Cosmic Ray work items to PDF-DOC-PAGE-ROTATION-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  (
    definition_name = '_coerce_pdf_page_rotation'
    AND start_pos_row BETWEEN 500 AND 520
  )
  OR (
    definition_name IN (
      'DocumentPDF',
      '__init__',
      'set_page_rotation',
      'page_rotation',
      '_page_rotation_operator'
    )
    AND start_pos_row BETWEEN 2130 AND 2790
  )
  OR (
    definition_name = '_shift_pdf_page_metadata_for_insert'
    AND start_pos_row BETWEEN 2551 AND 2554
  )
  OR (
    definition_name = '_shift_pdf_page_metadata_for_removal'
    AND start_pos_row BETWEEN 2670 AND 2675
  )
  OR (
    definition_name = 'to_pdf_bytes'
    AND start_pos_row BETWEEN 3320 AND 3345
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 3480 AND 3500
  )
  OR (
    definition_name = 'parameters'
    AND start_pos_row BETWEEN 3600 AND 3620
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND operator_name NOT LIKE '%BitAnd%'
AND operator_name NOT LIKE '%BitOr%'
AND operator_name NOT LIKE '%BitXor%'
AND operator_name NOT LIKE '%LShift%'
AND operator_name NOT LIKE '%RShift%'
AND operator_name NOT LIKE '%Pow%'
AND operator_name NOT LIKE '%FloorDiv%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to PDF page-rotation proof-critical rows."""
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
