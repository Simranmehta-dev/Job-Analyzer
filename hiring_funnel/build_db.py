"""Build the SQLite warehouse from synthetic data.

    python -m hiring_funnel.build_db --n 6000 --seed 7
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .generate import HiringDataGenerator
from .warehouse import Warehouse

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "funnel.db"


def build(path: str | Path = DEFAULT_DB, n: int = 6000, seed: int = 7) -> Warehouse:
    """Generate data and load it into a fresh warehouse at `path`."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wh = Warehouse(path)
    wh.load(HiringDataGenerator(n_applications=n, seed=seed).generate())
    return wh


def ensure_database(path: str | Path = DEFAULT_DB) -> Warehouse:
    """Open the warehouse, building it first if the file does not exist yet."""
    if not Path(path).exists():
        return build(path)
    return Warehouse(path)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--n", type=int, default=6000, help="number of applications")
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()
    wh = build(args.db, args.n, args.seed)
    print(f"Built {args.db}")
    for table, count in wh.table_counts().items():
        print(f"  {table:<18} {count:>7,}")


if __name__ == "__main__":
    main()
