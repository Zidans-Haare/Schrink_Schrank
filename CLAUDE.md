# Nicks Kühlschrank

Persönliche Handy-Web-App (PWA), die aus digitalen SPAR-Rechnungen schätzt, was wahrscheinlich noch im Kühlschrank/Vorrat ist. Gedacht für den Blick im Supermarkt: "Was habe ich noch zu Hause?"

Herkunft: Die Idee stammt aus dem HTW-Businessplan "MealMaster" (Inventar-Baustein). Nur dieser Baustein wird umgesetzt, und zwar als Eigenprojekt nur für mich (Nick), nicht als Produkt für andere.

## Ziel und Umfang

**Kern (jetzt):**
- SPAR-Rechnungs-PDFs hochladen (einzeln oder im Stapel)
- Artikel automatisch erkennen und einem Produkt samt Kategorie zuordnen
- Haltbarkeit schätzen und eine Ansicht "Wahrscheinlich noch da" zeigen, sortiert nach Ablauf
- Mit einem Tipp "aufgebraucht" oder "noch da" korrigieren, außerdem Dinge von Hand ergänzen (z. B. Gemüse vom Markt)

**Optional (später):**
- Supermarktvergleich: Preise aus heisse-preise.io (täglicher Rohdatensatz für Billa, Spar, Hofer, Lidl, MPREIS) neben die Stammprodukte legen
- Preishistorie pro Artikel aus den eigenen Rechnungen

**Bewusst gestrichen:** Rezept-Tinder, Rezeptbuch, Community, Familienaccounts, Werbung, Verkauf von Nutzerdaten.

## Gesetzte Entscheidungen

- **Form:** PWA, mobil-first, mit Offline-Cache der letzten Inventaransicht (schlechter Empfang im Markt)
- **Betrieb:** eigener Server unter `fridge.olomek.com` (Schreibweise beim Einrichten bestätigen), nur für eine Person. Docker Compose mit Caddy für HTTPS, Anleitung in `DEPLOY.md`.
- **Zugang:** bewusst **kein Passwort** (Nicks Entscheidung vom 03.10.2026, ursprünglich war ein einziges Passwort geplant). Wer die Adresse kennt, sieht die Daten. Bei Bedarf Basic-Auth im Caddyfile, siehe `DEPLOY.md`.
- **Stack:** Python + FastAPI, SQLite, pdfplumber. Frontend ist eine einzelne HTML-Datei mit Vanilla-JS (`backend/app/static/index.html`), kein Build-Schritt. PWA mit Manifest, Service Worker (`sw.js`) und lokalen Schriften.
- **Datenhaltung:** SQLite
- **Datenquelle:** exportierte SPAR-Rechnungs-PDFs. Die PDFs enthalten durchsuchbaren Text, OCR ist also nicht nötig. SPAR bietet nur den Export pro Rechnung und keine API.
- **Parser:** deterministischer Regex-Parser für das SPAR-Layout. Er prüft die Summe der erkannten Positionen gegen die Bonsumme (Vorbild: rewe-ebon-parser von webD97 und e-kotov). Wenn die Summe abweicht, kommt der Bon in eine Prüfliste.
- **Normalisierung der Bon-Kürzel:** erst eine eigene Alias-Tabelle `bontext → Produkt + Kategorie`. Nur bei unbekanntem Text ein Aufruf an ein Sprachmodell mit fester Kategorieliste und JSON-Ausgabe. Danach ein Bestätigungsklick, der den Alias dauerhaft speichert. Der API-Schlüssel bleibt serverseitig.
- **Nicht-Lebensmittel:** Pfand, Drogerie, Sackerl usw. per Kategorie ausblenden.
- **Haltbarkeit:** kleine eigene Tabelle mit etwa 30–50 Kategorien, abgeleitet aus den USDA-FoodKeeper-Daten, pro Produkt überschreibbar.
- **Schätzlogik:** Restwahrscheinlichkeit aus `min(Haltbarkeit, typischer Verbrauchsdauer)` seit dem letzten Kauf. Die typische Verbrauchsdauer kommt aus dem persönlichen Nachkaufintervall (Median der Tage zwischen Käufen). Anzeige als Ampel: grün = sicher da, gelb = vermutlich aufgebraucht, rot = abgelaufen oder weg. Korrekturen per Tipp trainieren die Dauer nach.
- **Datenmodell (Start):** `receipts` (Datum, Markt, Summe, Hash gegen Duplikate), `receipt_lines` (Bontext, Menge, Preis), `products` (Name, Kategorie, Haltbarkeit in Tagen, Lagerort), `aliases` (Bontext → product_id). Der Inventarstatus wird bei jeder Anfrage berechnet und nicht gespeichert.

## Wichtige Hinweise

- **Aufbewahrung bei SPAR:** laut SPAR-eigener Angabe 14 Monate ab Kaufdatum. Ältere Rechnungen sollten bald exportiert werden. Beim Zurücksetzen oder Neuanlegen des App-Kontos gehen sie verloren.
- **Anfrage an SPAR (app@spar.at):** Eine Mail nach einer API oder einem Sammelexport mit App-Login als Authentifizierung ist rausgegangen oder wird gesendet. Kommt eine Antwort, wird nur die Datenquelle ausgetauscht, der Rest bleibt.
- **Weitere Händler** (jö/BILLA, HOFER) bieten keinen Export. Nur Lidl Plus hat eine inoffizielle API (`lidl-plus`), die auch Österreich unterstützt. Sie ist fragil und nur optional.
- **Rechtliches:** Nur meine eigenen Rechnungen für mich selbst zu parsen ist unkritisch. Inoffizielle App-APIs verletzen meist die Nutzungsbedingungen. Wenn die App je für andere geöffnet wird, muss das neu bewertet werden.
- Die Marktrecherche (Vergleichstabelle, Repos, Quellen) liegt als eigenes Dokument vor.

## Referenzprojekte (Bausteine, nicht als Basis)

- rewe-ebon-parser (webD97, TypeScript; e-kotov, Python): Vorlage für PDF-Bon-Parser mit Summenprüfung
- Grocy: Inventar-Backend mit API, nur falls später ein exakter Bestand gewünscht ist (passt schlecht zur Wahrscheinlichkeitsidee)
- USDA FoodKeeper: Quelle für Haltbarkeits-Standardwerte
- heisse-preise.io / `heisse-preise-data`: Preisdaten für den optionalen Vergleich
- HNGRY (Liebherr): Konzeptvorbild für "ist wahrscheinlich noch da"

## Stand (03.10.2026)

Fertig: Parser (54 echte Rechnungen, alle Summen- und Steuerprüfungen grün), Import mit Duplikaterkennung, Kategorien und Bontext-Zuordnung (`backend/app/seed.py`), Schätzung und automatische Einkaufsliste (`backend/app/inventory.py`), Kühlschrank-Oberfläche, Korrekturen „aufgebraucht“ / „noch da“ mit Lernen der Verbrauchsdauer, PWA mit Offline-Modus und Offline-Warteschlange für Korrekturen.

Offen: Handeingabe (Markt-Gemüse), Sprachmodell für unbekannte Bontexte samt Bestätigung, Haltbarkeiten mit echten FoodKeeper-Daten abgleichen, Server-Einrichtung.

Entwicklung: `cd backend && .venv/bin/uvicorn app.main:app --reload`, Tests mit `.venv/bin/pytest`. Die Rechnungen liegen lokal in `Spar Rechnungen/` und nie im Repo (öffentlich); ohne sie überspringen sich die Tests, die sie brauchen.

## Offene Fragen fürs Brainstorming

Erledigt: 1 (Stack), 2 (Domain), 4 (kein Passwort), 7 (Reihenfolge), 8 (Testdaten). Noch offen: 3, 5, 6.


1. **Stack:** Was läuft auf dem Server (Docker, Node, Python)? Passend dazu Backend (z. B. FastAPI oder Node) und Frontend (z. B. SvelteKit oder Next.js) wählen.
2. **Domain:** Welche Domain oder Subdomain ist dafür vorgesehen?
3. **PDF-Eingang:** Reicht der Datei-Upload, oder soll unter Android ein Teilen-Ziel (Web Share Target) dazukommen? Unter iOS gibt es das nicht.
4. **Passwortschutz:** Passwort in der App, HTTP-Basic-Auth oder Vorschaltdienst am Server?
5. **Sprachmodell:** Welcher Anbieter und welches Modell für die Normalisierung unbekannter Kürzel?
6. **Handeingaben:** Wie einfach sollen manuelle Ergänzungen sein (z. B. nur Name und Menge)?
7. **Erste Version:** Wo soll der Schnitt liegen: Parser plus Liste, danach Ampel-Schätzung, danach Korrekturen?
8. **Testdaten:** Sobald die ersten exportierten SPAR-PDFs da sind (2–3 mit unterschiedlichem Inhalt: Pfand und Aktionen, Frischware, Haushaltsartikel), kommt zuerst der Parser, und zwar mit diesen als Testfällen.

## Arbeitsweise

- Zuerst Parser und Datenmodell mit echten Rechnungen als Testfällen, dann die Ansicht "Wahrscheinlich noch da", dann die Korrektur-Buttons und die Handeingabe.
- Kleine Schritte, jeder Schritt lauffähig. Vor größeren Entscheidungen kurz rückfragen.
- Sprache der Oberfläche und der Dokumentation: Deutsch.
