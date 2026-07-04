"""Filter Cosmic Ray work items to PDF-DOC-LINK-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  (
    definition_name = '_PDFUriLinkAnnotation'
    AND start_pos_row BETWEEN 87 AND 96
  )
  OR (
    definition_name IN (
      '_coerce_pdf_uri',
      '_coerce_pdf_link_rect'
    )
    AND start_pos_row BETWEEN 384 AND 407
  )
  OR (
    definition_name = '_pdf_optional_sequence'
    AND start_pos_row BETWEEN 828 AND 835
  )
  OR (
    definition_name IN (
      'add_uri_link',
      'clear_uri_links',
      'uri_links',
      '_shift_pdf_page_metadata_for_insert',
      '_shift_pdf_page_metadata_for_removal',
      '_uri_link_payload',
      '_uri_links_by_page',
      '_uri_link_annotation_object'
    )
    AND (
      start_pos_row BETWEEN 1648 AND 1664
      OR start_pos_row BETWEEN 1717 AND 1725
      OR start_pos_row BETWEEN 1745 AND 1754
      OR start_pos_row BETWEEN 1812 AND 1835
    )
  )
  OR (
    definition_name = 'to_pdf_bytes'
    AND (
      start_pos_row BETWEEN 1957 AND 1969
      OR start_pos_row BETWEEN 1975 AND 1983
    )
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 2125 AND 2131
  )
  OR (
    definition_name = 'parameters'
    AND start_pos_row BETWEEN 2156 AND 2157
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
    """Restrict a Cosmic Ray database to PDF URI link proof-critical rows."""
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
