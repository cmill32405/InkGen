"""Filter Cosmic Ray work items to RASTER-IMAGE-P1 rows."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = """
(
(
  module_path = 'src/InkGen/image_assets.py'
  AND (
    definition_name IN (
      '_coerce_image_bytes',
      '_coerce_finite_number',
      '_coerce_positive_number',
      '_coerce_position',
      'from_bytes',
      'from_file',
      'create_from_dict',
      'mime_type',
      'has_alpha',
      'parameters',
      'image',
      'png_bytes',
      'png_data_uri',
      '__init__',
      'points',
      'bbox',
      'convex_hull'
    )
    AND start_pos_row BETWEEN 27 AND 248
  )
)
OR (
  module_path = 'src/InkGen/drawing_components.py'
  AND definition_name IN ('__post_init__', 'to_component')
  AND start_pos_row BETWEEN 253 AND 273
)
OR (
  module_path = 'src/InkGen/svg_generator.py'
  AND definition_name IN ('create_from_dict', 'parameters', 'generate_svg')
  AND start_pos_row BETWEEN 1216 AND 1248
)
OR (
  module_path = 'src/InkGen/pdf_generator.py'
  AND (
    (
      definition_name IN ('image_resource_name', 'resource_name_for_asset', 'resources')
      AND start_pos_row BETWEEN 90 AND 135
    )
    OR (
      definition_name IN ('_pdf_image_samples', '_pdf_image_xobject')
      AND start_pos_row BETWEEN 201 AND 229
    )
    OR (
      definition_name IN ('create_from_dict', 'parameters', 'generate_pdf')
      AND start_pos_row BETWEEN 969 AND 1007
    )
    OR (
      definition_name IN ('to_pdf_bytes', '_render_page_content')
      AND start_pos_row BETWEEN 1141 AND 1234
    )
  )
)
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND operator_name != 'core/NumberReplacer'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to raster image work items."""
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
