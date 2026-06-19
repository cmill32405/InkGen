"""Filter Cosmic Ray work items to the PDF-P2 extraction-truth proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/extraction_truth.py'
AND definition_name IN (
  '__post_init__',
  'from_dict',
  'to_dict',
  'from_annotation',
  'annotate_extraction_truth',
  'get_extraction_truth_annotations',
  'set_extraction_truth_annotations',
  'serialize_extraction_truth_annotations',
  'restore_extraction_truth_annotations',
  'records_for_annotated_target',
  'bbox_to_pdf_points',
  'normalize_bbox',
  'sort_extraction_truth_records',
  'extraction_truth_json',
  '_coerce_annotation',
  '_is_number'
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND (
  operator_name = 'core/NumberReplacer'
  OR operator_name = 'core/AddNot'
  OR operator_name LIKE 'core/ReplaceComparisonOperator_%'
  OR operator_name LIKE 'core/ReplaceUnaryOperator_%'
  OR operator_name LIKE 'core/ReplaceBinaryOperator_Sub_%'
  OR operator_name = 'core/ReplaceAndWithOr'
  OR operator_name = 'core/ReplaceOrWithAnd'
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to PDF-P2 extraction-truth proof-critical work items."""
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
