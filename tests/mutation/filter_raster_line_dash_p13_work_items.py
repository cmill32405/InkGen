"""Filter Cosmic Ray work items to raster line-dash P13."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DELETE_UNSELECTED_SQL = r"""
DELETE FROM work_items
WHERE job_id NOT IN (
  SELECT job_id FROM mutation_specs
  WHERE module_path IN ('src/InkGen/raster_renderer.py', 'src\InkGen\raster_renderer.py')
  AND definition_name IN (
    '_validated_line_dash',
    '_nonnegative_finite_number',
    '_line_dash_segments',
    '_dash_cursor',
    '_next_dash_slot',
    '_point_along_line',
    '_draw_dashed_line',
    '_draw_line_component'
  )
  AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
  AND operator_name NOT LIKE '%BitAnd%'
  AND operator_name NOT LIKE '%BitOr%'
  AND operator_name NOT LIKE '%BitXor%'
  AND operator_name NOT LIKE '%LShift%'
  AND operator_name NOT LIKE '%RShift%'
  AND operator_name NOT LIKE '%FloorDiv%'
)
"""


def filter_work_items(db_path: Path) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to P13 proof-critical helpers."""
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        cursor.execute(DELETE_UNSELECTED_SQL)
        cursor.execute("DELETE FROM mutation_specs WHERE job_id NOT IN (SELECT job_id FROM work_items)")
        cursor.execute("DELETE FROM work_results WHERE job_id NOT IN (SELECT job_id FROM work_items)")
        after = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
    return before, after


def main() -> None:
    """Run the command-line filter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", type=Path)
    args = parser.parse_args()
    before, after = filter_work_items(args.db_path)
    print(f"work_items: {before} -> {after}")


if __name__ == "__main__":
    main()
