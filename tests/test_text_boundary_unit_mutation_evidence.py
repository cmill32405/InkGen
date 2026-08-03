"""Mutation evidence for drawing-text canvas-unit consistency."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from InkGen.style import Font
from tests.mutation_evidence_freshness import assert_manifest_sources_current

CONDITION = "TEXT-BOUNDARY-UNITS-P1"
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "mutation" / "text_boundary_units_v6_evidence.json"
DATABASE_SHA256 = "7662A0D7F316547B7B376B6C820BB8B752B6D2141725BB4431AF7396B791D573"
EQUIVALENT_SURVIVORS = {
    (
        "d0cd1d0d69544c3599242017351fa260",
        "src/InkGen/component.py",
        2206,
        33,
        "core/NumberReplacer",
    ),
}


@pytest.mark.condition(CONDITION)
def test_text_boundary_unit_mutation_database_is_complete() -> None:
    """All scoped workers finish normally with source-fresh pinned evidence."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    generated_at = datetime.fromisoformat(manifest["evidence_generated_utc"])
    assert manifest["condition"] == CONDITION
    assert manifest["database"]["sha256"] == DATABASE_SHA256
    assert datetime.fromisoformat(manifest["database"]["last_write_utc"]) <= generated_at

    assert_manifest_sources_current(ROOT, manifest, generated_at)

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
@settings(deadline=None)
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
