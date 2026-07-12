"""Filter Cosmic Ray work items to paragraph live-path rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND operator_name NOT LIKE 'core/ReplaceComparisonOperator_Is_%'
AND (
  (
    module_path = 'src/InkGen/paragraph.py'
    AND (
      (definition_name = 'layout_lines' AND start_pos_row IN (441, 443, 444, 445, 446, 448, 449, 452))
      OR (definition_name = 'to_drawing_group' AND start_pos_row IN (457, 458, 459))
      OR (definition_name = '_wrap_text' AND start_pos_row IN (463, 466, 467, 470, 472, 473, 474, 477, 478, 480))
      OR (definition_name = '_available_width' AND start_pos_row = 484)
      OR (definition_name = '_line_indent' AND start_pos_row IN (487, 489))
      OR (definition_name = '_measure_text' AND start_pos_row IN (492, 493, 494, 495, 496))
      OR (definition_name = '_line_height' AND start_pos_row IN (499, 506, 507))
      OR (definition_name = '_baseline_shift' AND start_pos_row = 513)
    )
  )
  OR (
    module_path = 'src/InkGen/drawing_components.py'
    AND (
      (definition_name = 'to_component' AND start_pos_row IN (235, 238, 239))
      OR (definition_name = 'to_group' AND start_pos_row IN (531, 532, 535, 537, 539, 541, 543, 544, 547))
    )
  )
  OR (
    module_path = 'src/InkGen/document_outputs.py'
    AND (
      (definition_name = 'add_paragraph' AND start_pos_row IN (145, 147))
      OR (definition_name IN ('to_plain_text', 'to_html', 'to_markdown', 'to_rtf', 'to_docx_bytes') AND start_pos_row IN (185, 189, 191, 197, 202, 203, 204, 209, 211, 213, 218, 219))
      OR (definition_name = '_block_docx' AND start_pos_row IN (275, 276))
      OR (definition_name = '_block_html' AND start_pos_row IN (282, 284))
      OR (definition_name = '_block_rtf' AND start_pos_row IN (290, 291))
      OR (definition_name = '_paragraph_docx' AND start_pos_row IN (299, 300, 301, 303, 304))
      OR (definition_name = '_paragraph_properties_docx' AND start_pos_row IN (329, 334, 355, 356, 357, 358, 359))
      OR (definition_name = '_run_properties_docx' AND start_pos_row IN (364, 366, 371))
      OR (definition_name = '_paragraph_css' AND start_pos_row BETWEEN 374 AND 388)
      OR (definition_name = '_paragraph_rtf' AND start_pos_row BETWEEN 390 AND 406)
      OR (definition_name = '_docx_line_spacing' AND start_pos_row IN (502, 503))
      OR (definition_name = '_block_parameters' AND start_pos_row IN (508, 509))
      OR (definition_name = '_block_from_parameters' AND start_pos_row IN (527, 528))
      OR (definition_name = '_block_plain_text' AND start_pos_row IN (537, 538))
      OR (definition_name = '_block_markdown' AND start_pos_row IN (545, 546))
      OR (definition_name = '_paragraph_markdown' AND start_pos_row = 553)
      OR (definition_name = '_mm_to_twips' AND start_pos_row = 1096)
    )
  )
)
AND NOT (
  module_path = 'src/InkGen/document_outputs.py'
  AND definition_name = '_block_from_parameters'
  AND start_pos_row = 527
  AND operator_name LIKE 'core/ReplaceComparisonOperator_Eq_%'
)
AND NOT (
  module_path = 'src/InkGen/document_outputs.py'
  AND definition_name = '_block_html'
  AND start_pos_row = 284
  AND operator_name = 'core/NumberReplacer'
)
AND NOT (
  module_path = 'src/InkGen/document_outputs.py'
  AND definition_name = '_paragraph_docx'
  AND start_pos_row = 301
  AND operator_name = 'core/AddNot'
)
AND NOT (
  module_path = 'src/InkGen/paragraph.py'
  AND definition_name = '_line_height'
  AND start_pos_row = 499
)
AND NOT (
  module_path = 'src/InkGen/document_outputs.py'
  AND definition_name = '_mm_to_twips'
  AND start_pos_row = 1096
  AND operator_name = 'core/NumberReplacer'
)
AND NOT (
  module_path = 'src/InkGen/paragraph.py'
  AND definition_name = '_available_width'
  AND start_pos_row = 484
  AND operator_name = 'core/NumberReplacer'
)
AND NOT (
  module_path = 'src/InkGen/paragraph.py'
  AND definition_name = '_baseline_shift'
  AND start_pos_row = 513
  AND operator_name = 'core/ReplaceBinaryOperator_Mul_Div'
)
AND NOT (
  module_path = 'src/InkGen/paragraph.py'
  AND definition_name = '_line_indent'
  AND start_pos_row IN (487, 489)
)
AND NOT (
  module_path = 'src/InkGen/paragraph.py'
  AND definition_name = '_measure_text'
  AND start_pos_row = 496
  AND operator_name = 'core/NumberReplacer'
)
AND NOT (
  module_path = 'src/InkGen/paragraph.py'
  AND definition_name = '_wrap_text'
  AND start_pos_row IN (474, 478)
)
AND NOT (
  module_path = 'src/InkGen/paragraph.py'
  AND definition_name = 'layout_lines'
  AND start_pos_row = 449
  AND (
    operator_name = 'core/ReplaceBinaryOperator_Sub_Mod'
    OR operator_name = 'core/NumberReplacer'
  )
)
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to paragraph live-path work items."""
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
