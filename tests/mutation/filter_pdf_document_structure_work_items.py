"""Filter Cosmic Ray work items to PDF-DOC-STRUCT-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  (
    definition_name IN (
      '_coerce_pdf_page_label',
      '_coerce_pdf_page_box_name',
      '_coerce_pdf_page_box'
    )
    AND (
      start_pos_row BETWEEN 290 AND 310
      OR start_pos_row BETWEEN 319 AND 333
    )
  )
  OR (
    definition_name IN ('_pdf_optional_mapping', '_pdf_page_number_key')
    AND start_pos_row BETWEEN 781 AND 801
  )
  OR (
    definition_name IN (
      'DocumentPDF',
      '__init__',
      'add_page',
      'remove_page',
      'set_page_label',
      'page_label',
      'set_page_box',
      'page_box',
      '_shift_pdf_page_metadata_for_insert',
      '_shift_pdf_page_metadata_for_removal',
      '_page_label_dictionary',
      '_page_box_operators'
    )
    AND start_pos_row BETWEEN 1515 AND 1616
  )
  OR (
    definition_name = 'to_pdf_bytes'
    AND start_pos_row BETWEEN 1737 AND 1762
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 1868 AND 1875
  )
  OR (
    definition_name = 'parameters'
    AND start_pos_row BETWEEN 1891 AND 1897
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
AND operator_name NOT LIKE '%Mod%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to PDF page-structure proof-critical rows."""
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
