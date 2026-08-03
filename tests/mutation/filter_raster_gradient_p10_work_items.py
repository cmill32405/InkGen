"""Filter Cosmic Ray work items to raster linear-gradient P10."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = r"""
module_path IN ('src/InkGen/raster_renderer.py', 'src\InkGen\raster_renderer.py')
AND (
  definition_name IN ('_validated_raster_gradient', '_render_linear_gradient_rectangle')
  OR (
    definition_name = '_validate_render_domain'
    AND start_pos_row BETWEEN 294 AND 296
  )
  OR (
    definition_name = '_render_component'
    AND start_pos_row BETWEEN 360 AND 389
  )
)
AND operator_name NOT LIKE '%Bit%'
AND operator_name NOT LIKE '%Shift%'
AND operator_name NOT LIKE '%FloorDiv%'
AND operator_name NOT LIKE '%Mod%'
AND operator_name NOT LIKE '%Pow%'
"""


def filter_work_items(db_path: Path) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to P10 proof-critical work items."""
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        cursor.execute(f"DELETE FROM work_items WHERE job_id NOT IN (SELECT job_id FROM mutation_specs WHERE {FILTER_SQL})")
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
