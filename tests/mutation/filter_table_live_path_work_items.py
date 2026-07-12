"""Filter Cosmic Ray work items to table live-path rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND (
  (
    module_path = 'src/InkGen/table.py'
    AND (
      (definition_name = 'cell_bounds' AND start_pos_row BETWEEN 170 AND 178)
      OR (definition_name = 'parameters' AND start_pos_row BETWEEN 300 AND 308)
      OR (definition_name = 'create_from_dict' AND start_pos_row BETWEEN 316 AND 365)
      OR (definition_name IN ('width', 'height') AND start_pos_row BETWEEN 201 AND 217)
    )
  )
  OR (
    module_path = 'src/InkGen/svg_generator.py'
    AND (
      (definition_name = '__init__' AND start_pos_row BETWEEN 1531 AND 1548)
      OR (definition_name = 'from_table' AND start_pos_row BETWEEN 1551 AND 1574)
      OR (definition_name = '_build_components' AND start_pos_row BETWEEN 1781 AND 1793)
      OR (definition_name = '_build_components' AND start_pos_row BETWEEN 1828 AND 1829)
    )
  )
  OR (
    module_path = 'src/InkGen/document_outputs.py'
    AND (
      (definition_name IN ('add_table', 'to_plain_text', 'to_html', 'to_markdown', 'to_rtf', 'to_docx_bytes') AND start_pos_row BETWEEN 149 AND 219)
      OR (definition_name IN ('_block_docx', '_block_html', '_block_rtf', '_table_docx') AND start_pos_row BETWEEN 274 AND 316)
      OR (definition_name IN ('_block_parameters', '_block_from_parameters', '_block_plain_text', '_block_markdown') AND start_pos_row BETWEEN 507 AND 549)
      OR (definition_name IN ('_table_plain_text', '_table_markdown', '_table_html') AND start_pos_row BETWEEN 556 AND 585)
      OR (definition_name = '_mm_to_twips' AND start_pos_row = 1096)
    )
  )
)
AND NOT (
  module_path = 'src/InkGen/table.py'
  AND definition_name = 'create_from_dict'
  AND start_pos_row IN (321, 351)
)
AND NOT (
  module_path = 'src/InkGen/document_outputs.py'
  AND definition_name = '_table_markdown'
  AND start_pos_row IN (565, 572)
)
AND NOT (
  module_path = 'src/InkGen/document_outputs.py'
  AND definition_name = '_table_html'
  AND start_pos_row = 583
  AND operator_name = 'core/NumberReplacer'
)
AND NOT (
  module_path = 'src/InkGen/svg_generator.py'
  AND definition_name = '_build_components'
  AND start_pos_row = 1788
  AND operator_name = 'core/NumberReplacer'
)
AND NOT (
  module_path = 'src/InkGen/svg_generator.py'
  AND definition_name = '_build_components'
  AND start_pos_row = 1792
  AND operator_name = 'core/ReplaceTrueWithFalse'
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to table live-path work items."""
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
