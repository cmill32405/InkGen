"""Freshness and completeness checks for raster path-stroke P17 evidence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tests.mutation_evidence_freshness import _canonical_source_sha256

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "mutation" / "raster_path_stroke_p17_evidence.json"


@pytest.mark.condition("RASTER-PATH-STROKE-P17")
def test_raster_path_stroke_mutation_certificate_matches_final_source_and_database() -> None:
    """P17: The retained complete campaign remains source-fresh and auditable."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    campaign = manifest["campaign"]
    database_path = ROOT / manifest["database"]["path"]

    assert manifest["condition"] == "RASTER-PATH-STROKE-P17"
    assert campaign == {
        "generated_candidates": 6321,
        "selected_work_items": 579,
        "completed_results": 579,
        "killed": 539,
        "survived": 40,
        "equivalent_survivors": 40,
        "worker_errors": 0,
        "worker_timeouts": 0,
        "raw_mutation_coverage": pytest.approx(539 / 579),
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

    proofs = manifest["equivalent_survivor_proofs"]
    proof_job_ids = [job_id for proof in proofs for job_id in proof["job_ids"]]
    assert len(proof_job_ids) == len(set(proof_job_ids)) == campaign["equivalent_survivors"]
    assert all(proof["premises"] and proof["proof"] for proof in proofs)
    assert sum(manifest["shard_sizes"]) == campaign["selected_work_items"]

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM work_items").fetchone()[0] == campaign["selected_work_items"]
        rows = connection.execute("SELECT job_id, worker_outcome, test_outcome, diff FROM work_results").fetchall()

    assert len(rows) == campaign["completed_results"]
    assert all(worker_outcome == "NORMAL" for _, worker_outcome, _, _ in rows)
    assert sum(test_outcome == "KILLED" for _, _, test_outcome, _ in rows) == campaign["killed"]
    survivors = {job_id for job_id, _, test_outcome, _ in rows if test_outcome == "SURVIVED"}
    assert survivors == set(proof_job_ids)
    assert all(diff.startswith("--- mutation diff ---") for _, _, _, diff in rows)
