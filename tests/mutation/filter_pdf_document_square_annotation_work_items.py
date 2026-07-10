"""Filter Cosmic Ray work items to PDF-DOC-SQUARE-ANNOTATION-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  (
    definition_name = '_PDFSquareAnnotation'
    AND start_pos_row BETWEEN 171 AND 178
  )
  OR (
    definition_name IN (
      '_coerce_pdf_annotation_color'
    )
    AND start_pos_row BETWEEN 547 AND 573
  )
  OR (
    definition_name IN (
      'add_square_annotation',
      'clear_square_annotations',
      'square_annotations',
      '_shift_pdf_page_metadata_for_insert',
      '_shift_pdf_page_metadata_for_removal',
      '_square_annotation_payload',
      '_square_annotations_by_page',
      '_square_annotation_object'
    )
    AND (
      start_pos_row BETWEEN 2144 AND 2166
      OR start_pos_row BETWEEN 2279 AND 2288
      OR start_pos_row BETWEEN 2376 AND 2386
      OR start_pos_row BETWEEN 2674 AND 2705
    )
  )
  OR (
    definition_name = 'to_pdf_bytes'
    AND (
      start_pos_row BETWEEN 2831 AND 2844
      OR start_pos_row BETWEEN 2878 AND 2879
    )
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 3076 AND 3083
  )
  OR (
    definition_name = 'parameters'
    AND start_pos_row BETWEEN 3126 AND 3129
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
    """Restrict a Cosmic Ray database to PDF square annotation proof-critical rows."""
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
