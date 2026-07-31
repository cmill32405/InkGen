"""Source-fresh mutation evidence for PDF text presentation."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest

from InkGen.pdf_generator import TextPDF
from InkGen.style import Font, TextStyle

CONDITION = "PDF-TEXT-PRESENTATION-P3"
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "mutation" / "pdf_text_presentation_v4_evidence.json"
DATABASE_SHA256 = "55DC8A415B47FFFF03141CF972D8CB607781B47A324B8D9513B77278E548261D"
EQUIVALENT_SURVIVORS = {
    (
        "9325f6b5ad2d44a7ad1b2686fe2e0ebd",
        "src/InkGen/component.py",
        2051,
        24,
        "core/ReplaceOrWithAnd",
    ),
    (
        "86145d13ebe748078d2e067944a1238f",
        "src/InkGen/pdf_generator.py",
        2039,
        18,
        "core/ReplaceComparisonOperator_Eq_LtE",
    ),
    (
        "d9fa7a6414f1444b890e1d8479215cbe",
        "src/InkGen/pdf_generator.py",
        2041,
        18,
        "core/ReplaceComparisonOperator_Eq_LtE",
    ),
}


def _canonical_source_sha256(path: Path) -> str:
    """Hash UTF-8 source with platform-independent newlines."""
    source = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(source.encode("utf-8")).hexdigest().upper()


@pytest.mark.condition(CONDITION)
def test_pdf_text_presentation_mutation_database_is_complete() -> None:
    """All scoped mutants have normal, source-fresh, explicitly classified outcomes."""
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
    assert len(work_items) == 271
    assert len({item["job_id"] for item in work_items}) == 271
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

    assert outcomes == Counter({("KILLED", "NORMAL"): 268, ("SURVIVED", "NORMAL"): 3})
    assert survivors == EQUIVALENT_SURVIVORS


@pytest.mark.condition(CONDITION)
def test_character_spacing_bounds_preserve_an_unsupported_empty_outline() -> None:
    """A missing outline surface remains unchanged instead of inventing geometry."""
    style = TextStyle("empty_outline_evidence", Font(size=12.0), character_spacing=2.0)
    component = TextPDF("ABC", (10.0, 20.0), style)
    outline: dict[str, object] = {}

    assert component._apply_character_spacing_bounds(outline) is outline  # noqa: SLF001
