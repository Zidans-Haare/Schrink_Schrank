import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("KS_DB", Path(__file__).resolve().parents[1] / "data" / "kuehlschrank.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS receipts (
    id           INTEGER PRIMARY KEY,
    bon_id       TEXT UNIQUE,
    file_hash    TEXT NOT NULL UNIQUE,      -- sha256 der PDF-Datei
    purchased_at TEXT NOT NULL,             -- ISO, lokale Zeit
    store        TEXT NOT NULL,
    total        INTEGER NOT NULL,          -- Cent
    needs_review INTEGER NOT NULL DEFAULT 0,
    problems     TEXT NOT NULL DEFAULT '',  -- eine Meldung pro Zeile
    imported_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS receipt_lines (
    id         INTEGER PRIMARY KEY,
    receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    position   INTEGER NOT NULL,
    kind       TEXT NOT NULL,     -- 'item' oder 'deposit' (eingelöster Leergutbon)
    text       TEXT NOT NULL,     -- Bontext wie gedruckt
    quantity   INTEGER NOT NULL,
    unit_price INTEGER NOT NULL,  -- Cent
    total      INTEGER NOT NULL,  -- Cent, vor Rabatten
    paid       INTEGER NOT NULL,  -- Cent, nach Rabatten
    tax        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lines_text ON receipt_lines(text);

CREATE TABLE IF NOT EXISTS categories (
    key        TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    storage    TEXT NOT NULL,
    shelf_days INTEGER NOT NULL,  -- Haltbarkeit ab Kauf
    use_days   INTEGER NOT NULL   -- angenommene Verbrauchsdauer ohne eigene Kaufdaten
);

CREATE TABLE IF NOT EXISTS products (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    category   TEXT REFERENCES categories(key),
    shelf_days INTEGER,           -- überschreibt die Kategorie-Haltbarkeit
    storage    TEXT               -- Kühlschrank, Tiefkühler, Vorrat
);

CREATE TABLE IF NOT EXISTS aliases (
    text       TEXT PRIMARY KEY,  -- Bontext
    product_id INTEGER NOT NULL REFERENCES products(id)
);
"""


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    from .seed import seed

    seed(conn)
    return conn
