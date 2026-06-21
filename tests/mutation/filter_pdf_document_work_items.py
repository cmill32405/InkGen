"""Filter Cosmic Ray work items to the PDF-DOC-P2 proof-critical rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
module_path = 'src/InkGen/pdf_generator.py'
AND (
  (definition_name = '_iter_layer_groups' AND start_pos_row BETWEEN 835 AND 840)
  OR (definition_name = '_render_page_content' AND start_pos_row IN (899, 900, 901, 902, 903, 907, 908))
  OR (definition_name = 'extraction_truth' AND start_pos_row IN (918, 919, 920, 921, 922, 925, 926, 927, 928, 929, 930, 931, 932))
  OR (definition_name = 'grammar_truth' AND start_pos_row IN (951, 952, 953, 954, 955, 958, 959, 960, 961, 962, 963, 964, 965))
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND (
  operator_name = 'core/NumberReplacer'
  OR operator_name = 'core/AddNot'
  OR operator_name LIKE 'core/ReplaceComparisonOperator_%'
  OR operator_name LIKE 'core/ReplaceUnaryOperator_%'
  OR operator_name IN (
    'core/ReplaceBinaryOperator_Add_Sub',
    'core/ReplaceBinaryOperator_Sub_Add',
    'core/ReplaceBinaryOperator_Mul_Div',
    'core/ReplaceBinaryOperator_Div_Mul'
  )
  OR operator_name = 'core/ReplaceAndWithOr'
  OR operator_name = 'core/ReplaceOrWithAnd'
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to PDF-DOC-P2 proof-critical work items."""
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
