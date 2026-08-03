"""Filter Cosmic Ray work items to the raster sampled-path P6 slice."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = r"""
module_path IN ('src/InkGen/raster_renderer.py', 'src\InkGen\raster_renderer.py')
AND (
  (definition_name = '_validate_render_domain' AND start_pos_row BETWEEN 296 AND 299)
  OR (definition_name = '_render_component' AND start_pos_row BETWEEN 361 AND 364)
  OR definition_name = '_reflect_path_control'
  OR (
    definition_name = '_sampled_path_subpaths'
    AND (
      start_pos_row BETWEEN 416 AND 417
      OR start_pos_row BETWEEN 423 AND 424
      OR start_pos_row BETWEEN 431 AND 432
      OR start_pos_row BETWEEN 444 AND 455
      OR start_pos_row BETWEEN 459 AND 503
    )
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND operator_name NOT LIKE '%BitAnd%'
AND operator_name NOT LIKE '%BitOr%'
AND operator_name NOT LIKE '%BitXor%'
AND operator_name NOT LIKE '%LShift%'
AND operator_name NOT LIKE '%RShift%'
AND operator_name NOT LIKE '%FloorDiv%'
"""


def filter_work_items(db_path: Path) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to P6 path proof obligations."""
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        cursor.execute(f"DELETE FROM work_items WHERE job_id NOT IN (SELECT job_id FROM mutation_specs WHERE {FILTER_SQL})")
        cursor.execute("DELETE FROM mutation_specs WHERE job_id NOT IN (SELECT job_id FROM work_items)")
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
