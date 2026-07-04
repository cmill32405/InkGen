"""Filter Cosmic Ray work items to PDF-DOC-OUTLINE-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  (
    definition_name = '_PDFOutlineEntry'
    AND start_pos_row BETWEEN 77 AND 85
  )
  OR (
    definition_name IN (
      '_coerce_pdf_outline_title',
      '_coerce_pdf_destination_number',
      '_coerce_pdf_outline_destination_token'
    )
    AND start_pos_row BETWEEN 347 AND 374
  )
  OR (
    definition_name = '_pdf_optional_sequence'
    AND start_pos_row BETWEEN 798 AND 803
  )
  OR (
    definition_name IN (
      'add_outline',
      'clear_outlines',
      'outlines',
      '_shift_pdf_page_metadata_for_insert',
      '_shift_pdf_page_metadata_for_removal',
      '_outline_entry_payload',
      '_outline_objects'
    )
    AND (
      start_pos_row BETWEEN 1591 AND 1614
      OR start_pos_row BETWEEN 1659 AND 1668
      OR start_pos_row BETWEEN 1678 AND 1688
      OR start_pos_row BETWEEN 1705 AND 1745
    )
  )
  OR (
    definition_name = 'to_pdf_bytes'
    AND (
      start_pos_row BETWEEN 1866 AND 1873
      OR start_pos_row BETWEEN 1892 AND 1895
      OR start_pos_row BETWEEN 1897 AND 1905
    )
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 2020 AND 2028
  )
  OR (
    definition_name = 'parameters'
    AND start_pos_row BETWEEN 2051 AND 2052
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
    """Restrict a Cosmic Ray database to PDF outline proof-critical rows."""
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
