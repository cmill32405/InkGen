"""Filter Cosmic Ray work items to PDF-DOC-LINE-ANNOTATION-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  (
    definition_name = '_PDFLineAnnotation'
    AND start_pos_row BETWEEN 197 AND 205
  )
  OR (
    definition_name IN (
      '_coerce_pdf_annotation_color',
      '_coerce_pdf_line_annotation_point',
      '_pdf_line_annotation_rect'
    )
    AND (
      start_pos_row BETWEEN 575 AND 601
      OR start_pos_row BETWEEN 612 AND 648
    )
  )
  OR (
    definition_name IN (
      'add_line_annotation',
      'clear_line_annotations',
      'line_annotations',
      '_shift_pdf_page_metadata_for_insert',
      '_shift_pdf_page_metadata_for_removal',
      '_line_annotation_payload',
      '_line_annotations_by_page',
      '_line_annotation_object'
    )
    AND (
      start_pos_row BETWEEN 2369 AND 2413
      OR start_pos_row BETWEEN 2545 AND 2553
      OR start_pos_row BETWEEN 2664 AND 2672
      OR start_pos_row BETWEEN 3019 AND 3050
    )
  )
  OR (
    definition_name = 'to_pdf_bytes'
    AND start_pos_row BETWEEN 3180 AND 3234
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 3447 AND 3455
  )
  OR (
    definition_name = 'parameters'
    AND start_pos_row BETWEEN 3506 AND 3507
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
    """Restrict a Cosmic Ray database to PDF line annotation proof-critical rows."""
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
