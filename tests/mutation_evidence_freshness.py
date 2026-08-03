"""Source-freshness checks for retained mutation evidence."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def _canonical_source(path: Path) -> str:
    """Read UTF-8 source with platform-independent newlines."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _canonical_source_sha256(path: Path) -> str:
    """Hash canonical UTF-8 source."""
    return hashlib.sha256(_canonical_source(path).encode("utf-8")).hexdigest().upper()


def original_mutation_hunk(diff: str) -> str:
    """Reconstruct the pre-mutation hunk from a retained unified diff."""
    original: list[str] = []
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk or line.startswith("\\ No newline") or line.startswith("+"):
            continue
        if line.startswith((" ", "-")):
            original.append(line[1:])
    if not original:
        raise ValueError("Mutation evidence must contain an original unified-diff hunk.")
    return "\n".join(original)


def assert_manifest_sources_current(root: Path, manifest: dict[str, Any], generated_at: datetime) -> None:
    """Verify immutable artifacts by hash and production mutation sites by hunk."""
    items_by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in manifest["work_items"]:
        items_by_module[item["module_path"].replace("\\", "/")].append(item)

    for relative_path, source_evidence in manifest["source_files"].items():
        normalized_path = relative_path.replace("\\", "/")
        source_path = root / relative_path
        scoped_items = items_by_module.get(normalized_path, [])
        if scoped_items:
            source = _canonical_source(source_path)
            for item in scoped_items:
                hunk = original_mutation_hunk(item["diff"])
                assert hunk in source, f"Mutation source changed for {normalized_path} job {item['job_id']} ({item['definition_name']})."
            continue

        assert _canonical_source_sha256(source_path) == source_evidence["sha256"]
        assert datetime.fromisoformat(source_evidence["last_write_utc"]) <= generated_at
