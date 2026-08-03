"""Contracts for mutation-evidence source freshness."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.mutation_evidence_freshness import assert_manifest_sources_current, original_mutation_hunk


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def _manifest(source: str, generated_at: datetime) -> dict:
    return {
        "source_files": {
            "module.py": {
                "sha256": _sha256(source),
                "last_write_utc": generated_at.isoformat(),
            }
        },
        "work_items": [
            {
                "job_id": "job-1",
                "module_path": "module.py",
                "definition_name": "calculate",
                "diff": (
                    "--- mutation diff ---\n"
                    "--- asrc/module.py\n"
                    "+++ bsrc/module.py\n"
                    "@@ -1,2 +1,2 @@\n"
                    " def calculate(value):\n"
                    "-    return value + 1\n"
                    "+    return value - 1"
                ),
            }
        ],
    }


def test_original_mutation_hunk_reconstructs_pre_mutation_context() -> None:
    manifest = _manifest("def calculate(value):\n    return value + 1\n", datetime.now(timezone.utc))

    assert original_mutation_hunk(manifest["work_items"][0]["diff"]) == ("def calculate(value):\n    return value + 1")


def test_scoped_freshness_allows_unrelated_module_growth(tmp_path: Path) -> None:
    generated_at = datetime.now(timezone.utc)
    original = "def calculate(value):\n    return value + 1\n"
    manifest = _manifest(original, generated_at)
    (tmp_path / "module.py").write_text("class AddedLater:\n    pass\n\n" + original, encoding="utf-8")

    assert_manifest_sources_current(tmp_path, manifest, generated_at)


def test_scoped_freshness_rejects_a_changed_mutation_site(tmp_path: Path) -> None:
    generated_at = datetime.now(timezone.utc)
    original = "def calculate(value):\n    return value + 1\n"
    manifest = _manifest(original, generated_at)
    (tmp_path / "module.py").write_text("def calculate(value):\n    return value + 2\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="Mutation source changed.*job-1.*calculate"):
        assert_manifest_sources_current(tmp_path, manifest, generated_at)


def test_unscoped_evidence_retains_whole_file_hash_validation(tmp_path: Path) -> None:
    generated_at = datetime.now(timezone.utc)
    original = "proof configuration\n"
    manifest = _manifest(original, generated_at)
    manifest["work_items"] = []
    (tmp_path / "module.py").write_text("changed configuration\n", encoding="utf-8")

    with pytest.raises(AssertionError):
        assert_manifest_sources_current(tmp_path, manifest, generated_at)


def test_original_mutation_hunk_rejects_missing_unified_hunk() -> None:
    with pytest.raises(ValueError, match="original unified-diff hunk"):
        original_mutation_hunk("not a unified diff")
