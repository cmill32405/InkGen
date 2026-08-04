"""Filter Cosmic Ray work items to raster line-cap P14."""

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
    '_validated_line_cap',
    '_validate_raster_stroke_style',
    '_draw_dispatched_line_component',
    '_line_cap_dash_geometry',
    '_zero_length_dash_centers',
    '_unit_tangent',
    '_square_cap_polygon',
    '_draw_capped_segment',
    '_draw_capped_line_component'
  )
  AND (definition_name != '_validated_line_dash' OR start_pos_row IN (489, 490))
  AND (definition_name != '_validate_raster_stroke_style' OR start_pos_row IN (337, 338, 341, 343))
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
    """Restrict a Cosmic Ray database to P14 proof-critical helpers."""
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
