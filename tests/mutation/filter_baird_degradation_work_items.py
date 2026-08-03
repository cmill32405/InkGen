"""Filter Cosmic Ray work items to Baird proof-critical definitions."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

FILTER_SQL = r"""
module_path IN ('src/InkGen/baird.py', 'src\InkGen\baird.py')
AND definition_name IN (
  '_finite_number',
  '_nonnegative_number',
  '_positive_number',
  'sigma_um_to_px',
  'sigma_px_to_um',
  '__post_init__',
  'clean',
  'sample',
  'as_dict',
  'manifest',
  'baird_degrade',
  'baird_degrade_asset',
  '_validated_gray_image',
  '_resize_bilinear',
  '_sample_bilinear',
  '_gaussian_blur',
  '_convolve_axis',
  '_validate_seed',
  '_validate_background'
)
AND operator_name NOT LIKE 'core/ReplaceBinaryOperator_BitOr_%'
AND operator_name NOT LIKE '%BitAnd%'
AND operator_name NOT LIKE '%BitOr%'
AND operator_name NOT LIKE '%BitXor%'
AND operator_name NOT LIKE '%LShift%'
AND operator_name NOT LIKE '%RShift%'
AND operator_name NOT LIKE '%FloorDiv%'
"""


def filter_work_items(db_path: Path, *, clear_results: bool) -> tuple[int, int]:
    """Restrict a Cosmic Ray database to Baird proof obligations."""
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
    """Run the command-line filter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", type=Path)
    parser.add_argument("--clear-results", action="store_true")
    args = parser.parse_args()

    before, after = filter_work_items(args.db_path, clear_results=args.clear_results)
    print(f"work_items: {before} -> {after}")


if __name__ == "__main__":
    main()
