"""Filter Cosmic Ray work items to the LINEAR-GRADIENT-P1 contract."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
  module_path IN ('src/InkGen/gradients.py', 'src\\InkGen\\gradients.py')
  OR (
    module_path IN ('src/InkGen/drawing_components.py', 'src\\InkGen\\drawing_components.py')
    AND start_pos_row BETWEEN 166 AND 192
  )
  OR (
    module_path IN ('src/InkGen/svg_generator.py', 'src\\InkGen\\svg_generator.py')
    AND (
      (definition_name = '_style_properties' AND start_pos_row BETWEEN 212 AND 214)
      OR start_pos_row BETWEEN 325 AND 503
      OR start_pos_row = 512
    )
  )
  OR (
    module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
    AND (
      definition_name = 'shading_resource_name'
      OR definition_name = 'resource_name_for_gradient'
      OR start_pos_row BETWEEN 945 AND 985
      OR start_pos_row BETWEEN 1573 AND 1666
      OR (definition_name = 'to_pdf_bytes' AND start_pos_row IN (3562, 3565, 3579, 3582))
    )
  )
  OR (
    module_path IN ('src/InkGen/extraction_truth.py', 'src\\InkGen\\extraction_truth.py')
    AND definition_name IN (
      'ExtractionTruthRecord',
      'from_annotation',
      'to_dict',
      'records_for_annotated_target',
      'sort_extraction_truth_records',
      '_target_truth_parameters'
    )
  )
  OR (
    module_path IN ('src/InkGen/dxf_generator.py', 'src\\InkGen\\dxf_generator.py')
    AND start_pos_row IN (198, 199)
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to gradient proof-critical work items."""
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
