"""Parser für digitale SPAR-Rechnungen (PDF mit Textebene).

Aufbau eines Bons (Ausschnitt):

    Ihr Einkauf am 11.05.2026 um 19:26 Uhr
    ----------------------------------------
    EUR
    VOESLAUER OHNE 1L            <- Name ohne Preis, Mengenzeile folgt
    2 x 0,97 1,94 B
    BARILLA SUGO 3,79 A
    App-Joker 25% -0,95          <- Rabatt auf die Zeile darüber
    Aktionsersparnis 0,50        <- nur Hinweis, zählt nicht zur Summe
    PFAND EINWEG 0,25 0,25 E     <- Einzelpreis + Gesamtpreis
    ----------------------------------------
    EINL. LEERG. 20% -3,89 B     <- optional: eingelöster Leergutbon
    ----------------------------------------
    SUMME: 38,97

Alle Beträge in Cent (int). Die Summe der Positionen, Rabatte und
Leergutbons wird gegen die Bonsumme geprüft. Weicht sie ab oder gibt es
unbekannte Zeilen, gilt der Bon als prüfbedürftig (`needs_review`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pdfplumber

AMOUNT = r"-?\d+,\d{2}"

RE_DATE = re.compile(r"^Ihr Einkauf am (\d{2}\.\d{2}\.\d{4}) um (\d{2}:\d{2}) Uhr$")
RE_SUM = re.compile(rf"^SUMME: ({AMOUNT})$")
RE_BON_ID = re.compile(r"^\d{30}$")
RE_SEPARATOR = re.compile(r"^-{10,}$")
RE_TAX = re.compile(rf"^(\d+,\d{{2}})% ({AMOUNT}) ({AMOUNT}) ({AMOUNT}) ([A-Z])$")

RE_QTY = re.compile(rf"^(\d+) x ({AMOUNT}) ({AMOUNT}) ([A-Z])$")
RE_UNIT_AND_TOTAL = re.compile(rf"^(.+?) ({AMOUNT}) ({AMOUNT}) ([A-Z])$")
RE_ITEM = re.compile(rf"^(.+?) ({AMOUNT}) ([A-Z])$")
RE_INFO = re.compile(rf"^(Aktionsersparnis) ({AMOUNT})$")
RE_DISCOUNT = re.compile(r"^(.+?) (-\d+,\d{2})$")


def cents(s: str) -> int:
    neg = s.startswith("-")
    euros, ct = s.lstrip("-").split(",")
    value = int(euros) * 100 + int(ct)
    return -value if neg else value


@dataclass
class Discount:
    text: str
    amount: int  # negativ


@dataclass
class Line:
    text: str
    quantity: int
    unit_price: int
    total: int  # vor Rabatten
    tax: str
    discounts: list[Discount] = field(default_factory=list)
    saving_info: int = 0  # "Aktionsersparnis", bereits im Preis enthalten

    @property
    def paid(self) -> int:
        return self.total + sum(d.amount for d in self.discounts)


@dataclass
class Deposit:
    """Eingelöster Leergutbon."""

    text: str
    amount: int  # negativ
    tax: str


@dataclass
class Receipt:
    bon_id: str
    purchased_at: datetime
    store: str
    total: int
    lines: list[Line]
    deposits: list[Deposit]
    tax_totals: dict[str, int]  # Steuerbuchstabe -> Bruttobetrag
    problems: list[str]

    @property
    def computed_total(self) -> int:
        return sum(l.paid for l in self.lines) + sum(d.amount for d in self.deposits)

    @property
    def needs_review(self) -> bool:
        return bool(self.problems)


def extract_text(pdf_path: str | Path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def parse_pdf(pdf_path: str | Path) -> Receipt:
    return parse_text(extract_text(pdf_path))


def parse_text(text: str) -> Receipt:
    rows = [r.strip() for r in text.splitlines() if r.strip()]
    problems: list[str] = []

    purchased_at = None
    total = None
    bon_id = ""
    tax_totals: dict[str, int] = {}
    for row in rows:
        if m := RE_DATE.match(row):
            purchased_at = datetime.strptime(" ".join(m.groups()), "%d.%m.%Y %H:%M")
        elif m := RE_SUM.match(row):
            total = cents(m.group(1))
        elif RE_BON_ID.match(row):
            bon_id = row
        elif m := RE_TAX.match(row):
            tax_totals[m.group(5)] = cents(m.group(4))

    store = _store(rows)
    if purchased_at is None:
        problems.append("Kaufdatum nicht gefunden")
    if total is None:
        problems.append("Bonsumme nicht gefunden")
    if not bon_id:
        problems.append("Bonnummer nicht gefunden")

    item_rows, deposit_rows = _sections(rows)
    lines = _parse_items(item_rows, problems)
    deposits = _parse_deposits(deposit_rows, problems)

    receipt = Receipt(
        bon_id=bon_id,
        purchased_at=purchased_at or datetime.min,
        store=store,
        total=total or 0,
        lines=lines,
        deposits=deposits,
        tax_totals=tax_totals,
        problems=problems,
    )
    if total is not None and receipt.computed_total != total:
        problems.append(
            f"Summe weicht ab: Positionen {receipt.computed_total / 100:.2f} "
            f"≠ Bon {total / 100:.2f}"
        )
    _check_tax_totals(receipt)
    return receipt


def _store(rows: list[str]) -> str:
    name = "SPAR"
    for i, row in enumerate(rows):
        if row.startswith("Vielen Dank für Ihren Einkauf bei") and i + 1 < len(rows):
            name = rows[i + 1]
    address = ", ".join(rows[:2]).split(", 0")[0]  # Telefonnummer abschneiden
    return f"{name} {address}".strip()


def _sections(rows: list[str]) -> tuple[list[str], list[str]]:
    """Positionen (EUR bis erster Strich) und Leergut (bis SUMME)."""
    try:
        start = rows.index("EUR") + 1
    except ValueError:
        return [], []
    items: list[str] = []
    deposits: list[str] = []
    target = items
    for row in rows[start:]:
        if RE_SUM.match(row):
            break
        if RE_SEPARATOR.match(row):
            target = deposits
            continue
        target.append(row)
    return items, deposits


def _parse_items(rows: list[str], problems: list[str]) -> list[Line]:
    lines: list[Line] = []
    pending_name: str | None = None

    for row in rows:
        if pending_name is not None:
            name, pending_name = pending_name, None
            if m := RE_QTY.match(row):
                qty, unit, tot, tax = m.groups()
                lines.append(Line(name, int(qty), cents(unit), cents(tot), tax))
                continue
            problems.append(f"Mengenzeile fehlt nach: {name!r}")

        if m := RE_INFO.match(row):
            if lines:
                lines[-1].saving_info += cents(m.group(2))
        elif m := RE_UNIT_AND_TOTAL.match(row):
            text, unit, tot, tax = m.groups()
            unit_c, tot_c = cents(unit), cents(tot)
            qty = tot_c // unit_c if unit_c and tot_c % unit_c == 0 else 1
            lines.append(Line(text, qty, unit_c, tot_c, tax))
        elif m := RE_ITEM.match(row):
            text, tot, tax = m.groups()
            lines.append(Line(text, 1, cents(tot), cents(tot), tax))
        elif m := RE_DISCOUNT.match(row):
            if lines:
                lines[-1].discounts.append(Discount(m.group(1), cents(m.group(2))))
            else:
                problems.append(f"Rabatt ohne Artikel: {row!r}")
        elif not re.search(r"\d,\d{2}", row):
            pending_name = row
        else:
            problems.append(f"Unbekannte Zeile: {row!r}")

    if pending_name is not None:
        problems.append(f"Mengenzeile fehlt nach: {pending_name!r}")
    return lines


def _parse_deposits(rows: list[str], problems: list[str]) -> list[Deposit]:
    deposits = []
    for row in rows:
        if (m := RE_ITEM.match(row)) and m.group(2).startswith("-"):
            deposits.append(Deposit(m.group(1), cents(m.group(2)), m.group(3)))
        else:
            problems.append(f"Unbekannte Zeile im Leergutteil: {row!r}")
    return deposits


def _check_tax_totals(receipt: Receipt) -> None:
    """Zweite Kontrolle: Bruttosummen je Steuersatz."""
    if not receipt.tax_totals:
        return
    per_tax: dict[str, int] = {}
    for line in receipt.lines:
        per_tax[line.tax] = per_tax.get(line.tax, 0) + line.paid
    for dep in receipt.deposits:
        per_tax[dep.tax] = per_tax.get(dep.tax, 0) + dep.amount
    for tax, amount in receipt.tax_totals.items():
        if per_tax.get(tax, 0) != amount:
            receipt.problems.append(
                f"Steuersatz {tax}: Positionen {per_tax.get(tax, 0) / 100:.2f} "
                f"≠ Bon {amount / 100:.2f}"
            )
