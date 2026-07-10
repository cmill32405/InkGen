"""Filter Cosmic Ray work items to PDF-GROUP-CLIP-PATH-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
AND (
  (
    definition_name IN (
      '_path_command_payload',
      '_clone_path_command',
      '_coerce_pdf_clip_path'
    )
    AND start_pos_row BETWEEN 602 AND 643
  )
  OR (
    definition_name = '_pdf_path_command_operators'
    AND start_pos_row BETWEEN 1053 AND 1155
  )
  OR (
    definition_name = '_path_command_from_dict'
    AND start_pos_row BETWEEN 1265 AND 1277
  )
  OR (
    definition_name IN (
      'parameters',
      '_command_operators'
    )
    AND start_pos_row BETWEEN 1555 AND 1561
  )
  OR (
    definition_name IN (
      '__init__',
      'set_clip_path',
      'clear_clip_path',
      'clip_path',
      'create_from_dict',
      'parameters',
      'generate_pdf'
    )
    AND (
      start_pos_row BETWEEN 1816 AND 1823
      OR start_pos_row BETWEEN 1850 AND 1865
      OR start_pos_row BETWEEN 1884 AND 1887
      OR start_pos_row BETWEEN 1923 AND 1927
      OR start_pos_row BETWEEN 1954 AND 1979
    )
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND operator_name NOT LIKE '%BitAnd%'
AND operator_name NOT LIKE '%BitOr%'
AND operator_name NOT LIKE '%BitXor%'
AND operator_name NOT LIKE '%LShift%'
AND operator_name NOT LIKE '%RShift%'
AND operator_name NOT LIKE '%Pow%'
AND operator_name NOT LIKE '%FloorDiv%'
AND operator_name NOT LIKE '%Mod%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to PDF group clip-path proof-critical rows."""
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
