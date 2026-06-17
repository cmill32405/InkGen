"""Filter Cosmic Ray work items to the CURVE-P1 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
  module_path = 'src/InkGen/component.py'
  AND definition_name = 'points'
  AND start_pos_row BETWEEN 1452 AND 1464
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = '_quadratic_to_cubic'
  AND start_pos_row BETWEEN 181 AND 190
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = 'generate_pdf'
  AND start_pos_row BETWEEN 382 AND 387
)
OR (
  module_path = 'src/InkGen/dxf_generator.py'
  AND definition_name = '_component_to_entities'
  AND start_pos_row BETWEEN 103 AND 105
)
OR (
  module_path = 'src/InkGen/dxf_generator.py'
  AND definition_name = '_lwpolyline_entity'
  AND start_pos_row BETWEEN 133 AND 145
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to CURVE-P1 proof-critical work items."""
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
