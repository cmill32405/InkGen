"""Filter Cosmic Ray work items to measured raster path dashes P18."""

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
    '_validate_raster_stroke_style',
    '_validate_dashed_path_miter_geometry',
    '_sampled_path_cumulative_distances',
    '_path_dash_intervals',
    '_zero_length_dash_distances',
    '_path_edge_index',
    '_path_point_at_distance',
    '_path_tangent_at_distance',
    '_path_points_between',
    '_path_join_records_with_distances',
    '_path_dash_run',
    '_join_closed_dash_seam',
    '_dashed_path_subpath',
    '_dashed_path_geometry',
    '_draw_path_strokes',
    '_painted_path_join_records',
    '_flatten_dash_sections',
    '_draw_dashed_path_subpath',
    '_semantic_path_join_records',
    '_semantic_path_join_triples'
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
    """Restrict a Cosmic Ray database to P18 proof-critical definitions."""
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
