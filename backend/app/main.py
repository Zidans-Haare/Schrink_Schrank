"""Webserver. Start:  uvicorn app.main:app --host 0.0.0.0 --port 8000"""

import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse

from .db import connect
from .importer import import_pdf

STATIC = Path(__file__).resolve().parent / "static"

# Übergangslösung, bis es Kategorien gibt: diese Bontexte sind keine Lebensmittel.
HIDDEN_PREFIXES = ("PFAND", "IN PAPIERTASCHE", "TRAGTASCHE", "SACKERL", "EINL. LEERG")

app = FastAPI(title="Nicks Kühlschrank")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/items")
def items():
    """Ein Eintrag pro Bontext, zuletzt gekauft zuerst."""
    conn = connect()
    rows = conn.execute(
        """
        SELECT l.text,
               MAX(r.purchased_at)        AS last_bought,
               COUNT(DISTINCT r.id)       AS times_bought,
               SUM(l.quantity)            AS total_quantity,
               MAX(r.needs_review)        AS needs_review
        FROM receipt_lines l JOIN receipts r ON r.id = l.receipt_id
        WHERE l.kind = 'item'
        GROUP BY l.text
        ORDER BY last_bought DESC, l.text
        """
    ).fetchall()
    result = []
    for row in rows:
        if row["text"].upper().startswith(HIDDEN_PREFIXES):
            continue
        last = conn.execute(
            """
            SELECT SUM(l.quantity) AS quantity, MAX(l.unit_price) AS unit_price,
                   SUM(l.paid) AS paid
            FROM receipt_lines l
            JOIN receipts r ON r.id = l.receipt_id
            WHERE l.text = ? AND r.purchased_at = ? AND l.kind = 'item'
            """,
            (row["text"], row["last_bought"]),
        ).fetchone()
        result.append(
            {
                **dict(row),
                "last_quantity": last["quantity"],
                "last_unit_price": last["unit_price"],
                "last_paid": last["paid"],
            }
        )
    return result


@app.get("/api/receipts")
def receipts():
    conn = connect()
    rows = conn.execute(
        "SELECT id, purchased_at, store, total, needs_review, problems FROM receipts"
        " ORDER BY purchased_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/upload")
def upload(files: list[UploadFile]):
    conn = connect()
    results = []
    for f in files:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(f.file.read())
            tmp.flush()
            try:
                status = import_pdf(conn, tmp.name)
            except Exception as e:  # kein lesbares PDF o. Ä.
                status = f"Fehler: {e}"
        results.append({"file": f.filename, "status": status})
    return results
