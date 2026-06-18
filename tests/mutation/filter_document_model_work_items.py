"""Filter Cosmic Ray work items to the DOCUMENT-MODEL-P1 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/document.py'
AND (
  (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 289 AND 295
  )
  OR (
    definition_name = 'add_page'
    AND start_pos_row BETWEEN 571 AND 587
  )
  OR (
    definition_name = 'remove_page'
    AND start_pos_row BETWEEN 600 AND 604
  )
  OR (
    definition_name = 'page'
    AND start_pos_row BETWEEN 615 AND 616
  )
  OR (
    definition_name IN ('_validate_insert_position', '_validate_existing_position', '_page_canvas_compatibility')
    AND start_pos_row BETWEEN 627 AND 650
  )
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to DOCUMENT-MODEL-P1 proof-critical work items."""
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
