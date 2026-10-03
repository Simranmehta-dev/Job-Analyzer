import sqlite3

import pytest


def test_all_tables_loaded(warehouse, data):
    counts = warehouse.table_counts()
    for name, df in data.tables().items():
        assert counts[name] == len(df)


def test_reload_is_idempotent(warehouse, data):
    before = warehouse.table_counts()
    warehouse.load(data)
    assert warehouse.table_counts() == before


def test_foreign_keys_are_enforced(warehouse):
    with pytest.raises(sqlite3.IntegrityError):
        warehouse.execute(
            "INSERT INTO fact_application VALUES (999999, 99, 1, 1, '2026-01-01', 'Rejected', NULL, 1)"
        )


def test_outcome_check_constraint(warehouse):
    with pytest.raises(sqlite3.IntegrityError):
        warehouse.execute(
            "INSERT INTO fact_application VALUES (999999, 1, 1, 1, '2026-01-01', 'Maybe', NULL, 1)"
        )
