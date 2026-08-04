"""Restrict a Cosmic Ray database to the PDF text-presentation slice."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND (
  (
    module_path = 'src/InkGen/style.py'
    AND definition_name IN ('__init__', 'create_from_dict', 'parameters', 'visible', 'character_spacing')
    AND (
      start_pos_row BETWEEN 1016 AND 1018
      OR start_pos_row BETWEEN 1037 AND 1038
      OR start_pos_row BETWEEN 1058 AND 1059
      OR start_pos_row BETWEEN 1289 AND 1310
    )
  )
  OR (
    module_path = 'src/InkGen/component.py'
    AND (
      (definition_name = '_compute_outline' AND start_pos_row = 2111)
      OR definition_name IN (
        '_outline_style_key', '_character_spacing_intervals',
        '_apply_character_spacing_bounds', '_outline_vertical_span'
      )
      OR (
        definition_name = '_fallback_outline'
        AND (start_pos_row BETWEEN 2207 AND 2210 OR start_pos_row = 2220)
      )
    )
  )
  OR (
    module_path = 'src/InkGen/pdf_generator.py'
    AND (
      definition_name = '_pdf_text_line_width'
      OR definition_name = '_pdf_text_aligned_x'
      OR (
        definition_name = 'generate_pdf'
        AND (start_pos_row BETWEEN 2123 AND 2124 OR start_pos_row BETWEEN 2129 AND 2132)
      )
    )
  )
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Keep only mutations that exercise the new presentation contract."""
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        if clear_results:
            cursor.execute("DELETE FROM work_results")
        cursor.execute(f"DELETE FROM work_items WHERE job_id NOT IN (SELECT job_id FROM mutation_specs WHERE {FILTER_SQL})")
        cursor.execute("DELETE FROM mutation_specs WHERE job_id NOT IN (SELECT job_id FROM work_items)")
        after = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
    return before, after


def main() -> None:
    """Filter the database named on the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", type=Path)
    parser.add_argument("--clear-results", action="store_true")
    arguments = parser.parse_args()
    before, after = filter_work_items(arguments.db_path, clear_results=arguments.clear_results)
    print(f"work_items: {before} -> {after}")


if __name__ == "__main__":
    main()
