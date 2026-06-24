"""Filter Cosmic Ray work items to COMPONENT-GROUP-PAYLOAD-P2 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/component.py'
AND (
  (
    definition_name IN (
      '_component_group_payload',
      '_component_group_required_field',
      '_component_group_sequence',
      '_component_group_style_payload',
      '_component_group_class'
    )
    AND start_pos_row BETWEEN 2111 AND 2159
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 2191 AND 2224
  )
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to component-group payload-envelope items."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        if clear_results:
            cursor.execute("DELETE FROM work_results")
        cursor.execute(
            f"""
            DELETE FROM work_items
            WHERE job_id NOT IN (
                SELECT job_id FROM mutation_specs WHERE {FILTER_SQL}
            )
            """,
        )
        cursor.execute(
            """
            DELETE FROM mutation_specs
            WHERE job_id NOT IN (SELECT job_id FROM work_items)
            """,
        )
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
