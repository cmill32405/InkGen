"""Filter Cosmic Ray work items to multiline text P11."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = r"""
(
  module_path IN ('src/InkGen/drawing_components.py', 'src\InkGen\drawing_components.py')
  AND definition_name = 'normalize_text_lines'
)
OR (
  module_path IN ('src/InkGen/svg_generator.py', 'src\InkGen\svg_generator.py')
  AND definition_name = 'generate_svg'
  AND start_pos_row BETWEEN 1284 AND 1297
)
OR (
  module_path IN ('src/InkGen/raster_renderer.py', 'src\InkGen\raster_renderer.py')
  AND (
    definition_name IN ('_validated_raster_text', '_render_text')
    OR (definition_name = '_validate_render_domain' AND start_pos_row = 309)
  )
  AND (
    definition_name != '_render_text'
    OR start_pos_row IN (862, 864)
    OR start_pos_row BETWEEN 873 AND 882
  )
)
"""


def filter_work_items(db_path: Path) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to P11 proof-critical work items."""
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
