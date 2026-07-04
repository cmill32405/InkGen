"""Filter Cosmic Ray work items to PDF-DOC-NAMED-DEST-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  (
    definition_name IN ('_PDFNamedDestination', '_PDFNamedDestinationLinkAnnotation')
    AND start_pos_row BETWEEN 108 AND 129
  )
  OR (
    definition_name IN (
      '_coerce_pdf_destination_name',
      '_coerce_pdf_destination_number',
      '_coerce_pdf_link_rect'
    )
    AND (
      start_pos_row BETWEEN 400 AND 425
      OR start_pos_row BETWEEN 443 AND 451
    )
  )
  OR (
    definition_name = '_pdf_optional_sequence'
    AND start_pos_row BETWEEN 874 AND 881
  )
  OR (
    definition_name IN (
      'add_named_destination',
      'clear_named_destinations',
      'named_destinations',
      'add_named_destination_link',
      'clear_named_destination_links',
      'named_destination_links',
      '_shift_pdf_page_metadata_for_insert',
      '_shift_pdf_page_metadata_for_removal',
      '_sorted_named_destinations',
      '_named_destination_payload',
      '_named_destination_link_payload',
      '_named_destination_links_by_page',
      '_named_destination_object',
      '_names_dictionary',
      '_named_destination_link_annotation_object'
    )
    AND (
      start_pos_row BETWEEN 1740 AND 1790
      OR start_pos_row BETWEEN 1862 AND 1880
      OR start_pos_row BETWEEN 1922 AND 1943
      OR start_pos_row BETWEEN 2059 AND 2118
    )
  )
  OR (
    definition_name = 'to_pdf_bytes'
    AND (
      start_pos_row BETWEEN 2242 AND 2253
      OR start_pos_row BETWEEN 2278 AND 2286
      OR start_pos_row BETWEEN 2286 AND 2287
    )
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 2441 AND 2456
  )
  OR (
    definition_name = 'parameters'
    AND start_pos_row BETWEEN 2485 AND 2492
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
    """Restrict a Cosmic Ray database to PDF named destination proof-critical rows."""
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
