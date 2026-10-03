"""Schätzung "Wahrscheinlich noch da" und automatische Einkaufsliste.

Pro Produkt:
    Verbrauchsdauer = Median der Tage zwischen zwei Käufen (ab 3 Käufen),
                      sonst die Standarddauer der Kategorie
    erwartet        = min(Haltbarkeit, Verbrauchsdauer)
    Rest            = 1 - Tage seit Kauf / erwartet

Ampel: grün = sicher da, gelb = bald weg (letztes Drittel), rot = abgelaufen
oder wahrscheinlich aufgebraucht. Rote Einträge bleiben noch kurz sichtbar und
fallen dann aus der Ansicht.

Einkaufsliste: alles, was du mindestens dreimal gekauft hast und dessen
Nachkaufintervall zu mindestens 80 % verstrichen ist. Liegt der letzte Kauf
mehr als drei Intervalle (mindestens 30 Tage) zurück, gilt die Gewohnheit als
aufgegeben und das Produkt fällt wieder von der Liste.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date
from statistics import median

FRIDGE_STORAGES = ("tiefkuehler", "kuehlschrank", "tuer", "vorrat")
SHOPPING_STORAGES = FRIDGE_STORAGES + ("haushalt",)
SHOPPING_MIN_PURCHASES = 3
SHOPPING_DUE = 0.8
SHOPPING_GIVEN_UP = 3
SHOPPING_GIVEN_UP_MIN_DAYS = 30
MIN_PURCHASES_FOR_INTERVAL = 3
YELLOW_BELOW = 1 / 3


@dataclass
class Estimate:
    days_since: int
    expected_days: int
    interval_days: float | None  # persönliches Nachkaufintervall
    remaining: float  # 0..1
    status: str  # gruen, gelb, rot
    expired: bool  # Haltbarkeit überschritten (nicht nur aufgebraucht)
    visible: bool  # noch in der Kühlschrankansicht zeigen


def estimate(purchase_days: list[date], shelf_days: int, use_days: int, today: date) -> Estimate:
    days = sorted(set(purchase_days))
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    interval = median(gaps) if len(days) >= MIN_PURCHASES_FOR_INTERVAL else None
    use = interval if interval is not None else use_days
    expected = max(1, round(min(shelf_days, use)))
    since = (today - days[-1]).days
    remaining = max(0.0, 1 - since / expected)

    if remaining == 0:
        status = "rot"
    elif remaining < YELLOW_BELOW:
        status = "gelb"
    else:
        status = "gruen"
    grace = max(2, expected // 2)
    return Estimate(
        days_since=since,
        expected_days=expected,
        interval_days=interval,
        remaining=round(remaining, 2),
        status=status,
        expired=since >= shelf_days,
        visible=since < expected + grace,
    )


def _purchases(conn: sqlite3.Connection):
    """Kaufdaten pro Produkt sowie nicht zugeordnete Bontexte."""
    rows = conn.execute(
        """
        SELECT l.text, p.id AS product_id, p.name, p.shelf_days AS product_shelf,
               c.key AS category, c.label AS category_label, c.storage,
               c.shelf_days, c.use_days,
               date(r.purchased_at) AS day, l.quantity, l.unit_price
        FROM receipt_lines l
        JOIN receipts r ON r.id = l.receipt_id
        LEFT JOIN aliases a ON a.text = l.text
        LEFT JOIN products p ON p.id = a.product_id
        LEFT JOIN categories c ON c.key = p.category
        WHERE l.kind = 'item'
        ORDER BY r.purchased_at
        """
    ).fetchall()
    products: dict[int, dict] = {}
    unknown: dict[str, dict] = {}
    for row in rows:
        if row["product_id"] is None or row["category"] is None:
            u = unknown.setdefault(row["text"], {"text": row["text"], "times_bought": 0})
            u["times_bought"] += 1
            u["last_bought"] = row["day"]
            continue
        p = products.setdefault(
            row["product_id"],
            {
                "id": row["product_id"],
                "name": row["name"],
                "category": row["category"],
                "category_label": row["category_label"],
                "storage": row["storage"],
                "shelf_days": row["product_shelf"] or row["shelf_days"],
                "use_days": row["use_days"],
                "days": [],
                "last_quantity": 0,
                "last_price": 0,
            },
        )
        day = date.fromisoformat(row["day"])
        if p["days"] and p["days"][-1] == day:
            p["last_quantity"] += row["quantity"]
        else:
            p["days"].append(day)
            p["last_quantity"] = row["quantity"]
        p["last_price"] = row["unit_price"]
    return list(products.values()), sorted(unknown.values(), key=lambda u: u["last_bought"], reverse=True)


def _public(p: dict, e: Estimate) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "category": p["category"],
        "category_label": p["category_label"],
        "storage": p["storage"],
        "last_bought": p["days"][-1].isoformat(),
        "times_bought": len(p["days"]),
        "last_quantity": p["last_quantity"],
        "last_price": p["last_price"],
        "days_since": e.days_since,
        "expected_days": e.expected_days,
        "days_left": max(0, e.expected_days - e.days_since),
        "interval_days": e.interval_days,
        "remaining": e.remaining,
        "status": e.status,
        "expired": e.expired,
    }


def fridge(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or date.today()
    products, unknown = _purchases(conn)
    items = []
    for p in products:
        if p["storage"] not in FRIDGE_STORAGES:
            continue
        e = estimate(p["days"], p["shelf_days"], p["use_days"], today)
        if e.visible:
            items.append(_public(p, e))
    items.sort(key=lambda i: (-i["remaining"], i["name"]))
    return {"today": today.isoformat(), "items": items, "unknown": unknown}


def shopping_list(conn: sqlite3.Connection, today: date | None = None) -> list[dict]:
    today = today or date.today()
    products, _ = _purchases(conn)
    result = []
    for p in products:
        if p["storage"] not in SHOPPING_STORAGES or len(p["days"]) < SHOPPING_MIN_PURCHASES:
            continue
        e = estimate(p["days"], p["shelf_days"], p["use_days"], today)
        if e.interval_days is None:
            continue
        due = e.days_since / e.interval_days
        given_up = max(SHOPPING_GIVEN_UP * e.interval_days, SHOPPING_GIVEN_UP_MIN_DAYS)
        if due >= SHOPPING_DUE and e.days_since <= given_up:
            result.append({**_public(p, e), "due": round(due, 2)})
    result.sort(key=lambda i: -i["due"])
    return result
