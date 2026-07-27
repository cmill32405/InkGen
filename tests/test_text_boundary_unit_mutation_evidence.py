"""Mutation evidence for drawing-text canvas-unit consistency."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from InkGen.style import Font

CONDITION = "TEXT-BOUNDARY-UNITS-P1"
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "mutation" / "text_boundary_units_v3_evidence.json"
DATABASE_SHA256 = "5E9921FB5B28290303DDD27B1802EDF4C05ACAB46DC585B5AE6A43A002277F0E"
EQUIVALENT_SURVIVORS = {
    (
        "262285c0231b4926b68df30449cb8a60",
        "src\\InkGen\\component.py",
        2028,
        33,
        "core/NumberReplacer",
    ),
}


def _canonical_source_sha256(path: Path) -> str:
    """Hash UTF-8 source with platform-independent newlines."""
    source = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(source.encode("utf-8")).hexdigest().upper()


@pytest.mark.condition(CONDITION)
def test_text_boundary_unit_mutation_database_is_complete() -> None:
    """All scoped workers finish normally with source-fresh pinned evidence."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    generated_at = datetime.fromisoformat(manifest["evidence_generated_utc"])
    assert manifest["condition"] == CONDITION
    assert manifest["database"]["sha256"] == DATABASE_SHA256
    assert datetime.fromisoformat(manifest["database"]["last_write_utc"]) <= generated_at

    for relative_path, source_evidence in manifest["source_files"].items():
        source_path = ROOT / relative_path
        assert _canonical_source_sha256(source_path) == source_evidence["sha256"]
        assert datetime.fromisoformat(source_evidence["last_write_utc"]) <= generated_at

    work_items = manifest["work_items"]
    assert len(work_items) == 91
    assert len({item["job_id"] for item in work_items}) == 91
    outcomes = Counter((item["test_outcome"], item["worker_outcome"]) for item in work_items)
    survivors = {
        (
            item["job_id"],
            item["module_path"],
            item["start_pos_row"],
            item["start_pos_col"],
            item["operator_name"],
        )
        for item in work_items
        if item["test_outcome"] == "SURVIVED"
    }

    assert outcomes == Counter({("KILLED", "NORMAL"): 90, ("SURVIVED", "NORMAL"): 1})
    assert survivors == EQUIVALENT_SURVIVORS


@pytest.mark.condition(CONDITION)
@given(st.floats(min_value=0.0, max_value=240.0, exclude_min=True))
def test_survivor_floor_replacement_is_exact_over_numeric_font_sizes(size: float) -> None:
    """Reachable numeric font sizes make the mutated negative floor equivalent."""
    normalized = Font(family="DejaVu Sans", size=size).size

    assert normalized >= 1.0
    assert max(normalized, 0.5) == max(normalized, -0.5)


@pytest.mark.condition(CONDITION)
@pytest.mark.parametrize(
    "size",
    ["xx-small", "x-small", "small", "medium", "large", "x-large", "xx-large"],
)
def test_survivor_floor_replacement_is_exact_over_named_font_sizes(size: str) -> None:
    """Reachable named font sizes make the mutated negative floor equivalent."""
    normalized = Font(family="DejaVu Sans", size=size).size

    assert normalized >= 1.0
    assert max(normalized, 0.5) == max(normalized, -0.5)
