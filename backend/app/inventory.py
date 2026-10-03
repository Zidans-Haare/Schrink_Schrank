"""Schätzung "Wahrscheinlich noch da" und automatische Einkaufsliste.

Pro Produkt:
    Verbrauchsdauer = gelernt aus "aufgebraucht"-Korrekturen (Median der Tage
                      vom Kauf bis "aufgebraucht"), sonst Median der Tage
                      zwischen zwei Käufen (ab 3 Käufen), sonst die
                      Standarddauer der Kategorie
    erwartet        = min(Haltbarkeit, Verbrauchsdauer)
    Rest            = 1 - Tage seit Kauf / erwartet

Korrekturen nach dem letzten Kauf:
    aufgebraucht -> weg, bis wieder gekauft wird
    noch da      -> neue Frist ab dem Tipp (halbe erwartete Dauer, mind.
                    2 Tage); die Haltbarkeit ab Kauf gilt weiter

Ampel: grün = sicher da, gelb = bald weg (letztes Drittel), rot = abgelaufen
oder wahrscheinlich aufgebraucht. Rote Einträge bleiben noch kurz sichtbar und
fallen dann aus der Ansicht.

Einkaufsliste: alles, was du mindestens dreimal gekauft hast und dessen
Nachkaufintervall zu mindestens 80 % verstrichen ist. Liegt der letzte Kauf
mehr als drei Intervalle (mindestens 30 Tage) zurück, gilt die Gewohnheit als
aufgegeben. Als aufgebraucht markierte Produkte (ab 2 Käufen) kommen immer
drauf, gerade als "noch da" bestätigte fliegen runter.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time
from statistics import median

FRIDGE_STORAGES = ("tiefkuehler", "kuehlschrank", "tuer", "vorrat")
SHOPPING_STORAGES = FRIDGE_STORAGES + ("haushalt",)
SHOPPING_MIN_PURCHASES = 3
SHOPPING_MIN_PURCHASES_USED_UP = 2
SHOPPING_DUE = 0.8
SHOPPING_GIVEN_UP = 3
SHOPPING_GIVEN_UP_MIN_DAYS = 30
SHOPPING_CONFIRMED_DAYS = 3
MIN_PURCHASES_FOR_INTERVAL = 3
YELLOW_BELOW = 1 / 3
GONE_LIST_DAYS = 45

USED_UP, STILL_THERE = "used_up", "still_there"


def now() -> datetime:
    """Aktuelle Zeit; in Tests ersetzbar."""
    return datetime.now()


def _dt(value: date | datetime) -> datetime:
    return value if isinstance(value, datetime) else datetime.combine(value, time())


@dataclass
class Estimate:
    days_since: int  # seit dem letzten Kauf
    expected_days: int
    interval_days: float | None  # persönliches Nachkaufintervall
    learned_days: float | None  # aus "aufgebraucht"-Korrekturen
    remaining: float  # 0..1
    days_left: int
    status: str  # gruen, gelb, rot, weg
    expired: bool  # Haltbarkeit überschritten
    visible: bool  # in der Kühlschrankansicht zeigen
    correction: str | None  # letzte Korrektur nach dem letzten Kauf
    correction_days: int | None  # vor wie vielen Tagen


def estimate(
    purchases: list[date | datetime],
    shelf_days: int,
    use_days: int,
    today: date | datetime,
    corrections: list[tuple[date | datetime, str]] = (),
) -> Estimate:
    bought = sorted({_dt(p) for p in purchases})
    days = sorted({p.date() for p in bought})
    today_d = _dt(today).date()
    fixes = sorted((_dt(at), kind) for at, kind in corrections)

    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    interval = median(gaps) if len(days) >= MIN_PURCHASES_FOR_INTERVAL else None

    # Gelernt: Tage vom jeweils letzten Kauf davor bis "aufgebraucht".
    observed = []
    for at, kind in fixes:
        before = [p for p in bought if p <= at]
        if kind == USED_UP and before:
            observed.append(max(1, (at.date() - before[-1].date()).days))
    learned = median(observed) if observed else None

    use = learned or interval or use_days
    expected = max(1, round(min(shelf_days, use)))
    last = bought[-1]
    since = (today_d - last.date()).days
    expired = since >= shelf_days

    current = [(at, kind) for at, kind in fixes if at >= last]
    correction, correction_days = (None, None)
    if current:
        correction = current[-1][1]
        correction_days = (today_d - current[-1][0].date()).days

    if correction == USED_UP:
        return Estimate(since, expected, interval, learned, 0.0, 0, "weg", expired, False, correction, correction_days)

    if correction == STILL_THERE:
        window = max(2, round(expected / 2))
        elapsed = correction_days
    else:
        window = expected
        elapsed = since
    remaining = max(0.0, 1 - elapsed / window)
    if expired:
        remaining = 0.0

    if remaining == 0:
        status = "rot"
    elif remaining < YELLOW_BELOW:
        status = "gelb"
    else:
        status = "gruen"
    grace = max(2, window // 2)
    return Estimate(
        days_since=since,
        expected_days=expected,
        interval_days=interval,
        learned_days=learned,
        remaining=round(remaining, 2),
        days_left=max(0, window - elapsed) if not expired else 0,
        status=status,
        expired=expired,
        visible=elapsed < window + grace,
        correction=correction,
        correction_days=correction_days,
    )


def _products(conn: sqlite3.Connection):
    """Käufe und Korrekturen pro Produkt sowie nicht zugeordnete Bontexte."""
    rows = conn.execute(
        """
        SELECT l.text, p.id AS product_id, p.name, p.shelf_days AS product_shelf,
               c.key AS category, c.label AS category_label, c.storage,
               c.shelf_days, c.use_days,
               r.purchased_at, l.quantity, l.unit_price
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
            u["last_bought"] = row["purchased_at"][:10]
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
                "bought": [],
                "corrections": [],
                "last_quantity": 0,
                "last_price": 0,
            },
        )
        at = datetime.fromisoformat(row["purchased_at"])
        if p["bought"] and p["bought"][-1] == at:
            p["last_quantity"] += row["quantity"]
        else:
            p["bought"].append(at)
            p["last_quantity"] = row["quantity"]
        p["last_price"] = row["unit_price"]

    for c in conn.execute("SELECT product_id, kind, at FROM corrections ORDER BY at"):
        if c["product_id"] in products:
            products[c["product_id"]]["corrections"].append((datetime.fromisoformat(c["at"]), c["kind"]))

    return list(products.values()), sorted(unknown.values(), key=lambda u: u["last_bought"], reverse=True)


def _with_estimate(p: dict, today: datetime) -> tuple[dict, Estimate]:
    e = estimate(p["bought"], p["shelf_days"], p["use_days"], today, p["corrections"])
    days = {b.date() for b in p["bought"]}
    item = {
        "id": p["id"],
        "name": p["name"],
        "category": p["category"],
        "category_label": p["category_label"],
        "storage": p["storage"],
        "last_bought": p["bought"][-1].date().isoformat(),
        "times_bought": len(days),
        "last_quantity": p["last_quantity"],
        "last_price": p["last_price"],
        "days_since": e.days_since,
        "expected_days": e.expected_days,
        "days_left": e.days_left,
        "interval_days": e.interval_days,
        "learned_days": e.learned_days,
        "remaining": e.remaining,
        "status": e.status,
        "expired": e.expired,
        "correction": e.correction,
        "correction_days": e.correction_days,
    }
    return item, e


def fridge(conn: sqlite3.Connection, today: datetime | None = None) -> dict:
    today = today or now()
    products, unknown = _products(conn)
    items, gone = [], []
    for p in products:
        if p["storage"] not in FRIDGE_STORAGES:
            continue
        item, e = _with_estimate(p, today)
        if e.visible:
            items.append(item)
        elif e.days_since <= GONE_LIST_DAYS:
            gone.append(item)
    items.sort(key=lambda i: (-i["remaining"], i["name"]))
    gone.sort(key=lambda i: i["days_since"])
    return {"today": today.date().isoformat(), "items": items, "gone": gone, "unknown": unknown}


def shopping_list(conn: sqlite3.Connection, today: datetime | None = None) -> list[dict]:
    today = today or now()
    products, _ = _products(conn)
    result = []
    for p in products:
        if p["storage"] not in SHOPPING_STORAGES:
            continue
        item, e = _with_estimate(p, today)
        times = item["times_bought"]
        if e.correction == STILL_THERE and e.correction_days <= SHOPPING_CONFIRMED_DAYS:
            continue
        if e.correction == USED_UP and times >= SHOPPING_MIN_PURCHASES_USED_UP:
            due = max(1.0, e.days_since / e.interval_days) if e.interval_days else 1.0
            result.append({**item, "due": round(due, 2)})
            continue
        if times < SHOPPING_MIN_PURCHASES or e.interval_days is None:
            continue
        due = e.days_since / e.interval_days
        given_up = max(SHOPPING_GIVEN_UP * e.interval_days, SHOPPING_GIVEN_UP_MIN_DAYS)
        if due >= SHOPPING_DUE and e.days_since <= given_up:
            result.append({**item, "due": round(due, 2)})
    result.sort(key=lambda i: (i["correction"] != USED_UP, -i["due"]))  # Aufgebrauchtes zuerst
    return result


def add_correction(conn: sqlite3.Connection, product_id: int, kind: str, at: datetime | None = None) -> int:
    with conn:
        return conn.execute(
            "INSERT INTO corrections (product_id, kind, at) VALUES (?, ?, ?)",
            (product_id, kind, (at or now()).isoformat(timespec="minutes")),
        ).lastrowid


def delete_correction(conn: sqlite3.Connection, correction_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM corrections WHERE id = ?", (correction_id,))
