"""Filter Cosmic Ray work items to raster line-join P15."""

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
    '_validated_line_join',
    '_validate_raster_stroke_style',
    '_render_rectangle_component',
    '_draw_styled_polygon',
    '_draw_regular_polygon_component',
    '_bevel_join_polygon',
    '_draw_joined_polyline',
    '_draw_polygon',
    '_render_component'
  )
  AND (definition_name != '_render_component' OR start_pos_row IN (464, 486, 508))
  AND (definition_name != '_render_rectangle_component' OR start_pos_row >= 396)
  AND (definition_name != '_draw_styled_polygon' OR start_pos_row >= 420)
  AND (definition_name != '_draw_regular_polygon_component' OR start_pos_row = 440)
  AND (definition_name != '_validate_raster_stroke_style' OR start_pos_row IN (336, 346))
  AND (definition_name != '_draw_joined_polyline' OR start_pos_row >= 1218)
  AND (definition_name != '_bevel_join_polygon' OR start_pos_row >= 1185)
  AND (definition_name != '_draw_polygon' OR start_pos_row >= 1260)
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
    """Restrict a Cosmic Ray database to P15 proof-critical definitions."""
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
