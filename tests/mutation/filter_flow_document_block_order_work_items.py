"""Filter Cosmic Ray work items to flow-document block order rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/document_outputs.py'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND (
  (definition_name IN ('add_paragraph', 'add_table', 'add_drawing_group') AND start_pos_row BETWEEN 143 AND 159)
  OR (definition_name = 'parameters' AND start_pos_row BETWEEN 162 AND 168)
  OR (definition_name = 'create_from_dict' AND start_pos_row BETWEEN 172 AND 180)
  OR (definition_name IN ('to_plain_text', 'to_html', 'to_markdown', 'to_rtf') AND start_pos_row BETWEEN 183 AND 214)
  OR (definition_name = '_docx_document_xml' AND start_pos_row BETWEEN 256 AND 258)
  OR (definition_name IN ('_block_docx', '_block_html', '_block_rtf') AND start_pos_row BETWEEN 274 AND 294)
  OR (definition_name = '_block_parameters' AND start_pos_row BETWEEN 507 AND 512)
  OR (definition_name = '_block_from_parameters' AND start_pos_row BETWEEN 527 AND 532)
  OR (definition_name = '_block_plain_text' AND start_pos_row BETWEEN 536 AND 541)
  OR (definition_name = '_block_markdown' AND start_pos_row BETWEEN 544 AND 549)
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to flow-document block-order checks."""
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
