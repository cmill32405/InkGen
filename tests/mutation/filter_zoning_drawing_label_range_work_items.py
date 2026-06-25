"""Filter Cosmic Ray work items to the ZONING-DRAWING-LABEL-RANGE-P2 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
(
  module_path = 'src/InkGen/drawing_components.py'
  AND definition_name = '_apply_parameters'
  AND start_pos_row = 624
)
OR (
  module_path = 'src/InkGen/drawing_components.py'
  AND definition_name = '_validate_zone_label_ranges'
  AND start_pos_row BETWEEN 626 AND 635
)
OR (
  module_path = 'src/InkGen/drawing_components.py'
  AND definition_name = '_zone_label_sequence_fits'
  AND start_pos_row BETWEEN 844 AND 850
)
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_BitAnd'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_BitOr'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_BitXor'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_Div'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_FloorDiv'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_LShift'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_Mod'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_Mul'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_Pow'
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_%_RShift'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to ZONING-DRAWING-LABEL-RANGE-P2 work items."""
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
