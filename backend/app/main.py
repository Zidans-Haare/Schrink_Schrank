"""Webserver. Start:  uvicorn app.main:app --host 0.0.0.0 --port 8000"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import inventory
from .db import connect
from .importer import import_pdf

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Nicks Kühlschrank")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/sw.js")
def service_worker():
    # Muss im Wurzelpfad liegen, damit er die ganze App abdeckt.
    return FileResponse(STATIC / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/api/fridge")
def fridge():
    return inventory.fridge(connect())


@app.get("/api/shopping")
def shopping():
    return inventory.shopping_list(connect())


class CorrectionIn(BaseModel):
    kind: Literal["used_up", "still_there"]
    at: datetime | None = None  # gesetzt, wenn die Korrektur offline getippt wurde


@app.post("/api/products/{product_id}/corrections")
def add_correction(product_id: int, body: CorrectionIn):
    conn = connect()
    if not conn.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone():
        raise HTTPException(404, "Produkt nicht gefunden")
    at = None
    if body.at is not None:
        at = body.at.replace(tzinfo=None)
        now = inventory.now()
        if not now - timedelta(days=30) <= at <= now + timedelta(minutes=5):
            raise HTTPException(422, "Zeitpunkt der Korrektur ist unplausibel")
    return {"id": inventory.add_correction(conn, product_id, body.kind, at)}


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
