"""Filter Cosmic Ray work items to PDF font resource rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path LIKE '%pdf_generator.py'
AND (
  (
    definition_name IN ('font_resource_name', '_PDFFontResource', '_PDFFontRegistry', 'resource_name_for_style', 'resource_name_for_base_font', '_resource_name_for_resource', 'resources')
    AND start_pos_row BETWEEN 84 AND 180
  )
  OR (
    definition_name IN ('_pdf_embedded_font_for_style', '_pdf_requested_family_is_generic', '_pdf_embedded_font_resource', '_pdf_glyph_width', '_pdf_font_unit', '_pdf_name', '_pdf_font_file_object', '_pdf_font_descriptor_object', '_pdf_font_object')
    AND start_pos_row BETWEEN 313 AND 433
  )
  OR (
    definition_name = '_pdf_base_font_for_style'
    AND start_pos_row BETWEEN 436 AND 470
  )
  OR (
    definition_name = 'generate_pdf'
    AND start_pos_row BETWEEN 1298 AND 1313
  )
  OR (
    definition_name IN ('to_pdf_bytes', '_render_page_content')
    AND (
      start_pos_row BETWEEN 1336 AND 1377
      OR start_pos_row BETWEEN 1423 AND 1430
      OR start_pos_row BETWEEN 1456 AND 1525
    )
  )
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%'
AND operator_name != 'core/NumberReplacer'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to PDF font work items."""
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
