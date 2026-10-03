"""Webserver. Start:  uvicorn app.main:app --host 0.0.0.0 --port 8000"""

import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse

from . import inventory
from .db import connect
from .importer import import_pdf

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Nicks Kühlschrank")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/fridge")
def fridge():
    return inventory.fridge(connect())


@app.get("/api/shopping")
def shopping():
    return inventory.shopping_list(connect())


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
