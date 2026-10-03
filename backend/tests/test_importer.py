from pathlib import Path

import pytest

from app.db import connect
from app.importer import DUPLICATE, NEW, import_pdf

RECEIPTS = Path(__file__).resolve().parents[2] / "Spar Rechnungen"
BON = RECEIPTS / "264200085400022608081736139287.pdf"

pytestmark = pytest.mark.skipif(not BON.exists(), reason="keine SPAR-Rechnungen vorhanden")


@pytest.fixture
def conn(tmp_path):
    return connect(tmp_path / "test.db")


def test_import_speichert_bon_und_zeilen(conn):
    assert import_pdf(conn, BON) == NEW
    r = conn.execute("SELECT * FROM receipts").fetchone()
    assert (r["total"], r["purchased_at"], r["needs_review"]) == (4439, "2026-08-08T17:35", 0)
    paid = conn.execute("SELECT SUM(paid) FROM receipt_lines").fetchone()[0]
    assert paid == 4439


def test_gleiche_datei_wird_uebersprungen(conn):
    import_pdf(conn, BON)
    assert import_pdf(conn, BON) == DUPLICATE
    assert conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1


def test_neu_exportierter_bon_wird_an_bonnummer_erkannt(conn, tmp_path):
    import_pdf(conn, BON)
    copy = tmp_path / "export.pdf"
    copy.write_bytes(BON.read_bytes() + b"\n%  anderer Export\n")
    assert import_pdf(conn, copy) == DUPLICATE
