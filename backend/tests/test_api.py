from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RECEIPTS = Path(__file__).resolve().parents[2] / "Spar Rechnungen"
pytestmark = pytest.mark.skipif(not RECEIPTS.exists(), reason="keine SPAR-Rechnungen vorhanden")


@pytest.fixture
def client(tmp_path, monkeypatch):
    from datetime import datetime

    from app import db, inventory, main
    from app.importer import import_pdf

    path = tmp_path / "test.db"
    monkeypatch.setattr(main, "connect", lambda: db.connect(path))
    monkeypatch.setattr(inventory, "now", lambda: datetime(2026, 10, 3, 20, 0))
    conn = db.connect(path)
    for pdf in sorted(RECEIPTS.glob("*.pdf")):
        import_pdf(conn, pdf)
    return TestClient(main.app)


def test_aufgebraucht_und_rueckgaengig(client):
    item = next(i for i in client.get("/api/fridge").json()["items"] if i["name"] == "Mozzarella")
    cid = client.post(f"/api/products/{item['id']}/corrections", json={"kind": "used_up"}).json()["id"]

    fridge = client.get("/api/fridge").json()
    assert "Mozzarella" not in [i["name"] for i in fridge["items"]]
    assert "Mozzarella" in [i["name"] for i in fridge["gone"]]
    assert "Mozzarella" in [i["name"] for i in client.get("/api/shopping").json()]

    client.delete(f"/api/corrections/{cid}")
    assert "Mozzarella" in [i["name"] for i in client.get("/api/fridge").json()["items"]]


def test_noch_da_nimmt_von_der_einkaufsliste(client):
    item = next(i for i in client.get("/api/shopping").json() if i["name"] == "Vöslauer")
    client.post(f"/api/products/{item['id']}/corrections", json={"kind": "still_there"})
    assert "Vöslauer" not in [i["name"] for i in client.get("/api/shopping").json()]
    assert "Vöslauer" in [i["name"] for i in client.get("/api/fridge").json()["items"]]


def test_unbekannte_korrektur_wird_abgelehnt(client):
    assert client.post("/api/products/1/corrections", json={"kind": "egal"}).status_code == 422
    assert client.post("/api/products/99999/corrections", json={"kind": "used_up"}).status_code == 404
