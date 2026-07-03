"""Filter Cosmic Ray work items to FLOW-DOCUMENT-MARKDOWN-P3 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path IN ('src/InkGen/document_outputs.py', 'src\\InkGen\\document_outputs.py')
AND (
  (
    definition_name = 'to_markdown'
    AND start_pos_row BETWEEN 200 AND 204
  )
  OR (
    definition_name = 'create_markdown'
    AND start_pos_row BETWEEN 244 AND 246
  )
  OR (
    definition_name IN (
      '_block_markdown',
      '_paragraph_markdown',
      '_table_markdown',
      '_markdown_escape',
      '_markdown_table_cell'
    )
    AND start_pos_row BETWEEN 544 AND 615
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
    """Restrict a Cosmic Ray database to Markdown proof-critical work items."""
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
