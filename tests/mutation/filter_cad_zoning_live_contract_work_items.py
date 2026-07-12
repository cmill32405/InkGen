"""Filter Cosmic Ray work items to legacy CAD zoning live-contract rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/cad_component_groups.py'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND (
  (definition_name = '__init__' AND start_pos_row IN (69, 72, 75, 112, 115, 118, 123, 125, 126, 127, 128))
  OR (definition_name = '_create_zoning' AND start_pos_row IN (197, 198, 200, 209, 211, 221, 232, 233, 234, 261, 262, 263, 264, 272, 277, 288, 289, 290, 320, 321, 322, 323))
  OR (definition_name = 'parameters' AND start_pos_row IN (350, 351, 354, 355, 356, 357, 358))
  OR (definition_name = 'create_from_dict' AND start_pos_row IN (376, 381, 382, 384, 389, 399, 400, 401))
)
AND NOT (
  definition_name = '_create_zoning'
  AND start_pos_row IN (230, 286)
)
AND NOT (
  definition_name IN ('__init__', 'create_from_dict')
  AND operator_name LIKE 'core/ReplaceComparisonOperator_Is_%'
)
AND NOT (
  definition_name = '__init__'
  AND start_pos_row = 115
  AND (
    operator_name = 'core/ReplaceComparisonOperator_NotEq_Gt'
    OR operator_name = 'core/ReplaceComparisonOperator_LtE_Eq'
    OR operator_name = 'core/NumberReplacer'
  )
)
AND NOT (
  definition_name = '_create_zoning'
  AND start_pos_row IN (197, 198, 200, 209, 221, 232, 233, 234, 263, 272, 277, 288, 289, 290, 322)
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to CAD zoning live-contract work items."""
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
