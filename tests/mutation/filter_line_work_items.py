"""Filter Cosmic Ray work items to the LINE-P1 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
(
  module_path = 'src/InkGen/component.py'
  AND definition_name IN ('__init__', '_coerce_point', '_check_inputs', 'point_1', 'point_2', 'points', 'bbox', 'convex_hull')
  AND start_pos_row BETWEEN 202 AND 367
)
OR (
  module_path = 'src/InkGen/svg_generator.py'
  AND definition_name IN ('generate_svg', 'parameters', 'create_from_dict')
  AND start_pos_row BETWEEN 362 AND 415
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name IN ('generate_pdf', 'parameters', 'create_from_dict')
  AND start_pos_row BETWEEN 304 AND 323
)
OR (
  module_path = 'src/InkGen/drawing_components.py'
  AND definition_name = 'to_component'
  AND start_pos_row BETWEEN 97 AND 106
)
OR (
  module_path = 'src/InkGen/dxf_generator.py'
  AND definition_name = '_component_to_entities'
  AND start_pos_row BETWEEN 91 AND 93
)
OR (
  module_path = 'src/InkGen/dxf_generator.py'
  AND definition_name = '_line_entity'
  AND start_pos_row BETWEEN 168 AND 182
)
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to LINE-P1 proof-critical work items."""
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
