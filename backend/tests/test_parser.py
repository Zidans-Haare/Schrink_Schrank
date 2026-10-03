from datetime import datetime
from pathlib import Path

import pytest

from app.parser import extract_text, parse_pdf, parse_text

RECEIPTS = Path(__file__).resolve().parents[2] / "Spar Rechnungen"
ALL_PDFS = sorted(RECEIPTS.glob("*.pdf"))

# Die echten Rechnungen sind privat und liegen nicht im Repo.
pytestmark = pytest.mark.skipif(not ALL_PDFS, reason="keine SPAR-Rechnungen vorhanden")


def pdf(bon_id: str) -> Path:
    return RECEIPTS / f"{bon_id}.pdf"


@pytest.mark.parametrize("path", ALL_PDFS, ids=lambda p: p.stem)
def test_alle_bons_gehen_auf(path):
    r = parse_pdf(path)
    assert r.problems == []
    assert r.computed_total == r.total
    assert r.bon_id == path.stem
    assert r.lines


def test_einfacher_bon():
    r = parse_pdf(pdf("264200085400062605111926259476"))
    assert r.purchased_at == datetime(2026, 5, 11, 19, 26)
    assert r.total == 1769
    assert r.store.startswith("INTERSPAR Ringmauergasse 9")
    assert [l.text for l in r.lines][:3] == [
        "IN PAPIERTASCHE",
        "MAN.NEAPOLIT.4-ER",
        "VOES. MILD 1L MW FL.",
    ]


def test_mengenzeile_und_pfand_einweg():
    r = parse_pdf(pdf("264200085400022608081736139287"))
    by_text = {l.text: l for l in r.lines}
    voes = by_text["VOESLAUER OHNE 1L"]
    assert (voes.quantity, voes.unit_price, voes.total) == (2, 97, 194)
    assert by_text["PFAND"].quantity == 2
    einweg = by_text["PFAND EINWEG"]
    assert (einweg.quantity, einweg.unit_price, einweg.total, einweg.tax) == (1, 25, 25, "E")


def test_rabatt_haengt_am_artikel_aktionsersparnis_zaehlt_nicht():
    r = parse_pdf(pdf("264200085400022604021851147315"))
    pfanne = next(l for l in r.lines if l.text == "SIMPEX PFANNE 28CM")
    assert pfanne.saving_info == 500
    assert [d.text for d in pfanne.discounts] == ["Rabatt Toepfe 20%"]
    assert pfanne.paid == 799


def test_leergutbon():
    r = parse_pdf(pdf("264200085400022609301705184153"))
    assert [(d.text, d.amount) for d in r.deposits] == [
        ("EINL. LEERG. 20%", -389),
        ("EINL. LEERGUTB.0% EW", -25),
    ]
    assert r.total == 3897


def test_abweichende_summe_landet_in_pruefliste():
    text = extract_text(pdf("264200085400062605111926259476"))
    r = parse_text(text.replace("AIRWAVES 1,39 A", "AIRWAVES 1,49 A"))
    assert r.needs_review
    assert any("Summe weicht ab" in p for p in r.problems)


def test_unbekannte_zeile_landet_in_pruefliste():
    text = extract_text(pdf("264200085400062605111926259476"))
    r = parse_text(text.replace("AIRWAVES 1,39 A", "AIRWAVES 0,512 kg 1,39"))
    assert r.needs_review
