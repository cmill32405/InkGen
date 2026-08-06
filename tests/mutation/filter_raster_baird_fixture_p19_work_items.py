"""Remove postponed-annotation-only mutants from the P19 campaign."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ANNOTATION_ONLY_OPERATORS = (
    "core/ReplaceBinaryOperator_BitOr_Add",
    "core/ReplaceBinaryOperator_BitOr_BitAnd",
    "core/ReplaceBinaryOperator_BitOr_BitXor",
    "core/ReplaceBinaryOperator_BitOr_Div",
    "core/ReplaceBinaryOperator_BitOr_FloorDiv",
    "core/ReplaceBinaryOperator_BitOr_LShift",
    "core/ReplaceBinaryOperator_BitOr_Mod",
    "core/ReplaceBinaryOperator_BitOr_Mul",
    "core/ReplaceBinaryOperator_BitOr_Pow",
    "core/ReplaceBinaryOperator_BitOr_RShift",
    "core/ReplaceBinaryOperator_BitOr_Sub",
    "core/ReplaceBinaryOperator_FloorDiv_Add",
    "core/ReplaceBinaryOperator_FloorDiv_BitAnd",
    "core/ReplaceBinaryOperator_FloorDiv_BitOr",
    "core/ReplaceBinaryOperator_FloorDiv_BitXor",
    "core/ReplaceBinaryOperator_FloorDiv_Div",
    "core/ReplaceBinaryOperator_FloorDiv_LShift",
    "core/ReplaceBinaryOperator_FloorDiv_Mod",
    "core/ReplaceBinaryOperator_FloorDiv_Mul",
    "core/ReplaceBinaryOperator_FloorDiv_Pow",
    "core/ReplaceBinaryOperator_FloorDiv_RShift",
    "core/ReplaceBinaryOperator_FloorDiv_Sub",
)


def filter_work_items(db_path: Path) -> tuple[int, int]:
    """Remove operators that can only mutate the postponed union annotation."""
    placeholders = ", ".join("?" for _ in ANNOTATION_ONLY_OPERATORS)
    with sqlite3.connect(db_path) as connection:
        before = connection.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
        connection.execute(
            f"DELETE FROM work_items WHERE job_id IN (SELECT job_id FROM mutation_specs WHERE operator_name IN ({placeholders}))",
            ANNOTATION_ONLY_OPERATORS,
        )
        connection.execute("DELETE FROM mutation_specs WHERE job_id NOT IN (SELECT job_id FROM work_items)")
        connection.execute("DELETE FROM work_results WHERE job_id NOT IN (SELECT job_id FROM work_items)")
        after = connection.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
    return before, after


def main() -> None:
    """Run the command-line filter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", type=Path)
    args = parser.parse_args()
    before, after = filter_work_items(args.db_path)
    print(f"work_items: {before} -> {after}")


if __name__ == "__main__":
    main()
