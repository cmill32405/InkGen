"""Partition a Cosmic Ray database into one deterministic execution shard."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def partition_work_items(db_path: Path, shard_index: int, shard_count: int) -> tuple[int, int]:
    """Keep the sorted job IDs assigned to one modulo shard."""
    if shard_count <= 0:
        raise ValueError("shard_count must be positive")
    if not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must be between zero and shard_count - 1")
    with sqlite3.connect(db_path) as connection:
        job_ids = [row[0] for row in connection.execute("SELECT job_id FROM work_items ORDER BY job_id")]
        keep = set(job_ids[shard_index::shard_count])
        connection.executemany("DELETE FROM work_items WHERE job_id = ?", ((job_id,) for job_id in job_ids if job_id not in keep))
        connection.execute("DELETE FROM mutation_specs WHERE job_id NOT IN (SELECT job_id FROM work_items)")
        connection.execute("DELETE FROM work_results WHERE job_id NOT IN (SELECT job_id FROM work_items)")
    return len(job_ids), len(keep)


def main() -> None:
    """Run the command-line partitioner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", type=Path)
    parser.add_argument("shard_index", type=int)
    parser.add_argument("shard_count", type=int)
    args = parser.parse_args()
    before, after = partition_work_items(args.db_path, args.shard_index, args.shard_count)
    print(f"work_items: {before} -> {after}")


if __name__ == "__main__":
    main()
