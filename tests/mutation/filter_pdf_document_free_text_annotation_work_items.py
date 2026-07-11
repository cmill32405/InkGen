"""Filter Cosmic Ray work items to PDF FreeText annotation proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
(
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = '_PDFFreeTextAnnotation'
  AND start_pos_row BETWEEN 167 AND 176
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = '_coerce_pdf_free_text_font_size'
  AND start_pos_row BETWEEN 613 AND 623
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name IN ('add_free_text_annotation', 'clear_free_text_annotations', 'free_text_annotations')
  AND start_pos_row BETWEEN 2336 AND 2363
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = '_shift_pdf_page_metadata_for_insert'
  AND start_pos_row BETWEEN 2584 AND 2593
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = '_shift_pdf_page_metadata_for_removal'
  AND start_pos_row BETWEEN 2710 AND 2719
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name IN ('_free_text_annotation_payload', '_free_text_annotations_by_page', '_free_text_annotation_object')
  AND start_pos_row BETWEEN 3022 AND 3058
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = 'to_pdf_bytes'
  AND (
    start_pos_row = 3297
    OR start_pos_row = 3312
    OR start_pos_row BETWEEN 3349 AND 3350
  )
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = 'create_from_dict'
  AND start_pos_row BETWEEN 3547 AND 3556
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = 'parameters'
  AND start_pos_row BETWEEN 3627 AND 3630
)
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitAnd_%'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_FloorDiv_%'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_Mod_%'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_Pow_%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to FreeText annotation proof-critical rows."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        if clear_results:
            cursor.execute("DELETE FROM work_results")
        cursor.execute(f"DELETE FROM work_items WHERE job_id NOT IN (SELECT job_id FROM mutation_specs WHERE {FILTER_SQL})")
        cursor.execute("DELETE FROM mutation_specs WHERE job_id NOT IN (SELECT job_id FROM work_items)")
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
