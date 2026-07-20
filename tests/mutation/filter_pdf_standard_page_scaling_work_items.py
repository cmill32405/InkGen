"""Filter Cosmic Ray work items to the ADR-0028 coordinate conversion paths."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  definition_name IN (
    '_pdf_points_per_canvas_unit',
    '_scaled_pdf_number',
    '_scaled_pdf_rectangle',
    '_scaled_pdf_destination_token',
    '_scale_pdf_truth_payload'
  )
  OR (definition_name = 'build' AND start_pos_row = 432)
  OR (definition_name = '_page_box_operators' AND start_pos_row = 2896)
  OR (definition_name = '_outline_destination' AND start_pos_row BETWEEN 2941 AND 2942)
  OR (definition_name = '_outline_objects' AND start_pos_row BETWEEN 2989 AND 2992)
  OR (definition_name = '_uri_link_annotation_object' AND start_pos_row = 3025)
  OR (definition_name = '_page_link_annotation_object' AND start_pos_row IN (3059, 3062, 3063))
  OR (definition_name = '_named_destination_object' AND start_pos_row BETWEEN 3110 AND 3111)
  OR (definition_name = '_names_dictionary' AND start_pos_row BETWEEN 3120 AND 3122)
  OR (definition_name = '_named_destination_link_annotation_object' AND start_pos_row = 3133)
  OR (definition_name = '_text_annotation_object' AND start_pos_row = 3161)
  OR (definition_name = '_free_text_annotation_object' AND start_pos_row IN (3188, 3191))
  OR (definition_name = '_highlight_annotation_object' AND start_pos_row BETWEEN 3221 AND 3224)
  OR (definition_name = '_square_annotation_object' AND start_pos_row IN (3252, 3255))
  OR (definition_name = '_circle_annotation_object' AND start_pos_row IN (3280, 3283))
  OR (definition_name = '_line_annotation_object' AND start_pos_row IN (3309, 3310, 3313))
  OR (
    definition_name = 'to_pdf_bytes'
    AND start_pos_row IN (3471, 3475, 3476, 3488, 3489, 3496, 3500, 3503, 3504, 3508, 3510, 3512, 3514, 3516, 3518, 3520, 3527, 3538)
  )
  OR (definition_name = '_render_page_content' AND start_pos_row BETWEEN 3558 AND 3561)
  OR (definition_name = 'extraction_truth' AND start_pos_row BETWEEN 3603 AND 3604)
  OR (definition_name = 'grammar_truth' AND start_pos_row BETWEEN 3637 AND 3638)
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to ADR-0028 proof-critical work items."""
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
