"""Import von SPAR-PDFs in die Datenbank.

Aufruf:  python -m app.importer "../Spar Rechnungen"
"""

import hashlib
import sqlite3
import sys
from pathlib import Path

from .db import connect
from .parser import parse_pdf

NEW, DUPLICATE, REVIEW = "neu", "doppelt", "prüfen"


def import_pdf(conn: sqlite3.Connection, path: Path | str) -> str:
    file_hash = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if conn.execute("SELECT 1 FROM receipts WHERE file_hash = ?", (file_hash,)).fetchone():
        return DUPLICATE

    r = parse_pdf(path)
    # Derselbe Bon kann erneut exportiert werden und dann andere Bytes haben.
    if r.bon_id and conn.execute("SELECT 1 FROM receipts WHERE bon_id = ?", (r.bon_id,)).fetchone():
        return DUPLICATE

    with conn:
        receipt_id = conn.execute(
            "INSERT INTO receipts (bon_id, file_hash, purchased_at, store, total, needs_review, problems)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                r.bon_id or None,
                file_hash,
                r.purchased_at.isoformat(timespec="minutes"),
                r.store,
                r.total,
                int(r.needs_review),
                "\n".join(r.problems),
            ),
        ).lastrowid
        rows = [
            ("item", l.text, l.quantity, l.unit_price, l.total, l.paid, l.tax) for l in r.lines
        ] + [("deposit", d.text, 1, d.amount, d.amount, d.amount, d.tax) for d in r.deposits]
        conn.executemany(
            "INSERT INTO receipt_lines"
            " (receipt_id, position, kind, text, quantity, unit_price, total, paid, tax)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(receipt_id, i, *row) for i, row in enumerate(rows)],
        )
    return REVIEW if r.needs_review else NEW


def main(folder: str) -> None:
    conn = connect()
    counts = {NEW: 0, DUPLICATE: 0, REVIEW: 0}
    for path in sorted(Path(folder).glob("*.pdf")):
        status = import_pdf(conn, path)
        counts[status] += 1
        if status == REVIEW:
            print(f"Prüfen: {path.name}")
    print(f"{counts[NEW]} neu, {counts[DUPLICATE]} schon vorhanden, {counts[REVIEW]} zur Prüfung")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../Spar Rechnungen")
