"""Filter Cosmic Ray work items to the BEZIER-FINITE-P2 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/component.py'
AND (
  (definition_name = '_coerce_point' AND start_pos_row BETWEEN 1508 AND 1514)
  OR (definition_name = '_coerce_finite_number' AND start_pos_row BETWEEN 1517 AND 1526)
  OR (definition_name = 'start_point' AND start_pos_row BETWEEN 1552 AND 1553)
  OR (definition_name = 'control_point' AND start_pos_row BETWEEN 1561 AND 1562)
  OR (definition_name = 'end_point' AND start_pos_row BETWEEN 1570 AND 1571)
  OR (definition_name = '_coerce_point' AND start_pos_row BETWEEN 1608 AND 1614)
  OR (definition_name = '_coerce_finite_number' AND start_pos_row BETWEEN 1617 AND 1626)
  OR (definition_name = 'start_point' AND start_pos_row BETWEEN 1654 AND 1655)
  OR (definition_name = 'control_point1' AND start_pos_row BETWEEN 1663 AND 1664)
  OR (definition_name = 'control_point2' AND start_pos_row BETWEEN 1672 AND 1673)
  OR (definition_name = 'end_point' AND start_pos_row BETWEEN 1681 AND 1682)
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to BEZIER-FINITE-P2 proof-critical work items."""
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
