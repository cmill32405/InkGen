"""Freshness and completeness checks for RASTER-GRADIENT-P10 mutation evidence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tests.mutation_evidence_freshness import _canonical_source_sha256

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "mutation" / "raster_gradient_p10_evidence.json"


@pytest.mark.condition("RASTER-GRADIENT-P10")
def test_raster_gradient_mutation_certificate_matches_final_source_and_database() -> None:
    """RASTER-GRADIENT-P10: The recorded complete campaign remains reproducible and current."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    campaign = manifest["campaign"]
    database_path = ROOT / manifest["database"]["path"]

    assert manifest["condition"] == "RASTER-GRADIENT-P10"
    assert campaign == {
        "generated_candidates": 3186,
        "selected_work_items": 311,
        "completed_results": 311,
        "killed": 298,
        "survived": 13,
        "equivalent_survivors": 13,
        "worker_errors": 0,
        "worker_timeouts": 0,
        "raw_mutation_coverage": pytest.approx(298 / 311),
        "effective_mutation_coverage": 1.0,
    }
    assert hashlib.sha256(database_path.read_bytes()).hexdigest().upper() == manifest["database"]["sha256"]

    text_evidence = [manifest["source"], *manifest["tests"], manifest["config"], manifest["filter"]]
    for evidence in text_evidence:
        assert _canonical_source_sha256(ROOT / evidence["path"]).upper() == evidence["sha256"]

    expected_survivors = {job_id for proof in manifest["equivalent_survivor_proofs"] for job_id in proof["job_ids"]}
    assert len(expected_survivors) == campaign["equivalent_survivors"]

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM work_items").fetchone()[0] == campaign["selected_work_items"]
        rows = connection.execute("SELECT job_id, worker_outcome, test_outcome, diff FROM work_results").fetchall()

    assert len(rows) == campaign["completed_results"]
    assert all(worker_outcome == "NORMAL" for _, worker_outcome, _, _ in rows)
    assert sum(test_outcome == "KILLED" for _, _, test_outcome, _ in rows) == campaign["killed"]
    survivors = {job_id for job_id, _, test_outcome, _ in rows if test_outcome == "SURVIVED"}
    assert survivors == expected_survivors
    assert all(diff.startswith("--- mutation diff ---") for _, _, _, diff in rows)
