"""Filter Cosmic Ray work items to rounded regular-polygon P9."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DOMAIN_SQL = r"""
(
  module_path IN ('src/InkGen/component.py', 'src\InkGen\component.py')
  AND definition_name IN ('regular_polygon_corner_geometry', 'sample_rounded_polygon_path')
)
OR (
  module_path IN ('src/InkGen/svg_generator.py', 'src\InkGen\svg_generator.py')
  AND definition_name = 'generate_svg'
  AND start_pos_row BETWEEN 895 AND 940
)
OR (
  module_path IN ('src/InkGen/pdf_generator.py', 'src\InkGen\pdf_generator.py')
  AND (
    definition_name = '_rounded_polygon_path'
    OR (definition_name = 'generate_pdf' AND start_pos_row BETWEEN 1970 AND 1990)
  )
)
OR (
  module_path IN ('src/InkGen/dxf_generator.py', 'src\InkGen\dxf_generator.py')
  AND definition_name = '_component_to_entities'
  AND start_pos_row BETWEEN 208 AND 215
)
OR (
  module_path IN ('src/InkGen/raster_renderer.py', 'src\InkGen\raster_renderer.py')
  AND (
    (definition_name = '_validate_render_domain' AND start_pos_row BETWEEN 294 AND 304)
    OR (definition_name = '_render_component' AND start_pos_row BETWEEN 421 AND 425)
    OR definition_name = '_regular_polygon_points'
  )
)
"""

FILTER_SQL = f"""({DOMAIN_SQL})
AND operator_name NOT LIKE '%Bit%'
AND operator_name NOT LIKE '%Shift%'
AND operator_name NOT LIKE '%FloorDiv%'
AND operator_name NOT LIKE '%Mod%'
AND operator_name NOT LIKE '%Pow%'
"""


def filter_work_items(db_path: Path) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to P9 proof-critical work items."""
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
