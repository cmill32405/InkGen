"""Filter Cosmic Ray work items to font renderer live-path rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND (
  (
    module_path = 'src/InkGen/svg_generator.py'
    AND definition_name = 'generate_svg'
    AND start_pos_row BETWEEN 1179 AND 1190
  )
  OR (
    module_path = 'src/InkGen/pdf_generator.py'
    AND definition_name = 'generate_pdf'
    AND start_pos_row IN (1901, 1918)
  )
  OR (
    module_path = 'src/InkGen/dxf_generator.py'
    AND definition_name = '_text_entity'
    AND start_pos_row IN (339, 347)
  )
  OR (
    module_path = 'src/InkGen/document_outputs.py'
    AND definition_name = '_run_properties_docx'
    AND start_pos_row BETWEEN 362 AND 370
  )
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to font renderer live paths."""
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
