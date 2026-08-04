"""Merge complete disjoint Cosmic Ray result shards into a master database."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

SELECT_RESULTS_SQL = "SELECT worker_outcome, output, test_outcome, diff, job_id FROM work_results"
INSERT_RESULTS_SQL = "INSERT INTO work_results (worker_outcome, output, test_outcome, diff, job_id) VALUES (?, ?, ?, ?, ?)"


def merge_shards(master_path: Path, shard_paths: list[Path]) -> tuple[int, int]:
    """Merge shard results after proving exact, disjoint job coverage."""
    with sqlite3.connect(master_path) as master:
        expected = {row[0] for row in master.execute("SELECT job_id FROM work_items")}
        master.execute("DELETE FROM work_results")
        merged: set[str] = set()
        result_rows: list[tuple[object, ...]] = []
        for shard_path in shard_paths:
            with sqlite3.connect(shard_path) as shard:
                shard_jobs = {row[0] for row in shard.execute("SELECT job_id FROM work_items")}
                completed = {row[0] for row in shard.execute("SELECT job_id FROM work_results")}
                if completed != shard_jobs:
                    raise ValueError(f"incomplete shard: {shard_path}")
                if merged & shard_jobs:
                    raise ValueError(f"overlapping shard: {shard_path}")
                merged |= shard_jobs
                result_rows.extend(shard.execute(SELECT_RESULTS_SQL))
        if merged != expected:
            raise ValueError("shards do not cover the master work-item set")
        master.executemany(INSERT_RESULTS_SQL, result_rows)
    return len(expected), len(result_rows)


def main() -> None:
    """Run the command-line merger."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("shards", nargs="+", type=Path)
    args = parser.parse_args()
    expected, merged = merge_shards(args.master, args.shards)
    print(f"work_results: {merged}/{expected}")


if __name__ == "__main__":
    main()
