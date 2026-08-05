"""Freshness and completeness checks for raster miter-limit P16 evidence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tests.mutation_evidence_freshness import _canonical_source_sha256

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "mutation" / "raster_miter_limit_p16_evidence.json"


@pytest.mark.condition("RASTER-MITER-LIMIT-P16")
def test_raster_miter_limit_mutation_certificate_matches_final_source_and_database() -> None:
    """P16: The retained complete campaign remains source-fresh and auditable."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    campaign = manifest["campaign"]
    database_path = ROOT / manifest["database"]["path"]

    assert manifest["condition"] == "RASTER-MITER-LIMIT-P16"
    assert campaign == {
        "generated_candidates": 5870,
        "selected_work_items": 701,
        "completed_results": 701,
        "killed": 701,
        "survived": 0,
        "equivalent_survivors": 0,
        "worker_errors": 0,
        "worker_timeouts": 0,
        "raw_mutation_coverage": 1.0,
        "effective_mutation_coverage": 1.0,
    }
    assert hashlib.sha256(database_path.read_bytes()).hexdigest().upper() == manifest["database"]["sha256"]

    text_evidence = [
        *manifest["source_files"],
        *manifest["condition_tests"],
        *manifest["mutation_tests"],
        manifest["config"],
        manifest["filter"],
        manifest["partition"],
        manifest["merge"],
    ]
    for evidence in text_evidence:
        assert _canonical_source_sha256(ROOT / evidence["path"]).upper() == evidence["sha256"]

    assert manifest["equivalent_survivor_proofs"] == []
    assert sum(manifest["shard_sizes"]) == campaign["selected_work_items"]

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM work_items").fetchone()[0] == campaign["selected_work_items"]
        rows = connection.execute("SELECT worker_outcome, test_outcome, diff FROM work_results").fetchall()

    assert len(rows) == campaign["completed_results"]
    assert all(worker_outcome == "NORMAL" for worker_outcome, _, _ in rows)
    assert all(test_outcome == "KILLED" for _, test_outcome, _ in rows)
    assert all(diff.startswith("--- mutation diff ---") for _, _, diff in rows)
