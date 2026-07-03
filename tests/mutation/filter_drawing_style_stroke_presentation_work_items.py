"""Filter Cosmic Ray work items to STYLE-DRAWING-STROKE-P2 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
  module_path IN ('src/InkGen/style.py', 'src\\InkGen\\style.py')
  AND (
    (
      definition_name IN (
        '_coerce_positive_float',
        '_coerce_stroke_dasharray',
        '_coerce_line_cap',
        '_coerce_line_join'
      )
      AND start_pos_row BETWEEN 53 AND 87
    )
    OR (
      definition_name IN (
        '__init__',
        'create_from_dict',
        'stroke_dasharray',
        'stroke_dash_offset',
        'stroke_linecap',
        'stroke_linejoin',
        'stroke_miterlimit',
        'parameters'
      )
      AND start_pos_row BETWEEN 311 AND 592
    )
  )
)
OR (
  module_path IN ('src/InkGen/svg_generator.py', 'src\\InkGen\\svg_generator.py')
  AND definition_name = '_style_properties'
  AND start_pos_row BETWEEN 197 AND 227
)
OR (
  module_path IN ('src/InkGen/pdf_generator.py', 'src\\InkGen\\pdf_generator.py')
  AND (
    (
      definition_name = '_pdf_stroke_presentation_operators'
      AND start_pos_row BETWEEN 309 AND 326
    )
    OR (
      definition_name = '_style_operators'
      AND start_pos_row BETWEEN 569 AND 590
    )
  )
)
"""

EXCLUSIONS_SQL = """
operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
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
    """Restrict a Cosmic Ray database to stroke-presentation proof-critical rows."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        before = cursor.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        if clear_results:
            cursor.execute("DELETE FROM work_results")
        cursor.execute(
            f"""
            DELETE FROM work_items
            WHERE job_id NOT IN (
                SELECT job_id FROM mutation_specs
                WHERE ({FILTER_SQL})
                AND {EXCLUSIONS_SQL}
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
