"""Filter Cosmic Ray work items to PDF-DOC-PAGE-LINK-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  (
    definition_name = '_PDFPageLinkAnnotation'
    AND start_pos_row BETWEEN 96 AND 108
  )
  OR (
    definition_name IN (
      '_coerce_pdf_destination_number',
      '_coerce_pdf_link_rect'
    )
    AND (
      start_pos_row BETWEEN 379 AND 389
      OR start_pos_row BETWEEN 410 AND 418
    )
  )
  OR (
    definition_name = '_pdf_optional_sequence'
    AND start_pos_row BETWEEN 841 AND 848
  )
  OR (
    definition_name IN (
      'add_page_link',
      'clear_page_links',
      'page_links',
      '_shift_pdf_page_metadata_for_insert',
      '_shift_pdf_page_metadata_for_removal',
      '_page_link_payload',
      '_page_links_by_page',
      '_page_link_annotation_object'
    )
    AND (
      start_pos_row BETWEEN 1677 AND 1705
      OR start_pos_row BETWEEN 1766 AND 1777
      OR start_pos_row BETWEEN 1806 AND 1817
      OR start_pos_row BETWEEN 1900 AND 1934
    )
  )
  OR (
    definition_name = 'to_pdf_bytes'
    AND (
      start_pos_row BETWEEN 2055 AND 2069
      OR start_pos_row BETWEEN 2079 AND 2089
    )
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 2238 AND 2247
  )
  OR (
    definition_name = 'parameters'
    AND start_pos_row BETWEEN 2274 AND 2275
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
    """Restrict a Cosmic Ray database to PDF internal page link proof-critical rows."""
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
