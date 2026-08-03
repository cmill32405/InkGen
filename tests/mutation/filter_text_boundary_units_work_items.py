"""Filter Cosmic Ray work items to TEXT-BOUNDARY-UNITS-P1 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
  (
    module_path IN ('src/InkGen/component.py', 'src\\InkGen\\component.py')
    AND (
      (definition_name = '_outline_font_sizes' AND start_pos_row = 2202)
      OR (definition_name = '_fallback_outline' AND start_pos_row IN (2206, 2208))
    )
  )
  OR (
    module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
    AND definition_name = '_outline_font_sizes'
    AND start_pos_row = 2094
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
"""


def filter_work_items(db_path: Path) -> tuple[int, int]:
    """Restrict one Cosmic Ray database to proof-critical changed rows."""
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        cursor.execute(f"DELETE FROM work_items WHERE job_id NOT IN (SELECT job_id FROM mutation_specs WHERE {FILTER_SQL})")
        cursor.execute("DELETE FROM mutation_specs WHERE job_id NOT IN (SELECT job_id FROM work_items)")
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
