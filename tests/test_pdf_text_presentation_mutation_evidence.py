"""Source-fresh mutation evidence for PDF text presentation."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest

from InkGen.pdf_generator import TextPDF
from InkGen.style import Font, TextStyle
from tests.mutation_evidence_freshness import assert_manifest_sources_current

CONDITION = "PDF-TEXT-PRESENTATION-P3"
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "mutation" / "pdf_text_presentation_v5_evidence.json"
DATABASE_SHA256 = "20820CAC6FBD9A74340BC75C470DBB572630D7F519223151B0928A929D48F14E"
EQUIVALENT_SURVIVORS = {
    (
        "9f3326e37717443fa1d926a43d231a56",
        "src/InkGen/component.py",
        2165,
        24,
        "core/ReplaceOrWithAnd",
    ),
    (
        "de91437c45874324a1a4cef15afd89d7",
        "src/InkGen/pdf_generator.py",
        2078,
        18,
        "core/ReplaceComparisonOperator_Eq_LtE",
    ),
    (
        "c83bcb51eee04cb7963bf2264f42f4ff",
        "src/InkGen/pdf_generator.py",
        2080,
        18,
        "core/ReplaceComparisonOperator_Eq_LtE",
    ),
}


@pytest.mark.condition(CONDITION)
def test_pdf_text_presentation_mutation_database_is_complete() -> None:
    """All scoped mutants have normal, source-fresh, explicitly classified outcomes."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    generated_at = datetime.fromisoformat(manifest["evidence_generated_utc"])
    assert manifest["condition"] == CONDITION
    assert manifest["database"]["sha256"] == DATABASE_SHA256
    assert datetime.fromisoformat(manifest["database"]["last_write_utc"]) <= generated_at

    assert_manifest_sources_current(ROOT, manifest, generated_at)

    work_items = manifest["work_items"]
    assert len(work_items) == 304
    assert len({item["job_id"] for item in work_items}) == 304
    pdf_generate_sites = Counter(
        (item["definition_name"], item["start_pos_row"])
        for item in work_items
        if item["module_path"].replace("\\", "/") == "src/InkGen/pdf_generator.py" and item["definition_name"] == "generate_pdf"
    )
    assert pdf_generate_sites == Counter(
        {
            ("generate_pdf", 2123): 33,
            ("generate_pdf", 2129): 2,
            ("generate_pdf", 2131): 8,
        }
    )
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

    assert outcomes == Counter({("KILLED", "NORMAL"): 301, ("SURVIVED", "NORMAL"): 3})
    assert survivors == EQUIVALENT_SURVIVORS


@pytest.mark.condition(CONDITION)
def test_character_spacing_bounds_preserve_an_unsupported_empty_outline() -> None:
    """A missing outline surface remains unchanged instead of inventing geometry."""
    style = TextStyle("empty_outline_evidence", Font(size=12.0), character_spacing=2.0)
    component = TextPDF("ABC", (10.0, 20.0), style)
    outline: dict[str, object] = {}

    assert component._apply_character_spacing_bounds(outline) is outline  # noqa: SLF001
