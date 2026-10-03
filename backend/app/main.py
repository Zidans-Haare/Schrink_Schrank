"""Webserver. Start:  uvicorn app.main:app --host 0.0.0.0 --port 8000"""

import tempfile
from pathlib import Path

from typing import Literal

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel
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


class CorrectionIn(BaseModel):
    kind: Literal["used_up", "still_there"]


@app.post("/api/products/{product_id}/corrections")
def add_correction(product_id: int, body: CorrectionIn):
    conn = connect()
    if not conn.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone():
        raise HTTPException(404, "Produkt nicht gefunden")
    return {"id": inventory.add_correction(conn, product_id, body.kind)}


@app.delete("/api/corrections/{correction_id}")
def delete_correction(correction_id: int):
    inventory.delete_correction(connect(), correction_id)
    return {"ok": True}


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
