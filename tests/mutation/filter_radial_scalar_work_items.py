"""Filter Cosmic Ray work items to the RADIAL-SCALAR-P2 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
  module_path = 'src/InkGen/component.py'
  AND (
    (definition_name = '__init__' AND start_pos_row BETWEEN 705 AND 706)
    OR (definition_name = '_coerce_polar_number' AND start_pos_row BETWEEN 715 AND 722)
    OR (definition_name = 'length' AND start_pos_row = 835)
    OR (definition_name = 'angle' AND start_pos_row = 858)
    OR (definition_name = '__init__' AND start_pos_row = 1088)
    OR (definition_name = '_coerce_positive_scalar' AND start_pos_row BETWEEN 1096 AND 1098)
    OR (definition_name = 'radius' AND start_pos_row = 1212)
    OR (definition_name = 'corner_radius' AND start_pos_row = 1237)
  )
)
OR (
  module_path = 'src/InkGen/svg_generator.py'
  AND (
    (definition_name = '__init__' AND start_pos_row = 831)
    OR (definition_name = '_coerce_radius' AND start_pos_row BETWEEN 836 AND 842)
    OR (definition_name = 'radius' AND start_pos_row = 897)
  )
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND (
    (definition_name = '__init__' AND start_pos_row = 650)
    OR (definition_name = '_coerce_radius' AND start_pos_row BETWEEN 655 AND 661)
  )
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to RADIAL-SCALAR-P2 proof-critical work items."""
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
