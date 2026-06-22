"""Filter Cosmic Ray work items to the LAYER-GROUP-P2 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
  module_path = 'src/InkGen/document.py'
  AND (
    (
      definition_name IN ('parameters', 'create_from_dict')
      AND start_pos_row BETWEEN 61 AND 84
    )
    OR (
      definition_name = 'remove_component_group'
      AND start_pos_row BETWEEN 194 AND 207
    )
    OR (
      definition_name = 'groups'
      AND start_pos_row BETWEEN 217 AND 219
    )
    OR (
      definition_name = '_restore_group_name_lookup'
      AND start_pos_row BETWEEN 248 AND 255
    )
  )
)
OR (
  module_path = 'src/InkGen/svg_generator.py'
  AND definition_name = '_iter_layer_groups'
  AND start_pos_row BETWEEN 1654 AND 1656
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND definition_name = '_iter_layer_groups'
  AND start_pos_row BETWEEN 837 AND 840
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to LAYER-GROUP-P2 proof-critical work items."""
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
