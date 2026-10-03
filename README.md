# Nicks Kühlschrank

Persönliche Handy-Web-App (PWA), die aus digitalen SPAR-Rechnungen schätzt, was wahrscheinlich noch im Kühlschrank oder Vorrat ist. Gedacht für den Blick im Supermarkt: „Was habe ich noch zu Hause?“

Ein Eigenprojekt nur für mich, kein Produkt für andere. Die Idee stammt aus dem HTW-Businessplan „MealMaster“ (Baustein Inventar).

## Was die App kann

- **Rechnungen importieren:** SPAR-Rechnungs-PDFs hochladen, einzeln oder im Stapel. Duplikate werden erkannt.
- **Artikel erkennen:** Ein deterministischer Parser liest die Positionen und prüft Summe und Steuer gegen den Bon. Weicht etwas ab, kommt der Bon in eine Prüfliste.
- **Zuordnung:** Bontexte werden über eine Alias-Tabelle einem Produkt samt Kategorie zugeordnet. Pfand, Drogerie und Sackerl werden ausgeblendet.
- **„Wahrscheinlich noch da“:** Die Ansicht zeigt den geschätzten Bestand, sortiert nach Ablauf, als Ampel:
  - grün: sicher da
  - gelb: vermutlich aufgebraucht
  - rot: abgelaufen oder weg
- **Korrekturen per Tipp:** „aufgebraucht“ oder „noch da“, mit Rückgängig. Die App lernt daraus die typische Verbrauchsdauer.
- **Einkaufsliste:** wird automatisch aus dem geschätzten Bestand und dem Nachkaufverhalten erzeugt.
- **Offline:** Die letzte Ansicht bleibt im Cache, Korrekturen ohne Empfang landen in einer Warteschlange und werden später gesendet (schlechter Empfang im Markt).

## Wie die Schätzung funktioniert

Der Inventarstatus wird bei jeder Anfrage berechnet und nicht gespeichert. Die Restwahrscheinlichkeit ergibt sich aus `min(Haltbarkeit, typische Verbrauchsdauer)` seit dem letzten Kauf. Die typische Verbrauchsdauer ist der Median der Tage zwischen Käufen desselben Produkts. Die Haltbarkeiten stehen in einer kleinen Kategorientabelle und sind pro Produkt überschreibbar.

## Stack

| Bereich | Technik |
| --- | --- |
| Backend | Python, FastAPI |
| Datenbank | SQLite |
| PDF | pdfplumber (die SPAR-PDFs enthalten Text, OCR ist nicht nötig) |
| Frontend | eine einzelne HTML-Datei mit Vanilla-JS, kein Build-Schritt |
| PWA | Manifest, Service Worker, lokale Schriften |
| Betrieb | Docker Compose mit Caddy (HTTPS) |

## Projektstruktur

```
backend/
  app/
    main.py        FastAPI-Routen
    parser.py      SPAR-Bon-Parser mit Summen- und Steuerprüfung
    importer.py    Import mit Duplikaterkennung (auch als Kommandozeile)
    inventory.py   Schätzung, Ampel, Einkaufsliste
    seed.py        Kategorien und Bontext-Zuordnung
    db.py          SQLite-Datenmodell
    static/        index.html, sw.js, manifest, Icons, Schriften
  tests/           pytest-Tests
  Dockerfile
docker-compose.yml
Caddyfile
DEPLOY.md          Anleitung für den Server
```

## Entwicklung

```sh
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Die App läuft dann unter <http://127.0.0.1:8000>. Tests:

```sh
.venv/bin/pytest
```

Die echten Rechnungen liegen lokal in `Spar Rechnungen/` und nie im Repo, weil sie private Daten enthalten. Ohne sie überspringen sich die Tests, die sie brauchen. Das Gleiche gilt für die Datenbank (`*.db`).

## API

| Route | Zweck |
| --- | --- |
| `GET /api/fridge` | geschätzter Bestand mit Ampel |
| `GET /api/shopping` | automatische Einkaufsliste |
| `POST /api/products/{id}/corrections` | Korrektur „aufgebraucht“ / „noch da“ |
| `DELETE /api/corrections/{id}` | Korrektur rückgängig machen |
| `GET /api/receipts` | importierte Rechnungen |
| `POST /api/upload` | Rechnungs-PDFs hochladen |

## Betrieb

Geplant ist ein eigener Server unter `fridge.olomek.com` mit Docker Compose und Caddy. HTTPS ist Pflicht, sonst funktionieren Offline-Modus und Installation als App nicht. Die Schritte stehen in [DEPLOY.md](DEPLOY.md).

Die App hat bewusst **kein Passwort**: Wer die Adresse kennt, sieht die Daten. Bei Bedarf lässt sich Basic-Auth im Caddyfile ergänzen (siehe `DEPLOY.md`).

## Stand

Fertig: Parser (54 echte Rechnungen, alle Summen- und Steuerprüfungen grün), Import, Kategorien und Zuordnung, Schätzung und Einkaufsliste, Oberfläche, Korrekturen mit Lernen, PWA mit Offline-Modus.

Offen:

- Handeingabe, z. B. für Gemüse vom Markt
- Sprachmodell für unbekannte Bontexte, mit Bestätigungsklick, der den Alias speichert
- Haltbarkeiten mit echten USDA-FoodKeeper-Daten abgleichen
- Server einrichten

Später, optional: Supermarktvergleich mit Preisen aus heisse-preise.io und Preishistorie pro Artikel aus den eigenen Rechnungen.

Bewusst gestrichen: Rezept-Tinder, Rezeptbuch, Community, Familienaccounts, Werbung, Verkauf von Nutzerdaten.

## Hinweise

- **Aufbewahrung bei SPAR:** 14 Monate ab Kaufdatum. Ältere Rechnungen rechtzeitig exportieren. Beim Zurücksetzen des App-Kontos gehen sie verloren.
- **Rechtliches:** Nur eigene Rechnungen für den eigenen Gebrauch zu parsen ist unkritisch. Wird die App je für andere geöffnet, muss das neu bewertet werden.

## Vorbilder

- rewe-ebon-parser (webD97, e-kotov): PDF-Bon-Parser mit Summenprüfung
- USDA FoodKeeper: Quelle für Haltbarkeits-Standardwerte
- heisse-preise.io: Preisdaten für den optionalen Vergleich
- HNGRY (Liebherr): Konzeptvorbild für „ist wahrscheinlich noch da“
