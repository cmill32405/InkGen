"""Filter Cosmic Ray work items to the BOUNDARY-CANVAS-P1 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/boundary.py'
AND (
  (
    definition_name IN ('_coerce_finite_number', '_coerce_positive_number', '_normalize_hull')
    AND start_pos_row BETWEEN 13 AND 66
  )
  OR (
    definition_name = '__init__'
    AND start_pos_row IN (75, 195)
  )
  OR (
    definition_name IN ('_hull_check', 'boundary_check')
    AND start_pos_row BETWEEN 115 AND 186
  )
  OR (
    definition_name IN ('width', 'height')
    AND start_pos_row IN (251, 262)
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to BOUNDARY-CANVAS-P1 proof-critical work items."""
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
