"""Filter Cosmic Ray work items to PDF text encoding boundary rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path LIKE '%pdf_generator.py'
AND (
  (
    definition_name = '_coerce_pdf_text_content'
    AND start_pos_row BETWEEN 463 AND 479
  )
  OR (
    definition_name = '_escape_pdf_text_string'
    AND start_pos_row BETWEEN 482 AND 495
  )
  OR (
    definition_name = '_pdf_glyph_width'
    AND start_pos_row BETWEEN 993 AND 1001
  )
  OR (
    definition_name = '_pdf_tounicode_cmap_object'
    AND start_pos_row BETWEEN 1038 AND 1065
  )
  OR (
    definition_name = '__init__'
    AND start_pos_row BETWEEN 1874 AND 1880
  )
  OR (
    definition_name = 'create_from_dict'
    AND start_pos_row BETWEEN 1882 AND 1890
  )
  OR (
    definition_name = 'generate_pdf'
    AND start_pos_row BETWEEN 1894 AND 1896
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
    """Restrict a Cosmic Ray database to PDF text encoding work items."""
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
