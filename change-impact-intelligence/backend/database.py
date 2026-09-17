"""
database.py

Tables:
  Projects       - one row per construction / renovation project
  Users          - people who can raise / approve revisions
  Revisions      - one row per change request, with the AI + engine
                    output cached on the row so the dashboard can be
                    built with simple SUM/AVG queries
  ImpactReports  - full JSON snapshot of every analysis run, kept so
                    we never lose the "how did we get this number"
                    trail even if the engines change later
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "change_impact.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS Projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    client      TEXT,
    budget      INTEGER DEFAULT 0,
    deadline    TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Users (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    role    TEXT DEFAULT 'Project Manager'
);

CREATE TABLE IF NOT EXISTS Revisions (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id              INTEGER NOT NULL,
    created_by              INTEGER,
    title                   TEXT NOT NULL,
    description             TEXT NOT NULL,
    category                TEXT,
    priority                TEXT DEFAULT 'Medium',
    status                  TEXT DEFAULT 'Pending Approval',

    ai_category             TEXT,
    affected_departments    TEXT,   -- comma separated
    affected_stakeholders   TEXT,   -- comma separated
    impact_summary          TEXT,

    material_cost           INTEGER DEFAULT 0,
    labor_cost              INTEGER DEFAULT 0,
    total_cost              INTEGER DEFAULT 0,

    procurement_delay       INTEGER DEFAULT 0,
    installation_delay      INTEGER DEFAULT 0,
    total_delay             INTEGER DEFAULT 0,

    risk_score              INTEGER DEFAULT 0,
    risk_level              TEXT DEFAULT 'Low',

    created_at              TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES Projects (id),
    FOREIGN KEY (created_by) REFERENCES Users (id)
);

CREATE TABLE IF NOT EXISTS ImpactReports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id   INTEGER NOT NULL,
    report_json   TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (revision_id) REFERENCES Revisions (id)
);
"""

SEED_USERS = [
    ("Priya Sharma", "Project Manager"),
    ("Rahul Verma", "Site Engineer"),
    ("Ananya Rao", "Client"),
    ("Karthik Iyer", "Procurement Lead"),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()


def _column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == column for row in cur.fetchall())


def init_db():
    with db_cursor() as cur:
        cur.executescript(SCHEMA)

        # Safe migrations for databases created before these columns existed.
        if not _column_exists(cur, "Revisions", "created_by"):
            cur.execute("ALTER TABLE Revisions ADD COLUMN created_by INTEGER")
        if not _column_exists(cur, "Projects", "client"):
            cur.execute("ALTER TABLE Projects ADD COLUMN client TEXT")
        if not _column_exists(cur, "Projects", "budget"):
            cur.execute("ALTER TABLE Projects ADD COLUMN budget INTEGER DEFAULT 0")
        if not _column_exists(cur, "Projects", "deadline"):
            cur.execute("ALTER TABLE Projects ADD COLUMN deadline TEXT")

        cur.execute("SELECT COUNT(*) AS c FROM Projects")
        if cur.fetchone()["c"] == 0:
            cur.execute(
                "INSERT INTO Projects (name, client, budget, deadline) VALUES (?, ?, ?, ?)",
                ("Luxury Villa Renovation", "ABC Builders", 12000000, "2026-12-30"),
            )

        cur.execute("SELECT COUNT(*) AS c FROM Users")
        if cur.fetchone()["c"] == 0:
            cur.executemany(
                "INSERT INTO Users (name, role) VALUES (?, ?)", SEED_USERS
            )


if __name__ == "__main__":
    init_db()
    print(f"Database initialised at {DB_PATH}")
