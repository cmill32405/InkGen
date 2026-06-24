"""Filter Cosmic Ray work items to the RECT-P1 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
(
  module_path = 'src/InkGen/component.py'
  AND definition_name = 'normalize_rectangle_corner_radii'
  AND start_pos_row BETWEEN 23 AND 49
)
OR (
  module_path = 'src/InkGen/svg_generator.py'
  AND definition_name IN ('_radius_check', 'corner_radii', 'generate_svg')
  AND start_pos_row BETWEEN 260 AND 335
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = '_rounded_rectangle_path'
  AND start_pos_row BETWEEN 182 AND 203
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name IN ('corner_radii', 'generate_pdf')
  AND start_pos_row BETWEEN 279 AND 294
)
OR (
  module_path = 'src/InkGen/drawing_components.py'
  AND definition_name = 'to_component'
  AND start_pos_row BETWEEN 73 AND 82
)
OR (
  module_path = 'src/InkGen/dxf_generator.py'
  AND definition_name = '_component_to_entities'
  AND start_pos_row BETWEEN 94 AND 96
)
OR (
  module_path = 'src/InkGen/dxf_generator.py'
  AND definition_name IN ('_rectangle_points', '_append_corner_arc')
  AND start_pos_row BETWEEN 116 AND 165
)
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to RECT-P1 proof-critical work items."""
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
