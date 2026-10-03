# Betrieb auf dem Server

Anleitung zum Einrichten von Nicks Kühlschrank auf einem eigenen Server unter
eigener Domain (geplant: `fridge.olomek.com`). Geschrieben für Nick und für
einen Claude, der die Einrichtung auf dem Server übernimmt.

## Aufbau

```
Internet ──443──▶ Caddy (HTTPS, Zertifikat automatisch) ──▶ app:8000 (FastAPI + SQLite)
                                                              └─ ./data/kuehlschrank.db
```

- `backend/Dockerfile`: die App (Python 3.13, Zeitzone Europe/Vienna)
- `docker-compose.yml`: App und Caddy
- `Caddyfile`: Reverse Proxy mit automatischem HTTPS für `$DOMAIN`

HTTPS ist Pflicht: Ohne HTTPS laufen weder Service Worker (Offline-Modus) noch
die Installation als App am Handy.

## Voraussetzungen

1. Docker mit Compose-Plugin (`docker compose version`)
2. DNS: A-Eintrag (und ggf. AAAA) für die Domain auf die Server-IP
3. Ports 80 und 443 (TCP, 443 auch UDP) offen und nicht von einem anderen
   Webserver belegt. **Läuft schon ein Reverse Proxy** (nginx, Traefik, ein
   anderer Caddy), den `caddy`-Dienst aus der Compose-Datei weglassen und die
   Domain im vorhandenen Proxy auf den App-Container (Port 8000) zeigen lassen.

## Einrichten

```sh
git clone https://github.com/Zidans-Haare/Schrink_Schrank.git kuehlschrank
cd kuehlschrank
echo "DOMAIN=fridge.olomek.com" > .env
docker compose up -d --build
docker compose logs -f caddy   # warten, bis das Zertifikat geholt ist
```

Prüfen:

```sh
curl -sI https://fridge.olomek.com/ | head -1          # HTTP/2 200
curl -s https://fridge.olomek.com/api/receipts | head  # []  bei leerer Datenbank
```

Das Docker-Image wurde lokal nicht gebaut (auf Nicks Mac gibt es kein Docker).
Die App selbst ist mit Python 3.14 getestet; falls der Build mit 3.13 hakt,
im Dockerfile die Python-Version anpassen.

## Daten übernehmen

Die Rechnungs-PDFs und die Datenbank liegen **nicht** im Repo (privat). Zwei Wege:

**A) Datenbank von Nicks Mac kopieren** (empfohlen, behält auch Korrekturen):

```sh
# auf dem Mac
scp backend/data/kuehlschrank.db server:kuehlschrank/data/
# auf dem Server
docker compose restart app
```

**B) PDFs neu importieren:**

```sh
# PDFs nach ./import kopieren, dann
docker compose exec app python -m app.importer /import
```

Danach kommen neue Rechnungen einfach über „+ Rechnungen“ in der App dazu.

## Zugriffsschutz

Die App hat **bewusst kein Passwort** (Nicks Entscheidung). Wer die Adresse
kennt, kann die Einkäufe sehen, Korrekturen setzen und PDFs hochladen. Soll
sich das ändern, ist der einfachste Weg Basic-Auth im `Caddyfile`:

```
{$DOMAIN} {
	basic_auth {
		nick <hash aus: docker compose exec caddy caddy hash-password>
	}
	...
}
```

Achtung: Basic-Auth und installierte PWAs vertragen sich unter iOS nicht immer
gut. Vorher mit Nick abstimmen.

## Aktualisieren

```sh
git pull
docker compose up -d --build
```

Nach Änderungen an `index.html`, Schriften oder Icons in
`backend/app/static/sw.js` die `VERSION` hochzählen, sonst sehen installierte
Apps den alten Stand erst beim zweiten Öffnen.

## Sicherung

Die gesamte App-Datenhaltung ist eine Datei: `./data/kuehlschrank.db`.
Konsistente Kopie im laufenden Betrieb, z. B. täglich per Cron:

```sh
docker compose exec -T app python -c "import sqlite3; s=sqlite3.connect('/data/kuehlschrank.db'); d=sqlite3.connect('/data/backup.db'); s.backup(d)"
```

`./data/backup.db` dann vom Server wegsichern.
