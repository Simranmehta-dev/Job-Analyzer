"""SQLite star schema: dimensions for who/what, facts for what happened."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .generate import HiringData

SCHEMA = """
DROP TABLE IF EXISTS fact_stage_event;
DROP TABLE IF EXISTS fact_application;
DROP TABLE IF EXISTS dim_stage;
DROP TABLE IF EXISTS dim_source;
DROP TABLE IF EXISTS dim_role;
DROP TABLE IF EXISTS dim_recruiter;

CREATE TABLE dim_stage (
    stage_id    INTEGER PRIMARY KEY,
    stage_name  TEXT NOT NULL UNIQUE,
    stage_order INTEGER NOT NULL UNIQUE
);
CREATE TABLE dim_source (
    source_id   INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL UNIQUE
);
CREATE TABLE dim_role (
    role_id    INTEGER PRIMARY KEY,
    department TEXT NOT NULL,
    job_title  TEXT NOT NULL
);
CREATE TABLE dim_recruiter (
    recruiter_id   INTEGER PRIMARY KEY,
    recruiter_name TEXT NOT NULL UNIQUE
);

-- Grain: one row per application.
CREATE TABLE fact_application (
    application_id INTEGER PRIMARY KEY,
    source_id      INTEGER NOT NULL REFERENCES dim_source(source_id),
    role_id        INTEGER NOT NULL REFERENCES dim_role(role_id),
    recruiter_id   INTEGER NOT NULL REFERENCES dim_recruiter(recruiter_id),
    applied_date   TEXT NOT NULL,
    outcome        TEXT NOT NULL CHECK (outcome IN ('Hired', 'Rejected', 'In Progress')),
    closed_date    TEXT,
    final_stage_id INTEGER NOT NULL REFERENCES dim_stage(stage_id)
);

-- Grain: one row per application per stage it reached.
CREATE TABLE fact_stage_event (
    application_id INTEGER NOT NULL REFERENCES fact_application(application_id),
    stage_id       INTEGER NOT NULL REFERENCES dim_stage(stage_id),
    entered_date   TEXT NOT NULL,
    exited_date    TEXT,
    days_in_stage  INTEGER,
    PRIMARY KEY (application_id, stage_id)
);

CREATE INDEX idx_app_date    ON fact_application(applied_date);
CREATE INDEX idx_app_source  ON fact_application(source_id);
CREATE INDEX idx_app_role    ON fact_application(role_id);
CREATE INDEX idx_evt_stage   ON fact_stage_event(stage_id);
"""


class Warehouse:
    """Thin wrapper around a SQLite connection with schema and bulk-load helpers."""

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON")

    def create_schema(self) -> None:
        """(Re)create all tables. Destroys existing data."""
        self._conn.executescript(SCHEMA)

    def load(self, data: HiringData) -> None:
        """Replace warehouse contents with `data`."""
        self.create_schema()
        for name, df in data.tables().items():
            df.to_sql(name, self._conn, if_exists="append", index=False)
        self._conn.commit()

    def query(self, sql: str, params: list | tuple = ()) -> pd.DataFrame:
        """Run a parameterised SELECT and return a DataFrame."""
        return pd.read_sql_query(sql, self._conn, params=params)

    def table_counts(self) -> dict[str, int]:
        tables = [r[0] for r in self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {t: self._conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}

    def execute(self, sql: str, params: list | tuple = ()) -> None:
        self._conn.execute(sql, params)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
