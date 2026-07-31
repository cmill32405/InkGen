"""Export source-fresh drawing-text boundary mutation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    Path("src/InkGen/component.py"),
    Path("src/InkGen/pdf_generator.py"),
    Path("tests/mutation/filter_text_boundary_units_work_items.py"),
    Path("tests/mutation/text_boundary_units_cosmic_ray.toml"),
    Path("tests/test_text_boundary_unit_contract.py"),
)


def _sha256(path: Path, *, canonical_text: bool) -> str:
    """Return an uppercase SHA-256 digest for one evidence input."""
    if canonical_text:
        source = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        payload = source.encode("utf-8")
    else:
        payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest().upper()


def _modified_utc(path: Path) -> str:
    """Return a filesystem modification timestamp in UTC."""
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def export_evidence(database: Path, output: Path) -> None:
    """Write deterministic outcomes plus mutation-input freshness metadata."""
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """
            SELECT m.job_id, m.module_path, m.definition_name, m.start_pos_row,
                   m.start_pos_col, m.operator_name, r.test_outcome,
                   r.worker_outcome, r.diff
            FROM mutation_specs m
            JOIN work_results r ON m.job_id = r.job_id
            ORDER BY m.module_path, m.start_pos_row, m.start_pos_col,
                     m.operator_name, m.job_id
            """
        ).fetchall()
        work_item_count = connection.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]

    if len(rows) != work_item_count:
        raise RuntimeError(f"mutation database is incomplete: {len(rows)} of {work_item_count} results")

    manifest = {
        "condition": "TEXT-BOUNDARY-UNITS-P1",
        "evidence_generated_utc": datetime.now(timezone.utc).isoformat(),
        "database": {
            "path": database.relative_to(ROOT).as_posix(),
            "sha256": _sha256(database, canonical_text=False),
            "last_write_utc": _modified_utc(database),
        },
        "source_files": {
            path.as_posix(): {
                "sha256": _sha256(ROOT / path, canonical_text=True),
                "last_write_utc": _modified_utc(ROOT / path),
            }
            for path in SOURCE_PATHS
        },
        "work_items": [
            {
                "job_id": row[0],
                "module_path": row[1],
                "definition_name": row[2],
                "start_pos_row": row[3],
                "start_pos_col": row[4],
                "operator_name": row[5],
                "test_outcome": row[6],
                "worker_outcome": row[7],
                "diff": row[8],
            }
            for row in rows
        ],
    }
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Export the command-line database to the requested JSON path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    export_evidence(arguments.database.resolve(), arguments.output.resolve())


if __name__ == "__main__":
    main()
